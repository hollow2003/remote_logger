import socket
import struct
import time


class NtpServer():
    def __init__(self, ntp_server_address, ntp_server_port):
        self.ntp_server_address = ntp_server_address
        self.ntp_server_port = ntp_server_port

    def start_ntp_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server.bind(self.ntp_server_address, self.ntp_server_port)
        print("NTP 服务器正在运行...")
        while True:
            data, address = server.recvfrom(1024)
            print(f"收到来自 {address} 的请求")  # 打印请求的地址
            if data:
                # 获取当前时间，并转换为NTP时间戳
                T2 = int(time.time()) + 2208988800  # 当前时间（NTP时间）
                print(f"服务器发送的时间戳 T2: {T2}")
                response = b'\x1b' + 47 * b'\0'  # 初始化NTP响应包
                # 填充原始时间戳
                orig_time = struct.unpack('!I', data[40:44])[0]  # 从请求中提取原始时间戳
                print(f"客户端请求的原始时间戳: {orig_time}")
                # 填充响应包
                # 填充原始时间戳
                response = response[:32] + struct.pack('!I', T2) + response[36:]  # 填充发送时间戳
                T3 = int(time.time()) + 2208988800  # 当前时间（NTP时间）
                response = response[:40] + struct.pack('!I', T3) + response[44:]
                print(f"发送的响应包: {response}")
                # 发送响应
                server.sendto(response, address)
                print(f"发送响应到 {address}")
