import json
import logging
import psycopg2
import psycopg2.extras
from jsonschema2db import JSONSchemaToPostgres

# 配置日志记录
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger()

if __name__ == '__main__':
    # 加载 JSON schema
    schema = {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "name": {
        "type": "string"
      },
      "age": {
        "type": "integer"
      }
    },
    "required": ["name", "age"]
  }
}










    json_to_pg = JSONSchemaToPostgres("localhost", schema, "root_table")
    # {'loginfo': {'functionName': 'string', 'checkpointName': 'string', 'logLevel': 'string'}, 'Position': {'x': 'number', 'y': 'number', 'raw': 'number'}}