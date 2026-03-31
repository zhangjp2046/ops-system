#!/usr/bin/env python3
"""
原生SNMP客户端
使用Python socket发送SNMP请求，不依赖外部库
支持SNMP v1/v2c
"""

import socket
import struct
import time
from typing import Optional, List, Tuple


class SNMPClient:
    """原生SNMP客户端"""
    
    # SNMP端口
    SNMP_PORT = 161
    
    # SNMP协议操作
    GET_REQUEST = 0xa0
    GET_NEXT_REQUEST = 0xa1
    GET_RESPONSE = 0xa2
    SET_REQUEST = 0xa3
    GET_BULK_REQUEST = 0xa5
    INFORM_REQUEST = 0xa6
    
    # 错误状态
    NO_ERROR = 0
    TOO_BIG = 1
    NO_SUCH_NAME = 2
    BAD_VALUE = 3
    READ_ONLY = 4
    GEN_ERR = 5
    
    def __init__(self, host: str, community: str = 'public', version: int = 1, timeout: int = 5, retries: int = 3):
        self.host = host
        self.community = community
        self.version = version  # 0 = v1, 1 = v2c
        self.timeout = timeout
        self.retries = retries
        self._request_id = int(time.time() * 1000) % 65535
    
    def _generate_request_id(self) -> int:
        """生成请求ID"""
        self._request_id = (self._request_id + 1) % 65536
        return self._request_id
    
    def _encode_oid(self, oid: str) -> bytes:
        """编码OID为DER格式"""
        # 将字符串OID转换为整数列表
        oid_parts = [int(x) for x in oid.split('.')]
        
        # 处理前两个部分 (x.y -> (x*40)+y)
        if len(oid_parts) >= 2:
            oid_parts[0] = (oid_parts[0] * 40) + oid_parts[1]
            oid_parts = oid_parts[2:] if len(oid_parts) > 2 else []
        
        result = bytes([0x06, len(oid_parts) + 1, oid_parts[0] if oid_parts else 0])
        
        for i, part in enumerate(oid_parts[1:], 1):
            if part < 128:
                result += bytes([part])
            else:
                # 编码为多字节
                encoded = []
                temp = part
                while temp > 0:
                    encoded.append(temp & 0x7f)
                    temp >>= 7
                encoded = encoded[::-1]
                for j, b in enumerate(encoded):
                    if j < len(encoded) - 1:
                        result += bytes([b | 0x80])
                    else:
                        result += bytes([b])
        
        return result
    
    def _encode_string(self, s: str) -> bytes:
        """编码字符串"""
        data = s.encode('utf-8')
        return bytes([0x04, len(data)]) + data
    
    def _encode_integer(self, i: int) -> bytes:
        """编码整数"""
        if i == 0:
            return bytes([0x02, 1, 0])
        
        result = []
        temp = i
        if i < 0:
            temp = -i
            complement = True
        else:
            complement = False
        
        while temp > 0:
            result.insert(0, temp & 0xff)
            temp >>= 8
        
        if result[0] & 0x80:
            result.insert(0, 0)
        
        if complement:
            result = [0xff - b for b in result]
            for i in range(len(result)):
                result[i] += 1
                if result[i] > 0xff:
                    result[i] = 0
                else:
                    break
            result = [~b & 0xff for b in result]
        
        return bytes([0x02, len(result)]) + bytes(result)
    
    def _build_header(self) -> bytes:
        """构建SNMP消息头"""
        # community
        community_bytes = self._encode_string(self.community)
        
        # v2c的PDU
        if self.version == 1:
            # v1版本
            pdu = bytes([self.GET_REQUEST, 0, 0])  # type, reserved, reserved
        else:
            # v2c版本
            pdu = bytes([self.GET_REQUEST, 0, 0])
        
        return community_bytes + pdu
    
    def _build_get_request_pdu(self, oid: str) -> bytes:
        """构建GET请求PDU"""
        request_id = self._generate_request_id()
        
        # variable bindings: OID with NULL value
        var_bind = self._encode_oid(oid) + bytes([0x05, 0x00])  # NULL
        
        # PDU部分
        pdu_data = (
            self._encode_integer(request_id) +
            self._encode_integer(0) +  # error status
            self._encode_integer(0) +  # error index
            bytes([0x30, 0x00]) + var_bind  # sequence
        )
        
        # 计算长度
        pdu_len = len(pdu_data)
        pdu_data = bytes([0x30, pdu_len]) + pdu_data
        
        return pdu_data
    
    def _build_packet(self, oid: str) -> bytes:
        """构建完整的SNMP数据包"""
        # SNMP v2c message
        version = self._encode_integer(1 if self.version == 1 else 0)
        community = self._encode_string(self.community)
        
        # PDU
        request_id = self._generate_request_id()
        var_bind = self._encode_oid(oid) + bytes([0x05, 0x00])  # OID + NULL
        
        var_bind_list = bytes([0x30, len(var_bind)]) + var_bind
        pdu_data = (
            self._encode_integer(request_id) +
            self._encode_integer(0) +  # error-status
            self._encode_integer(0) +  # error-index
            var_bind_list
        )
        
        # Community-level PDU
        if self.version == 1:
            pdu_type = self.GET_REQUEST
        else:
            pdu_type = self.GET_REQUEST
        
        pdu = bytes([pdu_type, 0, 0]) + pdu_data
        
        # 完整消息
        message = version + community + pdu
        
        # 包装为SEQUENCE
        packet = bytes([0x30, len(message)]) + message
        
        return packet
    
    def _parse_response(self, data: bytes) -> Optional[str]:
        """解析SNMP响应"""
        try:
            if len(data) < 50:
                return None
            
            # 跳过头部，直接找到值部分
            # 简化解析：找到最后一个0x30序列后的数据
            pos = 0
            
            # SEQUENCE
            if data[pos] != 0x30:
                return None
            pos += 2  # skip tag + length
            
            # Version
            if data[pos] != 0x02:
                return None
            pos += 2
            version_len = data[pos]
            pos += 1 + version_len
            
            # Community
            if data[pos] != 0x04:
                return None
            pos += 2
            community_len = data[pos]
            pos += 1 + community_len
            
            # Response PDU
            if data[pos] != 0xa2:  # GET_RESPONSE
                return None
            pos += 2
            response_len = data[pos]
            pos += 2
            
            # Request ID
            pos += data[pos] + 2
            
            # Error Status
            error_status = data[pos]
            pos += data[pos] + 2
            
            # Error Index
            error_index = data[pos]
            pos += data[pos] + 2
            
            # VarBind list SEQUENCE
            if data[pos] != 0x30:
                return None
            pos += 2
            var_bind_list_len = data[pos]
            pos += 2
            
            # VarBind SEQUENCE
            if data[pos] != 0x30:
                return None
            pos += 2
            var_bind_len = data[pos]
            pos += 2
            
            # OID
            if data[pos] != 0x06:
                return None
            pos += 2
            oid_len = data[pos]
            pos += 1
            oid_value = '.'.join(str(b) for b in data[pos:pos+oid_len])
            pos += oid_len
            
            # Value
            value_type = data[pos]
            pos += 1
            value_len = data[pos]
            pos += 1
            value = data[pos:pos+value_len]
            
            # 解析值
            if value_type == 0x04:  # String
                return value.decode('utf-8', errors='replace')
            elif value_type == 0x02:  # Integer
                if value_len == 1:
                    return str(value[0])
                elif value_len <= 4:
                    int_val = 0
                    for b in value:
                        int_val = (int_val << 8) | b
                    return str(int_val)
            elif value_type == 0x40:  # Timeticks
                if value_len <= 4:
                    int_val = 0
                    for b in value:
                        int_val = (int_val << 8) | b
                    return str(int_val)
            elif value_type == 0x06:  # OID
                return '.'.join(str(b) for b in value)
            
            return str(value)
            
        except Exception as e:
            print(f"解析响应失败: {e}")
            return None
    
    def get(self, oid: str) -> Optional[str]:
        """执行SNMP GET请求"""
        packet = self._build_packet(oid)
        
        for attempt in range(self.retries):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(self.timeout)
                sock.sendto(packet, (self.host, self.SNMP_PORT))
                
                try:
                    response, _ = sock.recvfrom(4096)
                    return self._parse_response(response)
                finally:
                    sock.close()
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"SNMP请求错误: {e}")
                continue
        
        return None
    
    def walk(self, oid: str) -> List[Tuple[str, str]]:
        """执行SNMP WALK (使用GET_NEXT)"""
        results = []
        current_oid = oid
        
        for attempt in range(self.retries):
            try:
                while True:
                    packet = self._build_walk_packet(current_oid)
                    
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.settimeout(self.timeout)
                    sock.sendto(packet, (self.host, self.SNMP_PORT))
                    
                    try:
                        response, _ = sock.recvfrom(8192)
                        oid_val, value = self._parse_walk_response(response, current_oid)
                        
                        if oid_val is None:
                            break
                        
                        results.append((oid_val, value))
                        current_oid = oid_val
                        
                        # 如果返回的OID不再是我们请求的OID的子集，说明已经结束
                        if not oid_val.startswith(oid.rstrip('0').rstrip('.')):
                            # 检查是否真的结束了
                            if len(results) > 0:
                                last_oid = results[-1][0]
                                if not self._is_child_oid(oid, last_oid):
                                    break
                                
                    finally:
                        sock.close()
                        
                break  # 成功完成
                
            except socket.timeout:
                continue
            except Exception as e:
                print(f"SNMP WALK错误: {e}")
                break
        
        return results
    
    def _build_walk_packet(self, oid: str) -> bytes:
        """构建WALK请求包"""
        version = self._encode_integer(1 if self.version == 1 else 0)
        community = self._encode_string(self.community)
        
        # GET_NEXT_REQUEST PDU
        request_id = self._generate_request_id()
        var_bind = self._encode_oid(oid) + bytes([0x05, 0x00])
        var_bind_list = bytes([0x30, len(var_bind)]) + var_bind
        
        pdu_data = (
            self._encode_integer(request_id) +
            self._encode_integer(0) +
            self._encode_integer(0) +
            var_bind_list
        )
        
        pdu = bytes([self.GET_NEXT_REQUEST, 0, 0]) + pdu_data
        message = version + community + pdu
        
        return bytes([0x30, len(message)]) + message
    
    def _parse_walk_response(self, data: bytes, start_oid: str) -> Tuple[Optional[str], Optional[str]]:
        """解析WALK响应"""
        try:
            if len(data) < 30:
                return None, None
            
            # 简化解析
            pos = 0
            
            # SEQUENCE
            if data[pos] != 0x30:
                return None, None
            pos += 2
            seq_len = data[pos]
            pos += 1
            
            # Version
            if data[pos] != 0x02:
                return None, None
            pos += 2
            pos += data[pos] + 1
            
            # Community
            if data[pos] != 0x04:
                return None, None
            pos += 2
            pos += data[pos] + 1
            
            # Response PDU
            if data[pos] != 0xa2:
                return None, None
            pos += 2
            pos += data[pos] + 1
            
            # Request ID
            pos += data[pos] + 2
            
            # Error Status
            error_status = data[pos]
            pos += data[pos] + 2
            if error_status != 0:
                return None, None
            
            # Error Index
            pos += data[pos] + 2
            
            # VarBind list
            if data[pos] != 0x30:
                return None, None
            pos += 2
            pos += data[pos] + 1
            
            # VarBind
            if data[pos] != 0x30:
                return None, None
            pos += 2
            pos += data[pos] + 1
            
            # OID
            if data[pos] != 0x06:
                return None, None
            pos += 2
            oid_len = data[pos]
            pos += 1
            oid_bytes = data[pos:pos+oid_len]
            oid_val = self._decode_oid(oid_bytes)
            pos += oid_len
            
            # Value
            value_type = data[pos]
            pos += 1
            value_len = data[pos]
            pos += 1
            value_bytes = data[pos:pos+value_len]
            
            # 解析值
            if value_type == 0x04:  # String
                value = value_bytes.decode('utf-8', errors='replace')
            elif value_type == 0x02:  # Integer
                int_val = 0
                for b in value_bytes:
                    int_val = (int_val << 8) | b
                value = str(int_val)
            elif value_type == 0x40:  # Timeticks
                int_val = 0
                for b in value_bytes:
                    int_val = (int_val << 8) | b
                value = str(int_val)
            elif value_type == 0x06:  # OID
                value = self._decode_oid(value_bytes)
            else:
                value = str(value_bytes)
            
            return oid_val, value
            
        except Exception as e:
            print(f"解析WALK响应失败: {e}")
            return None, None
    
    def _decode_oid(self, oid_bytes: bytes) -> str:
        """解码OID字节"""
        if len(oid_bytes) == 0:
            return ''
        
        oid = []
        oid.append(oid_bytes[0] // 40)
        oid.append(oid_bytes[0] % 40)
        
        value = 0
        for i, b in enumerate(oid_bytes[1:], 1):
            value = (value << 7) | (b & 0x7f)
            if not (b & 0x80):
                oid.append(value)
                value = 0
        
        return '.'.join(str(x) for x in oid)
    
    def _is_child_oid(self, parent: str, child: str) -> bool:
        """检查child是否是parent的子OID"""
        parent_parts = [int(x) for x in parent.split('.')]
        child_parts = [int(x) for x in child.split('.')]
        
        if len(child_parts) <= len(parent_parts):
            return False
        
        return child_parts[:len(parent_parts)] == parent_parts


def snmpget(host: str, oid: str, community: str = 'public', version: int = 1) -> Optional[str]:
    """简单的SNMP GET函数"""
    client = SNMPClient(host, community, version)
    return client.get(oid)


def snmpwalk(host: str, oid: str, community: str = 'public', version: int = 1) -> List[Tuple[str, str]]:
    """简单的SNMP WALK函数"""
    client = SNMPClient(host, community, version)
    return client.walk(oid)


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python snmp_client.py <host> <oid> [community]")
        sys.exit(1)
    
    host = sys.argv[1]
    oid = sys.argv[2]
    community = sys.argv[3] if len(sys.argv) > 3 else 'public'
    
    print(f"SNMP GET {host} {oid}...")
    result = snmpget(host, oid, community)
    print(f"Result: {result}")