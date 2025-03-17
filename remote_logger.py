import threading
import json
import time
from redis_client import RedisClient
from jsonschema2db import JSONSchemaToSqlite3
from flask import Flask, request
from remote_sidecar_launcher import RemoteSidecarLauncher

dbpath = 'server.db'

app = Flask(__name__)
redisClient = RedisClient()
schema2db = {}


@app.route('/launch_remote_sidecar', methods=['POST'])
def launch_remote_sidecar():
    data = json.loads(request.data)
    required_parameters = [
        "service_config", "control_port", "ntp_address", "redis_address", "redis_port",
        "target_redis_address", "target_redis_port", "remote_sidecar_launcher_ip", "local_config_path"
    ]
    missing_parameters = [param for param in required_parameters if param not in data]
    if missing_parameters:
        return "Missing Required Parameter: " + ", ".join(missing_parameters)
    else:
        load_config_file(data.get("local_config_path"))
        remoteSidecarLauncher = RemoteSidecarLauncher(
            data.get("service_config"),
            data.get("control_port"),
            data.get("ntp_address"),
            data.get("redis_address"),
            data.get("redis_port"),
            data.get("target_redis_address"),
            data.get("target_redis_port"),
            data.get("remote_sidecar_launcher_ip")
        )
        threading.Thread(target=remoteSidecarLauncher.launch_remote_sidecar, args=()).start()
        return "success"


@app.route('/data_synchronize', methods=['POST'])
def data_synchronize():
    data = json.loads(request.data)
    print("data syn:" + json.dumps(data))
    if "hostname" not in data or "list_key" not in data or "protocol" not in data:
        return "Missing required para!"
    else:
        result = redisClient.get_list(data["hostname"], data["list_key"])
        schema2db[data["hostname"]][data["list_key"]].insert_all_to_db(result, data["protocol"])
        return "Syn Data Success"


@app.route('/delete_host_config', methods=['POST'])
def delete_host_config():
    data = json.loads(request.data)
    if "hostname" not in data:
        return "Missing required para!"
    elif data.get("hostname") not in schema2db:
        return "host not found"
    else:
        del schema2db[data.get("hostname")]
        return "del success"


def load_config_file(config_file_path):
    with open(config_file_path, 'r', encoding='UTF-8') as f:
        load_dict = json.load(f)
        if "name" not in load_dict or "API" not in load_dict:
            print("Missing required para in config file")
            return "Missing required para in config file"
        if load_dict.get("name") in schema2db:
            return
        schema2db[load_dict.get("name")] = {}
        for item in load_dict["API"]:
            if item.get("protocol") == "unix":
                root_table_name = item.get("name") + "_" + item.get("protocol")
                dict_key = item.get("name") + "." + item.get("protocol") + "." + item.get("path")
                schema2db[load_dict.get("name")][dict_key] = JSONSchemaToSqlite3(load_dict["name"], item.get("schema"), dbpath, root_table_name=load_dict.get("name") + "_" + root_table_name, api_type="unix")
            elif item.get("protocol") == "http":
                dict_key = item.get("name") + "." + item.get("protocol") + "." + item.get("path") + "." + item.get("method")
                root_table_name = item.get("name") + "_" + item.get("protocol") + "_" + item.get("method")
                schema2db[load_dict.get("name")][dict_key] = JSONSchemaToSqlite3(load_dict["name"], item.get("schema"), dbpath, root_table_name=load_dict.get("name") + "_" + root_table_name, api_type="http")
            elif item.get("protocol") == "redis":
                root_table_name = item.get("key")
                schema2db[load_dict.get("name")][root_table_name] = JSONSchemaToSqlite3(load_dict["name"], item.get("schema"), dbpath, root_table_name=load_dict.get("name") + "_" + root_table_name, api_type="redis")
        print(schema2db)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=6400)
