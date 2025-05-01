import unittest
import sqlite3
from jsonschema import Draft7Validator
from jsonschema2db import JSONSchemaToSqlite3  # 替换为你的模块名
from collections import deque
from sqlalchemy import create_engine
database_path = "sqlite:///test.db"  # SQLite 数据库文件路径
engine = create_engine(database_path, echo=False)
class TestJSONSchemaToSqlite3(unittest.TestCase):
    def setUp(self):
        # 创建内存数据库
        self.engine = "test.db"
        self.simple_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#", 
            "type": "object", 
            "properties": {
                "list1":{
                    "type": "array", "items":[
                        {"type": "number"}, {"type": "string"}, {"type": "boolean"}
                    ]
                }, 
                "list2":{
                    "type": "array", 
                    "items": {
                        "type": "object", 
                        "properties": {
                            "name": {
                                "type": "string", "enum": ["name1", "name2"]
                            }
                        }
                    }
                }, 
                "list3": {
                    "type": "array", 
                    "items": { "type": "number" }
                },
                "normal1": {"type": "number" }, 
                "normal2": {"type": "string" }, 
                "object1": {
                    "type": "object", 
                    "properties": {
                        "name": {
                            "type": "string" 
                        },
                        "normal3": {"type": "boolean" }
                    },
                    "additionalProperties": True
                }
            }, 
            "required": ["normal1"]
        }
        self.simple_data = {
            "body": {
                "list1":[1, "1", False], 
                "list2":[
                    {"name": "name1"}, 
                    {"name": "name2"}
                ],
                "list3": [1, 2, 3], 
                "normal1": 1, 
                "normal2": "1", 
                "object1": {
                    "name": "name3",
                    "normal3": True,
                    "notInclude": "add"
                }
            }
        }

    # def test_generate_table_definitions_simple(self):
    #     js = JSONSchemaToSqlite3("test", self.simple_schema, self.engine, api_type="http")
    #     tables = js.generate_table_definitions()
        # self.assertIn("test", tables)
        # self.assertEqual(tables["test"]["name"], "TEXT")
        # self.assertEqual(tables["test"]["age"], "INTEGER")
        # self.assertEqual(tables["test"]["id"], "INTEGER PRIMARY KEY")

    # def test_generate_table_definitions_nested(self):
    #     nested_schema = {
    #         "type": "object",
    #         "properties": {
    #             "user": {
    #                 "type": "object",
    #                 "properties": {"id": {"type": "integer"}}
    #             }
    #         }
    #     }
    #     js = JSONSchemaToSqlite3("test2", nested_schema, self.engine)
    #     tables = js.generate_table_definitions()
    #     self.assertIn("test2_user", tables)
    #     self.assertIn("test2_id", tables["test2_user"])

    # def test_process_object_type(self):
    #     js = JSONSchemaToSqlite3("test", self.simple_schema, self.engine)
    #     columns = {}
    #     sub_nodes = []
    #     js.process_object_type(self.simple_schema, columns, sub_nodes, "test", None, {}, deque())
    #     self.assertEqual(columns["name"], "TEXT")
    #     self.assertEqual(columns["age"], "INTEGER")
    #     self.assertEqual(len(sub_nodes), 0)

    # def test_process_array_type(self):
    #     array_schema = {
    #         "type": "array",
    #         "items": [{"type": "string"}, {"type": "integer"}]
    #     }
    #     js = JSONSchemaToSqlite3("test", array_schema, self.engine)
    #     columns = {}
    #     sub_nodes = []
    #     js.process_array_type(array_schema, columns, sub_nodes, "test", None, {}, deque())
    #     self.assertEqual(columns["test_item_0"], "TEXT")
    #     self.assertEqual(columns["test_item_1"], "INTEGER")
    
    # def test_add_table_definition_root(self):
    #     js = JSONSchemaToSqlite3("test", self.simple_schema, self.engine, api_type="http")
    #     columns = {}
    #     sub_nodes = []
    #     tables = {}
    #     js.add_table_definition(columns, sub_nodes, "test", None, tables, deque())
    #     self.assertIn("id", tables["test"])
    #     self.assertIn("interval", tables["test"])

    # def test_get_basic_type(self):
    #     js = JSONSchemaToSqlite3("test", self.simple_schema, self.engine)
    #     self.assertEqual(js.get_basic_type("string"), "TEXT")
    #     self.assertEqual(js.get_basic_type("integer"), "INTEGER")
    #     self.assertEqual(js.get_basic_type("unknown"), "TEXT")

    # def test_handle_enum(self):
    #     js = JSONSchemaToSqlite3("test", self.simple_schema, self.engine)
    #     enum_schema = {"enum": ["red", "blue"]}
    #     result = js.handle_enum("color", enum_schema)
    #     self.assertIn("CHECK (color IN ('red', 'blue'))", result)

    # def test_create_tables(self):
    #     js = JSONSchemaToSqlite3("test", self.simple_schema, self.engine)
    #     js.create_tables()
    #     conn = sqlite3.connect(":memory:")
    #     cursor = conn.cursor()
    #     cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    #     tables = cursor.fetchall()
    #     self.assertIn(("test",), tables)

    # def test_flatten_dict(self):
    #     js = JSONSchemaToSqlite3("test", self.simple_schema, self.engine)
    #     result = js.flatten_dict(self.simple_data["body"])
    #     print(result)

    # def test_preprocessing_data(self):
    #     js = JSONSchemaToSqlite3("test", self.simple_schema, self.engine)
    #     data = {"body": {"name": "Alice"}, "extra": "value"}
    #     result = js.preprocessing_data(data)
    #     self.assertEqual(result[0]["test"]["extra"], "value")

    def test_insert_to_db(self):
        js = JSONSchemaToSqlite3("test", self.simple_schema, self.engine)
        js.create_tables()
        js.insert_to_db(self.simple_data)

    # def test_get_tables_max_id(self):
    #     js = JSONSchemaToSqlite3("test", self.simple_schema, self.engine)
    #     js.create_tables()
    #     js.insert_to_db(self.simple_data)
    #     js.get_tables_max_id()
    #     self.assertEqual(js.tables_max_id["test"], 1)
    
    # def test_insert_all_to_db(self):
    #     js = JSONSchemaToSqlite3("test", self.simple_schema, self.engine)
    #     js.create_tables()
    #     data_list = [{"body": {"name": "Alice", "age": 25}}]
    #     js.insert_all_to_db(data_list, "redis")
    #     conn = sqlite3.connect(":memory:")
    #     cursor = conn.cursor()
    #     cursor.execute("SELECT COUNT(*) FROM test")
    #     result = cursor.fetchone()[0]
    #     self.assertEqual(result, 1)
    
if __name__ == "__main__":
    #unittest.main()
    simple_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#", 
            "type": "object", 
            "properties": {
                "list1":{
                    "type": "array", 
                    "items":[
                        {"type": "number"}, {"type": "string"}, {"type": "boolean"}
                    ]
                }, 
                "list2":{
                    "type": "array", 
                    "items": {
                        "type": "object", 
                        "properties": {
                            "name": {
                                "type": "string", "enum": ["name1", "name2"]
                            }
                        }
                    }
                }, 
                "list3": {
                    "type": "array", 
                    "items": { "type": "number" }
                },
                "normal1": {"type": "number" }, 
                "normal2": {"type": "string" }, 
                "object1": {
                    "type": "object", 
                    "properties": {
                        "name": {
                            "type": "string" 
                        },
                        "normal3": {"type": "boolean" }
                    },
                    "additionalProperties": True,
                    "x-index": ["name"]
                }
            }, 
            "required": ["normal1"],
            "x-index": ["normal1", "normal2"]
        }
    simple_data = {
        "body": {
            "list1":[1, "1", False], 
            "list2":[
                {"name": "name1"}, 
                {"name": "name2"}
            ],
            "list3": [1, 2, 3], 
            "normal1": 1, 
            "normal2": "1", 
            "object1": {
                "name": "name3",
                "normal3": True,
                "notInclude": "add"
            }
        }
    }
    js = JSONSchemaToSqlite3("root_table", simple_schema, engine)
    js.create_tables()
    js.insert_all_to_db(simple_data, "http")