"""
监控协议测试API视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db.models import Avg, Max, Min, Count
from django.db.models import Q
from datetime import timedelta
import time
import logging

# 添加日志记录
logger = logging.getLogger(__name__)

from .test_config import MonitorTestConfig, MonitorTestResult
from .serializers import MonitorTestConfigSerializer, MonitorTestResultSerializer


# ============================================================
# MSSQLHandler 已弃用 — 请使用 protocols.py 中的 DatabaseProtocol(db_type='mssql')
# 参考: get_protocol_handler 中的 mssql 分支
# ============================================================
# class MSSQLHandler:
#     """MSSQL连接处理器 - 使用FreeTDS tsql（解决TLS兼容问题）"""
#     def __init__(self, host, port=1433, username='', password='', database='',
#                  timeout=10, encrypt=False, trust_server_certificate=False):
#         self.host = host
#         self.port = port
#         self.username = username
#         self.password = password
#         self.database = database or 'master'
#         self.timeout = timeout
#
#     def test_connect(self):
#         """使用 FreeTDS tsql 测试 MSSQL 连接"""
#         import subprocess
#         import os
#         import time
#
#         start_time = time.time()
#
#         try:
#             conf_path = '/tmp/freetds.conf'
#             if not os.path.exists(conf_path):
#                 with open(conf_path, 'w') as f:
#                     f.write('[global]\n    tds version = 7.4\n    encryption = off\n    client charset = UTF-8\n')
#
#             cmd = (f'TDSVER=7.4 tsql -H {self.host} -p {self.port} '
#                    f'-U {self.username} -P "{self.password}" '
#                    f'-D {self.database}')
#
#             proc = subprocess.Popen(
#                 cmd, shell=True, stdin=subprocess.PIPE,
#                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
#                 env={**os.environ, 'FREETDSCONF': conf_path}
#             )
#             stdout, stderr = proc.communicate(input='SELECT @@VERSION AS v\nGO\n', timeout=self.timeout + 5)
#
#             response_time = (time.time() - start_time) * 1000
#
#             if 'Microsoft SQL Server' in stdout:
#                 version = ''
#                 for line in stdout.split('\n'):
#                     if 'Microsoft SQL Server' in line:
#                         import re
#                         version = re.sub(r'(?:\d+>\s*)+', '', line.strip())
#                         break
#                 return {
#                     'success': True,
#                     'message': 'FreeTDS tsql 连接成功',
#                     'response_time': round(response_time, 2),
#                     'data': {
#                         'version': version[:100],
#                         'driver': 'FreeTDS tsql',
#                         'method': 'tsql'
#                     }
#                 }
#             elif 'Msg 18456' in stdout or 'Login failed' in stdout:
#                 return {
#                     'success': False,
#                     'error': '登录失败，请检查用户名密码',
#                     'response_time': round(response_time, 2)
#                 }
#             else:
#                 return {
#                     'success': False,
#                     'error': f'MSSQL连接失败: {stderr[:200] if stderr else stdout[:200]}',
#                     'response_time': round(response_time, 2)
#                 }
#
#         except subprocess.TimeoutExpired:
#             return {
#                 'success': False,
#                 'error': 'MSSQL连接超时',
#                 'response_time': (time.time() - start_time) * 1000
#             }
#         except FileNotFoundError:
#             return {
#                 'success': False,
#                 'error': 'tsql未安装，请执行: sudo apt-get install -y tdsodbc freetds-bin',
#                 'response_time': (time.time() - start_time) * 1000
#             }
#         except Exception as e:
#             return {
#                 'success': False,
#                 'error': f'MSSQL连接错误: {str(e)}',
#                 'response_time': (time.time() - start_time) * 1000
#             }


def get_protocol_handler(protocol, **kwargs):
    """获取协议处理器"""
    # MSSQL 使用 protocols.py 里的 DatabaseProtocol（全面测试：版本/数据库/配置/状态）
    # 其他协议使用 protocols.py 中的实现
    from .protocols import (
        PingProtocol, PortCheckProtocol, SSHProtocol,
        SNMPProtocol, DatabaseProtocol
    )

    if protocol == 'mssql':
        kwargs.pop('encrypt', None)
        kwargs.pop('trust_server_certificate', None)
        kwargs.setdefault('port', 1433)
        logger.info(f"MSSQL 测试使用 DatabaseProtocol(db_type='mssql') 替代已弃用的 MSSQLHandler")
        return DatabaseProtocol(db_type='mssql', **kwargs)

    if protocol == 'ping':
        return PingProtocol(**kwargs)
    elif protocol == 'port':
        port = kwargs.pop('port', None)
        handler = PortCheckProtocol(host=kwargs.get('host'), port=port, timeout=kwargs.get('timeout', 10))
        return handler
    elif protocol == 'ssh':
        return SSHProtocol(**kwargs)
    elif protocol == 'snmp':
        return SNMPProtocol(**kwargs)
    elif protocol == 'mysql':
        kwargs.setdefault('port', 3306)
        return DatabaseProtocol(db_type='mysql', **kwargs)
    elif protocol == 'postgresql':
        kwargs.setdefault('port', 5432)
        return DatabaseProtocol(db_type='postgresql', **kwargs)
    elif protocol == 'oracle':
        kwargs.setdefault('port', 1521)
        return DatabaseProtocol(db_type='oracle', **kwargs)
    else:
        raise ValueError(f"Unsupported protocol: {protocol}")


class MonitorTestConfigViewSet(viewsets.ModelViewSet):
    """监控测试配置视图集"""
    
    queryset = MonitorTestConfig.objects.all()
    serializer_class = MonitorTestConfigSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        # 资产筛选
        asset_id = self.request.query_params.get('asset')
        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)
        
        # 协议筛选
        protocol = self.request.query_params.get('protocol')
        if protocol:
            queryset = queryset.filter(protocol=protocol)
        
        return queryset.select_related('customer', 'asset', 'created_by')
    
    @action(detail=True, methods=['post'])
    def test(self, request, pk=None):
        """立即测试"""
        config = self.get_object()
        
        # 执行测试
        start_time = time.time()
        result = execute_protocol_test(config)
        test_duration = (time.time() - start_time) * 1000
        
        logger.info(f"MSSQL Test Result for config {pk}: {result}")
        
        # 保存测试结果
        test_result = MonitorTestResult.objects.create(
            config=config,
            status=result['status'],
            response_time=result.get('response_time'),
            error_message=result.get('error') or '',
            data=result.get('data', {}),
            test_duration=round(test_duration, 2),
            remote_addr=request.META.get('REMOTE_ADDR')
        )
        
        # 更新配置状态
        config.last_test_status = result['status']
        config.last_test_time = timezone.now()
        config.save()
        
        return Response({
            'success': result['status'] == 'success',
            'status': result['status'],
            'response_time': result.get('response_time'),
            'error': result.get('error'),
            'data': result.get('data', {}),
            'test_duration': round(test_duration, 2),
            'result_id': test_result.id
        })
    
    @action(detail=False, methods=['get'])
    def protocols(self, request):
        """获取支持的协议列表"""
        protocols = [
            {'code': 'ping', 'name': 'Ping (ICMP)', 'port': None, 'fields': []},
            {'code': 'port', 'name': '端口检测', 'portfields': ['port']},
            {'code': 'ssh', 'name': 'SSH', 'port': 22, 'fields': ['port', 'username', 'password', 'key_file']},
            {'code': 'snmp', 'name': 'SNMP', 'port': 161, 'fields': ['community', 'version', 'oid']},
            {'code': 'mysql', 'name': 'MySQL', 'port': 3306, 'fields': ['port', 'username', 'password', 'database']},
            {'code': 'postgresql', 'name': 'PostgreSQL', 'port': 5432, 'fields': ['port', 'username', 'password', 'database']},
            {'code': 'mssql', 'name': 'MSSQL', 'port': 1433, 'fields': ['port', 'username', 'password', 'database', 'encrypt', 'trust_server_certificate']},
            {'code': 'oracle', 'name': 'Oracle', 'port': 1521, 'fields': ['port', 'username', 'password', 'database']},
            {'code': 'ntp', 'name': 'NTP时间同步检测', 'port': 123, 'fields': []},
        ]
        return Response(protocols)


class MonitorTestResultViewSet(viewsets.ReadOnlyModelViewSet):
    """监控测试结果视图集"""
    
    queryset = MonitorTestResult.objects.all()
    serializer_class = MonitorTestResultSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 配置筛选
        config_id = self.request.query_params.get('config')
        if config_id:
            queryset = queryset.filter(config_id=config_id)
        
        # 状态筛选
        test_status = self.request.query_params.get('status')
        if test_status:
            queryset = queryset.filter(status=test_status)
        
        # 时间范围
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset.select_related('config')

    @action(detail=True, methods=['post'])
    def push(self, request, pk=None):
        """推送测试结果到 ops-center"""
        result = self.get_object()
        from apps.dashboard.push_service import push_monitor_test_result
        push_result = push_monitor_test_result(result.id)
        if push_result:
            return Response({'success': True, 'message': '推送成功', 'result': push_result})
        else:
            return Response({'success': False, 'message': '推送失败或未配置'}, status=400)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """测试结果统计"""
        config_id = request.query_params.get('config')
        queryset = self.get_queryset()
        
        if config_id:
            queryset = queryset.filter(config_id=config_id)
        
        # 过去24小时统计
        since = timezone.now() - timedelta(hours=24)
        recent = queryset.filter(created_at__gte=since)
        
        stats = recent.aggregate(
            total=Count('id'),
            success=Count('id', filter=Q(status='success')),
            failed=Count('id', filter=Q(status='failed')),
            avg_response_time=Avg('response_time'),
            max_response_time=Max('response_time'),
            min_response_time=Min('response_time'),
        )

        # 计算成功率
        if stats['total'] > 0:
            stats['success_rate'] = round(stats['success'] / stats['total'] * 100, 2)
        else:
            stats['success_rate'] = 0
        
        return Response(stats)


@api_view(['POST'])
@permission_classes([AllowAny])
def quick_test(request):
    """
    快速测试接口（无需认证，用于现场调试）
    """
    protocol = request.data.get('protocol', 'ping')
    host = request.data.get('host')
    port = request.data.get('port')
    timeout = int(request.data.get('timeout', 10))
    
    if not host:
        return Response({
            'success': False,
            'error': '缺少host参数'
        }, status=400)
    
    # 记录请求参数用于调试
    logger.info(f"Quick test requested: protocol={protocol}, host={host}, port={port}")
    
    # 准备参数
    params = {
        'host': host,
        'timeout': timeout,
    }
    
    if port:
        params['port'] = int(port)
    
    # 协议特定参数
    if protocol == 'ssh':
        params['username'] = request.data.get('username', '')
        params['password'] = request.data.get('password', '')
        params['key_file'] = request.data.get('key_file')
    elif protocol == 'snmp':
        params['community'] = request.data.get('community', 'public')
        params['oid'] = request.data.get('oid')
    elif protocol in ['mysql', 'postgresql', 'mssql', 'oracle']:
        params['username'] = request.data.get('username', '')
        params['password'] = request.data.get('password', '')
        params['database'] = request.data.get('database', '')
        # MSSQL 特定参数
        if protocol == 'mssql':
            params['encrypt'] = request.data.get('encrypt', False)
            params['trust_server_certificate'] = request.data.get('trust_server_certificate', False)
    
    logger.info(f"Test parameters prepared: {params}")
    
    # 执行测试
    start_time = time.time()
    
    try:
        handler = get_protocol_handler(protocol, **params)
        logger.info(f"Handler created successfully for protocol: {protocol}")
        result = handler.test_connect()
        logger.info(f"Protocol {protocol} test result: {result}")
    except ValueError as e:
        logger.error(f"ValueError in {protocol} test: {str(e)}")
        result = {
            'success': False,
            'error': str(e)
        }
    except ImportError as e:
        logger.error(f"ImportError in {protocol} test: {str(e)}")
        result = {
            'success': False,
            'error': f'缺少必要的模块: {str(e)}'
        }
    except Exception as e:
        logger.error(f"Exception in {protocol} test: {str(e)}")
        result = {
            'success': False,
            'error': f'测试执行失败: {str(e)}'
        }
    
    test_duration = (time.time() - start_time) * 1000

    # 保存测试结果（支持匿名用户）
    response_data = {
        'protocol': protocol,
        'host': host,
        'port': port,
        'test_duration': round(test_duration, 2),
        **result
    }

    try:
        temp_config, _ = MonitorTestConfig.objects.get_or_create(
            name=f'快速测试_{protocol}_{host}_{int(time.time())}'[:100],
            defaults={
                'customer_id': 1,
                'protocol': protocol,
                'host': host,
                'port': port if port else None,
                'config': {},
                'created_by': request.user if request.user.is_authenticated else None,
                'is_enabled': False,
            }
        )
        # 各协议返回的数据在顶层（不是 result['data']），需按协议提取
        if protocol == 'ping':
            data_to_save = {
                'reachable': result.get('reachable'),
                'packet_loss': result.get('packet_loss'),
                'min_rtt': result.get('min_rtt'),
                'max_rtt': result.get('max_rtt'),
                'avg_rtt': result.get('avg_rtt'),
                'output': result.get('output', ''),
            }
        elif protocol == 'port':
            data_to_save = {
                'open': result.get('open'),
                'service': result.get('service'),
                'banner': result.get('banner', ''),
            }
        elif protocol == 'ssh':
            data_to_save = {
                'authenticated': result.get('authenticated'),
                'error': result.get('error'),
            }
        elif protocol == 'snmp':
            data_to_save = {
                'available': result.get('available'),
                'snmp_version': result.get('snmp_version'),
                'version_tests': result.get('version_tests', {}),
                'system_info': result.get('system_info', {}),
                'device_info': result.get('device_info', {}),
                'oids': result.get('oids', {}),
                'raw_outputs': result.get('raw_outputs', {}),
                'walk_data': result.get('walk_data', {}),
                'interface_summary': result.get('interface_summary', {}),
            }
        elif protocol == 'mysql':
            data_to_save = {
                'version': result.get('version'),
                'db_info': result.get('db_info', {}),
                'variables': result.get('variables', {}),
                'databases': result.get('databases', []),
                'engines': result.get('engines', []),
                'status': result.get('status', {}),
                'raw_queries': result.get('raw_queries', {}),
            }
        elif protocol == 'mssql':
            data_to_save = {
                'version': result.get('version'),
                'db_info': result.get('db_info', {}),
                'databases': result.get('databases', []),
                'config': result.get('config', {}),
                'status': result.get('status', {}),
                'raw_output': result.get('raw_output', ''),
            }
        elif protocol == 'postgresql':
            data_to_save = {
                'version': result.get('version'),
                'db_info': result.get('db_info', {}),
                'databases': result.get('databases', []),
                'config': result.get('config', {}),
                'status': result.get('status', {}),
                'raw_output': result.get('raw_output', ''),
            }
        elif protocol == 'oracle':
            data_to_save = {
                'version': result.get('version'),
                'db_info': result.get('db_info', {}),
                'databases': result.get('databases', []),
                'tablespaces': result.get('tablespaces', []),
                'config': result.get('config', {}),
                'status': result.get('status', {}),
                'raw_output': result.get('raw_output', ''),
                'response_time': result.get('response_time'),
                'driver': result.get('driver', ''),
            }
        else:
            data_to_save = result.get('data', {}) if isinstance(result.get('data'), dict) else {}

        test_result = MonitorTestResult.objects.create(
            config=temp_config,
            status='success' if result.get('success') else 'failed',
            response_time=result.get('response_time'),
            error_message=result.get('error') or '',
            data=data_to_save,
            test_duration=round(test_duration, 2),
            remote_addr=request.META.get('REMOTE_ADDR')
        )
        response_data['result_id'] = test_result.id
    except Exception as e:
        logger.warning(f'保存快速测试结果失败: {e}')

    return Response(response_data)


def execute_protocol_test(config):
    """执行协议测试"""
    params = {
        'host': config.host,
        'timeout': config.interval if config.interval < 60 else 10,
    }
    
    if config.port:
        params['port'] = config.port
    
    # 解析协议特定配置
    protocol_config = config.config or {}
    
    if config.protocol == 'ssh':
        params['username'] = protocol_config.get('username', '')
        params['password'] = protocol_config.get('password', '')
        params['key_file'] = protocol_config.get('key_file')
    elif config.protocol == 'snmp':
        params['community'] = protocol_config.get('community', 'public')
        params['oid'] = protocol_config.get('oid')
    elif config.protocol in ['mysql', 'postgresql', 'mssql', 'oracle']:
        params['username'] = protocol_config.get('username', '')
        params['password'] = protocol_config.get('password', '')
        params['database'] = protocol_config.get('database', '')
        # MSSQL 特定参数
        if config.protocol == 'mssql':
            params['encrypt'] = protocol_config.get('encrypt', False)
            params['trust_server_certificate'] = protocol_config.get('trust_server_certificate', False)
    
    try:
        handler = get_protocol_handler(config.protocol, **params)
        result = handler.test_connect()
        
        # 格式化结果，确保 error 字段不为 null
        # 各协议测试结果的数据字段都在顶层，而非 result['data']，需分别提取
        data_to_save = {}
        if config.protocol == 'ping':
            data_to_save = {
                'reachable': result.get('reachable'),
                'packet_loss': result.get('packet_loss'),
                'min_rtt': result.get('min_rtt'),
                'max_rtt': result.get('max_rtt'),
                'avg_rtt': result.get('avg_rtt'),
                'output': result.get('output', ''),
            }
        elif config.protocol == 'port':
            data_to_save = {
                'open': result.get('open'),
                'service': result.get('service'),
                'banner': result.get('banner', ''),
            }
        elif config.protocol == 'ssh':
            data_to_save = {
                'authenticated': result.get('authenticated'),
                'error': result.get('error'),
            }
        elif config.protocol == 'snmp':
            data_to_save = {
                'available': result.get('available'),
                'snmp_version': result.get('snmp_version'),
                'version_tests': result.get('version_tests', {}),
                'system_info': result.get('system_info', {}),
                'device_info': result.get('device_info', {}),
                'oids': result.get('oids', {}),
                'raw_outputs': result.get('raw_outputs', {}),
                'walk_data': result.get('walk_data', {}),
                'interface_summary': result.get('interface_summary', {}),
            }
        elif config.protocol == 'mysql':
            data_to_save = {
                'version': result.get('version'),
                'db_info': result.get('db_info', {}),
                'variables': result.get('variables', {}),
                'databases': result.get('databases', []),
                'engines': result.get('engines', []),
                'status': result.get('status', {}),
                'raw_queries': result.get('raw_queries', {}),
            }
        elif config.protocol == 'mssql':
            data_to_save = {
                'version': result.get('version'),
                'db_info': result.get('db_info', {}),
                'databases': result.get('databases', []),
                'config': result.get('config', {}),
                'status': result.get('status', {}),
                'raw_output': result.get('raw_output', ''),
            }
        elif config.protocol == 'postgresql':
            data_to_save = {
                'version': result.get('version'),
                'db_info': result.get('db_info', {}),
                'databases': result.get('databases', []),
                'config': result.get('config', {}),
                'status': result.get('status', {}),
                'raw_output': result.get('raw_output', ''),
            }
        elif config.protocol == 'oracle':
            data_to_save = {
                'version': result.get('version'),
                'db_info': result.get('db_info', {}),
                'databases': result.get('databases', []),
                'tablespaces': result.get('tablespaces', []),
                'config': result.get('config', {}),
                'status': result.get('status', {}),
                'raw_output': result.get('raw_output', ''),
                'response_time': result.get('response_time'),
                'driver': result.get('driver', ''),
            }

        formatted_result = {
            'status': 'success' if result.get('success') else 'failed',
            'response_time': result.get('response_time'),
            'error': result.get('error') or '',
            'data': {k: v for k, v in data_to_save.items() if v is not None and v != {}},
        }

        # 对于 MSSQL 错误进行特殊处理
        if config.protocol == 'mssql' and formatted_result['status'] == 'failed':
            error_msg = formatted_result['error']
            if 'Adaptive Server connection failed' in error_msg:
                formatted_result['error'] += '\n请检查：\n1. MSSQL服务器是否运行\n2. 端口1433是否开放\n3. SQL Server Browser服务是否启动\n4. 是否启用了TCP/IP协议\n5. 防火墙设置\n6. 用户名密码是否正确\n7. 数据库是否允许SQL身份验证'
            elif 'No module named' in error_msg and 'mssql_handler' in error_msg:
                formatted_result['error'] = 'MSSQL模块未正确配置。请确保已安装pyodbc或pymssql模块。'
        
        logger.info(f"Protocol {config.protocol} test completed: {formatted_result}")
        return formatted_result
    except ImportError as e:
        error_msg = str(e)
        logger.error(f"ImportError in {config.protocol} test: {error_msg}")
        return {
            'status': 'error',
            'error': f'缺少必要的模块: {error_msg}',
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Exception in {config.protocol} test: {error_msg}")
        return {
            'status': 'error',
            'error': error_msg,
        }


@api_view(['GET'])
@permission_classes([AllowAny])
def mssql_diagnostics(request):
    """MSSQL诊断接口"""
    import platform
    import socket
    
    diagnostics = {
        'os': platform.system(),
        'platform': platform.platform(),
        'python_version': platform.python_version(),
        'timestamp': timezone.now().isoformat()
    }
    
    # 检查可用的Python MSSQL驱动
    try:
        import pyodbc
        diagnostics['pyodbc_available'] = True
        try:
            drivers = [x for x in pyodbc.drivers() if 'SQL Server' in x]
            diagnostics['pyodbc_drivers'] = drivers
        except:
            diagnostics['pyodbc_drivers'] = []
    except ImportError:
        diagnostics['pyodbc_available'] = False
        diagnostics['pyodbc_drivers'] = []
    
    try:
        import pymssql
        diagnostics['pymssql_available'] = True
    except ImportError:
        diagnostics['pymssql_available'] = False
    
    # 测试端口连通性
    host = request.GET.get('host', 'localhost')
    port = request.GET.get('port', '1433')
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, port))
        diagnostics['port_reachable'] = result == 0
        diagnostics['port_test_details'] = {
            'host': host,
            'port': port,
            'connection_result': result
        }
        sock.close()
    except Exception as e:
        diagnostics['port_reachable'] = False
        diagnostics['port_error'] = str(e)
    
    return Response(diagnostics)