# REMOTE logger手册
------
## 1. 简介
* 本项目旨在开发一种基于灵活数据规范的可配置的边缘计算日志采集系统。该系统的主要架构如下图所示。![系统整体架构图](https://github.com/hollow2003/edge_sidecarlogger/blob/using_thread/pics/c72dbcd1ca4e3e255cd4a03cc63f21b.png)该仓库代码用于作为中心日志收集端配合sidecar_logger使用。
### 1.1. jsonschema2db
* 该模块用于将**json schema**转换为数据库表结构并创建表，以及将数据进行处理后存入数据库，具体的算法如下。
#### 1.1.1. **json schema**转换为数据库表结构算法伪代码
```python
function generate_basic_orm(schema, root_table_name, api_type, engine):
    orm_classes = {}
    queue = [(schema, root_table_name, None)]
    
    while queue is not empty:
        current_schema, table_name, parent_table = queue.dequeue()
        
        if current_schema["type"] == "object":
            process_object_type(current_schema, table_name, parent_table, orm_classes, queue)
        else if current_schema["type"] == "array":
            process_array_type(current_schema, table_name, parent_table, orm_classes, queue)

    return orm_classes

function process_object_type(current_schema, table_name, parent_table, orm_classes, queue):
    columns = {}
    for key, value in current_schema["properties"]:
        if value["type"] in ["object", "array"]:
            queue.append((value, table_name + "_" + key, table_name))
        else:
            column_type = get_column_type(value)
            columns[key] = create_column(key, column_type)

    create_orm_class(columns, table_name, orm_classes, parent_table)

function process_array_type(current_schema, table_name, parent_table, orm_classes, queue):
    columns = {}
    if isinstance(items_schema, list):
        for index, item in enumerate(current_schema["items"]):
            column_type = get_column_type(item)
            columns[table_name + "_item_" + index] = create_column(table_name + "_item_" + index, column_type)
     elif isinstance(items_schema, dict):
        if items_schema.get("type") in ["object", "array"]:
            sub_table_name = f"{table_name}_item"
            sub_nodes.append((items_schema, sub_table_name))
    create_orm_class(columns, table_name, orm_classes, parent_table)

function create_orm_class(columns, table_name, orm_classes, parent_table):
    columns["id"] = create_column("id", Integer)
    if parent_table:
        columns[parent_table + "_id"] = create_column(parent_table + "_id", Integer, foreign_key=True)
    orm_classes[table_name] = type(table_name, (Base,), columns)
```
这个算法主要基于树的广度优先遍历实现。以下为主要的流程。
（1）首先在**generate_basic_orm**中实现的主要是层序遍历，将对象或列表类型存入队列**queue**中，每次弹出一个进行类型判断。
（2-1）如果最外层为对象，则进入**process_object_type**进行处理，具体为遍历其下的所有**properties**，如果为一般数据类型，则直接添加至这个对象对应的表中；否则，同样将其存入该层需要递归的队列**queue**中。无论哪种情况，都会创建一个表用于连接。
（2-2）如果最外层为列表，则进入**process_array_type**进行处理，具体为首先判断遍历**items**的类型，如果为列表，则为一般列表处理，其下的所有**items**项为一般数据类型（此处暂不支持一般项与对象共存的情况），直接添加至这个对象对应的表中。如果为字典，则其内容为列表或对象，将其再次添加进入队列**queue**中。无论哪种情况，都会创建一个表用于连接。
#### 1.1.2. 处理数据算法伪代码
```python
function preprocessing_data(data, schema, orm_classes):
    flattened_data = flatten_dict(data["body"])
    remove_key(data, "body")
    
    orm_instances = []
    for key, value in flattened_data:
        orm_instance = create_orm_instance(key, value, orm_classes)
        if "parent_index" in value:
            parent_id = get_parent_id(value["parent_index"], flattened_data)
            set_parent_id(orm_instance, parent_id)
        orm_instances.append(orm_instance)
        increment_table_max_id(key)
    
    return orm_instances

function flatten_dict(data):
    // 初始化栈进行扁平化
    cur_stack = [(data, root_table_name, None)]
    next_stack = []

    result = []
    while cur_stack is not empty:
        current, table_name, parent_index = cur_stack.pop()

        if type(current) is dict:
            flattened = flatten_dict_object(current, table_name, parent_index)
            add_sub_nodes_to_stack(current, table_name, next_stack)
            result.append(flattened)
        else if type(current) is list:
            flattened = flatten_dict_list(current, table_name, parent_index)
            add_sub_nodes_to_stack(current, table_name, next_stack)
            result.append(flattened)

        if cur_stack is empty and next_stack is not empty:
            // 交换栈
            cur_stack = next_stack
            next_stack = []

    return result

function flatten_dict_object(current, table_name, parent_index):
    flattened = {table_name: {}}
    for key, value in current.items():
        if type(value) is dict or type(value) is list:
            next_stack.append((value, table_name + "_" + key, table_name))
        else:
            flattened[table_name][key] = value

    if parent_index is not None:
        flattened[table_name][parent_relation[table_name]] = parent_index

    return flattened

function flatten_dict_list(current, table_name, parent_index):
    flattened = {table_name: []}
    for item in current:
        if type(item) is dict or type(item) is list:
            next_stack.append((item, table_name + "_item", table_name))
        else:
            flattened[table_name].append(item)

    if parent_index is not None:
        flattened[table_name][parent_relation[table_name]] = parent_index

    return flattened
```
这个算法基于树的广度优先算法实现，这主要是由于需要父子节点的关系（外键联系），因此在插入数据时应先插入父节点，再插入子节点，采用广度优先可以保证扁平化后数据父节点在前子节点在后。。以下为主要的流程。
（1）首先在**flatten_dict**中实现的主要是层序遍历，将当前层对象或列表类型存入队列**cur_stack**中，每次弹出一个进行类型判断。
（2-1）如果最外层为对象，则进入**flatten_dict_object**进行处理，具体为遍历其下的所有**properties**，如果为一般数据类型，则直接添加至这个数据对应的列表中；否则，同样将其存入下一层层需要递归的队列**next_stack**中。
（2-2）如果最外层为列表，则进入**flatten_dict_list**进行处理，具体为首先判断遍历**items**的类型，如果为一般数据类型，直接添加至这个对象对应的字典中。如果为列表或对象，将其再次添加存入下一层层需要递归的队列**next_stack**。
## 2. 环境配置
本环境配置是基于**centos7** **python 3.8.3**进行介绍的。使用pip进行python包管理。
```bash
sudo pip3 install redis
sudo pip3 install SQLAlchemy
sudo pip3 install jsonschema
sudo pip3 install flask
```
## 3. demo使用
### 3.1. 使用的配置文件
```json
{
   "id": 123456,
   "kind": "Ability",
   "name": "moving_robot",
   "process": "/usr/bin/python3.8 main.py",
   "port": 10800,
   "locate": {
      "address": "192.168.114.128",
      "MAC": "00:00:00:00:00:00"
   },
   "API": [
      {
         "name": "unix",
         "protocol": "unix",
         "path": "/home/hpr/consul/services/robot",
         "flushInterval": 1,
         "bufferSize": 4096,
         "maxMsgNum": 10,
         "logLevel": "DEBUG",
         "schema":{
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                  "loginfo": {
                     "type": "object",
		     "properties":{
			 "functionName": {
			      "type": "string",
			      "description": "需要记录日志的函数名",
			      "examples": ["checkSystemStatus"]
			   },
			   "checkpointName": {
			      "type": "string",
			      "description": "检查点名称",
			      "examples": ["初始化"]
			   },
			   "logLevel": {
			      "type": "string",
			      "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
			      "description": "日志级别",
			      "default": "INFO"
			   }
		     },
		     "additionalProperties": false,
		     "required": [
		 	   "functionName",
		 	   "checkpointName"
		      ]
                   },
                  "Position": {
                     "type": "object",
                     "properties": {
                           "x": {
                              "type": "number"
                           },
                           "y": {
                              "type": "number"
                           },
                           "raw": {
                              "type": "number"
                           }
                     },
                     "additionalProperties": false,
                     "required": [
                           "x",
                           "y",
                           "raw"
                     ]
                  }
            },
            "additionalProperties": false,
            "required": [
                  "logInfo",
                  "Position"
            ]
         },
         "message": "{functionName} 在 {checkpointName} 检查点时位于: x: {position.x}, y: {position.y} raw: {position.raw}"
      },
      {
         "name": "redis",
         "protocol": "redis",
         "port": "6379",
         "key": "moving_robot",
         "method": "LPOP",
         "flushInterval": 1,
         "bufferSize": 4096,
         "maxMsgNum": 10,
         "schema":{
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                  "loginfo": {
                     "type": "object",
		     "properties":{
			 "functionName": {
			      "type": "string",
			      "description": "需要记录日志的函数名",
			      "examples": ["checkSystemStatus"]
			   },
			   "checkpointName": {
			      "type": "string",
			      "description": "检查点名称",
			      "examples": ["初始化"]
			   },
			   "logLevel": {
			      "type": "string",
			      "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
			      "description": "日志级别",
			      "default": "INFO"
			   }
		     },
		     "additionalProperties": false,
		     "required": [
		 	   "functionName",
		 	   "checkpointName"
		      ]
                   },
                  "Position": {
                     "type": "object",
                     "properties": {
                           "x": {
                              "type": "number"
                           },
                           "y": {
                              "type": "number"
                           },
                           "raw": {
                              "type": "number"
                           }
                     },
                     "additionalProperties": false,
                     "required": [
                           "x",
                           "y",
                           "raw"
                     ]
                  }
            },
            "additionalProperties": false,
            "required": [
                  "loginfo",
                  "Position"
            ]
         },
         "message": "{functionName} 在 {checkpointName} 检查点时位于:  x: {position.x}, y: {position.y} raw: {position.raw}"
      },
      {
         "name": "http",
         "protocol": "http",
         "method": "GET",
         "port": "10800",
         "path": "/heartbeat",
         "interval": 1,
         "timeout": 5,
         "bufferSize": 1024,
         "maxMsgNum": 10,
         "logLevel": "INFO",
         "schema":{
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
               "status": {
                  "type": "string",
                  "enum": ["OK", "ERROR"],
                  "description": "心跳状态"
               }
            },
            "additionalProperties": false,
            "required": [
               "status"
            ]
        },
         "message": "{functionName} 在 {checkpointName} 检查点: {status}"
      }
   ]
}
```
### 3.2. 生成的数据库结构
见https://github.com/hollow2003/remote_logger/blob/master/print.pdf。
