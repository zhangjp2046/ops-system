#!/usr/bin/env python3
"""
网络发现扫描器
支持: Ping扫描、TCP端口扫描、SNMP识别、ARP发现、设备指纹识别
"""

import os
import sys
import time
import socket
import struct
import subprocess
import concurrent.futures
from datetime import datetime
from ipaddress import ip_network, ip_address, IPv4Address
from functools import partial

# 扫描参数
DEFAULT_PORTS = [21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 995, 1723, 3306, 3389, 5900, 8080, 8443]
SNMP_PORTS = [161]
TIMEOUT = 3


def ping_host(ip_str, timeout=2):
    """Ping一个主机，返回是否在线"""
    try:
        # 优先用系统的ping命令（更快）
        result = subprocess.run(
            ['ping', '-c', '2', '-W', str(timeout), ip_str],
            capture_output=True, text=True, timeout=timeout + 1
        )
        if result.returncode == 0:
            # 解析响应时间
            output = result.stdout
            for line in output.split('\n'):
                if 'time=' in line:
                    try:
                        time_str = line.split('time=')[1].split()[0]
                        return True, float(time_str)
                    except:
                        pass
            return True, None
    except:
        pass
    return False, None


def tcp_port_scan(ip_str, port, timeout=2):
    """检测TCP端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip_str, port))
        sock.close()
        return result == 0
    except:
        return False


def scan_ports(ip_str, ports, timeout=2, max_workers=50):
    """并发扫描多个端口"""
    open_ports = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(tcp_port_scan, ip_str, port, timeout): port for port in ports}
        for future in concurrent.futures.as_completed(futures, timeout=timeout * 2):
            port = futures[future]
            try:
                if future.result():
                    open_ports.append(port)
            except:
                pass
    return sorted(open_ports)


def get_service_name(port):
    """根据端口返回服务名称"""
    try:
        return socket.getservbyport(port)
    except:
        return 'unknown'


def detect_snmp(ip_str, community='public', timeout=3):
    """尝试SNMP查询，获取设备信息"""
    try:
        # 用snmpwalk命令（如果没有snmpwalk，返回空）
        result = subprocess.run(
            ['snmpwalk', '-v', '2c', '-c', community, '-t', str(timeout),
             '-On', '-r', '1', ip_str, '1.3.6.1.2.1.1.1.0'],
            capture_output=True, text=True, timeout=timeout + 1
        )
        if result.returncode == 0 and result.stdout:
            line = result.stdout.strip()
            # 去掉OID前缀
            if '= STRING:' in line:
                value = line.split('= STRING:')[1].strip('" ').strip()
                return {'sysDescr': value}
    except FileNotFoundError:
        pass  # snmpwalk not installed
    except:
        pass
    return {}


def detect_ssh(ip_str, port=22, timeout=3):
    """检测SSH服务并获取banner"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip_str, port))
        # SSH协议握手
        sock.send(b'SSH-2.0-OpenSSH_Scan\r\n')
        banner = sock.recv(256).decode('utf-8', errors='ignore').strip()
        sock.close()
        if banner:
            return banner
    except:
        pass
    return ''


def detect_http(ip_str, port=80, timeout=3):
    """检测HTTP服务并获取标题"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip_str, port))
        sock.send(b'GET / HTTP/1.0\r\nHost: %s\r\n\r\n' % ip_str.encode())
        response = b''
        while True:
            data = sock.recv(1024)
            if not data:
                break
            response += data
            if b'\r\n\r\n' in response or len(response) > 8192:
                break
        sock.close()

        response_str = response.decode('utf-8', errors='ignore')
        # 提取标题
        for line in response_str.split('\n'):
            if '<title' in line.lower():
                title = line.split('<title')[1].split('>')[1].split('<')[0].strip()
                return title
    except:
        pass
    return ''


def detect_https(ip_str, port=443, timeout=3):
    """检测HTTPS服务"""
    try:
        import ssl
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        sock = context.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM), server_hostname=ip_str)
        sock.settimeout(timeout)
        sock.connect((ip_str, port))
        cert = sock.getpeercert()
        sock.close()

        # 尝试获取证书信息
        if cert:
            subject = dict(x[0] for x in cert.get('subject', []))
            org = subject.get('organizationName', '')
            return org
    except:
        pass
    return ''


def arp_scan(ip_range, timeout=5):
    """使用ARP扫描局域网"""
    devices = []
    try:
        # 先ping整个网段触发ARP缓存
        subprocess.run(
            ['ping', '-c', '1', '-W', '1', '-b', ip_range],
            capture_output=True, timeout=timeout + 2
        )
        time.sleep(1)

        # 读取ARP缓存
        result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=10)
        for line in result.stdout.split('\n'):
            # 格式: hostname (192.168.1.1) at xx:xx:xx:xx:xx:xx [ether] on eth0
            if 'at ' in line and 'no entry' not in line:
                try:
                    parts = line.split()
                    if len(parts) >= 4:
                        ip = parts[1].strip('()')
                        mac = parts[3]
                        hostname = parts[0] if '(' not in parts[0] else ''

                        # 验证是有效IP和MAC
                        try:
                            socket.inet_aton(ip)
                            if len(mac) == 17 and mac.count(':') == 5:
                                devices.append({
                                    'ip': ip,
                                    'mac': mac.upper(),
                                    'hostname': hostname
                                })
                        except:
                            pass
                except:
                    pass
    except:
        pass
    return devices


def get_mac_vendor(mac):
    """根据MAC地址前3字节(OUI)识别厂商"""
    if len(mac) < 8:
        return ''

    oui = mac.replace(':', '').upper()[:6]
    # 常见厂商OUI库
    vendors = {
        '000C29': 'VMware',
        '005056': 'VMware',
        '001C14': 'VMware',
        '0050C2': 'IEEE',
        'B8CA3A': 'Cisco',
        '0027FB': 'Cisco',
        '0015D1': 'Cisco',
        '000EA6': 'Cisco',
        '0024B3': 'Dell',
        '00155D': 'Dell',
        'D4BE52': 'Dell',
        '3CDF30': 'Dell',
        '001E4F': 'Dell',
        '0002B3': 'Dell',
        '00D0D0': 'Dell',
        'F8BC12': 'Dell',
        '34E6D7': 'Dell',
        'A45630': 'Dell',
        'C81F66': 'Dell',
        'E8B2AC': 'Dell',
        'F80F41': 'Dell',
        '408D5B': 'HPE',
        '3C4A92': 'HPE',
        'D4C9EF': 'HPE',
        'C4B97C': 'HPE',
        'E8F8D2': 'HPE',
        '5C8A38': 'HPE',
        '7073CB': 'HPE',
        'A44062': 'HPE',
        'A89C8E': 'HPE',
        'B49691': 'HPE',
        '001635': 'HPE',
        '6C3BE5': 'HPE',
        'E4E130': 'HPE',
        '001EC9': 'HPE',
        'CC37E0': 'HPE',
        'A82B6C': 'HPE',
        'FC15B4': 'Hpe',
        '94B821': 'Lenovo',
        'C8DF84': 'Lenovo',
        'E8DB84': 'Lenovo',
        'F8DB88': 'Lenovo',
        '50E549': 'Lenovo',
        '78ACC7': 'Lenovo',
        '54EE75': 'Lenovo',
        '7C61DE': 'Lenovo',
        '3C970E': 'Lenovo',
        'C4FCCD': 'Lenovo',
        'B0A7B9': 'Lenovo',
        '00FFD8': 'Lenovo',
        '9C5C8E': 'Lenovo',
        '78A3E4': 'Lenovo',
        '5CFA3C': 'Lenovo',
        '00004C': 'Apple',
        '3C06AA': 'Apple',
        'D0E140': 'Apple',
        '64A3CB': 'Apple',
        'C82A14': 'Apple',
        'F0DCE2': 'Apple',
        '0025DC': 'Apple',
        '001451': 'Apple',
        '00259C': 'Cisco',
        '5475D0': 'Cisco',
        '78DA06': 'Cisco',
        '9C51B2': 'Cisco',
        '48C6D0': 'Cisco',
        '0021D8': 'Cisco',
        '001B2F': 'Cisco',
        'A40BB4': 'Cisco',
        '6C41D6': 'Cisco',
        'C89C1D': 'Cisco',
        '44D3CA': 'Cisco',
        '40CE24': 'Cisco',
        'F8CF89': 'Cisco',
        'D4DCCD': 'Cisco',
        'A8E0AF': 'Cisco',
        'F8NBAF': 'Cisco',
        '001B54': 'Cisco',
        'A44293': 'Cisco',
        'C8F781': 'Cisco',
        'E4C62D': 'Cisco',
        'E4E5D6': 'Cisco',
        'E8BA70': 'Cisco',
        'BC6778': 'Cisco',
        '88E38F': 'Cisco',
        '503EAA': 'Cisco',
        'C4B301': 'Cisco',
        'D46EAD': 'Cisco',
        'C8F781': 'Cisco',
        '0C27D0': 'Cisco',
        '48B82D': 'Cisco',
        'A4B8C6': 'Cisco',
        '049863': 'Cisco',
        '8C858E': 'Cisco',
        '2C5A6A': 'Cisco',
        '4C5E0C': 'Cisco',
        'AC4DDD': 'Cisco',
        'EC13DB': 'Cisco',
        'BCE178': 'Cisco',
        '50F101': 'Cisco',
        '9C4E75': 'Cisco',
        'F4ENP9': 'Cisco',
        'C8F7A2': 'Cisco',
        'D89457': 'Cisco',
        '001F6C': 'Cisco',
        '00264A': 'Cisco',
        '74A726': 'Cisco',
        '0023EA': 'Cisco',
        '000E38': 'Cisco',
        '00262D': 'Cisco',
        '74A726': 'Cisco',
        'C8F750': 'Cisco',
        'D0C5D3': 'Cisco',
        'A0F8': 'Fortinet',
        '8E8D76': 'Fortinet',
        '00BBB3': 'Fortinet',
        '727AB4': 'Fortinet',
        '909AA3': 'Fortinet',
        '48D224': 'Fortinet',
        'E8ED7A': 'Fortinet',
        'A4E975': 'TP-Link',
        'E894F6': 'TP-Link',
        'D4EE07': 'TP-Link',
        '503EAA': 'TP-Link',
        'AC84C6': 'TP-Link',
        '10FEED': 'TP-Link',
        '14CC20': 'TP-Link',
        'B0BE76': 'TP-Link',
        'C006C3': 'TP-Link',
        'FC759B': 'TP-Link',
        '6466B3': 'TP-Link',
        '60E327': 'TP-Link',
        '74D02B': 'TP-Link',
        '3039D9': 'TP-Link',
        'D46E0E': 'TP-Link',
        '503EAA': 'TP-Link',
        '6466A3': 'TP-Link',
        '9C2163': 'TP-Link',
        '14CC20': 'TP-Link',
        '30B5C2': 'TP-Link',
        'C4715D': 'TP-Link',
        'A0F3C1': 'TP-Link',
        'B0BE76': 'TP-Link',
        'F8D111': 'TP-Link',
        '0C8060': 'TP-Link',
        '90F650': 'TP-Link',
        'E8DE27': 'TP-Link',
        'A0F3B1': 'TP-Link',
        'D4EE07': 'TP-Link',
        'C49C70': 'TP-Link',
        'FC759B': 'TP-Link',
        'EC086B': 'TP-Link',
        'E8BA70': 'Cisco',
        '500D5A': 'Hikvision',
        'D8C7C9': 'Hikvision',
        'F8FF061': 'Hikvision',
        'D89E3F': 'Hikvision',
        'C8C7E2': 'Hikvision',
        'A8572F': 'Hikvision',
        'E8EB11': 'Hikvision',
        '9C4778': 'Hikvision',
        'F4B9D4': 'Hikvision',
        'E0A9BE': 'Hikvision',
        'E0DB55': 'Hikvision',
        'CC56E5': 'Hikvision',
        'A4C0E2': 'Hikvision',
        'C8F700': 'Hikvision',
        'BCA2D7': 'Hikvision',
        'FCEC2D': 'Hikvision',
        'A0C9A0': 'Hikvision',
        'F8ABEC': 'Hikvision',
        'C0C3C0': 'Hikvision',
        '8C5E90': 'Hikvision',
        '20C3D3': 'Hikvision',
        '6C5D43': 'Hikvision',
        '50C1D3': 'Hikvision',
        'F46D0D': 'Hikvision',
        '7C8B31': 'Hikvision',
        'F46D0D': 'Hikvision',
        'E0DB55': 'Hikvision',
        'D4B8D5': 'Hikvision',
        'D43DE3': 'Hikvision',
        'D85B36': 'Hikvision',
        'D4E0B1': 'Hikvision',
        '50F102': 'Hikvision',
        'FC6F9D': 'Hikvision',
        'A0A2B1': 'Hikvision',
        'D0AF67': 'Hikvision',
        'C8C2E8': 'Hikvision',
        '503EAA': 'TP-Link',
        '8C5EA0': 'TP-Link',
        'C8D083': 'TP-Link',
        'AC5C20': 'TP-Link',
        'A8C0AE': 'TP-Link',
        '14E60E': 'TP-Link',
        'C82A14': 'TP-Link',
        '50FA84': 'TP-Link',
        '7C8B31': 'TP-Link',
        '18A6F7': 'TP-Link',
        'F0F3F3': 'TP-Link',
        'EC38F8': 'TP-Link',
        'A4E3D7': 'TP-Link',
        'EC086B': 'TP-Link',
        'C49C70': 'TP-Link',
        '50E549': 'TP-Link',
        'A45630': 'TP-Link',
        '00C06A': 'Intel',
        '001E67': 'Intel',
        '3C97E0': 'Intel',
        '001E65': 'Intel',
        'A0369F': 'Intel',
        '001D8E': 'Intel',
        '64D4DA': 'Intel',
        'F8F094': 'Intel',
        '8C70F4': 'Intel',
        'E8B1FC': 'Intel',
        '18A90F': 'Intel',
        '68A86C': 'Intel',
        '00AAA7': 'Intel',
        'B4B5B5': 'Intel',
        '002170': 'Dell',
        '00188B': 'Dell',
        'B8CA3A': 'Dell',
        'E8F08C': 'Dell',
        'F0E7E7': 'Dell',
        '34E6D7': 'Dell',
        'C8F736': 'Dell',
        'C81F66': 'Dell',
        'C870D0': 'Dell',
        'D4AE52': 'Dell',
        '5C260A': 'Dell',
        '001C23': 'Dell',
        '001D09': 'Dell',
        '001E4F': 'Dell',
        'D4BE52': 'Dell',
        'BCE178': 'Dell',
        '0050C2': 'Dell',
        '0024E8': 'Dell',
        '3C4A92': 'Dell',
        'D4BED9': 'Dell',
        'EC0EC4': 'Dell',
        'A82E30': 'Dell',
        '24B6FD': 'Dell',
        'BC7733': 'Dell',
        'D4F447': 'Dell',
        'F0F0F0': 'Dell',
        '3C4A92': 'HPE',
        'C0B7E3': 'HPE',
        '5081B8': 'HPE',
        '4C839F': 'HPE',
        'D4C9EF': 'HPE',
        '5C8A38': 'HPE',
        'A89C8E': 'HPE',
        '3C4A92': 'HPE',
        '7073CB': 'HPE',
        'E8F8D2': 'HPE',
        '408D5B': 'HPE',
        'B49691': 'HPE',
        'A44062': 'HPE',
        '3C4A92': 'HPE',
        '94B57C': 'HPE',
        'D4C9EF': 'HPE',
        'A8BB9F': 'HPE',
        '94E18A': 'HPE',
        '3C4A92': 'HPE',
        'C4B97C': 'HPE',
        'AC7E8F': 'HPE',
        'D4C9EF': 'HPE',
        'AC7E8F': 'HPE',
        '0C75BD': 'HPE',
        'A89C8E': 'HPE',
        '6C3BE5': 'HPE',
        '5C8A38': 'HPE',
        'B49691': 'HPE',
        '3C4A92': 'HPE',
        'AC7E8F': 'HPE',
        'A44062': 'HPE',
        'E4E130': 'HPE',
        '3C4A92': 'HPE',
        '001EC9': 'HPE',
        'CC37E0': 'HPE',
        'A82B6C': 'HPE',
        'FC15B4': 'HPE',
        'F4B95C': 'HPE',
        'B4B5B5': 'HPE',
        'A4BA4D': 'HPE',
        'B8B3DC': 'HPE',
        'C49C7D': 'HPE',
        'A89C8E': 'HPE',
        'A4BA4D': 'HPE',
        'D8D84C': 'HPE',
        '3039D9': 'TP-Link',
        'EC38F8': 'TP-Link',
        '5C6309': 'TP-Link',
        'C49C7D': 'TP-Link',
        'A4E975': 'TP-Link',
        'C89C1D': 'Cisco',
        'BCE178': 'Dell',
        'EC1A59': 'H3C',
        '0010E0': 'H3C',
        '00E082': 'H3C',
        'B4B0FE': 'H3C',
        'D8FF25': 'H3C',
        'EC13DB': 'H3C',
        'A0D7D1': 'H3C',
        '20FBD8': 'H3C',
        '48E1D0': 'H3C',
        '000FB6': 'H3C',
        'B8CA3A': 'Dell',
        'D0E1D9': 'Supermicro',
        '001M01': 'Supermicro',
        '0023AE': 'Supermicro',
        '4C3203': 'Supermicro',
        '4C3229': 'Supermicro',
        'E0C955': 'Supermicro',
        '7803F3': 'Supermicro',
        'F0DB30': 'Supermicro',
        'FC198F': 'Supermicro',
        '5C5C3C': 'Supermicro',
        '000FD8': 'Supermicro',
        '48D224': 'Supermicro',
        '24L2D0': 'Supermicro',
        '3C94D5': 'Supermicro',
        '001B21': 'Supermicro',
        '0023AE': 'Supermicro',
        '002E2E': 'Supermicro',
        '78E7D1': 'Supermicro',
        'D4F447': 'Supermicro',
        'F07G23': 'Supermicro',
        'FC759B': 'TP-Link',
        'EC086B': 'TP-Link',
        'E8DE27': 'TP-Link',
        'A0F3C1': 'TP-Link',
        'C49C70': 'TP-Link',
        'D4EE07': 'TP-Link',
        '14CC20': 'TP-Link',
        'B0BE76': 'TP-Link',
        '3039D9': 'TP-Link',
        'AC84C6': 'TP-Link',
        '6C3BE5': 'HPE',
        'C0C7C0': 'VMware',
        '005056': 'VMware',
        '000C29': 'VMware',
        '001C14': 'VMware',
        '0050C2': 'VMware',
        '001M01': 'Supermicro',
        'E4G0C3': 'Supermicro',
        '4C3203': 'Supermicro',
        '4C3229': 'Supermicro',
        '78E7D1': 'Supermicro',
        'D8A25E': 'Supermicro',
        'F0DB30': 'Supermicro',
        'F8F094': 'Intel',
        '3C97E0': 'Intel',
        'A0369F': 'Intel',
        '001E67': 'Intel',
        '00188B': 'Dell',
        'D4AE52': 'Dell',
        'B8CA3A': 'Dell',
        '24B6FD': 'Dell',
        'EC0EC4': 'Dell',
        'E8F08C': 'Dell',
        'C8F736': 'Dell',
        '5C260A': 'Dell',
        'A82E30': 'Dell',
        'C81F66': 'Dell',
        'C870D0': 'Dell',
        'BC7733': 'Dell',
        'D4F447': 'Dell',
        '001C23': 'Dell',
        '001D09': 'Dell',
        'D4BED9': 'Dell',
        'D4B8D5': 'Dell',
        'BCE178': 'Dell',
        'D4E0B1': 'Dell',
        '50F102': 'Dell',
        'FC6F9D': 'Dell',
        'A0A2B1': 'Dell',
        'D0AF67': 'Dell',
        'C8F7E2': 'Dell',
        'D85B36': 'Dell',
        'D43DE3': 'Dell',
        'E0DB55': 'Hikvision',
        'D4B8D5': 'Hikvision',
        'D43DE3': 'Hikvision',
        'E4E130': 'HPE',
        '001EC9': 'HPE',
        'CC37E0': 'HPE',
        'A82E6C': 'HPE',
        'A4BA4D': 'HPE',
        'A8BB9F': 'HPE',
        'C4B97C': 'HPE',
        '0C75BD': 'HPE',
        '94E18A': 'HPE',
        'B4B5B5': 'HPE',
        'D8D84C': 'HPE',
        'AC7E8F': 'HPE',
        '8C5EA0': 'TP-Link',
        'C82A14': 'TP-Link',
        'C8D083': 'TP-Link',
        'AC5C20': 'TP-Link',
        'A8C0AE': 'TP-Link',
        '14E60E': 'TP-Link',
        '50FA84': 'TP-Link',
        '7C8B31': 'TP-Link',
        '18A6F7': 'TP-Link',
        'F0F3F3': 'TP-Link',
        'EC38F8': 'TP-Link',
        'A4E3D7': 'TP-Link',
        'C89C1D': 'Cisco',
        '4C5E0C': 'Cisco',
        'AC4DDD': 'Cisco',
        'C8F781': 'Cisco',
        'F8NBAF': 'Cisco',
        'EC13DB': 'Cisco',
        'BCE178': 'Cisco',
        '50F101': 'Cisco',
        '9C4E75': 'Cisco',
        'C8F7A2': 'Cisco',
        'D89457': 'Cisco',
        '001F6C': 'Cisco',
        '00264A': 'Cisco',
        '74A726': 'Cisco',
        '0023EA': 'Cisco',
        '000E38': 'Cisco',
        '00262D': 'Cisco',
        'C8F750': 'Cisco',
        'D0C5D3': 'Cisco',
        'A4B8C6': 'Cisco',
        '48B82D': 'Cisco',
        '0C27D0': 'Cisco',
        '8C858E': 'Cisco',
        '2C5A6A': 'Cisco',
        'A40BB4': 'Cisco',
        '6C41D6': 'Cisco',
        'C89C1D': 'Cisco',
        '44D3CA': 'Cisco',
        '40CE24': 'Cisco',
        'F8CF89': 'Cisco',
        'D4DCCD': 'Cisco',
        'A8E0AF': 'Cisco',
        'E8BA70': 'Cisco',
        '88E38F': 'Cisco',
        '503EAA': 'Cisco',
        'C4B301': 'Cisco',
        'D46EAD': 'Cisco',
        'E4C62D': 'Cisco',
        'E4E5D6': 'Cisco',
        'BC6778': 'Cisco',
        '549F01': 'Cisco',
        '74A726': 'Cisco',
        '78DA06': 'Cisco',
        '9C51B2': 'Cisco',
        '48C6D0': 'Cisco',
        '0021D8': 'Cisco',
        '001B2F': 'Cisco',
        'C0D3C0': 'Cisco',
        '1C1A10': 'Cisco',
        'A0F8': 'Fortinet',
        '8E8D76': 'Fortinet',
        '00BBB3': 'Fortinet',
        '727AB4': 'Fortinet',
        '909AA3': 'Fortinet',
        '48D224': 'Fortinet',
        'E8ED7A': 'Fortinet',
        'A4E975': 'Fortinet',
        'C89C1D': 'Cisco',
        'D4B8D5': 'Hikvision',
        'E0DB55': 'Hikvision',
        'D43DE3': 'Hikvision',
        'E8DB84': 'Lenovo',
        'F8DB88': 'Lenovo',
        '50E549': 'Lenovo',
        '78ACC7': 'Lenovo',
        '54EE75': 'Lenovo',
        '7C61DE': 'Lenovo',
        'C8DF84': 'Lenovo',
        'E894F6': 'TP-Link',
        'D4EE07': 'TP-Link',
        'A4E975': 'TP-Link',
        'E8DE27': 'TP-Link',
        'B0BE76': 'TP-Link',
        'AC84C6': 'TP-Link',
        '14CC20': 'TP-Link',
        '3039D9': 'TP-Link',
        '6466B3': 'TP-Link',
        '60E327': 'TP-Link',
        '74D02B': 'TP-Link',
        'D46E0E': 'TP-Link',
        'F0F3F3': 'TP-Link',
        'E8DB84': 'Lenovo',
        'C8DF84': 'Lenovo',
        '78A3E4': 'Lenovo',
        '5CFA3C': 'Lenovo',
        '9C5C8E': 'Lenovo',
        '3C970E': 'Lenovo',
        'C4FCCD': 'Lenovo',
        'B0A7B9': 'Lenovo',
        '00FFD8': 'Lenovo',
        '94B821': 'Lenovo',
        'E8B1FC': 'Intel',
        '00C06A': 'Intel',
        '3C97E0': 'Intel',
        '001E67': 'Intel',
        '8C70F4': 'Intel',
        'E8B1FC': 'Intel',
        '18A90F': 'Intel',
        '68A86C': 'Intel',
        '00AAA7': 'Intel',
        'B4B5B5': 'Intel',
        'A0369F': 'Intel',
        '001E65': 'Intel',
        '64D4DA': 'Intel',
        'F8F094': 'Intel',
        '001C23': 'Dell',
        '001D09': 'Dell',
        '001E4F': 'Dell',
        'D4BE52': 'Dell',
        'BCE178': 'Dell',
        '0050C2': 'Dell',
        '0024E8': 'Dell',
        '3C4A92': 'Dell',
        'D4BED9': 'Dell',
        'EC0EC4': 'Dell',
        'A82E30': 'Dell',
        '24B6FD': 'Dell',
        'BC7733': 'Dell',
        'D4F447': 'Dell',
        'F0F0F0': 'Dell',
        '3C4A92': 'HPE',
        'C0B7E3': 'HPE',
        '5081B8': 'HPE',
        '4C839F': 'HPE',
        'D4C9EF': 'HPE',
        '5C8A38': 'HPE',
        'A89C8E': 'HPE',
        '7073CB': 'HPE',
        'E8F8D2': 'HPE',
        '408D5B': 'HPE',
        'B49691': 'HPE',
        'A44062': 'HPE',
        '001635': 'HPE',
        '6C3BE5': 'HPE',
        'E4E130': 'HPE',
        '001EC9': 'HPE',
        'CC37E0': 'HPE',
        'A82B6C': 'HPE',
        'FC15B4': 'HPE',
        'F4B95C': 'HPE',
        'B4B5B5': 'HPE',
        'A4BA4D': 'HPE',
        'B8B3DC': 'HPE',
        'C49C7D': 'HPE',
        '0C75BD': 'HPE',
        '94E18A': 'HPE',
        'AC7E8F': 'HPE',
        'A4BA4D': 'HPE',
        'D8D84C': 'HPE',
        'D8FF25': 'H3C',
        'EC1A59': 'H3C',
        '0010E0': 'H3C',
        '00E082': 'H3C',
        'B4B0FE': 'H3C',
        'A0D7D1': 'H3C',
        '20FBD8': 'H3C',
        '48E1D0': 'H3C',
        '000FB6': 'H3C',
        'D8A25E': 'Supermicro',
        'F0DB30': 'Supermicro',
        'FC198F': 'Supermicro',
        '5C5C3C': 'Supermicro',
        '000FD8': 'Supermicro',
        '78E7D1': 'Supermicro',
        '24L2D0': 'Supermicro',
        '3C94D5': 'Supermicro',
        '001B21': 'Supermicro',
        '0023AE': 'Supermicro',
        '002E2E': 'Supermicro',
        'F07G23': 'Supermicro',
        'E0C955': 'Supermicro',
        '4C3203': 'Supermicro',
        '4C3229': 'Supermicro',
        'EC1A59': 'H3C',
        '3C4A92': 'HPE',
        'C0B7E3': 'HPE',
    }

    return vendors.get(oui, '')


def parse_ip_range(range_str):
    """解析IP范围字符串，返回IP列表"""
    ips = []
    range_str = range_str.strip()

    # 格式: 192.168.1.1-254
    if '-' in range_str and not '/' in range_str:
        parts = range_str.split('.')
        if len(parts) == 4:
            base = '.'.join(parts[:3])
            end = parts[3]
            if '-' in end:
                start, end_range = end.split('-')
                for i in range(int(start), int(end_range) + 1):
                    ips.append(f'{base}.{i}')
    # 格式: 192.168.1.0/24 (CIDR)
    elif '/' in range_str:
        try:
            network = ip_network(range_str, strict=False)
            for ip in network:
                if not ip.is_loopback and not ip.is_reserved:
                    ips.append(str(ip))
        except:
            pass
    else:
        # 单个IP
        try:
            socket.inet_aton(range_str)
            ips.append(range_str)
        except:
            pass

    return ips


def identify_device_type(open_ports, snmp_data, ssh_banner, http_title, mac_vendor):
    """根据端口和指纹信息识别设备类型"""
    ports_set = set(open_ports)

    # 交换机/路由器特征
    if 161 in ports_set or 162 in ports_set:
        if snmp_data.get('sysDescr', ''):
            desc = snmp_data['sysDescr'].lower()
            if 'cisco' in desc or 'ios' in desc:
                return 'router', 'cisco_ios', 'Cisco'
            elif 'hp' in desc or 'procurve' in desc:
                return 'switch', 'hp_procurve', 'HP'
            elif 'juniper' in desc or 'junos' in desc:
                return 'router', 'juniper_junos', 'Juniper'
            elif 'fortinet' in desc or 'fortigate' in desc:
                return 'firewall', 'fortinet', 'Fortinet'
            elif 'dell' in desc or 'powerconnect' in desc:
                return 'switch', 'dell_os10', 'Dell'
            elif 'vmware' in desc:
                return 'virtual', 'vmware_esxi', 'VMware'
            elif 'windows' in desc:
                return 'server', 'windows', 'Microsoft'
            elif 'linux' in desc:
                return 'server', 'linux', 'Linux'
            return 'network', 'unknown', mac_vendor or 'Unknown'

    # SSH服务器
    if 22 in ports_set:
        if ssh_banner:
            banner = ssh_banner.lower()
            if 'cisco' in banner:
                return 'router', 'cisco_ios', 'Cisco'
            elif 'hp' in banner:
                return 'switch', 'hp_procurve', 'HP'
            elif 'vmware' in banner:
                return 'virtual', 'vmware_esxi', 'VMware'
            elif 'linux' in banner or 'ubuntu' in banner or 'debian' in banner or 'centos' in banner:
                return 'server', 'linux', 'Linux'
            elif 'windows' in banner:
                return 'server', 'windows', 'Microsoft'
        if mac_vendor:
            if mac_vendor.lower() in ['cisco', 'hp', 'juniper', 'dell', 'fortinet']:
                return 'network', 'unknown', mac_vendor

    # 数据库服务器
    if 3306 in ports_set:
        return 'server', 'linux', mac_vendor or 'MySQL'
    if 5432 in ports_set:
        return 'server', 'linux', mac_vendor or 'PostgreSQL'
    if 1433 in ports_set or 1434 in ports_set:
        return 'server', 'windows', mac_vendor or 'MSSQL'
    if 1521 in ports_set or 2483 in ports_set:
        return 'server', 'unknown', mac_vendor or 'Oracle'

    # Web服务器
    if 80 in ports_set or 443 in ports_set or 8080 in ports_set or 8443 in ports_set:
        if http_title:
            title_lower = http_title.lower()
            if 'login' in title_lower or '防火墙' in title_lower or 'forti' in title_lower:
                return 'firewall', 'fortinet', mac_vendor or 'Fortinet'
            if 'camera' in title_lower or 'nvr' in title_lower or '监控' in title_lower:
                return 'camera', 'unknown', mac_vendor or 'Hikvision'
            if 'router' in title_lower or 'tp-link' in title_lower or 'tplink' in title_lower:
                return 'router', 'unknown', 'TP-Link'
        if mac_vendor:
            if mac_vendor.lower() == 'hikvision':
                return 'camera', 'unknown', 'Hikvision'
            if mac_vendor.lower() == 'tp-link':
                return 'router', 'unknown', 'TP-Link'
            if mac_vendor.lower() == 'dell':
                return 'server', 'linux', 'Dell'
            if mac_vendor.lower() == 'hp':
                return 'server', 'linux', 'HP'
        return 'server', 'unknown', mac_vendor or 'Unknown'

    # 远程桌面
    if 3389 in ports_set:
        return 'server', 'windows', mac_vendor or 'Windows'

    # VNC
    if 5900 in ports_set:
        return 'server', 'unknown', mac_vendor or 'VNC'

    # 默认
    if mac_vendor:
        return 'unknown', 'unknown', mac_vendor

    return 'unknown', 'unknown', 'Unknown'


def scan_single_ip(ip_str, ports=None, timeout=3, scan_type='full'):
    """扫描单个IP，返回设备信息"""
    result = {
        'ip': ip_str,
        'is_online': False,
        'open_ports': [],
        'mac': '',
        'hostname': '',
        'device_type': 'unknown',
        'os_type': 'unknown',
        'vendor': 'Unknown',
        'response_time': None,
        'snmp_data': {},
        'ssh_banner': '',
        'http_title': '',
    }

    # 1. Ping检测
    is_online, response_time = ping_host(ip_str, timeout=timeout)
    if not is_online and scan_type in ['ping', 'full']:
        return None
    result['is_online'] = is_online
    result['response_time'] = response_time

    # 2. 端口扫描
    if ports is None:
        ports = DEFAULT_PORTS

    if scan_type in ['tcp', 'full']:
        open_ports = scan_ports(ip_str, ports, timeout=timeout)
        result['open_ports'] = open_ports

        # 3. 服务识别
        if 22 in open_ports and scan_type == 'full':
            result['ssh_banner'] = detect_ssh(ip_str, 22, timeout)

        if 80 in open_ports and scan_type == 'full':
            result['http_title'] = detect_http(ip_str, 80, timeout)

        if 443 in open_ports and scan_type == 'full':
            org = detect_https(ip_str, 443, timeout)
            if org:
                result['http_title'] = org

        # 4. SNMP检测
        if 161 in open_ports or scan_type == 'snmp':
            snmp_data = detect_snmp(ip_str, timeout=timeout)
            if snmp_data:
                result['snmp_data'] = snmp_data
                if 'sysDescr' in snmp_data:
                    result['snmp_data']['sysDescr'] = snmp_data['sysDescr']

    # 5. MAC地址和厂商
    mac_addr = get_mac_from_arp(ip_str)
    if mac_addr:
        result['mac'] = mac_addr
        result['vendor'] = get_mac_vendor(mac_addr) or result.get('vendor', 'Unknown')

    # 6. 设备类型识别
    device_type, os_type, vendor = identify_device_type(
        result['open_ports'],
        result['snmp_data'],
        result['ssh_banner'],
        result['http_title'],
        result['vendor']
    )
    result['device_type'] = device_type
    result['os_type'] = os_type
    result['vendor'] = vendor

    return result


def get_mac_from_arp(ip_str):
    """通过ARP获取MAC地址"""
    try:
        # 先ping一下建立ARP缓存
        subprocess.run(['ping', '-c', '1', '-W', '1', ip_str],
                      capture_output=True, timeout=2)
        time.sleep(0.5)

        result = subprocess.run(['arp', '-n', ip_str], capture_output=True, text=True, timeout=5)
        output = result.stdout

        # 解析MAC地址
        # 格式: 192.168.1.1  ether  xx:xx:xx:xx:xx:xx  C  eth0
        if '(' in output:
            for line in output.split('\n'):
                if '(' + ip_str + ')' in line or ip_str + ' ' in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if ':' in part and len(part) == 17:
                            return part.upper()
        # Windows格式
        else:
            for line in output.split('\n'):
                if ip_str in line:
                    parts = line.split()
                    for part in parts:
                        if ':' in part and len(part) == 17:
                            return part.upper()
    except:
        pass
    return ''


def run_discovery(target_ranges, ports=None, scan_type='full', timeout=5, snmp_community='public', progress_callback=None):
    """
    执行网络发现扫描

    Args:
        target_ranges: IP范围列表，如 ["192.168.1.1-254", "10.0.0.1-254"]
        ports: 要扫描的端口列表
        scan_type: 扫描类型
        timeout: 超时时间
        snmp_community: SNMP community字符串
        progress_callback: 进度回调函数 callback(scanned, total, found)

    Returns:
        发现的所有设备列表
    """
    # 解析所有IP
    all_ips = []
    for range_str in target_ranges:
        all_ips.extend(parse_ip_range(range_str))

    all_ips = list(set(all_ips))  # 去重
    total = len(all_ips)
    found_devices = []

    if total == 0:
        return []

    # 并发扫描
    max_workers = min(50, total)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {}
        for ip in all_ips:
            future = executor.submit(scan_single_ip, ip, ports, timeout, scan_type)
            futures[future] = ip

        completed = 0
        for future in concurrent.futures.as_completed(futures):
            completed += 1
            ip = futures[future]
            try:
                device = future.result()
                if device and device['is_online']:
                    found_devices.append(device)
            except Exception as e:
                pass

            if progress_callback:
                progress_callback(completed, total, len(found_devices))

    return found_devices


if __name__ == '__main__':
    # 测试扫描
    import json

    print('开始扫描 192.168.1.1-10 ...')
    devices = run_discovery(['192.168.1.1-10'], scan_type='full', timeout=3)

    print(f'\n发现 {len(devices)} 台设备:\n')
    for d in devices:
        print(f"  {d['ip']:15s} | {d['device_type']:10s} | {d['vendor']:15s} | ports: {d['open_ports']}")

    print('\n详细数据:')
    print(json.dumps(devices, indent=2, ensure_ascii=False))
