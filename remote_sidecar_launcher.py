import requests
import json

class RemoteSidecarLauncher():
    def __init__(
            self, service_config, control_port, ntp_address, redis_address,
            redis_port, target_redis_address, target_redis_port, remote_sidecar_launcher_ip):
        self.service_config = service_config
        self.control_port = control_port
        self.redis_address = redis_address
        self.redis_port = redis_port
        self.ntp_address = ntp_address
        self.target_redis_address = target_redis_address
        self.target_redis_port = target_redis_port
        self.remote_sidecar_launcher_ip = remote_sidecar_launcher_ip
        pass

    def launch_remote_sidecar(self):
        data = {
            "service_config": self.service_config,
            "control_port": self.control_port,
            "ntp_address": self.ntp_address,
            "redis_address": self.redis_address,
            "redis_port": self.redis_port,
            "target_redis_address": self.target_redis_address,
            "target_redis_port": self.target_redis_port
            }
        try:
            response = requests.post(self.remote_sidecar_launcher_ip, json.dumps(data))
            print(response.json())
        except Exception as e:
            print('Failed to launch remote sidecar: %s' % (e))
        pass
