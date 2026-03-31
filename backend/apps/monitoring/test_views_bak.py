"""
监控协议测试API视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db.models import Avg, Max, Min
from datetime import timedelta
import time

from .test_config import MonitorTestConfig, MonitorTestResult
from .serializers import MonitorTestConfigSerializer, MonitorTestResultSerializer
from .protocols import get_protocol_handler


class MonitorTestConfigViewSet(viewsets.ModelViewSet):
    """监控测试配置视图集"""
    
    queryset = MonitorTestConfig.objects.all()
    serializer_class = MonitorTestConfigSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 客户筛选
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
            {'code': 'port', 'name': '端口检测', 'port': True, 'fields': ['port']},
            {'code': 'ssh', 'name': 'SSH', 'port': 22, 'fields': ['port', 'username', 'password', 'key_file']},
            {'code': 'snmp', 'name': 'SNMP', 'port': 161, 'fields': ['community', 'version', 'oid']},
            {'code': 'mysql', 'name': 'MySQL', 'port': 3306, 'fields': ['port', 'username', 'password', 'database']},
            {'code': 'postgresql', 'name': 'PostgreSQL', 'port': 5432, 'fields': ['port', 'username', 'password', 'database']},
            {'code': 'mssql', 'name': 'MSSQL', 'port': 1433, 'fields': ['port', 'username', 'password', 'database']},
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
        params['database'] = request.data.get('database')
        # db_type 由 handler lambda 设置，不需要在 params 中传递
    
    # 执行测试
    start_time = time.time()
    
    try:
        handler = get_protocol_handler(protocol, **params)
        result = handler.test_connect()
    except ValueError as e:
        result = {
            'success': False,
            'error': str(e)
        }
    except Exception as e:
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
        params['database'] = protocol_config.get('database')
        # db_type 由 handler lambda 设置
    
    try:
        handler = get_protocol_handler(config.protocol, **params)
        result = handler.test_connect()
        
        # 格式化结果，确保 error 字段不为 null
        return {
            'status': 'success' if result.get('success') else 'failed',
            'response_time': result.get('response_time'),
            'error': result.get('error') or '',
            'data': result.get('data', {}),
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
        }
