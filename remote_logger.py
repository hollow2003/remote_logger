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
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "studentId": {
      "type": "string"
    },
    "name": {
      "type": "string"
    },
    "courses": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "courseId": {
            "type": "string"
          },
          "courseName": {
            "type": "string"
          },
          "grades": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "examType": {
                  "type": "string"
                },
                "grade": {
                  "type": "string"
                }
              },
              "required": ["examType", "grade"]
            }
          }
        },
        "required": ["courseId", "courseName", "grades"]
      }
    }
  },
  "required": ["studentId", "name", "courses"]
}








    json_to_pg = JSONSchemaToPostgres("localhost", schema, "root_table")
    print(json_to_pg.flatten_dict({
  "studentId": "S12345",
  "name": "Alice",
  "courses": [
    {
      "courseId": "C001",
      "courseName": "Mathematics",
      "grades": [
        {
          "examType": "Midterm",
          "grade": "A"
        },
        {
          "examType": "Final",
          "grade": "B+"
        }
      ]
    },
    {
      "courseId": "C002",
      "courseName": "Physics",
      "grades": [
        {
          "examType": "Midterm",
          "grade": "B"
        },
        {
          "examType": "Final",
          "grade": "A"
        }
      ]
    }
  ]
}))
    # {'loginfo': {'functionName': 'string', 'checkpointName': 'string', 'logLevel': 'string'}, 'Position': {'x': 'number', 'y': 'number', 'raw': 'number'}}