#!/usr/bin/env python3
"""
告警阈值配置视图
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db.models import Q

from .threshold_models import AlertThreshold, AlertThresholdRule, AlertThresholdTemplate
from .threshold_serializers import (
    AlertThresholdSerializer, AlertThresholdCreateSerializer,
    AlertThresholdRuleSerializer, AlertThresholdTemplateSerializer,
    ThresholdCheckSerializer
)
from apps.inspection.check_items import INSPECTION_CHECK_ITEMS


class AlertThresholdViewSet(viewsets.ModelViewSet):
    """告警阈值配置视图集"""
    
    queryset = AlertThreshold.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return AlertThresholdCreateSerializer
        return AlertThresholdSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 客户筛选
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        # 协议筛选
        protocol = self.request.query_params.get('protocol')
        if protocol:
            queryset = queryset.filter(protocol=protocol)
        
        # 检查项筛选
        check_item = self.request.query_params.get('check_item')
        if check_item:
            queryset = queryset.filter(check_item_code=check_item)
        
        # 状态筛选
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset.select_related('customer', 'asset_type').prefetch_related('rules')
    
    @action(detail=False, methods=['get'])
    def available_items(self, request):
        """获取可用的检查项列表"""
        protocol = request.query_params.get('protocol')
        
        if protocol:
            protocols = {protocol: INSPECTION_CHECK_ITEMS.get(protocol, {})}
        else:
            protocols = INSPECTION_CHECK_ITEMS
        
        items = []
        for proto_code, proto_info in protocols.items():
            if not proto_info:
                continue
            for check in proto_info.get('checks', []):
                items.append({
                    'protocol': proto_code,
                    'protocol_name': proto_info['name'],
                    'check_item_code': check['code'],
                    'check_item_name': check['name'],
                    'description': check.get('description', ''),
                })
        
        return Response(items)
    
    @action(detail=False, methods=['post'])
    def check_threshold(self, request):
        """检查值是否触发阈值"""
        serializer = ThresholdCheckSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        return Response({
            'success': True,
            'data': serializer.validated_data
        })
    
    @action(detail=False, methods=['get'])
    def batch_check(self, request):
        """批量检查多个值"""
        items = request.query_params.getlist('items')
        customer_id = request.query_params.get('customer')
        asset_type_id = request.query_params.get('asset_type')
        protocol = request.query_params.get('protocol')
        
        results = []
        for item in items:
            try:
                check_item_code, value = item.split(':', 1)
                threshold = self._find_threshold(check_item_code, customer_id, asset_type_id, protocol)
                
                if threshold:
                    severity, severity_name = threshold.get_severity(value)
                    results.append({
                        'check_item_code': check_item_code,
                        'value': value,
                        'severity': severity,
                        'severity_name': severity_name,
                        'threshold_found': True
                    })
                else:
                    results.append({
                        'check_item_code': check_item_code,
                        'value': value,
                        'severity': 1,
                        'severity_name': '信息',
                        'threshold_found': False
                    })
            except ValueError:
                results.append({
                    'check_item_code': item,
                    'value': '',
                    'severity': 1,
                    'severity_name': '信息',
                    'error': '格式错误'
                })
        
        return Response(results)
    
    def _find_threshold(self, check_item_code, customer_id=None, asset_type_id=None, protocol=None):
        """查找最匹配的阈值配置（protocol 传入时只采纳同协议的行）"""
        queries = []
        
        if customer_id and asset_type_id:
            queries.append({
                'customer_id': customer_id,
                'asset_type_id': asset_type_id,
                'check_item_code': check_item_code,
                'is_active': True
            })
        
        if customer_id:
            queries.append({
                'customer_id': customer_id,
                'asset_type_id__isnull': True,
                'check_item_code': check_item_code,
                'is_active': True
            })
        
        queries.append({
            'customer_id__isnull': True,
            'asset_type_id__isnull': True,
            'check_item_code': check_item_code,
            'is_active': True
        })
        
        # 只采纳同协议的行
        if protocol:
            for q in queries:
                q['protocol'] = protocol

        for query in queries:
            # 同 alert_generator.get_threshold_severity：同层可能多行且不区分 protocol，
            # 必须逐行挑出「真的配了阈值」的那一行，否则会把整层放弃
            candidates = AlertThreshold.objects.filter(**query).order_by('pk')
            threshold = next((t for t in candidates if t.has_effective_threshold()), None)
            if threshold:
                return threshold
        
        return None
    
    @action(detail=True, methods=['post'])
    def test_value(self, request, pk=None):
        """测试某个值的严重程度"""
        threshold = self.get_object()
        value = request.data.get('value')
        
        if value is None:
            return Response({
                'success': False,
                'message': '缺少value参数'
            }, status=400)
        
        severity, severity_name = threshold.get_severity(value)
        
        return Response({
            'success': True,
            'value': value,
            'severity': severity,
            'severity_name': severity_name,
            'threshold_info': {
                'check_item_name': threshold.check_item_name,
                'direction': threshold.get_threshold_direction_display(),
                'warning': threshold.warning_threshold,
                'error': threshold.error_threshold,
                'critical': threshold.critical_threshold,
                'unit': threshold.unit
            }
        })


class AlertThresholdRuleViewSet(viewsets.ModelViewSet):
    """阈值规则视图集"""
    
    queryset = AlertThresholdRule.objects.all()
    serializer_class = AlertThresholdRuleSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        threshold_id = self.request.query_params.get('threshold')
        if threshold_id:
            queryset = queryset.filter(threshold_id=threshold_id)
        return queryset.select_related('threshold')


class AlertThresholdTemplateViewSet(viewsets.ModelViewSet):
    """阈值模板视图集"""
    
    queryset = AlertThresholdTemplate.objects.all()
    serializer_class = AlertThresholdTemplateSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        protocol = self.request.query_params.get('protocol')
        if protocol:
            queryset = queryset.filter(protocol=protocol)
        return queryset
    
    @action(detail=True, methods=['post'])
    def apply_to_customer(self, request, pk=None):
        """将模板应用到客户"""
        template = self.get_object()
        customer_id = request.data.get('customer_id')
        asset_type_id = request.data.get('asset_type_id')
        
        if not customer_id:
            return Response({
                'success': False,
                'message': '缺少customer_id'
            }, status=400)
        
        from apps.customers.models import Customer
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Response({
                'success': False,
                'message': '客户不存在'
            }, status=404)
        
        asset_type = None
        if asset_type_id:
            from apps.assets.models import AssetType
            try:
                asset_type = AssetType.objects.get(id=asset_type_id)
            except AssetType.DoesNotExist:
                return Response({
                    'success': False,
                    'message': '资产类型不存在'
                }, status=404)
        
        # 创建阈值配置
        config = template.default_config
        threshold = AlertThreshold.objects.create(
            customer=customer,
            asset_type=asset_type,
            check_item_code=template.check_item_code,
            check_item_name=template.check_item_name,
            protocol=template.protocol,
            threshold_direction=config.get('threshold_direction', 'upper'),
            value_type=config.get('value_type', 'number'),
            warning_threshold=config.get('warning_threshold', ''),
            error_threshold=config.get('error_threshold', ''),
            critical_threshold=config.get('critical_threshold', ''),
            unit=config.get('unit', '%'),
            description=config.get('description', ''),
            config=config.get('config', {}),
        )
        
        return Response({
            'success': True,
            'message': '模板应用成功',
            'threshold_id': threshold.id
        })


@api_view(['GET'])
@permission_classes([AllowAny])
def get_default_thresholds(request):
    """获取默认阈值配置建议"""
    
    defaults = {
        'mysql': [
            {
                'check_item_code': 'SESSIONS',
                'check_item_name': '会话连接数',
                'threshold_direction': 'upper',
                'value_type': 'number',
                'unit': '个',
                'warning_threshold': '100',
                'error_threshold': '200',
                'critical_threshold': '300',
                'description': 'MySQL当前连接数阈值'
            },
            {
                'check_item_code': 'BUFFER_HIT',
                'check_item_name': '缓冲池命中率',
                'threshold_direction': 'lower',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '95',
                'error_threshold': '90',
                'critical_threshold': '80',
                'description': 'InnoDB缓冲池命中率，低于阈值告警'
            },
        ],
        'oracle': [
            {
                'check_item_code': 'TABLESPACE',
                'check_item_name': '表空间使用率',
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '80',
                'error_threshold': '90',
                'critical_threshold': '95',
                'description': 'Oracle表空间使用率阈值'
            },
            {
                'check_item_code': 'SESSIONS',
                'check_item_name': '会话连接数',
                'threshold_direction': 'upper',
                'value_type': 'number',
                'unit': '个',
                'warning_threshold': '200',
                'error_threshold': '400',
                'critical_threshold': '500',
                'description': 'Oracle当前会话数阈值'
            },
            {
                'check_item_code': 'BUFFER_HIT',
                'check_item_name': '缓冲命中率',
                'threshold_direction': 'lower',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '95',
                'error_threshold': '90',
                'critical_threshold': '80',
                'description': 'Buffer Cache命中率阈值'
            },
        ],
        'snmp': [
            {
                'check_item_code': 'CPU_USAGE',
                'check_item_name': 'CPU使用率',
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '80',
                'error_threshold': '90',
                'critical_threshold': '95',
                'description': '设备CPU使用率阈值'
            },
            {
                'check_item_code': 'MEM_USAGE',
                'check_item_name': '内存使用率',
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '80',
                'error_threshold': '90',
                'critical_threshold': '95',
                'description': '设备内存使用率阈值'
            },
            {
                'check_item_code': 'DISK_USAGE',
                'check_item_name': '磁盘使用率',
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '80',
                'error_threshold': '90',
                'critical_threshold': '95',
                'description': '磁盘空间使用率阈值'
            },
        ],
        'ssh': [
            {
                'check_item_code': 'CPU_USAGE',
                'check_item_name': 'CPU使用率',
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '80',
                'error_threshold': '90',
                'critical_threshold': '95',
                'description': '服务器CPU使用率阈值'
            },
            {
                'check_item_code': 'MEM_USAGE',
                'check_item_name': '内存使用率',
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '80',
                'error_threshold': '90',
                'critical_threshold': '95',
                'description': '服务器内存使用率阈值'
            },
            {
                'check_item_code': 'DISK_USAGE',
                'check_item_name': '磁盘使用率',
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '80',
                'error_threshold': '90',
                'critical_threshold': '95',
                'description': '磁盘空间使用率阈值'
            },
            {
                'check_item_code': 'LOAD_AVERAGE',
                'check_item_name': '系统负载',
                'threshold_direction': 'upper',
                'value_type': 'number',
                'unit': '',
                'warning_threshold': '4',
                'error_threshold': '8',
                'critical_threshold': '16',
                'description': '系统平均负载（建议设为CPU核心数）'
            },
        ],
        'ping': [
            {
                'check_item_code': 'PING_LATENCY',
                'check_item_name': '响应延迟',
                'threshold_direction': 'upper',
                'value_type': 'number',
                'unit': 'ms',
                'warning_threshold': '100',
                'error_threshold': '500',
                'critical_threshold': '1000',
                'description': 'Ping响应延迟阈值'
            },
            {
                'check_item_code': 'PING_PACKET_LOSS',
                'check_item_name': '丢包率',
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '1',
                'error_threshold': '5',
                'critical_threshold': '10',
                'description': 'Ping丢包率阈值'
            },
        ],
    }
    
    protocol = request.query_params.get('protocol')
    if protocol:
        return Response(defaults.get(protocol, []))
    
    return Response(defaults)
