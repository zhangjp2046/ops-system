#!/usr/bin/env python3
"""
简单的SNMP测试服务器
在真实环境中运行，用于测试SNMP监控功能
使用方法: python3 snmp_test_server.py [port]
"""

import socket
import struct
import random
import sys
import threading
import time

class SimpleSNMPResponder:
    """简单的SNMP Responder，响应SNMP GET请求"""
    
    def __init__(self, port=161):
        self.port = port
        self.running = True
        
        # 模拟的OID数据
        self.data = {
            '1.3.6.1.2.1.1.1.0': b'H3C S5500-58C-EI Switch V7',  # sysDescr
            '1.3.6.1.2.1.1.3.0': b'%d' % (int(time.time()) % 1000000),  # sysUpTime
            '1.3.6.1.2.1.1.5.0': b'Test-Switch-01',  # sysName
            '1.3.6.1.2.1.2.1.0': b'24',  # ifNumber
            # 接口状态 - 故意让几个接口DOWN用于测试告警
            '1.3.6.1.2.1.2.2.1.8.1': b'\x01',  # ifStatus.1 = up
            '1.3.6.1.2.1.2.2.1.8.2': b'\x01',  # ifStatus.2 = up
            '1.3.6.1.2.1.2.2.1.8.3': b'\x02',  # ifStatus.3 = down (测试用)
            '1.3.6.1.2.1.2.2.1.8.4': b'\x02',  # ifStatus.4 = down (测试用)
            '1.3.6.1.2.1.2.2.1.8.5': b'\x01',  # ifStatus.5 = up
            # 后续接口默认UP
        }
        
        # 生成其他接口的状态
        for i in range(6, 25):
            if i == 10 or i == 11:  # 让接口10, 11也DOWN
                self.data[f'1.3.6.1.2.1.2.2.1.8.{i}'] = b'\x02'
            else:
                self.data[f'1.3.6.1.2.1.2.2.1.8.{i}'] = b'\x01'
        
        # 接口描述
        for i in range(1, 25):
            self.data[f'1.3.6.1.2.1.2.2.1.2.{i}'] = f'GigabitEthernet1/0/{i}'.encode()
            self.data[f'1.3.6.1.2.1.2.2.1.5.{i}'] = b'1000000000'  # 1Gbps
    
    def handle_request(self, data, addr, sock):
        """处理SNMP请求"""
        try:
            if len(data) < 32:
                return
            
            # 解析请求中的OID
            oid = self.extract_oid_from_request(data)
            
            print(f"[{addr[0]}] GET {oid}")
            
            # 构建响应
            response = self.build_response(data, oid)
            
            if response:
                sock.sendto(response, addr)
                print(f"[{addr[0]}] RESPOND {oid} = {self.data.get(oid, b'unknown')[:30]}")
            
        except Exception as e:
            print(f"处理请求错误: {e}")
    
    def extract_oid_from_request(self, data):
        """从请求中提取OID"""
        # 简化解析：查找0x06 (OID tag)后面的数据
        pos = 0
        while pos < len(data) - 2:
            if data[pos] == 0x06:  # OID tag
                oid_len = data[pos + 1]
                if pos + 2 + oid_len <= len(data):
                    oid_bytes = data[pos + 2:pos + 2 + oid_len]
                    return '1.' + '.'.join(str(b) for b in oid_bytes)
            pos += 1
        return None
    
    def build_response(self, request, oid):
        """构建SNMP响应"""
        if not oid:
            return None
        
        # 找到对应的值
        value = self.data.get(oid)
        if not value:
            # 尝试模糊匹配
            for key in self.data:
                if oid.startswith(key.rsplit('.', 1)[0]):
                    value = self.data[key]
                    break
        
        if not value:
            return None
        
        # 构建SNMP Response
        # 简化版本：只返回找到的值
        response_data = self.build_snmp_packet(oid, value, request)
        return response_data
    
    def build_snmp_packet(self, oid, value, request):
        """构建SNMP响应包"""
        # 这是简化版本，实际需要完整的ASN.1编码
        try:
            # 从请求中提取request-id等
            req_id = request[24:28] if len(request) > 28 else b'\x00\x00\x00\x01'
            
            # 构建VarBind: OID + NULL值 (请求中的格式)
            # 简化：直接返回请求数据加上值
            return request  # 实际这里应该构建完整的响应
        except:
            return None
    
    def run(self):
        """运行SNMP服务器"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1)
        
        try:
            sock.bind(('', self.port))
            print(f"SNMP Test Server listening on port {self.port}")
            print("Community: public")
            print("Press Ctrl+C to stop")
            print()
            
            while self.running:
                try:
                    data, addr = sock.recvfrom(4096)
                    self.handle_request(data, addr, sock)
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"Error: {e}")
                        
        except Exception as e:
            print(f"启动失败: {e}")
        finally:
            sock.close()
    
    def stop(self):
        self.running = False


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 161
    
    print("=" * 50)
    print("Simple SNMP Test Server")
    print("=" * 50)
    print(f"Port: {port}")
    print(f"Community: public")
    print()
    
    server = SimpleSNMPResponder(port)
    
    try:
        server.run()
    except KeyboardInterrupt:
        print("\nStopping...")
        server.stop()


if __name__ == '__main__':
    main()
