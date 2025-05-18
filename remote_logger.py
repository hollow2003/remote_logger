import threading
import json
import time
import queue
from redis_client import RedisClient
from JSONSchema2ORM import JSONSchemaToORM
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from flask import Flask, request, jsonify
from remote_sidecar_launcher import RemoteSidecarLauncher

engine = create_engine('sqlite:///server.db', echo=False)
Session = sessionmaker(bind=engine)
session = Session()
app = Flask(__name__)
redisClient = RedisClient()
schema2db = {}


@app.route('/launch_remote_sidecar', methods=['POST'])
def launchRemoteSidecar():
    
    data = json.loads(request.data)
    if "service_config" not in data or\
            "control_port" not in data or\
            "ntp_address" not in data or\
            "redis_address" not in data or\
            "redis_port" not in data or\
            "target_redis_address" not in data or\
            "target_redis_port" not in data or\
            "remote_sidecar_launcher_ip" not in data or\
            "local_config_path" not in data:
        return "Missing Required Parameter"
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
            data.get("remote_sidecar_launcher_ip"))
        result_queue = queue.Queue()

        def run_and_return():
            try:
                result = remoteSidecarLauncher.launch_remote_sidecar()
                result_queue.put({"status": "success", "result": result})
            except Exception as e:
                result_queue.put({"status": "error", "msg": str(e)})

        thread = threading.Thread(target=run_and_return)
        thread.start()
        thread.join()  # 等待线程执行完毕

        result = result_queue.get()
        return jsonify(result)


@app.route('/data_synchronize', methods=['POST'])
def data_synchronize():
    data = json.loads(request.data)
    print("data syn:" + json.dumps(data))
    if "hostname" not in data or "list_key" not in data or "protocol" not in data:
        return "Missing required para!"
    else:
        result = redisClient.get_list(data["hostname"], data["list_key"])
        
        def insert_task():
            schema2db[data["hostname"]][data["list_key"]].insert_all_to_db(result, data["protocol"])
        
        import threading
        t = threading.Thread(target=insert_task)
        t.start()
        
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
            schema_path = item.get("schema")
            with open(schema_path, 'r', encoding='UTF-8') as schema_file:
                schema_content = json.load(schema_file)
            if item.get("protocol") == "unix":
                root_table_name = item.get("name") + "_" + item.get("protocol")
                dict_key = item.get("name") + "." + item.get("protocol") + "." + item.get("path")
                schema2db[load_dict.get("name")][dict_key] = JSONSchemaToORM(load_dict["name"], schema_content, engine, root_table_name=load_dict.get("name") + "_" + root_table_name, api_type="unix")
            elif item.get("protocol") == "http":
                dict_key = item.get("name") + "." + item.get("protocol") + "." + item.get("path") + "." + item.get("method")
                root_table_name = item.get("name") + "_" + item.get("protocol") + "_" + item.get("method")
                schema2db[load_dict.get("name")][dict_key] = JSONSchemaToORM(load_dict["name"], schema_content, engine, root_table_name=load_dict.get("name") + "_" + root_table_name, api_type="http")
            elif item.get("protocol") == "redis":
                root_table_name = item.get("key")
                schema2db[load_dict.get("name")][root_table_name] = JSONSchemaToORM(load_dict["name"], schema_content, engine, root_table_name=load_dict.get("name") + "_" + root_table_name, api_type="redis")


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=6400)
