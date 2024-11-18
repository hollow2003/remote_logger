from sqlalchemy import Column, Float, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base
from jsonschema import Draft7Validator
from collections import deque
from jsonschema.exceptions import SchemaError


Base = declarative_base()


class JSONSchemaToPostgres():
    def __init__(self, hostname, schema, root_table_name=None):
        self.hostname = hostname
        self.schema = schema
        if root_table_name is None:
            self.root_table_name = hostname
        else:
            self.root_table_name = root_table_name
        self.validate_schema()
        self.required_fields = {}
        self.orms = self.generate_orm()

    def validate_schema(self):
        try:
            # 验证 schema 是否符合标准
            Draft7Validator.check_schema(self.schema)
            print("Schema 是有效的标准 Schema")
        except SchemaError as e:
            print(f"Schema 无效: {e.message}")

    # def schema_to_tree(self, schema=None, parent_name=None, required=None):
    #     # 不支持 oneof 或 allof
    #     if schema is None:
    #         schema = self.schema
    #     if parent_name is None:
    #         parent_name = "root"
    #     if required is None:
    #         required = []
    #     if schema["type"] == "object":
    #         properties_tree = {}
    #         for prop_name, prop_schema in schema['properties'].items():
    #             properties_tree[prop_name] = self.schema_to_tree(prop_schema, prop_name, schema.get("required"))
    #         return properties_tree
    #     elif schema["type"] == "array":
    #         items_tree = []
    #         if isinstance(schema.get("items"), dict):
    #             items_tree.append(self.schema_to_tree(schema['items'], parent_name, schema.get("required")))
    #             return items_tree
    #         elif isinstance(schema.get("items"), list):
    #             for item_schema in schema['items']:
    #                 items_tree.append(self.schema_to_tree(item_schema, parent_name, schema.get("required")))
    #             return items_tree
    #     elif "type" in schema:
    #         if parent_name in required:
    #             return {"type": schema["type"], "required": True}
    #         else:
    #             return {"type": schema["type"], "required": False}
    #     return None

    # def print_tree(self, tree=None, indent=0):
    #     if tree is None:
    #         tree = self.schema_tree
    #     # 如果树是字典类型
    #     if isinstance(tree, dict):
    #         for key, value in tree.items():
    #             print(' ' * indent + f"{key}:")
    #             self.print_tree(value, indent + 2)  # 缩进增加，表示层级
    #     # 如果树是列表类型
    #     elif isinstance(tree, list):
    #         for i, item in enumerate(tree):
    #             print(' ' * indent + f"Item {i}:")
    #             self.print_tree(item, indent + 2)
    #     # 否则，打印值
    #     else:
    #         print(' ' * indent + str(tree))  # 这里是正确的：打印树节点的值

    # def generate_orm(self):
    #     # 只允许结构体数组(items 为字典，可以包含其他基本类型)，最外层只为结构体
    #     # 如果为"items":[]则里面只能为基本类型
    #     queue = deque([(self.schema, self.root_table_name, None)])
    #     orm_classes = {}
    #     while queue:
    #         columns = {}
    #         sub_nodes = []
    #         current_schema, table_name, parent_table = queue.popleft()
    #         if current_schema.get("type") == "object":  # 如果是对象类型
    #             for key, value in current_schema.get("properties", {}).items():
    #                 if value.get("type") == "object" or value.get("type") == "array":
    #                     # 递归处理嵌套的 object 类型
    #                     sub_table_name = f"{table_name}_{key}"
    #                     sub_nodes.append((value, sub_table_name))
    #                 else:
    #                     # 处理基本类型
    #                     columns[key] = Column(key, self.get_basic_type(value.get("type")))
    #             if columns:
    #                 columns["id"] = Column("id", Integer, primary_key=True)
    #                 if parent_table is not None:
    #                     columns[f"{parent_table}_id"] = ForeignKey(f"{parent_table}.id")
    #                     orm_classes[parent_table + "_" + table_name] = self.create_orm_class(parent_table + "_" + table_name, columns)
    #                 else:
    #                 # 创建 ORM 类
    #                     orm_classes[table_name] = self.create_orm_class(table_name, columns)

    #                 # 将子节点加入队列
    #                 for sub_node, sub_table_name in sub_nodes:
    #                     queue.append((sub_node, sub_table_name, table_name))
    #             else:
    #                 for sub_node, sub_table_name in sub_nodes:
    #                     queue.append((sub_node, sub_table_name, None))

    #         elif current_schema.get("type") == "array":  # 如果是数组类型

    #             if type(current_schema.get("items")) == list:
    #                 index = 0
    #                 for item in current_schema.get("items", []):
    #                     columns[table_name + "_item_" + str(index)] = Column(table_name + "_item_" + str(index), self.get_basic_type(item.get("type")), nullable=False)
    #                     index += 1
    #             else:
    #                 if "type" in current_schema.get("items"):
    #                     if current_schema.get("items").get("type") == "object" or current_schema.get("items").get("type") == "array":
    #                         sub_table_name = table_name
    #                         sub_nodes.append((current_schema.get("items"), sub_table_name))
    #             if columns:
    #                 columns["id"] = Column("id", Integer, primary_key=True)
    #                 if parent_table is not None:
    #                     columns[f"{parent_table}_id"] = ForeignKey(f"{parent_table}.id")
    #                     orm_classes[parent_table + "_" + table_name] = self.create_orm_class(parent_table + "_" + table_name, columns)
    #                 else:
    #                 # 创建 ORM 类
    #                     orm_classes[table_name] = self.create_orm_class(table_name, columns)
    #                 # 将子节点加入队列
    #                 for sub_node, sub_table_name in sub_nodes:
    #                     queue.append((sub_node, sub_table_name, table_name))
    #             else:
    #                 for sub_node, sub_table_name in sub_nodes:
    #                     queue.append((sub_node, sub_table_name, None))
    #     return orm_classes

    def generate_orm(self):
        # 初始化队列进行层序遍历，存储表格及其父表的相关信息
        # 不支持 oneof 或 allof
        # 如果"items" :[]，则[]内只能为基础类型
        # 如果最外层为array，且"items" : {}，为结构体列表，则会先产生一个root_table_name只包含id，
        # 还有一个root_table_root_table_item包含结构体
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
                columns[key] = Column(
                    key,
                    self.get_basic_type(value.get("type")),
                    nullable=(key not in current_schema.get("required"))
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
                columns[f"{table_name}_item_{index}"] = Column(
                    f"{table_name}_item_{index}",
                    self.get_basic_type(item.get("type")),
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
        """生成 ORM 类并将子节点加入队列"""
        if columns:
            columns["id"] = Column("id", Integer, primary_key=True)

            # 如果有父表，添加外键
            if parent_table:
                columns[f"{parent_table}_id"] = ForeignKey(
                    f"{self.root_table_name}.id"
                )
                orm_classes[
                    f"{parent_table}_{table_name}"
                ] = self.create_orm_class(
                    f"{parent_table}_{table_name}", columns
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
                    self.root_table_name)
                )

        else:
            if table_name == self.root_table_name:
                columns["id"] = Column("id", Integer, primary_key=True)
                orm_classes[table_name] = self.create_orm_class(
                    table_name,
                    columns
                )
            for sub_node, sub_table_name in sub_nodes:
                node_queue.append((
                    sub_node,
                    sub_table_name,
                    self.root_table_name
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

    def create_orm_class(self, table_name, columns):
        """根据字段创建 ORM 类"""
        print(table_name)
        print(columns)
        attrs = {
            '__tablename__': table_name,
            '__classname__': table_name
        }
        for column_name, column_type in columns.items():
            attrs[column_name] = column_type
        return type(table_name, (Base,), attrs)
