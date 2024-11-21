import json
import logging
import psycopg2
import psycopg2.extras
from jsonschema2db import JSONSchemaToPostgres
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# PostgreSQL 数据库连接URL
DATABASE_URL = "postgresql+psycopg2://username:password@localhost/mydatabase"

# 创建连接池
engine = create_engine(
    DATABASE_URL,
    pool_size=10,           # 最大连接数
    max_overflow=20,        # 超过池大小时允许的最大溢出连接数
    pool_timeout=30,        # 等待连接池可用连接的超时时间
    pool_recycle=3600,      # 每个连接的最大生命周期（秒）
)
Session = sessionmaker(bind=engine)

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







    con = 1
    json_to_pg = JSONSchemaToPostgres("localhost", schema, con, "root_table", "http")
    print(json_to_pg.insert_to_db({"interval": 1, "body": {
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
  }}, con))
    # {'loginfo': {'functionName': 'string', 'checkpointName': 'string', 'logLevel': 'string'}, 'Position': {'x': 'number', 'y': 'number', 'raw': 'number'}}