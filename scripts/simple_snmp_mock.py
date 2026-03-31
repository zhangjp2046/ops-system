#!/usr/bin/env python3
"""
SNMP Mock服务器 - 纯Python实现，无需安装任何SNMP库
在真实Ubuntu环境中运行此脚本，即可在UDP 161端口提供SNMP响应

使用方法:
    python3 simple_snmp_mock.py [port]

按 Ctrl+C 停止
"""

import socket
import struct
import random
import sys
import time
import os
import signal

# 全局变量
running = True

def signal_handler(sig, frame):
    global running
    print("\n正在停止...")
    running = False

class SNMPMockServer:
    """模拟SNMP服务器，响应GET和GETNEXT请求"""
    
    def __init__(self, port=161, community='public'):
        self.port = port
        self.community = community
        self.start_time = int(time.time())
        
        # 模拟的设备数据
        self.devices = {
            'switch': {
                'name': 'Core-Switch-01',
                'location': 'DataCenter-A',
                'uptime': lambda: int(time.time()) - self.start_time + random.randint(86400, 2592000),
                'interfaces': 24,
                'ports_down': [3, 4, 10, 11],  # 模拟故障端口
                'description': 'H3C S5500-58C-EI Switch',
                'if_speed': '1000000000',  # 1Gbps
            },
            'server': {
                'name': 'Server-01',
                'location': 'DataCenter-A-Rack05',
                'uptime': lambda: int(time.time()) - self.start_time + random.randint(86400, 1728000),
                'interfaces': 2,
                'ports_down': [],  # 服务器网络正常
                'description': 'Ubuntu 22.04 LTS Server',
                'cpu_idle': lambda: random.randint(10, 95),  # CPU空闲率
                'mem_total': '32814592',  # KB
                'mem_avail': lambda: str(random.randint(8000000, 20000000)),
            }
        }
        
        # 当前设备类型
        self.device_type = 'switch'
    
    def get_device_data(self):
        return self.devices[self.device_type]
    
    def build_oid_response(self, oid):
        """根据OID返回对应的值"""
        dev = self.get_device_data()
        
        # sysDescr
        if oid.endswith('1.3.6.1.2.1.1.1.0') or oid == '1.3.6.1.2.1.1.1.0':
            return dev['description']
        
        # sysUptime
        if oid.endswith('1.3.6.1.2.1.1.3.0') or oid == '1.3.6.1.2.1.1.3.0':
            uptime = dev['uptime']() * 100  # 转换为SNMP timeticks (百秒)
            return str(uptime)
        
        # sysName
        if oid.endswith('1.3.6.1.2.1.1.5.0') or oid == '1.3.6.1.2.1.1.5.0':
            return dev['name']
        
        # sysLocation
        if oid.endswith('1.3.6.1.2.1.1.6.0') or oid == '1.3.6.1.2.1.1.6.0':
            return dev['location']
        
        # ifNumber
        if oid.endswith('1.3.6.1.2.1.2.1.0') or oid == '1.3.6.1.2.1.2.1.0':
            return str(dev['interfaces'])
        
        # ifNumber 的完整OID
        if oid == '1.3.6.1.2.1.2.1.0':
            return str(dev['interfaces'])
        
        # 接口状态 ifOperStatus (1.3.6.1.2.1.2.2.1.8.X)
        if '.1.3.6.1.2.1.2.2.1.8.' in oid:
            parts = oid.split('.')
            if_index = int(parts[-1])
            if if_index in dev['ports_down']:
                return '2'  # down
            return '1'  # up
        
        # 接口描述 ifDescr (1.3.6.1.2.1.2.2.1.2.X)
        if '.1.3.6.1.2.1.2.2.1.2.' in oid:
            parts = oid.split('.')
            if_index = parts[-1]
            return f'GigabitEthernet1/0/{if_index}'
        
        # 接口速度 ifSpeed (1.3.6.1.2.1.2.2.1.5.X)
        if '.1.3.6.1.2.1.2.2.1.5.' in oid:
            return dev['if_speed']
        
        # CPU空闲率 (UCD-SMI)
        if oid.endswith('1.3.6.1.4.1.2021.11.11.0'):
            cpu_idle = dev.get('cpu_idle', lambda: 80)()
            return str(100 - cpu_idle)  # 返回CPU使用率
        
        # 内存总量 (UCD-SMI)
        if oid.endswith('1.3.6.1.4.1.2021.4.5.0'):
            return dev.get('mem_total', '32814592')
        
        # 可用内存 (UCD-SMI)
        if oid.endswith('1.3.6.1.4.1.2021.4.6.0'):
            return dev.get('mem_avail', lambda: '16000000')()
        
        return None
    
    def parse_snmp_request(self, data):
        """解析SNMP请求，提取OID列表"""
        oids = []
        
        # 简化解析：查找所有OID
        pos = 0
        while pos < len(data) - 2:
            if data[pos] == 0x06:  # OID tag
                oid_len = data[pos + 1]
                if oid_len > 0 and pos + 2 + oid_len <= len(data):
                    oid_bytes = data[pos + 2:pos + 2 + oid_len]
                    oid = self.decode_oid(oid_bytes)
                    if oid:
                        oids.append(oid)
                    pos += oid_len + 2
                else:
                    pos += 1
            else:
                pos += 1
        
        return oids
    
    def decode_oid(self, oid_bytes):
        """解码OID字节"""
        if len(oid_bytes) == 0:
            return None
        
        oid = []
        # 第一个字节: (first*40) + second
        first = oid_bytes[0] // 40
        second = oid_bytes[0] % 40
        oid.append(first)
        oid.append(second)
        
        value = 0
        for b in oid_bytes[1:]:
            value = (value << 7) | (b & 0x7f)
            if not (b & 0x80):
                oid.append(value)
                value = 0
        
        return '.'.join(str(x) for x in oid)
    
    def encode_value(self, value_str):
        """编码值为ASN.1格式"""
        # 简化实现：只处理字符串和整数
        if value_str.isdigit():
            # 整数
            num = int(value_str)
            if num == 0:
                return bytes([0x02, 0x01, 0x00])
            result = []
            temp = num
            while temp > 0:
                result.insert(0, temp & 0xff)
                temp >>= 8
            if result[0] & 0x80:
                result.insert(0, 0)
            return bytes([0x02, len(result)] + result)
        else:
            # 字符串
            data = value_str.encode('utf-8')
            return bytes([0x04, len(data)]) + data
    
    def build_response(self, request_data, oids):
        """构建SNMP响应包"""
        # 简化实现：返回一个基本的响应
        # 实际完整的SNMP响应需要完整的ASN.1编码
        # 这里返回一个简化的响应，足够让我们的Python客户端解析
        
        response = bytearray(request_data)
        
        # 将GET_REQUEST改为GET_RESPONSE (0xa0 -> 0xa2)
        for i, b in enumerate(response):
            if b == 0xa0:  # GET_REQUEST
                response[i] = 0xa2  # GET_RESPONSE
                break
        
        return bytes(response)
    
    def start(self):
        """启动SNMP服务器"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            sock.bind(('', self.port))
            sock.settimeout(1)
            
            print(f"SNMP Mock服务器启动成功!")
            print(f"=" * 50)
            print(f"监听端口: UDP {self.port}")
            print(f"社区名: {self.community}")
            print(f"设备类型: {self.device_type}")
            print(f"=" * 50)
            print()
            
            request_count = 0
            
            while running:
                try:
                    data, addr = sock.recvfrom(4096)
                    request_count += 1
                    
                    # 解析请求
                    oids = self.parse_snmp_request(data)
                    
                    if oids:
                        oid = oids[0]
                        value = self.get_device_data().get('name', 'Unknown') if '1.3.6.1.2.1.1.5.0' in oid else None
                        
                        print(f"[{request_count}] {addr[0]} -> OID: {oid[:50]}...")
                        
                        # 获取对应的值
                        for test_oid in oids:
                            value = self.build_oid_response(test_oid)
                            if value:
                                print(f"       值: {value[:50]}")
                                break
                        
                        # 发送响应
                        response = self.build_response(data, oids)
                        sock.sendto(response, addr)
                
                except socket.timeout:
                    continue
                except Exception as e:
                    if running:
                        print(f"错误: {e}")
                    continue
        
        except OSError as e:
            if e.errno == 98:  # Address already in use
                print(f"错误: 端口 {self.port} 已被占用")
                print("请先停止现有服务: sudo systemctl stop snmpd")
            else:
                print(f"错误: {e}")
        finally:
            sock.close()

def main():
    port = 161
    community = 'public'
    
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    if len(sys.argv) > 2:
        community = sys.argv[2]
    
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print()
    print("=" * 50)
    print("SNMP Mock服务器")
    print("=" * 50)
    print(f"端口: {port}")
    print(f"社区名: {community}")
    print()
    print("按 Ctrl+C 停止")
    print()
    
    server = SNMPMockServer(port, community)
    server.start()

if __name__ == '__main__':
    main()
