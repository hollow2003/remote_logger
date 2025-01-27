import redis
import json


class RedisClient():
    def __init__(self):
        self.client = redis.Redis(host='localhost', port=6379, decode_responses=True)

    def get_list(self, host, list_key):
        key = host + "/" + list_key
        tmp = self.client.lpop(key)
        result = []
        while tmp:
            print(tmp)
            result.append(json.loads(tmp))
            tmp = self.client.lpop(key)
        return result
