# REMOTE logger手册
------
## 1. 简介
* 本项目旨在开发一种基于灵活数据规范的可配置的边缘计算日志采集系统。该系统的主要架构如下图所示。![系统整体架构图](https://github.com/hollow2003/edge_sidecarlogger/blob/main/pics/%E6%97%A5%E5%BF%97%E9%87%87%E9%9B%86%E7%B3%BB%E7%BB%9F%E6%95%B4%E4%BD%93%E6%9E%B6%E6%9E%84%E5%9B%BE.png)该仓库代码用于作为中心日志收集端配合sidecar_logger使用。
### 1.1. jsonschema2db
* 该模块用于将**json schema**转换为数据库表结构并创建表，以及将数据进行处理后存入数据库，具体的算法如下。
#### 1.1.1. **json schema**转换为数据库表结构算法伪代码
```python
算法 1: GenerateBasicOrm (S, T, H, A)
输入：S ∈ Schema（灵活数据规范Schema），T ∈ String（根表名），H ∈ String（主机名），A ∈ String（API类型，可选）
输出：C ∈ Dict<String, ORMClass>（表定义集合，键为表名，值为ORM类）
复杂度：时间复杂度 O(|S|)（遍历Schema节点），空间复杂度 O(|S|)（队列和ORM类存储）
1  Q ← ∅; // 初始化空双端队列Q，用于遍历Schema节点 
2  T_root ← T if T ≠ ∅ else H; // 设置根表名，默认为主机名 
3  Q.enqueue((S, T_root, ∅)); // 加入初始Schema、根表名和空父表 
4  C ← ∅; // 初始化空字典C存储ORM类 
5      while ¬Q.isEmpty() do // 层序遍历直至队列为空 
6          (S_current, T_current, P_parent) ← Q.dequeue(); // 取出Schema、表名、父表 
7          if type(S_current) = "object" then
8              ProcessObjectType(S_current, T_current, P_parent, Q, C, A); // 处理对象
9          else if type(S_current) = "array" then
10             ProcessArrayType(S_current, T_current, P_parent, Q, C, A); // 处理数组
11 return C; // 返回表定义集合
```
```python
算法 2:ProcessObjectType(S, T, P, Q, C, A)
输入：S ∈ Schema（object类型Schema），T ∈ String（表名），P ∈ String（父表名），Q ∈ Queue<(Schema, String, String)>（待处理队列），C ∈ Dict<String, ORMClass>（表定义集合），A ∈ String（API类型，可选）
输出：无（更新Q和C）
复杂度：时间复杂度 O(|S.properties|)（遍历属性），空间复杂度 O(|S.properties|)（列和子节点存储）
1  D ← ∅; // 初始化列定义字典 
2  N ← ∅; // 初始化子节点列表
3  for (key, value) ∈ S.properties do // 遍历对象属性 
4      if type(value) ∈ {"object", "array"} then 
5          T_sub ← T + "_" + key; // 生成子表名 
6          N.append((value, T_sub)); // 加入子节点 
7      else 
8          if "enum" ∈ value then 
9              (type, constraints) ← HandleEnum(key, value); // 处理枚举 
10         else 
11             type ← GetBasicType(value.type); // 映射基本类型 
12     D[key] ← Column(type, constraints, nullable=¬(key ∈ S.required)); // 添加列 
13 if S.additionalProperties = true then 
14     D["additionalProperties"] ← Column(JSON, nullable=true); // 添加JSON列 
15 I ← S.x-index; // 获取索引定义 
16 CreateAndAddORMClass(D, N, T, P, Q, C, I, A); // 创建表定义
```
```python
算法 3:ProcessArrayType(S, T, P, Q, C, A)
输入：S ∈ Schema（array类型Schema），T ∈ String（表名），P ∈ String（父表名），Q ∈ Queue<(Schema, String, String)>（待处理队列），C ∈ Dict<String, ORMClass>（表定义集合），A ∈ String（API类型，可选）
输出：无（更新Q和C）
复杂度：时间复杂度 O(|S.items|)（遍历items），空间复杂度 O(S.items)（列和子节点存储）
1  D ← ∅; // 初始化列定义字典 
2  N ← ∅; // 初始化子节点列表 
3  items ← S.items; // 获取数组items 
4  if type(items) = list then 
5      for i, item ∈ enumerate(items) do // 遍历列表型items 
6          key ← T + "_item_" + str(i); 
7          if "enum" ∈ item then 
8              (type, constraints) ← HandleEnum(key, item); 
9          else 
10             type ← GetBasicType(item.type); 
11         D[key] ← Column(type, constraints, nullable=false); // 添加列 
12 else if type(items) = dict then 
13     if items.type ∈ {"object", "array"} then 
14         T_sub ← T + "_item"; // 生成子表名 
15         N.append((items, T_sub)); // 加入子节点 
16     else 
17         key ← T + "_item"; 
18         if "enum" ∈ items then 
19             (type, constraints) ← HandleEnum(key, items); 
20         else 
21             type ← GetBasicType(items.type); 
22         D[key] ← Column(type, constraints, nullable=false); // 添加列 
23 CreateAndAddORMClass(D, N, T, P, Q, C, ∅, A); // 创建表定义
```
```python
算法 4:CreateAndAddOrmClass(D, N, T, P, Q, C, I, A)
输入：D ∈ Dict<String, Column>（列定义），N ∈ List<(Schema, String)>（子节点）， T ∈ String（表名），P ∈ String（父表名）， Q ∈ Queue<(Schema, String, String)>（待处理队列）， C ∈ Dict<String, ORMClass>（表定义集合），I ∈ List<String>（索引字段）， A ∈ String（API类型）
输出：无（更新C和Q） 
复杂度：时间复杂度 O(|D| + |N|)（处理列和子节点），空间复杂度 O(|D| + |N|)
1  D["id"] ← Column(Integer, primary_key=true); // 添加主键 
2  if T = T_root then 
3      if A = "http" then 
4          D["interval"] ← Column(Integer); 
5          D["timeout"] ← Column(Integer); 
6          D["status_code"] ← Column(Integer); 
7      else if A = "unix" then 
8          D["interval"] ← Column(Integer); 
9  if P ≠ ∅ then 
10     D[P + "_id"] ← Column(Integer, ForeignKey(P + ".id")); // 添加外键 
11     parent_relation[T] ← P + "_id"; // 记录父子关系 
12 C[T] ← CreateORMClass(T, D, I); // 生成ORM类 
13 for (S_sub, T_sub) ∈ N do 
14     Q.enqueue((S_sub, T_sub, T)); // 加入子节点
```
```python
算法 5:CreateOrmClass(T, D, I)
输入：T ∈ String（表名），D ∈ Dict<String, Column>（列定义），I ∈ List<String>（索引字段） 
输出：O ∈ ORMClass（ORM类） 
复杂度：时间复杂度 O(|D| + |I|)（处理列和索引），空间复杂度 O(|D| + |I|）
1  attrs ← {"__tablename__": T, "__classname__": T}; // 初始化ORM属性 
2  for (key, column) ∈ D do 
3      attrs[key] ← column; // 添加列定义 
4  indexes ← ∅; // 初始化索引列表 
5  if I ≠ ∅ then 
6      for field ∈ I do 
7          if field ∉ D then 
8              raise ValueError("Invalid index field: " + field); 
9      if |I| = 1 then 
10         indexes.append(Index("idx_" + T + "_" + I[0], I[0])); // 单字段索引 
11     else 
12         indexes.append(Index("idx_" + T + "_composite", I)); // 复合索引 
13 if indexes ≠ ∅ then 
14     attrs["__table_args__"] ← tuple(indexes); // 设置索引 
15 O ← type(T, (Base,), attrs); // 创建ORM类 
16 return O;
```
&emsp;&emsp;这个算法主要基于树的广度优先遍历实现。以下为主要的流程。\
&emsp;&emsp;算法首先通过GenerateTableDefinitions方法初始化一个全局双端队列node_queue，用于层序遍历 Schema 结构，队列中的每个元素包含当前Schema 片段、表名和父表名，同时维护一个全局集合orm_classes存储生成的ORM类定义。接着，根据Schema类型分别处理：对于object类型，遍历其properties，将基本类型映射为列，处理枚举约束和可空性，复杂类型生成子表并加入待处理队列，动态字段则添加JSON列，索引信息也被提取；对于array类型，若items是列表，则为每项生成列，若是字典，则根据类型生成单列或子表。随后，通过CreateAndAddOrmClass生成ORM类，为每张表添加主键id，根表添加额外字段，有父表时添加外键并记录关系，同时处理索引。最后，当队列为空时GenerateBasicOrm返回orm_classes，CreateTables调用Base.metadata.create_all 创建表结构，ORM 框架自动添加外键约束，完成转换。
#### 1.1.2. 处理数据算法伪代码
```python
算法 6:FlattenDict(D, S, T, R, P)
输入：D ∈ JSON（输入JSON数据），S ∈ Schema（JSON Schema），T ∈ String（根表名）， R ∈ Dict<String, Integer>（表最大ID记录），P ∈ Dict<String, String>（父子关系） 
输出：L ∈ List<Dict<String, Dict<String, Any>>>（扁平化表数据列表） 
复杂度：时间复杂度 O(|D|)（遍历JSON节点），空间复杂度 O(|D|)（队列和结果存储）
1  cur_stack ← ∅; // 初始化当前层队列 
2  next_stack ← ∅; // 初始化下一层队列 
3  L ← ∅; // 初始化结果列表 
4  cur_stack.push((D, T, ∅, S)); // 加入初始数据、根表名、空父索引和Schema 
5  while ¬cur_stack.isEmpty() do // 层序遍历 
6      (D_current, T_current, I_parent, S_current) ← cur_stack.pop(); // 取出数据、表名、父索引、Schema 
7      R[T_current] ← R[T_current] + 1; // 递增表 ID 
8      M ← {T_current: ∅}; // 初始化当前表字典 
9      if type(D_current) = "dict" then // 处理对象 
10         P_defined ← S_current.properties.keys; // 获取定义属性 
11         A_allowed ← S_current.additionalProperties; // 检查动态字段 
12         A_props ← ∅; // 初始化动态字段字典 
13         for (key, value) ∈ D_current do 
14             if key ∈ P_defined then 
15                 if type(value) ∈ {"dict", "list"} then 
16                     T_sub ← T_current + "_" + key; // 生成子表名 
17                     next_stack.push((value, T_sub, R[T_current], 
18                                     S_current.properties[key])); 
19                 else 
20                     M[T_current][key] ← value; // 添加基本类型 
21             else if A_allowed then 
22                 A_props[key] ← value; // 存储动态字段 
23         if A_allowed and A_props ≠ ∅ then 
24             M[T_current]["additionalProperties"] ← A_props; // 添加JSON字段 
25         if I_parent ≠ ∅ then 
26             M[T_current][P[T_current]] ← I_parent; // 添加父表外键 
27         L.append(M); // 添加到结果 
28     else if type(D_current) = "list" then // 处理数组 
29         if is_same_type(D_current) then // 检查元素类型一致性 
30             for item ∈ D_current do 
31                 M_temp ← {T_current: {T_current + "_item": item}}; // 生成单一列
32                 if I_parent ≠ ∅ then 
33                     M_temp[T_current][P[T_current]] ← I_parent; 
34                 L.append(M_temp); 
35         else 
36             for i, item ∈ enumerate(D_current) do 
37                 if type(item) ∈ {"dict", "list"} then 
38                     next_stack.push((item, T_current + "_item", 
39                                     R[T_current], S_current.items)); 
40                 else 
41                     M[T_current][T_current + "_item_" + str(i)] ← item; // 多列 
42             if I_parent ≠ ∅ then 
43                 M[T_current][P[T_current]] ← I_parent; 
44             L.append(M); 
45     if cur_stack.isEmpty() and ¬next_stack.isEmpty() then 
46         cur_stack ← next_stack; // 切换到下一层 
47         next_stack ← ∅; 
48 return L; // 返回扁平化结果
```
```python
算法 7:PreprocessingData(D, L, C, R, P)
输入：D ∈ Dict（输入数据，含body和额外字段）， C ∈ Dict<String, ORMClass>（表定义集合），R ∈ Dict<String, Integer>（表最大ID记录）， P ∈ Dict<String, String>（父子关系） 
输出：O ∈ List<ORMInstance>（ORM实例列表） 
复杂度：时间复杂度 O(|L|)（遍历扁平化数据），空间复杂度 O(|L|)（ORM实例存储）
1  L ← flatten_dict(D["body"], S); // 扁平化body数据 
2  O ← ∅; // 初始化ORM实例列表 
3  for key, value ∈ D do // 处理额外字段（如interval） 
4      if key ≠ "body" then
5          L[0][T_root][key] ← value; // 合并到根表 
6  for M ∈ L do // 遍历扁平化数据 
7      for T, V ∈ M do // 遍历表数据 
8          I_parent ← ∅; // 初始化父表ID 
9          P_table ← ∅; // 初始化父表名 
10         if P[T] ∈ V then 
11             P_table ← parent_table_from(P[T]); // 获取父表名 
12             I_parent ← R[P_table]; // 获取父表ID 
13             delete V[P[T]]; // 删除父索引 
14         O_instance ← C[T](V); // 创建ORM实例 
15         if I_parent ≠ ∅ then 
16         O_instance[P[T]] ← I_parent; // 设置外键 
17         O.append(O_instance); // 添加到结果 
18 return O; // 返回ORM实例列表
```
&emsp;&emsp;这个算法基于树的广度优先算法实现，这主要是由于需要父子节点的关系（外键联系），因此在插入数据时应先插入父节点，再插入子节点，采用广度优先可以保证扁平化后数据父节点在前子节点在后。。以下为主要的流程。\
&emsp;&emsp;算法以JSON数据和对应的JSON Schema为输入，通过层序遍历维护一个当前层对象队列，存储待处理的数据实体及其关联的表名、父表索引和Schema。每次迭代从队列中弹出一个元素，根据其类型选择处理路径。若队列为空，则完成扁平化处理。\
&emsp;&emsp;对于对象类型数据，算法遍历其属性，检查是否在Schema的 properties中定义。对于定义的属性，若为基本类型，直接添加到当前表的扁平化字典；若为对象或数组，生成子表名，并将其加入下一层队列以递归处理。若Schema允许additionalProperties，未定义属性存储为JSON格式的additionalProperties字段。若存在父表关联，添加父表外键至字典。\
&emsp;&emsp;对于数组类型数据，算法分析数组元素的类型一致性。若元素类型一致，为每个元素生成单一列，并创建独立的扁平化字典；若类型不一致，为每个元素生成独立列。若元素为对象或数组，生成子表名，加入next_stack递归处理。父表外键同样记录至字典。\
&emsp;&emsp;完成扁平化后，算法返回包含所有表数据的字典列表。PreprocessingData方法将这些字典转换为ORM实例。对于根表数据，合并额外字段；对于子表数据，设置父表外键。最终生成ORM实例列表，供数据库插入使用。
## 2. 环境配置
&emsp;&emsp;本环境配置是基于**centos7** **python 3.8.3**进行介绍的。使用pip进行python包管理。
```shell
sudo pip3 install redis
sudo pip3 install SQLAlchemy
sudo pip3 install jsonschema
sudo pip3 install flask
```
&emsp;&emsp;仓库中也包含了requirements.txt，可以直接通过该文件一键安装所需要的py库。
```shell
sudo pip3 install -r requestments.txt
```
## 3. demo使用
### 3.1. 使用的配置文件
```json
{
    "id": 123456,
    "kind": "Ability",
    "name": "moving_robot",
    "process": "python3 main.py",
    "port": 10800,
    "locate": {
        "address": "192.168.239.129",
        "MAC": "00:00:00:00:00:00"
    },
    "API": [
    {
        "name": "unix",
        "protocol": "unix",
        "path": "/home/hpr/mock_robot/robot",
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
                    "x-index": [["logLevel"]],
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
                    "x-index": [["logLevel"]],
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
