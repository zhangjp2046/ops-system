from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
import hashlib
import secrets

from .models import Alert, AlertRule, AlertSubscription
from .serializers import (
    AlertSerializer, AlertRuleSerializer, 
    AlertSubscriptionSerializer, AlertReceiveSerializer
)
from apps.workorder.models import WorkOrder, WorkOrderStep
from apps.assets.models import Asset


def generate_api_key():
    """生成API Key"""
    return secrets.token_hex(32)


class AlertViewSet(viewsets.ModelViewSet):
    """告警视图集"""
    
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 客户筛选
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        
        # 状态筛选
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # 严重程度筛选
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity=severity)
        
        # 时间范围
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        return queryset.select_related('customer', 'asset')
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """确认告警"""
        alert = self.get_object()
        alert.status = 'ACKNOWLEDGED'
        alert.acknowledged_at = timezone.now()
        alert.save()
        return Response({'success': True, 'message': '告警已确认'})
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """解决告警"""
        alert = self.get_object()
        alert.status = 'RESOLVED'
        alert.resolved_at = timezone.now()
        alert.save()
        return Response({'success': True, 'message': '告警已解决'})
    
    @action(detail=True, methods=['post'])
    def create_workorder(self, request, pk=None):
        """根据告警创建工单"""
        alert = self.get_object()
        
        # 检查是否已有工单
        if hasattr(alert, 'workorder'):
            return Response({'success': False, 'message': '告警已创建工单'})
        
        # 创建工单
        workorder = WorkOrder.objects.create(
            title=f'【告警】{alert.title}',
            resume=alert.description[:200] if alert.description else alert.title[:200],
            customer=alert.customer,
            asset=alert.asset,
            order_type=1,  # 技术工单
            priority=1 if alert.severity >= 3 else 0,  # 严重程度>=3为紧急
            status=0,  # 新建
            description=f'''## 告警信息
- 告警标题: {alert.title}
- 严重程度: {alert.get_severity_display()}
- 告警类型: {alert.alert_type}
- 发生时间: {alert.occurred_at or alert.created_at}
- 资产: {alert.asset.asset_name if alert.asset else '未知'}

## 告警描述
{alert.description or '无'}

## 指标信息
- 指标名称: {alert.metric_name}
- 指标值: {alert.metric_value}
- 阈值: {alert.threshold}
''',
        )
        
        # 添加跟进记录
        WorkOrderStep.objects.create(
            order=workorder,
            status=1,
            title='系统自动创建',
            description=f'由告警「{alert.title}」自动创建工单'
        )
        
        return Response({
            'success': True, 
            'message': f'工单已创建',
            'workorder_id': workorder.id
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """告警统计"""
        queryset = self.get_queryset()
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        
        total = queryset.count()
        today_count = queryset.filter(created_at__date=today).count()
        week_count = queryset.filter(created_at__date__gte=week_ago).count()
        
        # 按状态统计
        by_status = {}
        for s, name in Alert.STATUS_CHOICES:
            by_status[s] = {'name': name, 'count': queryset.filter(status=s).count()}
        
        # 按严重程度统计
        by_severity = {}
        for s, name in Alert.SEVERITY_CHOICES:
            by_severity[s] = {'name': name, 'count': queryset.filter(severity=s).count()}
        
        return Response({
            'total': total,
            'today': today_count,
            'week': week_count,
            'by_status': by_status,
            'by_severity': by_severity,
        })


class AlertRuleViewSet(viewsets.ModelViewSet):
    """告警规则视图集"""
    
    queryset = AlertRule.objects.all()
    serializer_class = AlertRuleSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        return queryset.select_related('customer')


class AlertSubscriptionViewSet(viewsets.ModelViewSet):
    """告警订阅视图集"""
    
    queryset = AlertSubscription.objects.all()
    serializer_class = AlertSubscriptionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        return queryset.select_related('customer')


@api_view(['POST'])
@permission_classes([AllowAny])
def receive_alert(request):
    """
    接收本地监控系统上报的告警
    支持API Key认证或Token认证
    """
    serializer = AlertReceiveSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response({
            'success': False,
            'message': '数据格式错误',
            'errors': serializer.errors
        }, status=400)
    
    data = serializer.validated_data
    
    # 方式1: 通过API Key认证（推荐）
    api_key = request.headers.get('X-API-Key') or request.query_params.get('api_key')
    if api_key:
        from apps.customers.models import Customer
        try:
            customer = Customer.objects.get(api_key=api_key)
        except Customer.DoesNotExist:
            return Response({
                'success': False,
                'message': '无效的API Key'
            }, status=401)
    else:
        # 方式2: 通过客户ID+Token（兼容旧方式）
        customer_id = data.get('customer_id')
        if not customer_id:
            return Response({
                'success': False,
                'message': '缺少客户标识'
            }, status=400)
        from apps.customers.models import Customer
        try:
            customer = Customer.objects.get(id=customer_id)
        except Customer.DoesNotExist:
            return Response({
                'success': False,
                'message': '客户不存在'
            }, status=404)
    
    # 查找资产
    asset = None
    asset_id = data.get('asset_identifier')
    if asset_id:
        # 尝试通过IP或主机名查找
        from apps.assets.models import AssetData
        asset_data = AssetData.objects.filter(
            field__field_code='ip_address',
            string_value=asset_id
        ).first()
        if asset_data:
            asset = asset_data.asset
        else:
            # 尝试通过ID直接查找
            try:
                asset = Asset.objects.get(id=int(asset_id))
            except (ValueError, Asset.DoesNotExist):
                pass
    
    # 创建告警
    alert = Alert.objects.create(
        title=data['title'],
        description=data.get('description', ''),
        customer=customer,
        asset=asset,
        severity=data.get('severity', 2),
        alert_type=data.get('alert_type', ''),
        source='LOCAL',
        metric_name=data.get('metric_name', ''),
        metric_value=data.get('metric_value', ''),
        threshold=data.get('threshold', ''),
        occurred_at=data.get('occurred_at') or timezone.now(),
        alert_data=data.get('alert_data', {}),
    )
    
    # 检查是否需要自动创建工单
    rules = AlertRule.objects.filter(
        customer=customer,
        status='ACTIVE',
        auto_create_workorder=True
    )
    
    workorder_id = None
    for rule in rules:
        # 简单匹配：告警类型或指标匹配规则
        if rule.alert_type and rule.alert_type == alert.alert_type:
            workorder = _create_workorder_from_alert(alert, rule)
            workorder_id = workorder.id
            break
    
    return Response({
        'success': True,
        'message': '告警接收成功',
        'alert_id': alert.id,
        'workorder_id': workorder_id
    }, status=201)


def _create_workorder_from_alert(alert, rule):
    """根据告警和规则创建工单"""
    template = rule.workorder_template or {}
    
    workorder = WorkOrder.objects.create(
        title=template.get('title', f'【告警】{alert.title}'),
        resume=alert.description[:200] if alert.description else alert.title[:200],
        customer=alert.customer,
        asset=alert.asset,
        order_type=template.get('order_type', 1),
        priority=template.get('priority', 1 if alert.severity >= 3 else 0),
        status=0,
        description=f'''## 告警信息
- 告警标题: {alert.title}
- 严重程度: {alert.get_severity_display()}
- 告警类型: {alert.alert_type}
- 发生时间: {alert.occurred_at or alert.created_at}

## 告警描述
{alert.description or '无'}

## 触发规则
- 规则名称: {rule.name}
''',
    )
    
    WorkOrderStep.objects.create(
        order=workorder,
        status=1,
        title='系统自动创建',
        description=f'由告警规则「{rule.name}」自动创建'
    )
    
    return workorder


@api_view(['GET'])
@permission_classes([AllowAny])
def get_customer_api_info(request):
    """获取客户的API认证信息（需要管理员权限）"""
    customer_id = request.query_params.get('customer_id')
    if not customer_id:
        return Response({'message': '缺少customer_id'}, status=400)
    
    from apps.customers.models import Customer
    try:
        customer = Customer.objects.get(id=customer_id)
    except Customer.DoesNotExist:
        return Response({'message': '客户不存在'}, status=404)
    
    # 如果没有API Key，生成一个新的
    if not customer.api_key:
        customer.api_key = generate_api_key()
        customer.save()
    
    return Response({
        'customer_id': customer.id,
        'customer_name': customer.customer_name,
        'api_key': customer.api_key,
        'endpoint': '/api/alerts/receive/',
    })
