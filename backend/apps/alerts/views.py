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

    @action(detail=False, methods=['post'], url_path='batch-delete')
    def batch_delete(self, request):
        """批量删除告警"""
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': '请提供要删除的ID列表'}, status=400)
        deleted, _ = Alert.objects.filter(id__in=ids).delete()
        return Response({'deleted': deleted})


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
    接收本地监控系统的告警
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

    return Response({
        'success': True,
        'message': '告警接收成功',
        'alert_id': alert.id,
    }, status=201)


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
