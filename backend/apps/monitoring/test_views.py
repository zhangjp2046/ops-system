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


class MSSQLHandler:
    """MSSQL连接处理器"""
    def __init__(self, host, port=1433, username='', password='', database='', 
                 timeout=10, encrypt=False, trust_server_certificate=False):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.timeout = timeout
        self.encrypt = encrypt
        self.trust_server_certificate = trust_server_certificate

    def test_connect(self):
        """
        尝试多种方法连接MSSQL
        """
        import time
        
        start_time = time.time()
        
        # 方法1: 使用pyodbc
        result = self._try_pyodbc_connect()
        if result['success']:
            result['response_time'] = (time.time() - start_time) * 1000
            return result
        
        # 方法2: 使用pymssql
        result = self._try_pymssql_connect()
        if result['success']:
            result['response_time'] = (time.time() - start_time) * 1000
            return result
        
        # 如果都失败了，返回最后的错误
        result['response_time'] = (time.time() - start_time) * 1000
        return result

    def _try_pyodbc_connect(self):
        """
        使用pyodbc连接MSSQL
        """
        try:
            import pyodbc
            
            # 尝试找到合适的驱动
            available_drivers = [x for x in pyodbc.drivers() if 'SQL Server' in x]
            if not available_drivers:
                return {
                    'success': False,
                    'error': '未找到可用的SQL Server ODBC驱动。请安装 Microsoft ODBC Driver for SQL Server。',
                    'data': {'available_drivers': pyodbc.drivers()}
                }
            
            # 优先使用较新的驱动
            driver = None
            for d in ['ODBC Driver 18 for SQL Server', 'ODBC Driver 17 for SQL Server', 'SQL Server Native Client 11.0', 'SQL Server']:
                for available_driver in available_drivers:
                    if d.lower() in available_driver.lower():
                        driver = available_driver
                        break
                if driver:
                    break
            
            if not driver:
                driver = available_drivers[0]  # 使用第一个可用的驱动
            
            conn_str = (
                f"DRIVER={{{driver}}};"
                f"SERVER={self.host},{self.port};"
                f"DATABASE={self.database or 'master'};"
                f"UID={self.username};"
                f"PWD={self.password};"
                f"Connect Timeout={self.timeout};"
            )
            
            if self.encrypt:
                conn_str += "Encrypt=yes;"
            if self.trust_server_certificate:
                conn_str += "TrustServerCertificate=yes;"
            
            conn = pyodbc.connect(conn_str, timeout=self.timeout)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            
            return {
                'success': True,
                'message': 'pyodbc连接成功',
                'data': {'driver_used': driver}
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'pyodbc连接失败: {str(e)}',
                'data': {'available_drivers': pyodbc.drivers()}
            }

    def _try_pymssql_connect(self):
        """
        使用pymssql连接MSSQL
        """
        try:
            import pymssql
            
            conn = pymssql.connect(
                server=f"{self.host}:{self.port}",
                user=self.username,
                password=self.password,
                database=self.database or 'master',
                timeout=self.timeout,
                login_timeout=self.timeout
            )
            
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            conn.close()
            
            return {
                'success': True,
                'message': 'pymssql连接成功',
                'data': {'library_used': 'pymssql'}
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'pymssql连接失败: {str(e)}'
            }


def get_protocol_handler(protocol, **kwargs):
    """获取协议处理器"""
    if protocol == 'mssql':
        return MSSQLHandler(**kwargs)
    elif protocol == 'ping':
        # 这里应该实现
        from .protocols.ping_handler import PingHandler
        return PingHandler(**kwargs)
    elif protocol == 'port':
        # 这里应该有端口检测处理器的实现
        from .protocols.port_handler import PortHandler
        return PortHandler(**kwargs)
    elif protocol == 'ssh':
        # 这里应该有SSH处理器的实现
        from .protocols.ssh_handler import SSHHandler
        return SSHHandler(**kwargs)
    elif protocol == 'snmp':
        # 这里应该有SNMP处理器的实现
        from .protocols.snmp_handler import SNMPHandler
        return)
    elif protocol == 'mysql':
        # 这里        from .protocols.mysql_handler import MySQLHandlerHandler(**kwargs)
    elif protocol == 'postgresql':
        # 这里应该有PostgreSQL处理器的实现
        from .protocols.postgresql_handler import PostgreSQLHandler
        return PostgreSQLHandler(**kwargs)
    elif protocol == 'oracle':
        # 这里应该有Oracle处理器的实现
        from .protocols.oracle_handler import OracleHandler
        return OracleHandler(**kwargs)
    else:
        raise ValueError(f"Unsupported protocol: {protocol}")


class MonitorTestConfigViewSet(viewsets.ModelViewSet):
    """监控测试配置视图集"""
    
    queryset = MonitorTestConfig.objects.all()
    serializer_class = MonitorTestConfigSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        #        customer_id = self.request.query_params.get('customer')
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
            error_message=result.get('error', ''),
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
            min_response_time_time'),
        )
        
        # 计算成功率
        if stats['total'] > 0:
            stats(stats['success'] / stats['total'] * 100, 2)
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
    
    return Response({
        'protocol': protocol,
        'host': host,
        'port': port,
        'test_duration': round(test_duration, 2),
        **result
    })


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
        formatted_result = {
            'status': 'success' if result.get('success') else 'failed',
            'response_time': result.get('response_time'),
            'error': result.get('error') or '',
            'data': result.get('data', {}),
        }
        
        # 对于 MSSQL 错误进行特殊处理
        if config.protocol == 'mssql'status'] == 'failed':
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
    port =('port', '1433'))
    
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