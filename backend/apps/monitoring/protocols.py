"""
监控数据采集协议支持模块
"""
import socket
import subprocess
import paramiko
import re
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
    """SNMP协议"""
    
    name = "snmp"
    
    def __init__(self, host: str, port: int = 161, community: str = 'public',
                 oid: str = None, version: str = '2c', timeout: int = 10):
        super().__init__(host, port, timeout)
        self.community = community
        self.oid = oid
        self.version = version  # v1, v2c, v3
    
    def test_connect(self) -> Dict[str, Any]:
        """测试SNMP连接"""
        result = {
            'success': False,
            'available': False,
            'error': None
        }
        
        # 检查snmpwalk是否安装
        try:
            subprocess.run(['which', 'snmpwalk'], capture_output=True, timeout=5)
        except:
            result['error'] = 'snmpwalk未安装，请执行: apt install snmp-utils'
            return result
        
        try:
            # 测试 SNMP sysDescr
            cmd = [
                'snmpget', '-v', '2c', '-c', self.community,
                '-t', str(self.timeout),
                '-Ov',  # 只输出值
                self.host,
                '1.3.6.1.2.1.1.1.0'  # sysDescr
            ]
            
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, timeout=self.timeout + 5)
            output = output.decode('utf-8', errors='ignore').strip()
            
            if output:
                result['success'] = True
                result['available'] = True
                result['sysDescr'] = output
            
        except subprocess.TimeoutExpired:
            result['error'] = 'SNMP查询超时'
        except subprocess.CalledProcessError as e:
            output = e.output.decode('utf-8', errors='ignore') if e.output else ''
            if 'No Response' in output:
                result['error'] = 'SNMP无响应，检查community string和防火墙'
            else:
                result['error'] = f'SNMP错误: {output[:100]}'
        except Exception as e:
            result['error'] = f'错误: {str(e)}'
        
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
        result = {
            'success': False,
            'connected': False,
            'version': None,
            'error': None
        }
        
        try:
            import pymysql
            conn = pymysql.connect(
                host=self.host,
                port=self.port or 3306,
                user=self.username,
                password=self.password,
                database=self.database,
                connect_timeout=self.timeout
            )
            
            cursor = conn.cursor()
            cursor.execute('SELECT VERSION()')
            version = cursor.fetchone()
            result['version'] = version[0] if version else None
            result['connected'] = True
            result['success'] = True
            
            cursor.close()
            conn.close()
            
        except ImportError:
            result['error'] = 'pymysql未安装: pip install pymysql'
        except pymysql.err.OperationalError as e:
            result['error'] = f'连接失败: {str(e)[:100]}'
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
        """测试MSSQL连接 - 使用FreeTDS tsql（解决TLS兼容问题）"""
        result = {
            'success': False,
            'connected': False,
            'version': None,
            'error': None
        }

        try:
            # 配置 FreeTDS 环境
            import os
            conf_path = '/tmp/freetds.conf'
            if not os.path.exists(conf_path):
                with open(conf_path, 'w') as f:
                    f.write('[global]\n    tds version = 7.4\n    encryption = off\n    client charset = UTF-8\n')

            # 使用 tsql 执行查询
            cmd = (f'TDSVER=7.4 tsql -H {self.host} -p {self.port or 1433} '
                   f'-U {self.username} -P "{self.password}" '
                   f'-D {self.database or "master"}')

            proc = subprocess.Popen(
                cmd, shell=True, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                env={**os.environ, 'FREETDSCONF': conf_path}
            )
            stdout, stderr = proc.communicate(input='SELECT @@VERSION AS v\nGO\n', timeout=self.timeout + 5)

            # 解析版本信息
            if 'Microsoft SQL Server' in stdout:
                for line in stdout.split('\n'):
                    if 'Microsoft SQL Server' in line:
                        version = line.strip()
                        # 去掉 tsql 前缀
                        version = re.sub(r'(?:\d+>\s*)+', '', version)
                        result['version'] = version[:100]
                        break
                result['connected'] = True
                result['success'] = True
            elif 'Msg 18456' in stdout or 'Login failed' in stdout:
                result['error'] = '登录失败，请检查用户名密码'
            elif 'Adaptive Server connection failed' in stdout or 'connection failed' in stdout:
                result['error'] = '连接失败，请检查地址和端口'
            else:
                result['error'] = f'MSSQL连接异常: {stderr[:200] if stderr else stdout[:200]}'

        except subprocess.TimeoutExpired:
            result['error'] = 'MSSQL连接超时'
        except FileNotFoundError:
            result['error'] = 'tsql未安装，请执行: sudo apt-get install -y tdsodbc freetds-bin'
        except Exception as e:
            result['error'] = f'MSSQL连接错误: {str(e)}'

        return result
    
    def _test_oracle(self) -> Dict[str, Any]:
        """测试Oracle连接 - 使用sqlplus命令行"""
        result = {
            'success': False,
            'connected': False,
            'version': None,
            'error': None
        }

        try:
            dsn = f'{self.username}/{self.password}@{self.host}:{self.port or 1521}/{self.database or "ORCL"}'
            sql = "SELECT banner FROM v$version WHERE ROWNUM = 1;\nEXIT;"
            proc = subprocess.Popen(
                f'sqlplus -S {dsn}',
                shell=True, stdin=subprocess.PIPE,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            stdout, stderr = proc.communicate(input=sql, timeout=self.timeout + 5)

            if 'Oracle Database' in stdout:
                for line in stdout.split('\n'):
                    line = line.strip()
                    if 'Oracle Database' in line:
                        result['version'] = line[:100]
                        break
                result['connected'] = True
                result['success'] = True
            elif 'ORA-01017' in stdout:
                result['error'] = '登录失败，请检查用户名密码'
            elif 'ORA-12541' in stdout:
                result['error'] = '连接失败，请检查监听器是否启动'
            elif 'ORA-' in stdout:
                match = re.search(r'(ORA-\d+:.*)', stdout)
                result['error'] = match.group(1) if match else f'Oracle错误: {stdout[:200]}'
            else:
                result['error'] = f'Oracle连接异常: {stdout[:200]}'

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
                
        except:
            pass
        
        result['data'] = data
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
    }
    
    handler_class = handlers.get(protocol.lower())
    if handler_class:
        return handler_class(**kwargs)
    
    raise ValueError(f'不支持的协议: {protocol}')
