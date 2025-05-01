from sqlalchemy import Column, Float, Integer, String, Boolean, ForeignKey, CheckConstraint, JSON, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from jsonschema import Draft7Validator
from collections import deque
from jsonschema.exceptions import SchemaError
import enum


Base = declarative_base()


class JSONSchemaToSqlite3():
    def __init__(self, hostname, schema, engine, root_table_name=None, api_type=None):
        self.hostname = hostname
        self.schema = schema
        if root_table_name is None:
            self.root_table_name = hostname
        else:
            self.root_table_name = root_table_name
        self.tables_max_id = {}
        self.parent_relation = {}
        self.parent_index = {}
        self.api_type = api_type
        self.validate_schema()
        self.engine = engine
        self.orms = self.generate_basic_orm()
        self.create_tables()
        Session = sessionmaker(bind=engine)
        with Session() as session:
            self.get_tables_max_id()

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
        # 规则1：array 的 items 只有三种形式，一种为item为object的数组，一种为长度确定，指定位置为基本类型的数组，以及类型统一类型的数组。对于类型统一类型的数组如果需要限制长度，需要使用minItems和 maxItems关键字指定数组的长度。
        # 规则2：禁止使用id, parent_id, parent_index关键字
        # 规则3：不支持 oneof 或 allof 以及 additionalProperties
        # 生成规则1：如果最外层一定会生成一个表root_table_name
        # 生成规则2：如果为结构体数组，则生成table_name_item作为存储结构体的表,同时生成名为table_name的表
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
                    column_type, constraints = self.handle_enum(key, value)
                    columns[key] = Column(
                        key,
                        column_type,
                        *constraints,
                        nullable=("required" not in current_schema or key not in current_schema.get("required"))
                    )
                else:
                    # 不是 enum 类型时，使用基本类型
                    column_type = self.get_basic_type(value.get("type"))
                    columns[key] = Column(
                        key,
                        column_type,
                        nullable=("required" not in current_schema or key not in current_schema.get("required"))
                    )
        # 检查 additionalProperties 是否为 true，添加 JSON 列
        if current_schema.get("additionalProperties", False) is True:
            columns["additionalProperties"] = Column("additionalProperties", JSON, nullable=True)

        table_index = current_schema.get("x-index", False)

        self.create_and_add_orm_class(
            columns, sub_nodes,
            table_name,
            parent_table,
            orm_classes,
            node_queue,
            table_index=table_index
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
                column_name = f"{table_name}_item_{index}"
                if "enum" in item:
                    column_type, constraints = self.handle_enum(
                        f"{table_name}_item_{index}", item
                    )
                    columns[column_name] = Column(
                        column_name,
                        column_type,
                        *constraints,
                        nullable=False
                    )
                else:
                    # 不是 enum 类型时，使用基本类型
                    column_type = self.get_basic_type(item.get("type"))
                    columns[column_name] = Column(
                        column_name,
                        column_type,
                        nullable=False
                    )
                index += 1
        elif isinstance(items_schema, dict):
            if items_schema.get("type") in ["object", "array"]:
                sub_table_name = f"{table_name}_item"
                sub_nodes.append((items_schema, sub_table_name))
            else:
                column_name = f"{table_name}_item"
                if "enum" in items_schema:
                    column_type, constraints = self.handle_enum(
                        f"{table_name}_item", items_schema
                    )
                    columns[column_name] = Column(
                        column_name,
                        column_type,
                        *constraints,
                        nullable=False
                    )
                else:
                    # 不是 enum 类型时，使用基本类型
                    column_type = self.get_basic_type(items_schema.get("type"))
                    columns[column_name] = Column(
                        column_name,
                        column_type,
                        nullable=False
                    )

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
            parent_table, orm_classes, node_queue,
            table_index=False
    ):
        columns["id"] = Column("id", Integer, primary_key=True)
        if table_name == self.root_table_name:
            if self.api_type == "http":
                columns["interval"] = Column("interval", Integer)
                columns["timeout"] = Column("timeout", Integer)
                columns["status_code"] = Column("status_code", Integer)
            elif self.api_type == "unix":
                columns["interval"] = Column("interval", Integer)
        """生成 ORM 类并将子节点加入队列"""
        # 如果有父表，添加外键
        if parent_table:
            columns[f"{parent_table}_id"] = Column(f"{parent_table}_id", Integer, ForeignKey(
                f"{parent_table}.id"
            ))
            self.parent_relation[table_name] = f"{parent_table}_id"
        orm_classes[table_name] = self.create_orm_class(
            table_name, columns, table_index
        )

        # 加入子节点
        for sub_node, sub_table_name in sub_nodes:
            node_queue.append((
                sub_node,
                sub_table_name,
                table_name)
            )

    def get_basic_type(self, schema_item):
        """根据 schema 类型返回 SQLAlchemy 类型"""
        type_mapping = {
            "string": String,
            "integer": Integer,
            "boolean": Boolean,  # 可用 Integer 或 Boolean
            "float": Float,
            "number": Float
        }
        return type_mapping.get(schema_item, String)  # 默认使用 String 类型

    def handle_enum(self, key, value):
        enum_values = value.get("enum", [])
        enum_type = value.get("type", "string")  

        if enum_type == "string":
            column_type = String
        elif enum_type in ["integer", "number"]:
            column_type = Integer if enum_type == "integer" else Float
            enum_values = [str(v) for v in enum_values]  # Ensure values are stringified for CHECK constraint
        else:
            column_type = String  # Fallback to String for unsupported types

        # Generate comma-separated string for CHECK constraint
        quoted_values = [f"'{v}'" for v in enum_values]
        values_str = ','.join(quoted_values)
        # Generate CHECK constraint using simplified f-string
        check_constraint = CheckConstraint(f"{key} IN ({values_str})")
        
        return column_type, [check_constraint]

    def create_orm_class(self, table_name, columns, table_index):
        """根据字段创建 ORM 类"""
        print(table_name)
        print(columns)
        attrs = {
            '__tablename__': table_name,
            '__classname__': table_name
        }
        for column_name, column in columns.items():
            attrs[column_name] = column
        indexes = []
        if isinstance(table_index, list) and table_index:
            # 验证 x-index 中的字段是否存在
            invalid_fields = [field for field in table_index if field not in columns]
            if invalid_fields:
                raise ValueError(f"Invalid index fields for table {table_name}: {invalid_fields}")
            if len(table_index) == 1:
                # 单字段索引：idx_table_name_key
                field = table_index[0]
                indexes.append(Index(f'idx_{table_name}_{field}', field))
            else:
                # 多字段索引：idx_table_name_composite
                indexes.append(Index(f'idx_{table_name}_composite', *table_index))

        # 设置 __table_args__
        if indexes:
            attrs['__table_args__'] = tuple(indexes)
        return type(table_name, (Base,), attrs)

    def create_tables(self):
        Base.metadata.create_all(self.engine)

    def flatten_dict(self, data, schema=None):
        result = []
        cur_stack = [(data, self.root_table_name, None, self.schema)]
        next_stack = []
        while cur_stack:
            current, table_name, parent_index, current_schema = cur_stack.pop()
            self.tables_max_id[table_name] += 1
            flattened = {table_name: {}}
            additional_props = {}
            if isinstance(current, dict):
                defined_properties = current_schema.get("properties", {}).keys()
                allow_additional = current_schema.get("additionalProperties", False) is True
                for key, value in current.items():
                    if key in defined_properties:
                        if isinstance(value, dict) or isinstance(value, list):
                            # 如果值是字典，则将该字典继续添加到队列中
                            sub_schema = current_schema.get("properties", {}).get(key, {})
                            next_stack.append((value, table_name + '_' + key, self.tables_max_id[table_name], sub_schema))
                        else:
                            # 如果值是基本类型，直接添加到当前扁平化字典
                            flattened[table_name][key] = value
                    elif allow_additional:
                        additional_props[key] = value
                if parent_index is not None:
                    flattened[table_name][self.parent_relation[table_name]] = parent_index
                if allow_additional and additional_props:
                    flattened[table_name]["additionalProperties"] = additional_props

                if parent_index is not None:
                    flattened[table_name][self.parent_relation[table_name]] = parent_index
                result.append(flattened)

            elif isinstance(current, list):
                temp = {}
                same_type_flag = 1
                void_flag = 0
                data_type = type(current[0])
                items_schema = current_schema.get("items", {})
                for item in current:
                    if type(item) is not data_type:
                        same_type_flag = 0
                        break
                for item in current:
                    if isinstance(item, dict) or isinstance(item, list):
                        # 如果值是字典，则将该字典继续添加到队列中
                        next_stack.append((item, table_name + "_item", self.tables_max_id[table_name], items_schema))
                        if void_flag == 0:
                            result.append(flattened)
                            void_flag = 1
                    else:
                        if same_type_flag == 0:
                            index = 0
                            for inner_item in current:
                                temp[table_name + "_item_" + str(index)] = inner_item
                                index += 1
                            if parent_index is not None:
                                temp[self.parent_relation[table_name]] = parent_index
                            flattened[table_name] = temp
                            result.append(flattened)
                        else:
                            for inner_item in current:
                                flattened = {table_name: {table_name + "_item": inner_item}}
                                if parent_index is not None:
                                    flattened[table_name][self.parent_relation[table_name]] = parent_index
                                result.append(flattened)
                        break
            if not cur_stack and next_stack:
                temp_stack = []
                while next_stack:
                    temp_stack.append(next_stack.pop())
                while temp_stack:
                    cur_stack.append(temp_stack.pop())
        print(result)
        return result

    def preprocessing_data(self, data):
        result = self.flatten_dict(data["body"])
        del data["body"]
        orm_instances = []
        for key in data:
            result[0][self.root_table_name][key] = data[key]
        for item in result:
            for key, value in item.items():
                parent_id = None
                parent_table = None
                if "parent_index" in value:
                    parent_table = next(iter(result[value["parent_index"]]))
                    parent_id = self.tables_max_id[parent_table]
                    del value["parent_index"]
                orm_instance = self.orms[key](**value)
                if parent_id:
                    setattr(orm_instance, f"{parent_table}_id", parent_id)
                orm_instances.append(orm_instance)
        return orm_instances

    def insert_to_db(self, data):
        if (Draft7Validator(self.schema).is_valid(data.get("body"))):
            Session = sessionmaker(bind=self.engine)
            with Session() as session:
                try:
                    session.add_all(self.preprocessing_data(data))
                    session.commit()
                except Exception as e:
                    session.rollback()
                    print(f"Insert failed: {e}")
        else:
            print("valiate failed")

    def get_tables_max_id(self):
        with self.engine.connect() as connection:
            for table_name, _ in self.orms.items():
                result = connection.execute(f"SELECT MAX(id) FROM {table_name}").scalar()
                self.tables_max_id[table_name] = result if result is not None else 0

    def insert_all_to_db(self, data, protocol):
        if not isinstance(data, list):
            return "data need to be list"
        batch_size = 100  # 每批插入 100 条
        Session = sessionmaker(bind=self.engine)
        with Session() as session:
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                orm_instances = []
                for item in batch:
                    processed = {"body": item} if protocol == "redis" else item
                    orm_instances.extend(self.preprocessing_data(processed))
                try:
                    session.add_all(orm_instances)
                    session.commit()
                except Exception as e:
                    session.rollback()
                    print(f"Batch insert failed: {e}")