import json
import logging
import sqlite3
from jsonschema2db import JSONSchemaToPostgres
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import Flask, request, jsonify

engine = create_engine('sqlite:///server.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()

app = Flask(__name__)
# # PostgreSQL 数据库连接URL
# DATABASE_URL = "postgresql+psycopg2://username:password@localhost/mydatabase"

# # 创建连接池
# engine = create_engine(
#     DATABASE_URL,
#     pool_size=10,           # 最大连接数
#     max_overflow=20,        # 超过池大小时允许的最大溢出连接数
#     pool_timeout=30,        # 等待连接池可用连接的超时时间
#     pool_recycle=3600,      # 每个连接的最大生命周期（秒）
# )
# Session = sessionmaker(bind=engine)

@app.route('/launch_remote_sidecar', methods=['POST'])
def launchRemoteSidecar():
    data = response.json()
# if "service_config" not in data or "service_config" not in data or "service_config" not in data or "service_config" not in data or "service_config" not in data or "service_config" not in data or "service_config" not in data or


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

    json_to_pg = JSONSchemaToPostgres("localhost", schema, engine, "root_table", "http")
    print(json_to_pg.parent_relation)
    print(json_to_pg.insert_to_db({"interval": 1, "body": {"studentId": "1", "name": "1", "courses": [{"courseId": "C001", "courseName": "Mathematics", "grades": [{"examType": "Midterm1", "grade": "A"}, {"examType": "Final1", "grade": "B+"}]}, {"courseId": "C002", "courseName": "Physics", "grades": [{"examType": "Midterm", "grade": "B"}, {"examType": "Final", "grade": "A"}]}]}}, session))
    # {'loginfo': {'functionName': 'string', 'checkpointName': 'string', 'logLevel': 'string'}, 'Position': {'x': 'number', 'y': 'number', 'raw': 'number'}}