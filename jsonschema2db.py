from jsonschema import Draft7Validator
from collections import deque
from jsonschema.exceptions import SchemaError
import sqlite3
from collections import deque
import enum
import json
import time


class JSONSchemaToSqlite3():
    def __init__(self, hostname, schema, db_path, root_table_name=None, api_type=None):
        self.hostname = hostname
        self.schema = schema
        if root_table_name is None:
            self.root_table_name = hostname
        else:
            self.root_table_name = root_table_name
        self.tables_max_id = {}
        self.parent_relation = {}
        self.api_type = api_type
        self.validate_schema()
        self.db_path = db_path
        self.tables = self.generate_table_definitions()
        self.create_tables()

    def validate_schema(self):
        try:
            # 验证 schema 是否符合标准
            Draft7Validator.check_schema(self.schema)
        except SchemaError as e:
            print(f"Schema 无效: {e.message}")

    def generate_table_definitions(self):
        """生成表定义，基于 JSON Schema"""
        node_queue = deque([(self.schema, self.root_table_name, None)])
        tables = {}

        while node_queue:
            columns = {}
            sub_nodes = []
            current_schema, table_name, parent_table = node_queue.popleft()

            schema_type = current_schema.get("type")

            if schema_type == "object":
                self.process_object_type(
                    current_schema, columns, sub_nodes, table_name,
                    parent_table, tables, node_queue
                )
            elif schema_type == "array":
                self.process_array_type(
                    current_schema, columns, sub_nodes, table_name,
                    parent_table, tables, node_queue
                )

        return tables

    def process_object_type(
            self, current_schema, columns, sub_nodes, table_name,
            parent_table, tables, node_queue
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
                columns[key] = column_type
        additional_properties = current_schema.get("additionalProperties", False)
        if additional_properties:
            columns["additionalProperties"] = "TEXT"  # 存储额外属性的 JSON 字符串
        self.add_table_definition(columns, sub_nodes, table_name, parent_table, tables, node_queue)

    def process_array_type(
            self, current_schema, columns, sub_nodes,
            table_name, parent_table, tables, node_queue
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
                columns[f"{table_name}_item_{index}"] = column_type
                index += 1
        elif isinstance(items_schema, dict):
            if items_schema.get("type") in ["object", "array"]:
                sub_table_name = f"{table_name}_item"
                sub_nodes.append((items_schema, sub_table_name))
            else:
                if "enum" in items_schema:
                    column_type = self.handle_enum(
                        f"{table_name}_item", items_schema
                    )
                else:
                    # 不是 enum 类型时，使用基本类型
                    column_type = self.get_basic_type(items_schema.get("type"))
                columns[f"{table_name}_item"] = column_type

        self.add_table_definition(columns, sub_nodes, table_name, parent_table, tables, node_queue)

    def add_table_definition(self, columns, sub_nodes, table_name, parent_table, tables, node_queue):
        """添加表定义，包括主键和外键"""
        columns["id"] = "INTEGER PRIMARY KEY"
        if table_name == self.root_table_name:
            if self.api_type == "http":
                columns["interval"] = "INTEGER"
                columns["timeout"] = "INTEGER"
                columns["status_code"] = "INTEGER"
            elif self.api_type == "unix":
                columns["interval"] = "INTEGER"
        if parent_table:
            columns[f"{parent_table}_id"] = "INTEGER"
            self.parent_relation[table_name] = f"{parent_table}_id"
        tables[table_name] = columns

        for sub_node, sub_table_name in sub_nodes:
            node_queue.append((sub_node, sub_table_name, table_name))

    def get_basic_type(self, schema_item):
        """根据 schema 类型返回 SQLAlchemy 类型"""
        type_mapping = {
            "string": "TEXT",
            "integer": "INTEGER",
            "boolean": "TEXT",  # 可用 Integer 或 Boolean
            "float": "REAL",
            "number": "INTEGER"
        }
        return type_mapping.get(schema_item, "TEXT")  # 默认使用 String 类型

    def handle_enum(self, key, value):
        enum_values = value.get("enum", [])
        if enum_values:
            # 生成 CHECK 约束的条件
            conditions = []
            for v in enum_values:
                if isinstance(v, str):
                    # 转义字符串中的单引号
                    escaped_v = v.replace("'", "''")
                    conditions.append(f"'{escaped_v}'")
                elif isinstance(v, (int, float)):
                    # 数字直接转为字符串
                    conditions.append(str(v))
                elif isinstance(v, bool):
                    # 布尔值转为 1 或 0
                    conditions.append("1" if v else "0")
                else:
                    raise ValueError(f"不支持的枚举类型: {type(v)}")
            check_constraint = f"CHECK ({key} IN ({', '.join(conditions)}))"
            return f"TEXT {check_constraint}"
        return "TEXT"

    def create_tables(self):
        """使用纯 SQLite 创建表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for table_name, columns in self.tables.items():
            column_defs = []
            for col_name, col_type in columns.items():
                if col_name == "id":
                    column_def = f"{col_name} {col_type}"
                elif col_name.endswith("_id"):
                    ref_table = col_name[:-3]
                    column_def = f"{col_name} INTEGER REFERENCES {ref_table}(id)"
                else:
                    column_def = f"{col_name} {col_type}"
                column_defs.append(column_def)
            create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({', '.join(column_defs)})"
            cursor.execute(create_table_sql)

        conn.commit()
        conn.close()

    def flatten_dict(self, data):
        result = []
        cur_stack = [(data, self.schema, self.root_table_name, None)]
        next_stack = []
        while cur_stack:
            current, current_schema, table_name, parent_index = cur_stack.pop()
            self.tables_max_id[table_name] = self.tables_max_id.get(table_name, 0) + 1
            flattened = {table_name: {}}
            additional_props = {}

            if isinstance(current, dict):
                defined_properties = current_schema.get("properties", {}).keys()
                for key, value in current.items():
                    if key in defined_properties:
                        if isinstance(value, dict) or isinstance(value, list):
                            sub_schema = current_schema["properties"][key]
                            next_stack.append((value, sub_schema, f"{table_name}_{key}", self.tables_max_id[table_name]))
                        else:
                            if isinstance(value, bool):  # 检查是否为布尔值
                                value = 'true' if value else 'false'  # 转换为字符串
                            flattened[table_name][key] = value
                    else:
                        additional_props[key] = value

                if additional_props:
                    flattened[table_name]["additionalProperties"] = json.dumps(additional_props)

                if parent_index is not None:
                    flattened[table_name][self.parent_relation[table_name]] = parent_index
                result.append(flattened)
            # 处理数组类型（保持原有逻辑）
            elif isinstance(current, list):
                temp = {}
                same_type_flag = 1
                void_flag = 0
                data_type = type(current[0]) if current else None
                for item in current:
                    if type(item) is not data_type:
                        same_type_flag = 0
                        break
                for item in current:
                    if isinstance(item, dict) or isinstance(item, list):
                        sub_schema = current_schema.get("items", {})
                        next_stack.append((item, sub_schema, f"{table_name}_item", self.tables_max_id[table_name]))
                        if void_flag == 0:
                            if parent_index is not None:
                                temp[self.parent_relation[table_name]] = parent_index
                            flattened[table_name] = temp
                            result.append(flattened)
                            void_flag = 1
                    else:
                        if same_type_flag == 0:
                            index = 0
                            for inner_item in current:
                                if isinstance(inner_item, bool):  # 检查是否为布尔值
                                    inner_item = 'true' if inner_item else 'false'  # 转换为字符串
                                temp[f"{table_name}_item_{index}"] = inner_item
                                index += 1
                            if parent_index is not None:
                                temp[self.parent_relation[table_name]] = parent_index
                            flattened[table_name] = temp
                            result.append(flattened)
                        else:
                            for inner_item in current:
                                if isinstance(inner_item, bool):  # 检查是否为布尔值
                                    inner_item = 'true' if inner_item else 'false'  # 转换为字符串
                                flattened = {table_name: {f"{table_name}_item": inner_item}}
                                if parent_index is not None:
                                    flattened[table_name][self.parent_relation[table_name]] = parent_index
                                result.append(flattened)
                        break
            if not cur_stack and next_stack:
                cur_stack, next_stack = next_stack, []
        return result

    def preprocessing_data(self, data):
        result = self.flatten_dict(data["body"])
        del data["body"]
        for key in data:
            result[0][self.root_table_name][key] = data[key]
        return result

    def insert_to_db(self, data):
        if not Draft7Validator(self.schema).is_valid(data.get("body")):
            print("验证失败")
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        start_time = time.time()
        records = self.preprocessing_data(data)
        for item in records:
            for table_name, record in item.items():
                if record:
                    columns = ", ".join(record.keys())
                    placeholders = ", ".join("?" * len(record))
                    insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                    cursor.execute(insert_sql, list(record.values()))
                else:
                    columns = "id"
                    placeholders = "?"
                    insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                    cursor.execute(insert_sql, [None])  # 使用 None 让 SQLite 自动填充 id
                    
        conn.commit()
        conn.close()

    def get_tables_max_id(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        for table_name in self.tables.keys():
            cursor.execute(f"SELECT MAX(id) FROM {table_name}")
            result = cursor.fetchone()[0]
            self.tables_max_id[table_name] = result if result is not None else 0

        conn.close()

    def insert_all_to_db(self, data, protocol):
        if not isinstance(data, list):
            return "数据需要是列表类型"
        global total_preprocess_time
        records = []
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('PRAGMA foreign_keys = ON')
        for i in range(len(data)):
            if protocol == "redis":
                records += self.preprocessing_data({"body": data[i]})
            else:
                records += self.preprocessing_data(data[i])
        for item in records:
            for table_name, record in item.items():
                if record:
                    columns = ", ".join(record.keys())
                    placeholders = ", ".join("?" * len(record))
                    insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                    cursor.execute(insert_sql, list(record.values()))
                else:
                    columns = "id"
                    placeholders = "?"
                    insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})"
                    cursor.execute(insert_sql, [None])  # 使用 None 让 SQLite 自动填充 id
                    
        conn.commit()
        conn.close()
