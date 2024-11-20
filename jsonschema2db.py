from sqlalchemy import Column, Float, Integer, String, Boolean, Enum, ForeignKey
from sqlalchemy.orm import declarative_base
from jsonschema import Draft7Validator
from collections import deque
from jsonschema.exceptions import SchemaError
import enum


Base = declarative_base()


class JSONSchemaToPostgres():
    def __init__(self, hostname, schema, root_table_name=None, api_type=None):
        self.hostname = hostname
        self.schema = schema
        if root_table_name is None:
            self.root_table_name = hostname
        else:
            self.root_table_name = root_table_name
        self.api_type = api_type
        self.validate_schema()
        self.orms = self.generate_basic_orm()
        
    def validate_schema(self):
        try:
            # 验证 schema 是否符合标准
            Draft7Validator.check_schema(self.schema)
            print("Schema 是有效的标准 Schema")
        except SchemaError as e:
            print(f"Schema 无效: {e.message}")

    def generate_basic_orm(self):
        # 初始化队列进行层序遍历，存储表格及其父表的相关信息，仅使用基本类型
        # 以下规则中，非基本类型指的是 array 或 object
        # 规则1：array 的 items 只有两种形式，一种为结构体数组，一种为指定位置为基本类型的数组
        # 规则2：禁止使用id关键字
        # 规则3：不支持 oneof 或 allof 以及 additionalProperties
        # 生成规则1：如果最外层一定会生成一个表root_table_name
        # 生成规则2：如果为结构体数组，则不会生成对应的表，而是生成table_name_item作为存储结构体的表
        # 生成规则3：如果结构体内没有基本类型，则不会生成table_name，而是继续处理内部的非基本类型
        node_queue = deque([(self.schema, self.root_table_name, None)])
        orm_classes = {}

        while node_queue:
            columns = {}
            sub_nodes = []
            current_schema, table_name, parent_table = node_queue.popleft()

            schema_type = current_schema.get("type")

            if schema_type == "object":
                self.process_object_type(
                    current_schema,
                    columns, sub_nodes,
                    table_name,
                    parent_table,
                    orm_classes,
                    node_queue
                )

            elif schema_type == "array":
                self.process_array_type(
                    current_schema,
                    columns,
                    sub_nodes,
                    table_name,
                    parent_table,
                    orm_classes,
                    node_queue
                )

        return orm_classes

    def process_object_type(
            self, current_schema, columns, sub_nodes, table_name,
            parent_table, orm_classes, node_queue
    ):
        """处理对象类型 schema"""
        for key, value in current_schema.get("properties", {}).items():
            if value.get("type") in ["object", "array"]:
                sub_table_name = f"{table_name}_{key}"
                sub_nodes.append((value, sub_table_name))
            else:
                if "enum" in value:
                    column_type = self.handle_enum(key, value)
                else:
                    # 不是 enum 类型时，使用基本类型
                    column_type = self.get_basic_type(value.get("type"))
                columns[key] = Column(
                    key,
                    column_type,
                    nullable=("required" not in current_schema or key not in current_schema.get("required"))
                )

        self.create_and_add_orm_class(
            columns, sub_nodes,
            table_name,
            parent_table,
            orm_classes,
            node_queue
        )

    def process_array_type(
            self, current_schema, columns, sub_nodes,
            table_name, parent_table, orm_classes, node_queue
    ):
        """处理数组类型 schema"""
        items_schema = current_schema.get("items")
        if isinstance(items_schema, list):
            index = 0
            for item in items_schema:
                if "enum" in item:
                    column_type = self.handle_enum(
                        f"{table_name}_item_{index}", item
                    )
                else:
                    # 不是 enum 类型时，使用基本类型
                    column_type = self.get_basic_type(item.get("type"))
                columns[f"{table_name}_item_{index}"] = Column(
                    f"{table_name}_item_{index}",
                    column_type,
                    nullable=False
                )
                index += 1
        elif isinstance(items_schema, dict):
            if items_schema.get("type") in ["object", "array"]:
                sub_table_name = f"{table_name}_item"
                sub_nodes.append((items_schema, sub_table_name))

        self.create_and_add_orm_class(
            columns,
            sub_nodes,
            table_name,
            parent_table,
            orm_classes,
            node_queue
        )

    def create_and_add_orm_class(
            self, columns, sub_nodes, table_name,
            parent_table, orm_classes, node_queue
    ):
        columns["id"] = Column("id", Integer, primary_key=True)
        if table_name == self.root_table_name:
            if self.api_type == "http":
                columns["interval"] = Column("interval", Integer)
                columns["timeout"] = Column("timeout", Integer)
                columns["status_code"] = Column("status_code", Integer)
        """生成 ORM 类并将子节点加入队列"""
        if columns:
            # 如果有父表，添加外键
            if parent_table:
                columns[f"{parent_table}_id"] = ForeignKey(
                    f"{parent_table}.id"
                )
                orm_classes[
                    table_name
                ] = self.create_orm_class(
                    table_name, columns
                )
            else:
                orm_classes[table_name] = self.create_orm_class(
                    table_name,
                    columns
                )

            # 加入子节点
            for sub_node, sub_table_name in sub_nodes:
                node_queue.append((
                    sub_node,
                    sub_table_name,
                    table_name)
                )

        else:
            orm_classes[table_name] = self.create_orm_class(
                    table_name,
                    columns
                )
            for sub_node, sub_table_name in sub_nodes:
                node_queue.append((
                    sub_node,
                    sub_table_name,
                    parent_table
                    )
                )

    def get_basic_type(self, schema_item):
        """根据 schema 类型返回 SQLAlchemy 类型"""
        type_mapping = {
            "string": String,
            "integer": Integer,
            "boolean": Boolean,  # 可用 Integer 或 Boolean
            "float": Float
        }
        return type_mapping.get(schema_item, String)  # 默认使用 String 类型

    def handle_enum(self, key, value):
        """
        Handles enum types.
        """
        enum_values = value.get("enum", [])
        enum_type = value.get("type", "string")  
        # Default to string type for enum

        if enum_type == "string":
            EnumType = enum.Enum(
                f"{key.capitalize()}_Enum", enum_values, type=str
            )
        elif enum_type == "integer":
            # If enum is of integer type
            enum_values = [int(v) for v in enum_values]
            EnumType = enum.Enum(
                f"{key.capitalize()}_Enum", enum_values, type=int
            )
        elif enum_type == "number":
            # If enum is of number type
            enum_values = [float(v) for v in enum_values]
            EnumType = enum.Enum(
                f"{key.capitalize()}_Enum", enum_values, type=float
            )

        # Return SQLAlchemy Enum type
        return Enum(EnumType)

    def create_orm_class(self, table_name, columns):
        """根据字段创建 ORM 类"""
        print(table_name)
        print(columns)
        attrs = {
            '__tablename__': table_name,
            '__classname__': table_name
        }
        for column_name, column in columns.items():
            attrs[column_name] = column
        return type(table_name, (Base,), attrs)

    def flatten_dict(self, data):
        result = []
        stack = [(data, self.root_table_name, None)]
        index = -1
        while stack:
            current, table_name, parent_index = stack.pop()
            if isinstance(current, dict):
                flattened = {table_name: {}}
                for key, value in current.items():
                    if isinstance(value, dict) or isinstance(value, list):
                        # 如果值是字典，则将该字典继续添加到队列中
                        stack.append((value, table_name + '_' + key, index))
                    else:
                        # 如果值是基本类型，直接添加到当前扁平化字典
                        flattened[table_name][key] = value
                if flattened[table_name] != {} or table_name == self.root_table_name:
                    # 将当前层的扁平字典添加到结果中
                    if parent_index is not None:
                        flattened[table_name]["parent_index"] = parent_index
                    result.append(flattened)
                    index += 1
            elif isinstance(current, list):
                flattened = {}
                temp = []
                for item in current:
                    if isinstance(item, dict) or isinstance(item, list):
                        # 如果值是字典，则将该字典继续添加到队列中
                        stack.append((item, table_name + "_item", index))
                    else:
                        temp.append(item)
                if temp != []:
                    flattened[table_name] = temp
                if flattened != {}:
                    # 将当前层的扁平字典添加到结果中
                    if parent_index is not None:
                        flattened[table_name]["parent_index"] = parent_index
                    result.append(flattened)
                    index += 1
        return result

    def insert_to_db(self, data, con):
        result = self.flatten_dict(data["body"])
        del data["body"]
        cur = con.cursor()
        orm_instances = []
        for key in data:
            result[0][self.root_table_name][key] = data[key]
        for item in result:
            for key, value in item.items():
                parent_id = 1
                parent_table = None
                if "parent_index" in value:
                    parent_table = next(iter(result[value["parent_index"]]))
                    cur.execute(f"SELECT MAX(id) FROM {parent_table}")
                    parent_id = cur.fetchone()[0]
                    del value["parent_index"]
                orm_instance = self.orms[key](**value)
                if parent_table:
                    setattr(orm_instance, parent_table, parent_id)
                orm_instances.append(orm_instance)
        return orm_instances
