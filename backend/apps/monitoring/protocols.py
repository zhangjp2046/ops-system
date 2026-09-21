"""
监控数据采集协议支持模块
"""
import socket
import subprocess
import paramiko
import re
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class BaseProtocol(ABC):
    """采集协议基类"""
    
    name = "base"
    
    def __init__(self, host: str, port: int = None, timeout: int = 10):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.error = None
    
    @abstractmethod
    def test_connect(self) -> Dict[str, Any]:
        """测试连接"""
        pass
    
    @abstractmethod
    def collect(self) -> Dict[str, Any]:
        """采集数据"""
        pass


class PingProtocol(BaseProtocol):
    """Ping协议"""
    
    name = "ping"
    
    def test_connect(self) -> Dict[str, Any]:
        """测试Ping连通性"""
        result = {
            'success': False,
            'reachable': False,
            'response_time': None,
            'packet_loss': None,
            'error': None
        }
        
        try:
            # 使用ping -c 4 发送4个包
            cmd = ['ping', '-c', '4', '-W', str(self.timeout), self.host]
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=self.timeout + 5)
            output = output.decode('utf-8', errors='ignore')
            
            # 解析结果
            if '0% packet loss' in output or '0.0% packet loss' in output:
                result['reachable'] = True
                result['success'] = True
            
            # 提取响应时间
            match = re.search(r'(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)/(\d+\.\d+)', output)
            if match:
                result['response_time'] = float(match.group(1))  # avg
                result['min_rtt'] = float(match.group(1))
                result['max_rtt'] = float(match.group(2))
                result['avg_rtt'] = float(match.group(3))
            
            # 提取丢包率
            match = re.search(r'(\d+)% packet loss', output)
            if match:
                result['packet_loss'] = int(match.group(1))
                
        except subprocess.TimeoutExpired:
            result['error'] = '连接超时'
        except subprocess.CalledProcessError as e:
            output = e.output.decode('utf-8', errors='ignore') if e.output else str(e)
            if '100% packet loss' in output:
                result['error'] = '主机不可达'
            else:
                result['error'] = f'Ping失败: {output[:100]}'
        except Exception as e:
            result['error'] = f'错误: {str(e)}'
        
        return result
    
    def collect(self) -> Dict[str, Any]:
        """采集Ping数据"""
        return self.test_connect()


class PortCheckProtocol(BaseProtocol):
    """端口检测协议"""
    
    name = "port"
    
    def test_connect(self) -> Dict[str, Any]:
        """测试端口连通性"""
        result = {
            'success': False,
            'port_open': False,
            'response_time': None,
            'error': None
        }
        
        if not self.port:
            result['error'] = '端口号未指定'
            return result
        
        start_time = datetime.now()
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            connect_result = sock.connect_ex((self.host, self.port))
            end_time = datetime.now()
            
            response_time = (end_time - start_time).total_seconds() * 1000  # 转换为毫秒
            
            if connect_result == 0:
                result['success'] = True
                result['port_open'] = True
                result['response_time'] = round(response_time, 2)
            else:
                result['port_open'] = False
                result['error'] = f'端口 {self.port} 不可访问'
                
            sock.close()
            
        except socket.timeout:
            result['error'] = '连接超时'
        except socket.gaierror:
            result['error'] = '主机名解析失败'
        except Exception as e:
            result['error'] = f'错误: {str(e)}'
        
        return result
    
    def collect(self) -> Dict[str, Any]:
        """采集端口数据"""
        return self.test_connect()


class SSHProtocol(BaseProtocol):
    """SSH协议"""
    
    name = "ssh"
    
    def __init__(self, host: str, port: int = 22, username: str = '', password: str = '', 
                 key_file: str = None, timeout: int = 10):
        super().__init__(host, port, timeout)
        self.username = username
        self.password = password
        self.key_file = key_file
    
    def test_connect(self) -> Dict[str, Any]:
        """测试SSH连接"""
        result = {
            'success': False,
            'authenticated': False,
            'error': None
        }
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # 连接参数
            connect_kwargs = {
                'hostname': self.host,
                'port': self.port,
                'timeout': self.timeout,
                'look_for_keys': False,
                'allow_agent': False,
            }
            
            if self.key_file:
                connect_kwargs['key_filename'] = self.key_file
            elif self.password:
                connect_kwargs['password'] = self.password
            else:
                connect_kwargs['look_for_keys'] = True
            
            ssh.connect(**connect_kwargs)
            result['authenticated'] = True
            result['success'] = True
            ssh.close()
            
        except paramiko.AuthenticationException:
            result['error'] = '认证失败，请检查用户名密码'
        except paramiko.SSHException as e:
            result['error'] = f'SSH错误: {str(e)[:100]}'
        except socket.timeout:
            result['error'] = '连接超时'
        except socket.gaierror:
            result['error'] = '主机名解析失败'
        except Exception as e:
            result['error'] = f'错误: {str(e)}'
        
        return result
    
    def collect(self) -> Dict[str, Any]:
        """通过SSH采集系统信息"""
        result = self.test_connect()
        
        if not result['success']:
            return result
        
        # 如果连接成功，采集系统信息
        data = {
            'success': True,
            'hostname': None,
            'uptime': None,
            'cpu_usage': None,
            'memory_usage': None,
            'disk_usage': None,
            'load_average': None,
        }
        
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            connect_kwargs = {
                'hostname': self.host,
                'port': self.port,
                'timeout': self.timeout,
                'look_for_keys': False,
                'allow_agent': False,
            }
            
            if self.key_file:
                connect_kwargs['key_filename'] = self.key_file
            elif self.password:
                connect_kwargs['password'] = self.password
            else:
                connect_kwargs['look_for_keys'] = True
            
            ssh.connect(**connect_kwargs)
            
            commands = {
                'hostname': 'hostname',
                'uptime': 'uptime',
                'cpu_usage': "top -bn1 | grep 'Cpu(s)' | awk '{print $2}'",
                'memory': "free -m | grep Mem",
                'disk': "df -h / | tail -1 | awk '{print $5}'",
                'load': 'uptime | grep -oP "load average: \\K[^"]+"',
            }
            
            for key, cmd in commands.items():
                stdin, stdout, stderr = ssh.exec_command(cmd, timeout=self.timeout)
                output = stdout.read().decode('utf-8', errors='ignore').strip()
                if key == 'memory':
                    # 解析内存: total used free
                    parts = output.split()
                    if len(parts) >= 3:
                        data['memory_total'] = parts[0]
                        data['memory_used'] = parts[1]
                        data['memory_free'] = parts[2]
                        try:
                            used = int(parts[1])
                            total = int(parts[0])
                            data['memory_usage'] = round(used / total * 100, 1) if total > 0 else 0
                        except:
                            pass
                elif key == 'disk':
                    data['disk_usage'] = output.replace('%', '')
                elif key == 'load':
                    data['load_average'] = output
                else:
                    data[key] = output
            
            ssh.close()
            
        except Exception as e:
            data['error'] = str(e)
        
        result['data'] = data
        return result


class SNMPProtocol(BaseProtocol):
    """SNMP协议 — 支持多版本测试与详细数据采集"""

    name = "snmp"

    # 常用系统OID
    COMMON_OIDS = {
        'sysDescr': '1.3.6.1.2.1.1.1.0',
        'sysObjectID': '1.3.6.1.2.1.1.2.0',
        'sysUpTime': '1.3.6.1.2.1.1.3.0',
        'sysContact': '1.3.6.1.2.1.1.4.0',
        'sysName': '1.3.6.1.2.1.1.5.0',
        'sysLocation': '1.3.6.1.2.1.1.6.0',
        'sysServices': '1.3.6.1.2.1.1.7.0',
        'ifNumber': '1.3.6.1.2.1.2.1.0',
    }

    def __init__(self, host: str, port: int = 161, community: str = 'public',
                 oid: str = None, version: str = '2c', timeout: int = 10):
        super().__init__(host, port, timeout)
        self.community = community
        self.oid = oid
        self.version = version  # v1, v2c, v3

    def _check_snmp_tools(self) -> bool:
        """检查系统是否安装了 snmp 命令行工具"""
        try:
            r = subprocess.run(['which', 'snmpget'], capture_output=True, timeout=5)
            return r.returncode == 0
        except Exception:
            return False

    def _snmp_raw_cmd(self, version: str, oid: str, extra_flags: list = None) -> dict:
        """执行原始 snmpget 命令，返回完整输出"""
        ver_flag = '1' if version == 'v1' else '2c' if version == 'v2c' else '3'
        cmd = [
            'snmpget', '-v', ver_flag, '-c', self.community,
            '-t', str(self.timeout), '-r', '1',
            f'{self.host}:{self.port}', oid
        ]
        if extra_flags:
            cmd.extend(extra_flags)

        result = {'cmd': ' '.join(cmd), 'stdout': '', 'stderr': '', 'exit_code': -1, 'success': False}

        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout + 5
            )
            result['exit_code'] = r.returncode
            result['stdout'] = r.stdout.strip()
            result['stderr'] = r.stderr.strip()
            result['success'] = r.returncode == 0
        except subprocess.TimeoutExpired:
            result['stderr'] = f'Timeout (>{self.timeout}s)'
        except FileNotFoundError:
            result['stderr'] = 'snmpget not found'
        except Exception as e:
            result['stderr'] = str(e)

        return result

    def _snmp_get_value(self, version: str, oid: str) -> str:
        """获取单个 OID 的值（简洁）"""
        try:
            ver_flag = '1' if version == 'v1' else '2c' if version == 'v2c' else '3'
            cmd = [
                'snmpget', '-v', ver_flag, '-c', self.community,
                '-Ovq', '-t', str(self.timeout), '-r', '1',
                f'{self.host}:{self.port}', oid
            ]
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=self.timeout + 5)
            return output.decode('utf-8', errors='ignore').strip().strip('"').strip("'")
        except Exception:
            return ''

    def _snmp_walk(self, oid: str) -> Dict[str, str]:
        """批量查询，返回 {full_oid: value}"""
        result = {}
        try:
            # 只拿值
            cmd1 = ['snmpwalk', '-v', '2c', '-c', self.community, '-Oqv',
                    '-t', str(self.timeout), f'{self.host}:{self.port}', oid]
            out1 = subprocess.check_output(cmd1, stderr=subprocess.DEVNULL, timeout=self.timeout + 10)
            values = out1.decode('utf-8', errors='ignore').strip().split('\n')

            # 拿完整OID
            cmd2 = ['snmpwalk', '-v', '2c', '-c', self.community, '-On',
                    '-t', str(self.timeout), f'{self.host}:{self.port}', oid]
            out2 = subprocess.check_output(cmd2, stderr=subprocess.DEVNULL, timeout=self.timeout + 10)
            lines = [l.strip() for l in out2.decode('utf-8', errors='ignore').strip().split('\n') if l.strip()]

            for i, val in enumerate(values):
                if i < len(lines):
                    full_oid = lines[i].split('=')[0].strip()
                    result[full_oid] = val.strip().strip('"')
        except Exception:
            pass
        return result

    def test_connect(self) -> Dict[str, Any]:
        """全面SNMP测试：多版本兼容性 + 多OID数据采集 + 原始输出"""
        result = {
            'success': False,
            'available': False,
            'error': None,
            'version_tests': {},      # 各版本测试结果
            'system_info': {},        # 系统信息（解析后）
            'device_info': {},        # 设备摘要
            'oids': {},               # 所有查询的OID结果
            'raw_outputs': {},        # 原始snmpget输出
            'walk_data': {},          # walk数据
            'interface_summary': {},  # 接口摘要
        }

        # 1. 检查工具
        if not self._check_snmp_tools():
            result['error'] = 'snmp-utils未安装，请执行: apt install snmp-utils'
            return result

        # 2. 版本兼容性测试 —— 逐一尝试 v1, v2c, v3
        versions_to_try = ['v2c']
        if self.version == 'v1':
            versions_to_try = ['v1', 'v2c']
        elif self.version == 'v3':
            versions_to_try = ['v3', 'v2c', 'v1']

        best_version = None
        for ver in versions_to_try:
            sysdescr_oid = '1.3.6.1.2.1.1.1.0'
            raw = self._snmp_raw_cmd(ver, sysdescr_oid)
            raw_data = {
                'cmd': raw['cmd'],
                'stdout': raw['stdout'],
                'stderr': raw['stderr'],
                'exit_code': raw['exit_code'],
                'success': raw['success'],
            }

            if raw['success']:
                best_version = ver
                result['version_tests'][ver] = {
                    'status': 'ok',
                    'value': raw['stdout'][:200],
                    'raw': raw_data,
                }
                # 只要 v2c 成功就不再往下试
                if ver == 'v2c':
                    break
            else:
                err_msg = raw['stderr'][:150] if raw['stderr'] else raw['stdout'][:150]
                result['version_tests'][ver] = {
                    'status': 'failed',
                    'error': err_msg,
                    'raw': raw_data,
                }

        if not best_version:
            result['error'] = '所有SNMP版本均失败。检查community string、IP和防火墙(udp 161)'
            # 把各版本的 raw 输出也带回，方便排查
            result['errors'] = {
                ver: info.get('error', 'unknown')
                for ver, info in result['version_tests'].items()
            }
            return result

        result['success'] = True
        result['available'] = True
        result['snmp_version'] = best_version

        # 3. 批量查询常用系统 OID
        oid_results = {}
        for name, oid in self.COMMON_OIDS.items():
            val = self._snmp_get_value(best_version, oid)
            if val:
                oid_results[name] = val
        result['oids'] = oid_results

        # 4. 解析 sysDescr — 识别设备类型
        sys_descr = oid_results.get('sysDescr', '')
        result['sysDescr'] = sys_descr
        if sys_descr:
            device_type = 'unknown'
            sys_lower = sys_descr.lower()
            if any(k in sys_lower for k in ['cisco', 'ios', 'catalyst']):
                device_type = 'cisco'
            elif any(k in sys_lower for k in ['huawei', 'vrp']):
                device_type = 'huawei'
            elif any(k in sys_lower for k in ['h3c', 'comware', 'h3']):
                device_type = 'h3c'
            elif any(k in sys_lower for k in ['ruijie', '锐捷']):
                device_type = 'ruijie'
            elif any(k in sys_lower for k in ['linux', 'ubuntu', 'centos', 'debian']):
                device_type = 'linux_server'
            elif any(k in sys_lower for k in ['windows', 'microsoft']):
                device_type = 'windows_server'
            elif any(k in sys_lower for k in ['fortinet', 'fortigate']):
                device_type = 'fortinet'
            elif any(k in sys_lower for k in ['juniper', 'junos']):
                device_type = 'juniper'
            elif any(k in sys_lower for k in ['hp', 'procurve', 'aruba']):
                device_type = 'hp_aruba'

            result['device_type'] = device_type

        # 5. 构建 device_info 摘要
        result['device_info'] = {
            'hostname': oid_results.get('sysName', ''),
            'location': oid_results.get('sysLocation', ''),
            'contact': oid_results.get('sysContact', ''),
            'os': sys_descr[:120] if sys_descr else '',
            'uptime': oid_results.get('sysUpTime', ''),
            'interface_count': oid_results.get('ifNumber', ''),
            'device_type': result.get('device_type', 'unknown'),
        }

        # 6. 尝试采集接口信息（仅 v2c 有效时做）
        if best_version == 'v2c' or best_version == 'v1':
            try:
                if_name_map = self._snmp_walk('1.3.6.1.2.1.2.2.1.2')
                if_status_map = self._snmp_walk('1.3.6.1.2.1.2.2.1.8')
                if_speed_map = self._snmp_walk('1.3.6.1.2.1.2.2.1.5')

                result['walk_data']['ifDescr'] = if_name_map
                result['walk_data']['ifOperStatus'] = if_status_map
                result['walk_data']['ifSpeed'] = if_speed_map

                status_map = {1: 'up', 2: 'down', 3: 'testing', 4: 'unknown', 5: 'dormant', 6: 'notPresent', 7: 'lowerLayerDown'}
                up_count = 0
                down_count = 0
                interfaces = []

                for oid, name in if_name_map.items():
                    idx = oid.split('.')[-1]
                    try:
                        idx_int = int(idx)
                    except ValueError:
                        continue
                    status_val = int(if_status_map.get(f'.1.3.6.1.2.1.2.2.1.8.{idx}', 4))
                    speed = int(if_speed_map.get(f'.1.3.6.1.2.1.2.2.1.5.{idx}', 0))

                    st = status_map.get(status_val, 'unknown')
                    if st == 'up':
                        up_count += 1
                    elif st == 'down':
                        down_count += 1

                    interfaces.append({
                        'index': idx_int,
                        'name': name,
                        'status': st,
                        'speed_bps': speed,
                        'speed_display': f'{speed // 1000000}Mbps' if speed >= 1000000 else f'{speed // 1000}Kbps',
                    })

                result['interface_summary'] = {
                    'total': len(interfaces),
                    'up': up_count,
                    'down': down_count,
                    'interfaces': interfaces[:20],  # 最多列出20个
                }

                # 添加到 device_info
                result['device_info']['interface_total'] = len(interfaces)
                result['device_info']['interface_up'] = up_count
                result['device_info']['interface_down'] = down_count

            except Exception as e:
                result['walk_data']['error'] = str(e)[:100]

        # 7. 尝试采集存储/CPU（HOST-RESOURCES-MIB，服务器类设备）
        try:
            storage_desc = self._snmp_walk('1.3.6.1.2.1.25.2.3.1.3')
            if storage_desc:
                storage_size = self._snmp_walk('1.3.6.1.2.1.25.2.3.1.5')
                storage_used = self._snmp_walk('1.3.6.1.2.1.25.2.3.1.6')
                storage_units = self._snmp_walk('1.3.6.1.2.1.25.2.3.1.4')

                def fix_key(d):
                    return {k if k.startswith('.') else '.' + k: v for k, v in d.items()}
                storage_desc = fix_key(storage_desc)
                storage_size = fix_key(storage_size)
                storage_used = fix_key(storage_used)
                storage_units = fix_key(storage_units)

                storage_items = []
                for oid, desc in storage_desc.items():
                    idx = oid.split('.')[-1]
                    try:
                        sz = int(storage_size.get(f'.1.3.6.1.2.1.25.2.3.1.5.{idx}', 0))
                        used = int(storage_used.get(f'.1.3.6.1.2.1.25.2.3.1.6.{idx}', 0))
                        unit = int(storage_units.get(f'.1.3.6.1.2.1.25.2.3.1.4.{idx}', 4096))
                        sz_mb = round(sz * unit / 1024 / 1024, 2)
                        used_mb = round(used * unit / 1024 / 1024, 2)
                        pct = round(used / sz * 100, 1) if sz > 0 else 0
                        storage_items.append({
                            'name': desc,
                            'size_mb': sz_mb,
                            'used_mb': used_mb,
                            'used_pct': pct,
                        })
                    except (ValueError, KeyError):
                        continue

                result['storage'] = storage_items[:20]

            # CPU
            cpu_data = self._snmp_walk('1.3.6.1.2.1.25.3.3.1.2')
            if cpu_data:
                cpus = []
                for oid, val in cpu_data.items():
                    try:
                        cpus.append(int(val))
                    except ValueError:
                        continue
                result['cpu'] = {'count': len(cpus), 'loads': cpus, 'avg_load': round(sum(cpus) / len(cpus), 1) if cpus else 0}
                result['device_info']['cpu_count'] = len(cpus)
                result['device_info']['cpu_avg_load'] = result['cpu']['avg_load']

        except Exception as e:
            pass  # HR MIB 仅服务器类设备支持，静默忽略

        # 8. 对自定义 oid 进行一次查询
        if self.oid:
            custom_raw = self._snmp_raw_cmd(best_version, self.oid)
            result['custom_oid'] = {
                'oid': self.oid,
                'raw_cmd': custom_raw['cmd'],
                'stdout': custom_raw['stdout'],
                'stderr': custom_raw['stderr'],
                'success': custom_raw['success'],
            }

        return result

    def _snmp_get(self, oid: str) -> Optional[str]:
        """单个 OID 查询"""
        try:
            cmd = ['snmpget', '-v', '2c', '-c', self.community, '-Ovq', '-t', str(self.timeout), self.host, oid]
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=self.timeout + 5)
            val = output.decode('utf-8', errors='ignore').strip(); return val.strip('"').strip("'")
        except:
            return None

    def _snmp_walk(self, oid: str) -> Dict[str, str]:
        """批量 OID 查询，返回 {oid: value}"""
        result = {}
        try:
            cmd = ['snmpwalk', '-v', '2c', '-c', self.community, '-Oqv', '-t', str(self.timeout), self.host, oid]
            output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=self.timeout + 10)
            values = output.decode('utf-8', errors='ignore').strip().split('\n')

            cmd2 = ['snmpwalk', '-v', '2c', '-c', self.community, '-On', '-t', str(self.timeout), self.host, oid]
            output2 = subprocess.check_output(cmd2, stderr=subprocess.DEVNULL, timeout=self.timeout + 10)
            oids = [line.strip() for line in output2.decode('utf-8', errors='ignore').strip().split('\n') if line.strip()]

            for i, val in enumerate(values):
                if i < len(oids):
                    full_oid = oids[i].split('=')[0].strip() if '=' in oids[i] else oids[i]
                    result[full_oid] = val.strip().strip('"')
        except:
            pass
        return result

    def collect(self) -> Dict[str, Any]:
        """采集详细SNMP设备信息"""
        result = self.test_connect()

        if not result['success']:
            return result

        data = {
            'success': True,
            'device_info': {},
            'system': {},
            'cpu': [],
            'memory': {},
            'disk': [],
            'network': [],
            'metrics': {}
        }

        try:
            # ========== 基本系统信息 ==========
            sys_oids = {
                'sysDescr': '1.3.6.1.2.1.1.1.0',       # 系统描述
                'sysObjectID': '1.3.6.1.2.1.1.2.0',    # 设备类型OID
                'sysUpTime': '1.3.6.1.2.1.1.3.0',      # 运行时间
                'sysContact': '1.3.6.1.2.1.1.4.0',     # 联系人
                'sysName': '1.3.6.1.2.1.1.5.0',        # 主机名
                'sysLocation': '1.3.6.1.2.1.1.6.0',    # 位置
                'sysServices': '1.3.6.1.2.1.1.7.0',    # 服务层
            }
            for name, oid in sys_oids.items():
                val = self._snmp_get(oid)
                if val is not None:
                    data['system'][name] = val

            # 解析运行时间
            uptime_str = data['system'].get('sysUpTime', '')
            if 'days' in uptime_str:
                data['system']['uptime_display'] = uptime_str.split(')')[1].strip() if ')' in uptime_str else uptime_str
            else:
                data['system']['uptime_display'] = uptime_str

            # ========== CPU 信息 (HOST-RESOURCES-MIB) ==========
            cpu_oids = self._snmp_walk('1.3.6.1.2.1.25.3.3.1.2')  # hrProcessorLoad
            for oid, val in cpu_oids.items():
                idx = oid.split('.')[-1]
                data['cpu'].append({
                    'index': int(idx),
                    'load': int(val),
                    'name': f'CPU {idx}'
                })

            # ========== 内存和磁盘 (HOST-RESOURCES-MIB) ==========
            import time as _time
            storage_desc = self._snmp_walk('1.3.6.1.2.1.25.2.3.1.3')
            storage_size = self._snmp_walk('1.3.6.1.2.1.25.2.3.1.5')
            storage_used = self._snmp_walk('1.3.6.1.2.1.25.2.3.1.6')
            storage_units = self._snmp_walk('1.3.6.1.2.1.25.2.3.1.4')

            # 如果 walk 返回的 key 不是 . 开头，修复格式
            def fix_key(oid_dict):
                return {k if k.startswith('.') else '.' + k: v for k, v in oid_dict.items()}

            storage_desc = fix_key(storage_desc)
            storage_size = fix_key(storage_size)
            storage_used = fix_key(storage_used)
            storage_units = fix_key(storage_units)

            for oid, desc in storage_desc.items():
                idx = oid.split('.')[-1]
                size = int(storage_size.get(f'.1.3.6.1.2.1.25.2.3.1.5.{idx}', 0))
                used = int(storage_used.get(f'.1.3.6.1.2.1.25.2.3.1.6.{idx}', 0))
                units = int(storage_units.get(f'.1.3.6.1.2.1.25.2.3.1.4.{idx}', 4096))

                size_mb = round(size * units / 1024 / 1024, 2)
                used_mb = round(used * units / 1024 / 1024, 2)
                free_mb = round(size_mb - used_mb, 2)
                pct = round(used / size * 100, 1) if size > 0 else 0

                item = {
                    'index': int(idx),
                    'name': desc,
                    'size_mb': size_mb,
                    'used_mb': used_mb,
                    'free_mb': free_mb,
                    'used_pct': pct,
                }

                if 'Memory' in desc:
                    data['memory'][desc] = item
                elif '\\' in desc or '/' in desc:
                    data['disk'].append(item)

            # ========== 网络接口 ==========
            try:
                if_descr = self._snmp_walk('1.3.6.1.2.1.2.2.1.2')       # ifDescr
                if_status = self._snmp_walk('1.3.6.1.2.1.2.2.1.8')       # ifOperStatus
                if_speed = self._snmp_walk('1.3.6.1.2.1.2.2.1.5')        # ifSpeed

                status_map = {1: 'up', 2: 'down', 3: 'testing', 4: 'unknown', 5: 'dormant'}

                for oid, name in if_descr.items():
                    idx = oid.split('.')[-1]
                    try:
                        idx_int = int(idx)
                    except ValueError:
                        continue  # 跳过无法解析的 OID

                    status_val = int(if_status.get(f'.1.3.6.1.2.1.2.2.1.8.{idx}', 4))
                    speed = int(if_speed.get(f'.1.3.6.1.2.1.2.2.1.5.{idx}', 0))

                    data['network'].append({
                        'index': idx_int,
                        'name': name,
                        'status': status_map.get(status_val, 'unknown'),
                        'speed_bps': speed,
                        'speed_display': f'{speed // 1000000}Mbps' if speed >= 1000000 else f'{speed // 1000}Kbps',
                    })
            except Exception:
                pass  # 网络接口采集失败不影响整体

            # ========== 汇总 ==========
            data['device_info'] = {
                'hostname': data['system'].get('sysName', ''),
                'os': data['system'].get('sysDescr', '')[:100],
                'uptime': data['system'].get('uptime_display', ''),
                'cpu_count': len(data['cpu']),
                'cpu_avg_load': round(sum(c['load'] for c in data['cpu']) / max(len(data['cpu']), 1), 1),
                'disk_count': len(data['disk']),
                'disk_total_mb': round(sum(d['size_mb'] for d in data['disk']), 2),
                'disk_used_mb': round(sum(d['used_mb'] for d in data['disk']), 2),
                'network_count': len(data['network']),
                'network_up': sum(1 for n in data['network'] if n['status'] == 'up'),
            }

        except Exception as e:
            import traceback
            data['error'] = f'{str(e)}\n{traceback.format_exc()[:500]}'

        result['data'] = data
        return result


class DatabaseProtocol(BaseProtocol):
    """数据库协议"""
    
    name = "database"
    
    def __init__(self, host: str, port: int = None, database: str = None,
                 username: str = '', password: str = '', db_type: str = 'mysql', timeout: int = 10):
        super().__init__(host, port, timeout)
        self.database = database
        self.username = username
        self.password = password
        self.db_type = db_type.lower()  # mysql, postgresql, mssql, oracle
    
    def test_connect(self) -> Dict[str, Any]:
        """测试数据库连接"""
        result = {
            'success': False,
            'connected': False,
            'version': None,
            'error': None
        }
        
        if self.db_type == 'mysql':
            return self._test_mysql()
        elif self.db_type == 'postgresql':
            return self._test_postgresql()
        elif self.db_type == 'mssql':
            return self._test_mssql()
        elif self.db_type == 'oracle':
            return self._test_oracle()
        else:
            result['error'] = f'不支持的数据库类型: {self.db_type}'
            return result
    
    def _test_mysql(self) -> Dict[str, Any]:
        """全面 MySQL 测试：版本、变量、数据库列表、引擎、状态、原始SQL"""
        result = {
            'success': False,
            'connected': False,
            'version': None,
            'error': None,
            'db_info': {},       # 数据库信息
            'variables': {},     # 关键系统变量
            'databases': [],     # 数据库列表
            'engines': [],       # 存储引擎
            'status': {},        # 运行状态
            'raw_queries': {},   # 原始 SQL 输出
        }

        try:
            import pymysql
            conn = pymysql.connect(
                host=self.host,
                port=self.port or 3306,
                user=self.username,
                password=self.password,
                database=self.database or 'mysql',
                connect_timeout=self.timeout
            )
            cursor = conn.cursor()

            # 1. 版本
            cursor.execute('SELECT VERSION() AS v')
            row = cursor.fetchone()
            result['version'] = row[0] if row else ''

            # 2. 数据库列表
            cursor.execute('SHOW DATABASES')
            result['databases'] = [r[0] for r in cursor.fetchall()]

            # 3. 存储引擎
            cursor.execute("SHOW ENGINES")
            engines = cursor.fetchall()
            result['engines'] = [
                {'engine': e[0], 'support': e[1], 'comment': e[2] or ''}
                for e in engines if e[1] in ('YES', 'DEFAULT')
            ]

            # 4. 关键系统变量
            var_names = [
                'version', 'version_comment', 'hostname', 'port',
                'max_connections', 'max_allowed_packet',
                'character_set_server', 'collation_server',
                'innodb_buffer_pool_size', 'innodb_log_file_size',
                'wait_timeout', 'interactive_timeout',
                'datadir', 'basedir', 'tmpdir',
                'log_bin', 'server_id', 'thread_cache_size',
                'query_cache_type', 'have_ssl',
            ]
            for vn in var_names:
                try:
                    cursor.execute(f"SHOW VARIABLES LIKE '{vn}'")
                    row = cursor.fetchone()
                    if row:
                        result['variables'][vn] = row[1]
                except Exception:
                    pass

            # 5. 运行状态
            status_names = [
                'Uptime', 'Threads_connected', 'Threads_running',
                'Connections', 'Questions', 'Queries',
                'Bytes_received', 'Bytes_sent',
                'Slow_queries', 'Open_tables', 'Table_locks_immediate',
                'Table_locks_waited', 'Innodb_buffer_pool_read_requests',
                'Innodb_buffer_pool_reads', 'Innodb_rows_read',
                'Created_tmp_disk_tables', 'Select_full_join',
                'Aborted_connects', 'Max_used_connections',
            ]
            for sn in status_names:
                try:
                    cursor.execute(f"SHOW GLOBAL STATUS LIKE '{sn}'")
                    row = cursor.fetchone()
                    if row:
                        result['status'][sn] = row[1]
                except Exception:
                    pass

            # 6. 可用数据库数量
            result['db_count'] = len(result['databases'])
            result['db_info'] = {
                'db_count': len(result['databases']),
                'max_connections': result['variables'].get('max_connections', ''),
                'current_connections': result['status'].get('Threads_connected', ''),
                'uptime_seconds': result['status'].get('Uptime', ''),
                'datadir': result['variables'].get('datadir', ''),
                'version_comment': result['variables'].get('version_comment', ''),
                'hostname': result['variables'].get('hostname', self.host),
                'character_set': result['variables'].get('character_set_server', ''),
                'collation': result['variables'].get('collation_server', ''),
                'log_bin': result['variables'].get('log_bin', ''),
            }

            result['connected'] = True
            result['success'] = True

            cursor.close()
            conn.close()

        except ImportError:
            result['error'] = 'pymysql未安装: pip install pymysql'
        except pymysql.err.OperationalError as e:
            result['error'] = f'连接失败: {str(e)[:150]}'
            # 解析常见错误码
            err_str = str(e)
            if '1045' in err_str:
                result['error'] = '认证失败(1045): 用户名或密码错误'
            elif '1049' in err_str:
                result['error'] = f'数据库不存在(1049): {self.database}'
            elif '2003' in err_str:
                result['error'] = '无法连接(2003): 请检查MySQL服务是否运行、端口是否正确、防火墙是否放行'
            elif '2005' in err_str:
                result['error'] = '未知主机(2005): 主机名解析失败'
        except Exception as e:
            result['error'] = f'错误: {str(e)}'

        return result
    
    def _test_postgresql(self) -> Dict[str, Any]:
        result = {
            'success': False,
            'connected': False,
            'version': None,
            'error': None
        }
        
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=self.host,
                port=self.port or 5432,
                user=self.username,
                password=self.password,
                dbname=self.database,
                connect_timeout=self.timeout
            )
            
            cursor = conn.cursor()
            cursor.execute('SELECT version()')
            version = cursor.fetchone()
            result['version'] = version[0] if version else None
            result['connected'] = True
            result['success'] = True
            
            cursor.close()
            conn.close()
            
        except ImportError:
            result['error'] = 'psycopg2未安装: pip install psycopg2-binary'
        except Exception as e:
            result['error'] = f'错误: {str(e)}'
        
        return result
    
    def _test_mssql(self) -> Dict[str, Any]:
        """全面 MSSQL 测试：版本、数据库列表、配置、连接池状态、原始 tsql 输出"""
        result = {
            'success': False,
            'connected': False,
            'version': None,
            'error': None,
            'db_info': {},         # 数据库摘要
            'databases': [],       # 数据库列表
            'config': {},          # 配置参数
            'status': {},          # 运行状态
            'raw_output': '',      # 原始 tsql 输出
        }

        try:
            import os

            # TDS 版本列表：7.4(MSSQL2012+) → 7.3(MSSQL2008/R2) → 7.2(MSSQL2005) → 7.1(MSSQL2000)
            TDS_VERSIONS = ['7.4', '7.3', '7.2', '7.1']
            # 记录连接成功的 TDS 版本
            connected_tds = None

            for tds_ver in TDS_VERSIONS:
                conf_path = f'/tmp/freetds_{tds_ver}.conf'
                if not os.path.exists(conf_path):
                    with open(conf_path, 'w') as f:
                        f.write(f'[global]\n    tds version = {tds_ver}\n    encryption = off\n    client charset = UTF-8\n')

                def tsql_query(sql_block: str, tds_ver=tds_ver, conf_path=conf_path) -> str:
                    """执行单个 tsql 查询块，返回 stdout"""
                    cmd = (f'TDSVER={tds_ver} tsql -H {self.host} -p {self.port or 1433} '
                           f'-U {self.username} -P "{self.password}" '
                           f'-D {self.database or "master"}')
                    proc = subprocess.Popen(
                        cmd, shell=True, stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                        env={**os.environ, 'FREETDSCONF': conf_path}
                    )
                    stdout, stderr = proc.communicate(
                        input=sql_block, timeout=self.timeout + 5
                    )
                    return stdout, stderr

                # 用版本查询测试连接
                stdout, stderr = tsql_query("SELECT @@VERSION AS v\nGO\n")
                if 'Microsoft SQL Server' in stdout or 'Adaptive Server' in stdout:
                    connected_tds = tds_ver
                    result['raw_output'] += f'-- TDS版本: {tds_ver} --\n{stdout[:200]}\n'
                    break

                # 如果所有版本都失败了
                if tds_ver == TDS_VERSIONS[-1]:
                    if 'Msg 18456' in stdout or 'Login failed' in stdout:
                        result['error'] = '登录失败(18456): 请检查用户名密码和SQL Server身份验证模式'
                    elif 'Adaptive Server connection failed' in stdout or 'connection failed' in stdout:
                        result['error'] = '连接失败: 请检查地址、端口和防火墙，确认SQL Browser服务已启动'
                    elif 'timeout' in stderr.lower() or 'timeout' in stdout.lower():
                        result['error'] = '连接超时: 请检查网络连通性和防火墙'
                    else:
                        result['error'] = f'MSSQL连接异常(所有TDS版本均失败): {stderr[:200] if stderr else stdout[:200]}'
                    return result

            # 重新创建 tsql_query 闭包，使用已连接的 TDS 版本
            conf_path = f'/tmp/freetds_{connected_tds}.conf'

            def tsql_query(sql_block: str) -> str:
                cmd = (f'TDSVER={connected_tds} tsql -H {self.host} -p {self.port or 1433} '
                       f'-U {self.username} -P "{self.password}" '
                       f'-D {self.database or "master"}')
                proc = subprocess.Popen(
                    cmd, shell=True, stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    env={**os.environ, 'FREETDSCONF': conf_path}
                )
                stdout, stderr = proc.communicate(
                    input=sql_block, timeout=self.timeout + 5
                )
                return stdout, stderr

            # 拆成多个短查询避免一次数据太多
            queries = {
                'version': "SELECT @@VERSION AS v\nGO\n",
                'databases': "SELECT name FROM sys.databases WHERE state = 0 ORDER BY name\nGO\n",
                'config': """
SELECT name, value_in_use FROM sys.configurations
WHERE name IN (
 'max server memory (MB)', 'min server memory (MB)',
 'user connections', 'max degree of parallelism',
 'fill factor (%)', 'backup compression default',
 'blocked process threshold (s)',
 'max worker threads', 'recovery interval (min)'
)
GO
""",
                'status': """
SELECT
 (SELECT cntr_value FROM sys.dm_os_performance_counters
  WHERE counter_name = 'User Connections') AS user_connections,
 (SELECT cntr_value FROM sys.dm_os_performance_counters
  WHERE counter_name = 'Batch Requests/sec') AS batch_requests,
 (SELECT cntr_value FROM sys.dm_os_performance_counters
  WHERE (object_name LIKE '%:Buffer Manager%' OR object_name = 'SQLServer:Buffer Manager')
   AND counter_name = 'Page life expectancy')
  AS page_life_expectancy,
 (SELECT cntr_value FROM sys.dm_os_performance_counters
  WHERE (object_name LIKE '%:General Statistics%' OR object_name = 'SQLServer:General Statistics')
   AND counter_name = 'Processes blocked')
  AS processes_blocked
GO
""",
                'session_info': """
SELECT COUNT(*) AS total_sessions,
 SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) AS running,
 SUM(CASE WHEN status = 'sleeping' THEN 1 ELSE 0 END) AS sleeping
FROM sys.dm_exec_sessions WHERE is_user_process = 1
GO
""",
                'disk_usage': """
SELECT
    DB_NAME(d.database_id) AS db,
    SUM(CASE WHEN d.type = 0 THEN CAST(d.size AS BIGINT) ELSE 0 END) * 8 / 1024 AS data_mb,
    SUM(CASE WHEN d.type = 1 THEN CAST(d.size AS BIGINT) ELSE 0 END) * 8 / 1024 AS log_mb
FROM sys.master_files d
GROUP BY d.database_id
ORDER BY db
GO
""",
                'disk_usage_simple': """
SELECT
    DB_NAME(database_id) AS db,
    CAST(SUM(CASE WHEN type = 0 THEN size ELSE 0 END) AS BIGINT) * 8 / 1024 AS total_mb
FROM sys.master_files
GROUP BY database_id
ORDER BY db
GO
""",
            }

            # 版本查询输出已经得到，解析版本
            for line in stdout.split('\n'):
                if 'Microsoft SQL Server' in line:
                    v = line.strip()
                    v = re.sub(r'(?:\d+>\s*)+', '', v)
                    result['version'] = v[:200]
                    break

            result['success'] = True
            result['connected'] = True

            # --- 数据库列表 ---
            stdout, stderr = tsql_query(queries['databases'])
            result['raw_output'] += f'\n-- 数据库列表 --\n{stdout[:300]}\n'
            dbs = []
            capture = False
            for line in stdout.split('\n'):
                line = line.strip()
                # 去掉 tsql prompt 前缀如 "1> 2> name" → "name"
                clean = re.sub(r'^\d+>\s*(?:\d+>\s*)*', '', line)
                # 过滤 locale/encoding/tsql 调试行
                if not clean or clean.startswith('locale') or clean.startswith('using default'):
                    continue
                if clean.startswith('name') or 'name' in clean and '---' in stdout:
                    capture = True
                    continue
                if capture and clean and not clean.startswith('(') and not clean.startswith('-')\
                   and 'rows)' not in clean and clean not in ('', 'GO'):
                    dbs.append(clean)
            result['databases'] = dbs[:50]

            # --- 配置参数 ---
            stdout, stderr = tsql_query(queries['config'])
            result['raw_output'] += f'\n-- 配置 --\n{stdout[:500]}\n'
            # 解析：用 \t 分割，跳过表头行（列名全是字母/下划线）
            for line in stdout.split('\n'):
                line = line.strip()
                clean = re.sub(r'^\d+>\s*(?:\d+>\s*)*', '', line)
                if not clean or clean.startswith('locale') or clean.startswith('using default'):
                    continue
                if not clean or clean.startswith('(') or clean.startswith('-')\
                   or 'rows)' in clean or clean in ('', 'GO'):
                    continue
                # 用 tab 分割精确提取 name/value_in_use
                parts = clean.split('\t')
                if len(parts) >= 2:
                    name = parts[0].strip()
                    val = parts[1].strip()
                    # 跳过表头行（列名为英文单词）
                    if name in ('name', 'value_in_use', 'description', 'config_name'):
                        continue
                    # 跳过全是字母的假数据行
                    if re.match(r'^[a-zA-Z_]+$', name):
                        continue
                    result['config'][name] = val

            # --- 运行状态 ---
            stdout, stderr = tsql_query(queries['status'])
            result['raw_output'] += f'\n-- 状态 --\n{stdout[:500]}\n'
            for line in stdout.split('\n'):
                line = line.strip()
                clean = re.sub(r'^\d+>\s*(?:\d+>\s*)*', '', line)
                if not clean or clean.startswith('locale') or clean.startswith('using default'):
                    continue
                if not clean or clean.startswith('(') or clean.startswith('-')\
                   or 'rows)' in clean:
                    continue
                parts = clean.split('\t')
                if len(parts) >= 4:
                    # 跳过表头行（全是字母/下划线，不含数字）
                    if not re.search(r'\d', clean):
                        continue
                    result['status']['user_connections'] = parts[0]
                    result['status']['batch_requests'] = parts[1]
                    result['status']['page_life_expectancy'] = parts[2]
                    result['status']['processes_blocked'] = parts[3]
                    break

            # --- session信息 ---
            stdout, stderr = tsql_query(queries['session_info'])
            result['raw_output'] += f'\n-- Sessions --\n{stdout[:300]}\n'
            for line in stdout.split('\n'):
                line = line.strip()
                clean = re.sub(r'^\d+>\s*(?:\d+>\s*)*', '', line)
                if not clean or clean.startswith('locale') or clean.startswith('using default'):
                    continue
                if not clean or clean.startswith('(') or clean.startswith('-')\
                   or 'rows)' in clean:
                    continue
                parts = clean.split('\t')
                if len(parts) >= 5:
                    # 跳过表头行（全是字母/下划线）
                    if not re.search(r'\d', clean):
                        continue
                    result['status']['total_sessions'] = parts[0]
                    result['status']['running_sessions'] = parts[1]
                    result['status']['sleeping_sessions'] = parts[2]
                    break

            # --- 数据文件/日志文件大小 ---
            disk_usage_result = None   # 记录是否有数据
            for disk_query_name in ('disk_usage', 'disk_usage_simple'):
                stdout, stderr = tsql_query(queries[disk_query_name])
                if disk_query_name == 'disk_usage':
                    result['raw_output'] += f'\n-- 文件大小 --\n{stdout[:500]}\n'
                file_sizes = []
                is_simple = (disk_query_name == 'disk_usage_simple')
                for line in stdout.split('\n'):
                    line = line.strip()
                    clean = re.sub(r'^\d+>\s*(?:\d+>\s*)*', '', line)
                    if not clean or clean.startswith('locale') or clean.startswith('using default'):
                        continue
                    if not clean or clean.startswith('(') or clean.startswith('-')\
                       or 'rows)' in clean:
                        continue
                    # 跳过表头行（纯英文字母/下划线，不含数字）
                    if not re.search(r'\d', clean):
                        continue
                    # 尝试 tab 分割，失败则用空白分割
                    parts = clean.split('\t')
                    if len(parts) == 1 and is_simple:
                        parts = clean.split()
                    elif len(parts) == 1 and not is_simple:
                        parts = clean.split()
                    if is_simple:
                        if len(parts) >= 2:
                            try:
                                file_sizes.append({
                                    'db': parts[0],
                                    'data_mb': int(float(parts[1])),
                                    'log_mb': 0,
                                })
                            except (ValueError, IndexError):
                                pass
                    else:
                        if len(parts) >= 2:
                            try:
                                data_val = int(float(parts[1])) if len(parts) >= 2 else 0
                                log_val = int(float(parts[2])) if len(parts) >= 3 else 0
                                file_sizes.append({
                                    'db': parts[0],
                                    'data_mb': data_val,
                                    'log_mb': log_val,
                                })
                            except (ValueError, IndexError):
                                pass
                if file_sizes:
                    result['file_sizes'] = file_sizes
                    disk_usage_result = file_sizes
                    break
            if not disk_usage_result:
                result['file_sizes'] = []

            # --- 构建 db_info ---
            total_data_mb = sum(f.get('data_mb', 0) or 0 for f in result.get('file_sizes', []))
            total_log_mb = sum(f.get('log_mb', 0) or 0 for f in result.get('file_sizes', []))
            result['db_info'] = {
                'version': result['version'][:100] if result['version'] else '',
                'db_count': len(result['databases']),
                'user_connections': result['status'].get('user_connections', ''),
                'page_life_expectancy': result['status'].get('page_life_expectancy', ''),
                'total_sessions': result['status'].get('total_sessions', ''),
                'running_sessions': result['status'].get('running_sessions', ''),
                'processes_blocked': result['status'].get('processes_blocked', '0'),
                'max_memory_mb': result['config'].get('max server memory (MB)', ''),
                'user_connections_limit': result['config'].get('user connections', ''),
                'max_dop': result['config'].get('max degree of parallelism', ''),
                'total_data_mb': total_data_mb,
                'total_log_mb': total_log_mb,
            }

        except subprocess.TimeoutExpired:
            result['error'] = 'MSSQL连接超时'
        except FileNotFoundError:
            result['error'] = 'tsql未安装，请执行: sudo apt-get install -y tdsodbc freetds-bin'
        except Exception as e:
            result['error'] = f'MSSQL连接错误: {str(e)}'

        return result
    
    def _test_oracle(self) -> Dict[str, Any]:
        """全面 Oracle 测试：版本、实例信息、表空间、会话、缓冲命中率、归档日志"""
        result = {
            'success': False,
            'connected': False,
            'version': None,
            'error': None,
            'db_info': {},         # 数据库摘要
            'databases': [],       # 数据库列表（Oracle 返回表空间作为"数据库"）
            'tablespaces': [],     # 表空间使用率详情
            'config': {},          # 关键配置
            'status': {},          # 运行状态
            'raw_output': '',      # 原始 sqlplus 输出
        }

        def _sqlplus_query(sql_block: str) -> str:
            """使用 sqlplus 执行 SQL，返回 stdout"""
            dsn = f'{self.username}/{self.password}@{self.host}:{self.port or 1521}/{self.database or "ORCL"}'
            # 设置 NLS_LANG 确保中文不乱码
            my_env = os.environ.copy()
            my_env['NLS_LANG'] = 'AMERICAN_AMERICA.AL32UTF8'
            proc = subprocess.Popen(
                f'sqlplus -S {dsn}',
                shell=True, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                env=my_env
            )
            stdout, stderr = proc.communicate(input=sql_block, timeout=self.timeout + 5)
            return stdout

        def _parse_oracle_output(stdout: str, query_name: str = '') -> list:
            """解析 sqlplus pipe-delimited 输出为 list[dict]
            支持两种输出格式：
              - HEADING ON:  第一行为表头，第二行为分隔线 ---，之后为数据行
              - HEADING OFF: 直接为数据行，返回 list[dict]（键名为 col_0, col_1...）
            """
            rows = []
            lines = stdout.split('\n')
            if not lines:
                return rows

            # 检测并收集 ORA 错误（保留以便 debug）
            oras = [l.strip() for l in lines if 'ORA-' in l]
            for o in oras:
                result['raw_output'] += f'  ⚠ {query_name} 错误: {o}\n'

            # 跳过 sqlplus 消息和空行
            clean = []
            for line in lines:
                s = line.strip()
                if not s:
                    continue
                if s.startswith('SQL>') or s.startswith('Connected') or s.startswith('Disconnected'):
                    continue
                if re.match(r'^ORA-', s) or re.match(r'^SP2-', s) or s.startswith('ERROR'):
                    continue
                if re.match(r'^[-]+$', s) or all(c in '-+| ' for c in s):
                    continue
                clean.append(s)
            if len(clean) < 1:
                return rows

            # 猜测是否有表头: 如果第一行含大写字母+下划线列名，视为表头
            first = clean[0]
            has_header = False
            if '|' in first:
                parts = [p.strip() for p in first.split('|')]
                # 列名特征：都含大写字母或下划线，且第二个部分不含纯数字
                col_name_count = sum(1 for p in parts if p and (p.isupper() or '_' in p))
                if col_name_count >= 2 and len(parts) >= 2:
                    has_header = True
            if has_header:
                headers = [h.strip() for h in first.split('|')]
                for data_line in clean[1:]:
                    vals = [v.strip() for v in data_line.split('|')]
                    if len(vals) == len(headers):
                        rows.append(dict(zip(headers, vals)))
                    elif len(vals) > 1:
                        # 补齐（偶尔值中含|）
                        vals = vals[:len(headers)]
                        if vals:
                            rows.append(dict(zip(headers, vals)))
            else:
                # 无表头模式：使用第一行作为表头
                vals = [v.strip() for v in first.split('|') if v.strip()]
                if len(vals) >= 2 and not vals[0].isnumeric():
                    headers = vals
                    for data_line in clean[1:]:
                        row_vals = [v.strip() for v in data_line.split('|') if v.strip()]
                        if len(row_vals) == len(headers):
                            rows.append(dict(zip(headers, row_vals)))
                else:
                    # 完全无表头，生成列名
                    if '|' in first:
                        headers = [f'col_{i}' for i in range(len(first.split('|')))]
                        for line in clean:
                            vals = [v.strip() for v in line.split('|')]
                            rows.append(dict(zip(headers, vals)))
            return rows

        def _try_query(sql: str, query_name: str) -> str:
            """执行查询并捕获 ORA 错误，返回 stdout"""
            try:
                stdout = _sqlplus_query(sql)
                result['raw_output'] += f'-- {query_name} --\n{stdout[:500]}\n'
                return stdout
            except Exception as e:
                result['raw_output'] += f'-- {query_name} -- 查询异常: {str(e)}\n'
                return ''

        try:
            # 验证连接 + 获取版本
            sql_block = """SET PAGESIZE 0 FEEDBACK OFF VERIFY OFF HEADING OFF ECHO OFF LINESIZE 4000
SELECT banner FROM v$version WHERE ROWNUM = 1;
EXIT;
"""
            stdout = _sqlplus_query(sql_block)
            result['raw_output'] += f'-- 版本 --\n{stdout[:500]}\n'

            if 'ORA-' in stdout and 'Oracle Database' not in stdout:
                if 'ORA-01017' in stdout:
                    result['error'] = '登录失败，请检查用户名密码'
                elif 'ORA-12541' in stdout:
                    result['error'] = '连接失败，请检查监听器是否启动'
                elif 'ORA-12170' in stdout or 'ORA-12535' in stdout:
                    result['error'] = '连接超时，请检查网络连通性'
                else:
                    match = re.search(r'(ORA-\d+:.*?)(?:\n|$)', stdout)
                    result['error'] = match.group(1) if match else f'Oracle错误: {stdout[:200]}'
                return result

            if 'Oracle Database' not in stdout:
                result['error'] = f'Oracle连接异常: {stdout[:200]}'
                return result

            # 解析版本
            for line in stdout.split('\n'):
                if 'Oracle Database' in line:
                    result['version'] = line.strip()[:200]
                    break
            result['connected'] = True
            result['success'] = True

            # 记录采集开始时间，用来计算 response_time
            _collect_start = time.time()

            # ====== 1. 实例信息 ======
            stdout = _try_query("""SET PAGESIZE 1000 FEEDBACK OFF VERIFY OFF HEADING ON ECHO OFF COLSEP | LINESIZE 4000
SELECT instance_name, host_name, version, status,
       NVL(TO_CHAR(startup_time, 'YYYY-MM-DD HH24:MI:SS'), 'N/A') AS startup_time,
       logins
FROM v$instance;
EXIT;
""", '实例')
            inst_rows = _parse_oracle_output(stdout, '实例')
            if inst_rows:
                inst = inst_rows[0]
                result['db_info'] = {
                    'instance_name': inst.get('INSTANCE_NAME', inst.get('instance_name', '')),
                    'host_name': inst.get('HOST_NAME', inst.get('host_name', '')),
                    'version': result['version'][:100] if result['version'] else '',
                    'status': inst.get('STATUS', inst.get('status', '')),
                    'startup_time': inst.get('STARTUP_TIME', inst.get('startup_time', '')),
                    'logins': inst.get('LOGINS', inst.get('logins', '')),
                }
            else:
                result['db_info'] = {
                    'instance_name': '',
                    'host_name': '',
                    'version': result['version'][:100] if result['version'] else '',
                    'status': '',
                    'startup_time': '',
                    'logins': '',
                }

            # ====== 2. 表空间列表（优先 dba_tablespaces，失败用 v$tablespace）======
            stdout = _try_query("""SET PAGESIZE 1000 FEEDBACK OFF VERIFY OFF HEADING ON ECHO OFF COLSEP | LINESIZE 4000
SELECT tablespace_name, status, contents, logging, extent_management, segment_space_management
FROM dba_tablespaces ORDER BY tablespace_name;
EXIT;
""", '表空间(dba)')
            if 'ORA-00942' in stdout:
                # fallback: 使用 v$tablespace（PUBLIC 可访问）
                result['raw_output'] += '  ⚠ dba_tablespaces 无权限，尝试 v$tablespace\n'
                stdout = _try_query("""SET PAGESIZE 1000 FEEDBACK OFF VERIFY OFF HEADING ON ECHO OFF COLSEP | LINESIZE 4000
SELECT name AS tablespace_name,
       DECODE(BITAND(flags, 1), 0, 'ONLINE', 'OFFLINE') AS status,
       DECODE(contents, 0, 'PERMANENT', 1, 'TEMPORARY', 2, 'UNDO', 'PERMANENT') AS contents
FROM v$tablespace ORDER BY name;
EXIT;
""", '表空间(v$)')
            ts_rows = _parse_oracle_output(stdout, '表空间')
            result['databases'] = [r.get('TABLESPACE_NAME', r.get('tablespace_name', '')) for r in ts_rows if r.get('TABLESPACE_NAME', r.get('tablespace_name', ''))]
            result['tablespaces'] = ts_rows

            # ====== 3. 表空间使用率（优先 dba_data_files+dba_free_space，失败用 v$datafile）======
            stdout = _try_query("""SET PAGESIZE 1000 FEEDBACK OFF VERIFY OFF HEADING ON ECHO OFF COLSEP | LINESIZE 4000
SELECT df.tablespace_name,
       ROUND(df.total_mb, 2) AS total_mb,
       ROUND(df.total_mb - NVL(fs.free_mb, 0), 2) AS used_mb,
       ROUND(NVL(fs.free_mb, 0), 2) AS free_mb,
       ROUND((df.total_mb - NVL(fs.free_mb, 0)) / df.total_mb * 100, 2) AS used_pct
FROM (SELECT tablespace_name, SUM(bytes) / 1024 / 1024 AS total_mb
      FROM dba_data_files GROUP BY tablespace_name) df
LEFT JOIN (SELECT tablespace_name, SUM(bytes) / 1024 / 1024 AS free_mb
           FROM dba_free_space GROUP BY tablespace_name) fs
ON df.tablespace_name = fs.tablespace_name
ORDER BY used_pct DESC;
EXIT;
""", '使用率(dba)')
            if 'ORA-00942' in stdout:
                result['raw_output'] += '  ⚠ dba_data_files/dba_free_space 无权限，尝试 v$datafile\n'
                stdout = _try_query("""SET PAGESIZE 1000 FEEDBACK OFF VERIFY OFF HEADING ON ECHO OFF COLSEP | LINESIZE 4000
SELECT t.name AS tablespace_name,
       ROUND(SUM(d.bytes) / 1024 / 1024, 2) AS total_mb,
       ROUND(SUM(d.bytes) / 1024 / 1024, 2) AS total_mb_alt
FROM v$tablespace t, v$datafile d
WHERE t.ts# = d.ts#
GROUP BY t.name
ORDER BY t.name;
EXIT;
""", '使用率(v$)')
            # 整合使用率到 tablespaces 中
            usage_rows = _parse_oracle_output(stdout, '使用率')
            usage_map = {
                r.get('TABLESPACE_NAME', r.get('tablespace_name', '')): {
                    'total_mb': r.get('TOTAL_MB', r.get('total_mb', 0)),
                    'used_mb': r.get('USED_MB', r.get('used_mb', 0)),
                    'free_mb': r.get('FREE_MB', r.get('free_mb', 0)),
                    'used_pct': r.get('USED_PCT', r.get('used_pct', 0)),
                } for r in usage_rows
            }
            # v$datafile fallback: 没有 used_mb/free_mb/used_pct，只有 total_mb
            is_vdata_fallback = 'TOTAL_MB_ALT' in stdout or 'total_mb_alt' in stdout
            for ts in result['tablespaces']:
                name = ts.get('TABLESPACE_NAME', ts.get('tablespace_name', ''))
                if name in usage_map and usage_map[name]['total_mb']:
                    ts.update(usage_map[name])
                elif is_vdata_fallback and name in usage_map:
                    # v$datafile fallback: 仅设置总大小，使用率和已用/空闲未知
                    ts['total_mb'] = usage_map[name]['total_mb']
                    ts['used_mb'] = 'N/A'
                    ts['free_mb'] = 'N/A'
                    ts['used_pct'] = 'N/A'

            # ====== 4. 数据文件列表 ======
            stdout = _try_query("""SET PAGESIZE 1000 FEEDBACK OFF VERIFY OFF HEADING ON ECHO OFF COLSEP | LINESIZE 4000
SELECT t.name AS tablespace_name,
       ROUND(SUM(d.bytes) / 1024 / 1024, 2) AS total_size_mb,
       COUNT(*) AS file_count
FROM v$tablespace t, v$datafile d
WHERE t.ts# = d.ts#
GROUP BY t.name
ORDER BY t.name;
EXIT;
""", '数据文件')

            # ====== 5. 会话信息 ======
            stdout = _try_query("""SET PAGESIZE 1000 FEEDBACK OFF VERIFY OFF HEADING ON ECHO OFF COLSEP | LINESIZE 4000
SELECT COUNT(*) AS total_sessions,
       SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) AS active_sessions,
       SUM(CASE WHEN status = 'INACTIVE' THEN 1 ELSE 0 END) AS inactive_sessions
FROM v$session WHERE type = 'USER';
EXIT;
""", '会话')
            sess_rows = _parse_oracle_output(stdout, '会话')
            if sess_rows:
                s = sess_rows[0]
                result['status']['total_sessions'] = s.get('TOTAL_SESSIONS', s.get('total_sessions', 0))
                result['status']['active_sessions'] = s.get('ACTIVE_SESSIONS', s.get('active_sessions', 0))
                result['status']['inactive_sessions'] = s.get('INACTIVE_SESSIONS', s.get('inactive_sessions', 0))

            # ====== 6. 缓冲命中率 ======
            stdout = _try_query("""SET PAGESIZE 1000 FEEDBACK OFF VERIFY OFF HEADING ON ECHO OFF COLSEP | LINESIZE 4000
SELECT name, value FROM v$sysstat
WHERE name IN ('session logical reads', 'physical reads', 'physical writes',
               'parse count (total)', 'parse count (hard)', 'execute count',
               'user commits', 'user rollbacks');
EXIT;
""", '性能')
            stat_rows = _parse_oracle_output(stdout, '性能')
            stats = {}
            for sr in stat_rows:
                key = sr.get('NAME', sr.get('name', ''))
                val = sr.get('VALUE', sr.get('value', '0'))
                stats[key] = val
            logical = int(stats.get('session logical reads', 1) or 1)
            physical = int(stats.get('physical reads', 0) or 0)
            hit_ratio = round((logical - physical) / max(logical, 1) * 100, 2) if logical > 0 else 0
            result['status']['buffer_hit_ratio'] = hit_ratio
            result['status']['logical_reads'] = logical
            result['status']['physical_reads'] = physical
            result['status']['parse_total'] = stats.get('parse count (total)', 0)
            result['status']['parse_hard'] = stats.get('parse count (hard)', 0)
            result['status']['execute_count'] = stats.get('execute count', 0)
            result['status']['user_commits'] = stats.get('user commits', 0)
            result['status']['user_rollbacks'] = stats.get('user rollbacks', 0)

            # ====== 7. SGA 内存 ======
            stdout = _try_query("""SET PAGESIZE 1000 FEEDBACK OFF VERIFY OFF HEADING ON ECHO OFF COLSEP | LINESIZE 4000
SELECT ROUND(value / 1024 / 1024, 0) AS sga_mb FROM v$parameter WHERE name = 'sga_max_size';
EXIT;
""", 'SGA')
            sga_rows = _parse_oracle_output(stdout, 'SGA')
            if sga_rows:
                result['status']['sga_size_mb'] = sga_rows[0].get('SGA_MB', sga_rows[0].get('sga_mb', 0))

            # ====== 8. 归档日志使用率（v$recovery_file_dest 仅在有 FRA 的库中存在）======
            stdout = _try_query("""SET PAGESIZE 1000 FEEDBACK OFF VERIFY OFF HEADING ON ECHO OFF COLSEP | LINESIZE 4000
SELECT name AS DESTINATION,
       ROUND(space_used / 1024 / 1024, 2) AS USED_MB,
       ROUND(space_limit / 1024 / 1024, 2) AS LIMIT_MB,
       ROUND(space_used / space_limit * 100, 2) AS USED_PCT
FROM v$recovery_file_dest;
EXIT;
""", '归档')
            # ORA-00942/00904: 未配置 Flash Recovery Area 或视图结构不同，跳过
            if 'ORA-00942' not in stdout and 'ORA-00904' not in stdout:
                arch_rows = _parse_oracle_output(stdout, '归档')
                if arch_rows:
                    arch = arch_rows[0]
                    result['status']['archive_used_pct'] = arch.get('USED_PCT', arch.get('used_pct', 0))
                    result['status']['archive_used_mb'] = arch.get('USED_MB', arch.get('used_mb', 0))
                    result['status']['archive_limit_mb'] = arch.get('LIMIT_MB', arch.get('limit_mb', 0))
            else:
                result['raw_output'] += '  ⚠ v$recovery_file_dest 无权限或未配置FRA，跳过归档\n'

            # ====== 构建 db_info 摘要 ======
            result['db_info'].update({
                'db_count': len(result['databases']),
                'total_sessions': result['status'].get('total_sessions', 0),
                'active_sessions': result['status'].get('active_sessions', 0),
                'buffer_hit_ratio': result['status'].get('buffer_hit_ratio', 0),
                'sga_size_mb': result['status'].get('sga_size_mb', 0),
            })

            # 计算采集响应时间（从连接成功到数据采集完毕的耗时）
            result['response_time'] = round((time.time() - _collect_start) * 1000, 2)
            result['driver'] = 'sqlplus (oracle-instantclient)'

        except subprocess.TimeoutExpired:
            result['error'] = 'Oracle连接超时'
        except FileNotFoundError:
            result['error'] = 'sqlplus未安装，请安装Oracle客户端'
        except Exception as e:
            result['error'] = f'Oracle连接错误: {str(e)}'

        return result
    
    def collect(self) -> Dict[str, Any]:
        """采集数据库状态"""
        result = self.test_connect()
        
        if not result['success']:
            return result
        
        data = {
            'success': True,
            'version': result.get('version'),
            'databases': [],
            'tablespaces': []
        }
        
        try:
            if self.db_type == 'mysql':
                import pymysql
                conn = pymysql.connect(
                    host=self.host,
                    port=self.port or 3306,
                    user=self.username,
                    password=self.password,
                    connect_timeout=self.timeout
                )
                cursor = conn.cursor()
                cursor.execute('SHOW DATABASES')
                data['databases'] = [db[0] for db in cursor.fetchall()]
                cursor.close()
                conn.close()
                
            elif self.db_type == 'oracle':
                # Oracle 采集：表空间使用率 + 数据库列表
                data['databases'] = result.get('databases', [])
                data['tablespaces'] = result.get('tablespaces', [])
                # 从 test_connect 中提取表空间使用数据
                ts_usage = []
                for ts in data['tablespaces']:
                    if isinstance(ts, dict) and 'used_pct' in ts:
                        ts_usage.append({
                            'tablespace_name': ts.get('TABLESPACE_NAME', ts.get('tablespace_name', '')),
                            'total_mb': ts.get('total_mb', ts.get('TOTAL_MB', 0)),
                            'used_mb': ts.get('used_mb', ts.get('USED_MB', 0)),
                            'used_pct': ts.get('used_pct', ts.get('USED_PCT', 0)),
                            'status': ts.get('STATUS', ts.get('status', '')),
                        })
                if ts_usage:
                    data['tablespace_usage'] = ts_usage
                    
        except:
            pass
        
        result['data'] = data
        return result


class NTPProtocol(BaseProtocol):
    """NTP时间同步检测协议"""

    name = "ntp"

    def __init__(self, host: str, port: int = 123, timeout: int = 10):
        super().__init__(host, port, timeout)

    def _query_ntp(self) -> dict:
        """执行NTP查询，返回时间信息"""
        import ntplib
        import time

        result = {
            'success': False,
            'server_time': None,
            'local_time': None,
            'offset': None,
            'delay': None,
            'stratum': None,
            'ref_id': None,
            'error': None,
        }

        try:
            client = ntplib.NTPClient()
            local_before = time.time()
            response = client.request(self.host, version=3, timeout=self.timeout)
            local_after = time.time()

            local_time = (local_before + local_after) / 2

            result['success'] = True
            result['server_time'] = response.tx_time
            result['local_time'] = local_time
            result['offset'] = round(response.offset, 3)
            result['delay'] = round(response.delay, 3)
            result['stratum'] = response.stratum
            result['ref_id'] = response.ref_id

        except ntplib.NTPException as e:
            result['error'] = f'NTP协议错误: {str(e)[:100]}'
        except socket.timeout:
            result['error'] = 'NTP连接超时'
        except socket.gaierror:
            result['error'] = '主机名解析失败'
        except OSError as e:
            result['error'] = f'网络错误: {str(e)[:100]}'
        except Exception as e:
            result['error'] = f'错误: {str(e)[:100]}'

        return result

    def test_connect(self) -> Dict[str, Any]:
        """测试NTP连通性"""
        result = self._query_ntp()
        return result

    def collect(self) -> Dict[str, Any]:
        """采集NTP时间同步数据"""
        from datetime import datetime, timezone

        result = self._query_ntp()

        if result['success']:
            # 格式化时间字符串供前端展示
            result['server_time_str'] = datetime.fromtimestamp(
                result['server_time'], tz=timezone.utc
            ).strftime('%Y-%m-%d %H:%M:%S UTC')
            result['local_time_str'] = datetime.fromtimestamp(
                result['local_time']
            ).strftime('%Y-%m-%d %H:%M:%S')

            # 额外状态字段
            abs_offset = abs(result['offset'])
            if abs_offset < 0.1:
                result['sync_status'] = '同步'
                result['severity'] = 1
            elif abs_offset < 1.0:
                result['sync_status'] = '轻微偏差'
                result['severity'] = 2
            elif abs_offset < 10.0:
                result['sync_status'] = '较大偏差'
                result['severity'] = 3
            else:
                result['sync_status'] = '严重偏差'
                result['severity'] = 4

            result['data'] = {
                'offset': result['offset'],
                'delay': result['delay'],
                'server_time': result['server_time_str'],
                'local_time': result['local_time_str'],
                'sync_status': result['sync_status'],
                'stratum': result['stratum'],
            }

        return result


def get_protocol_handler(protocol: str, **kwargs) -> BaseProtocol:

    """获取协议处理器"""
    handlers = {
        'ping': PingProtocol,
        'port': PortCheckProtocol,
        'ssh': SSHProtocol,
        'snmp': SNMPProtocol,
        'database': DatabaseProtocol,
        'mysql': lambda **kw: DatabaseProtocol(db_type='mysql', port=kw.pop('port', 3306), **kw),
        'postgresql': lambda **kw: DatabaseProtocol(db_type='postgresql', port=kw.pop('port', 5432), **kw),
        'mssql': lambda **kw: DatabaseProtocol(db_type='mssql', port=kw.pop('port', 1433), **kw),
        'oracle': lambda **kw: DatabaseProtocol(db_type='oracle', port=kw.pop('port', 1521), **kw),
        'ntp': NTPProtocol,
    }
    
    handler_class = handlers.get(protocol.lower())
    if handler_class:
        return handler_class(**kwargs)
    
    raise ValueError(f'不支持的协议: {protocol}')
