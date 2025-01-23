import threading
import json
from redis_client import RedisClient
from jsonschema2db import JSONSchemaToSqlite3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import Flask, request
from remote_sidecar_launcher import RemoteSidecarLauncher

engine = create_engine('sqlite:///server.db', echo=True)
Session = sessionmaker(bind=engine)
session = Session()
app = Flask(__name__)
redisClient = RedisClient()
schema2db = {}

@app.route('/launch_remote_sidecar', methods=['POST'])
def launchRemoteSidecar():
    data = request.json()
    if "service_config" not in data or\
            "control_port" not in data or\
            "ntp_address" not in data or\
            "redis_address" not in data or\
            "redis_port" not in data or\
            "target_redis_address" not in data or\
            "target_redis_port" not in data or\
            "remote_sidecar_launcher_ip" not in data:
        return "Missing Required Parameter"
    else:
        remoteSidecarLauncher = RemoteSidecarLauncher(
            data.get("service_config"),
            data.get("control_port"),
            data.get("ntp_address"),
            data.get("redis_address"),
            data.get("redis_port"),
            data.get("target_redis_address"),
            data.get("target_redis_port"),
            data.get("remote_sidecar_launcher_ip"))
        threading.Thread(target=remoteSidecarLauncher.launch_remote_sidecar, args=()).start()


@app.route('/data_synchronize', methods=['POST'])
def data_synchronize():
    data = json.loads(request.data)
    if "hostname" not in data or "list_key" not in data:
        return "Missing required para!"
    else:
        result = redisClient.get_list(data["hostname"], data["list_key"])
        threading.Thread(target=schema2db[data["hostname"]][data["list_key"]].insert_all_to_db, args=(result, session)).start()
        return "Syn Data Success"


def load_config_file(config_file_path):
    with open(config_file_path, 'r', encoding='UTF-8') as f:
        load_dict = json.load(f)
        if "name" not in load_dict or "API" not in load_dict:
            print("Missing required para in config file")
            return "Missing required para in config file"
        schema2db[load_dict.get("name")] = {}
        for item in load_dict["API"]:
            if item.get("protocol") == "unix":
                root_table_name = item.get("name") + "_" + item.get("protocol")
                dict_key = item.get("name") + "." + item.get("protocol") + "." + item.get("path")
                schema2db[load_dict.get("name")][dict_key] = JSONSchemaToSqlite3(load_dict["name"], item.get("schema"), engine, root_table_name=load_dict.get("name") + "_" + root_table_name)
            elif item.get("protocol") == "http":
                dict_key = item.get("name") + "." + item.get("protocol") + "." + item.get("path") + "." + item.get("method")
                root_table_name = item.get("name") + "_" + item.get("protocol") + item.get("method")
                schema2db[load_dict.get("name")][dict_key] = JSONSchemaToSqlite3(load_dict["name"], item.get("schema"), engine, root_table_name=load_dict.get("name") + "_" + root_table_name)
            elif item.get("protocol") == "redis":
                root_table_name = item.get("key")
                schema2db[load_dict.get("name")][root_table_name] = JSONSchemaToSqlite3(load_dict["name"], item.get("schema"), engine, root_table_name=load_dict.get("name") + "_" + root_table_name)


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
    load_config_file('/home/hpr/consul/remote_logger/test.json')
    print(schema2db)
    # print(json_to_pg.insert_to_db({"interval": 1, "body": {"studentId": "1", "name": "1", "courses": [{"courseId": "C001", "courseName": "Mathematics", "grades": [{"examType": "Midterm1", "grade": "A"}, {"examType": "Final1", "grade": "B+"}]}, {"courseId": "C002", "courseName": "Physics", "grades": [{"examType": "Midterm", "grade": "B"}, {"examType": "Final", "grade": "A"}]}]}}, session))
    # {'loginfo': {'functionName': 'string', 'checkpointName': 'string', 'logLevel': 'string'}, 'Position': {'x': 'number', 'y': 'number', 'raw': 'number'}}
    app.run(host="0.0.0.0", port=6400)
