from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from django.db.models import Count, Q, Subquery, OuterRef, Max, F

from .models import MonitoringTask, MonitoringResult, AlertRule, Alert, MonitoringDataPoint
from .serializers import (
    MonitoringTaskSerializer, MonitoringResultSerializer,
    AlertRuleSerializer, AlertSerializer, AlertStatisticsSerializer,
    MonitoringDataPointSerializer
)


class MonitoringTaskFilter(django_filters.FilterSet):
    """监控任务过滤器"""
    
    asset = django_filters.NumberFilter(field_name='asset__id')
    task_type = django_filters.CharFilter(field_name='task_type')
    status = django_filters.CharFilter(field_name='status')
    is_enabled = django_filters.BooleanFilter()
    
    class Meta:
        model = MonitoringTask
        fields = ['asset', 'task_type', 'status', 'is_enabled']


class MonitoringTaskViewSet(viewsets.ModelViewSet):
    """监控任务视图集"""
    
    queryset = MonitoringTask.objects.all()
    serializer_class = MonitoringTaskSerializer
    permission_classes = []
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = MonitoringTaskFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'last_run_time']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """手动执行监控任务"""
        task = self.get_object()
        
        # 这里可以添加实际的监控执行逻辑
        # 目前只是模拟
        return Response({
            'message': f'任务 {task.name} 已加入执行队列',
            'task_id': task.id
        })
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """启用任务"""
        task = self.get_object()
        task.is_enabled = True
        task.save()
        return Response({'message': '任务已启用'})
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """禁用任务"""
        task = self.get_object()
        task.is_enabled = False
        task.save()
        return Response({'message': '任务已禁用'})


class MonitoringResultFilter(django_filters.FilterSet):
    """监控结果过滤器"""
    
    asset = django_filters.NumberFilter(field_name='asset__id')
    task = django_filters.NumberFilter(field_name='task__id')
    status = django_filters.CharFilter(field_name='status')
    start_time = django_filters.DateTimeFilter(field_name='start_time')
    
    class Meta:
        model = MonitoringResult
        fields = ['asset', 'task', 'status', 'start_time']


class MonitoringResultViewSet(viewsets.ModelViewSet):
    """监控结果视图集"""
    
    queryset = MonitoringResult.objects.all()
    serializer_class = MonitoringResultSerializer
    permission_classes = []
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = MonitoringResultFilter
    ordering_fields = ['start_time', 'status', 'response_time']
    ordering = ['-start_time']
    
    @action(detail=False, methods=['get'])
    def latest(self, request):
        """获取最新结果"""
        asset_id = request.query_params.get('asset_id')
        if not asset_id:
            return Response({'error': '需要asset_id参数'}, status=400)
        
        results = MonitoringResult.objects.filter(
            asset_id=asset_id
        ).order_by('-start_time')[:10]
        
        serializer = self.get_serializer(results, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取统计信息"""
        asset_id = request.query_params.get('asset_id')
        
        queryset = MonitoringResult.objects.all()
        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)
        
        stats = {
            'total': queryset.count(),
            'success': queryset.filter(status='success').count(),
            'warning': queryset.filter(status='warning').count(),
            'critical': queryset.filter(status='critical').count(),
            'error': queryset.filter(status__in=['error', 'timeout']).count(),
        }
        
        return Response(stats)


class AlertRuleFilter(django_filters.FilterSet):
    """告警规则过滤器"""
    
    asset_type = django_filters.NumberFilter(field_name='asset_type__id')
    severity = django_filters.CharFilter(field_name='severity')
    is_enabled = django_filters.BooleanFilter()
    
    class Meta:
        model = AlertRule
        fields = ['asset_type', 'severity', 'is_enabled']


class AlertRuleViewSet(viewsets.ModelViewSet):
    """告警规则视图集"""
    
    queryset = AlertRule.objects.all()
    serializer_class = AlertRuleSerializer
    permission_classes = []
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = AlertRuleFilter
    search_fields = ['name', 'description']
    ordering = ['-created_at']
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """启用规则"""
        rule = self.get_object()
        rule.is_enabled = True
        rule.save()
        return Response({'message': '规则已启用'})
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """禁用规则"""
        rule = self.get_object()
        rule.is_enabled = False
        rule.save()
        return Response({'message': '规则已禁用'})


class AlertFilter(django_filters.FilterSet):
    """告警记录过滤器"""
    
    asset = django_filters.NumberFilter(field_name='asset__id')
    severity = django_filters.CharFilter(field_name='severity')
    status = django_filters.CharFilter(field_name='status')
    
    class Meta:
        model = Alert
        fields = ['asset', 'severity', 'status']


class AlertViewSet(viewsets.ModelViewSet):
    """告警记录视图集"""
    
    queryset = Alert.objects.all()
    serializer_class = AlertSerializer
    permission_classes = []
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = AlertFilter
    search_fields = ['title', 'message']
    ordering_fields = ['occurred_at', 'severity', 'status']
    ordering = ['-occurred_at']
    
    @action(detail=True, methods=['post'])
    def acknowledge(self, request, pk=None):
        """确认告警"""
        alert = self.get_object()
        alert.status = 'acknowledged'
        alert.acknowledged_at = request.data.get('acknowledged_at')
        alert.acknowledged_by = request.data.get('acknowledged_by', 'system')
        alert.save()
        return Response({'message': '告警已确认'})
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """解决告警"""
        alert = self.get_object()
        alert.status = 'resolved'
        alert.resolved_at = request.data.get('resolved_at')
        alert.resolved_by = request.data.get('resolved_by', 'system')
        alert.resolution_note = request.data.get('resolution_note', '')
        alert.save()
        return Response({'message': '告警已解决'})
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        """关闭告警"""
        alert = self.get_object()
        alert.status = 'closed'
        alert.save()
        return Response({'message': '告警已关闭'})
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """告警统计"""
        queryset = Alert.objects.all()
        
        stats = queryset.aggregate(
            total=Count('id'),
            open=Count('id', filter=Q(status='open')),
            acknowledged=Count('id', filter=Q(status='acknowledged')),
            resolved=Count('id', filter=Q(status='resolved')),
            closed=Count('id', filter=Q(status='closed')),
        )
        
        # 按严重程度统计
        severity_stats = Alert.objects.values('severity').annotate(
            count=Count('id')
        )
        
        stats['by_severity'] = {
            item['severity']: item['count'] 
            for item in severity_stats
        }
        
        # 按资产统计
        asset_stats = Alert.objects.values(
            'asset__asset_name'
        ).annotate(
            count=Count('id'),
            open_count=Count('id', filter=Q(status='open'))
        ).order_by('-open_count')[:10]
        
        stats['by_asset'] = list(asset_stats)
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def unhandled(self, request):
        """未处理告警"""
        alerts = Alert.objects.filter(
            status__in=['open', 'acknowledged']
        ).order_by('-occurred_at')[:50]

        serializer = self.get_serializer(alerts, many=True)
        return Response(serializer.data)


class MonitoringDataViewSet(viewsets.ReadOnlyModelViewSet):
    """监控数据中心 - 只读视图集"""
    queryset = MonitoringDataPoint.objects.all()
    serializer_class = MonitoringDataPointSerializer
    filter_backends = [filters.OrderingFilter]
    filterset_class = None  # 使用 get_queryset 里的自定义过滤
    ordering_fields = ['recorded_at', 'numeric_value', 'severity']
    ordering = ['-recorded_at']

    def get_queryset(self):
        queryset = super().get_queryset()
        asset_id = self.request.query_params.get('asset')
        check_item_code = self.request.query_params.get('check_item_code')
        protocol = self.request.query_params.get('protocol')
        customer_id = self.request.query_params.get('customer')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')

        if asset_id:
            queryset = queryset.filter(asset_id=asset_id)
        if check_item_code:
            queryset = queryset.filter(check_item_code=check_item_code)
        if protocol:
            queryset = queryset.filter(protocol=protocol)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        if start_date:
            from django.utils import timezone
            queryset = queryset.filter(recorded_at__gte=start_date)
        if end_date:
            queryset = queryset.filter(recorded_at__lte=end_date)

        return queryset

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """每个资产每个指标的最近一条数据"""
        from django.db.models import Subquery, OuterRef

        latest_ids = MonitoringDataPoint.objects.filter(
            asset=OuterRef('asset'),
            check_item_code=OuterRef('check_item_code')
        ).order_by('-recorded_at').values('id')[:1]

        latest_data = MonitoringDataPoint.objects.filter(
            id__in=Subquery(latest_ids)
        ).order_by('asset', 'check_item_code')

        serializer = self.get_serializer(latest_data, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def timeline(self, request):
        """
        指标时间线 - 按资产+指标获取时间序列数据
        query params: asset, check_item_code, days(default 7)
        """
        from django.utils import timezone
        from datetime import timedelta

        asset_id = request.query_params.get('asset')
        check_item_code = request.query_params.get('check_item_code')
        days = int(request.query_params.get('days', 7))

        if not asset_id or not check_item_code:
            return Response({'error': '需要 asset 和 check_item_code 参数'}, status=400)

        start_time = timezone.now() - timedelta(days=days)
        data = MonitoringDataPoint.objects.filter(
            asset_id=asset_id,
            check_item_code=check_item_code,
            recorded_at__gte=start_time,
        ).order_by('recorded_at')

        serializer = self.get_serializer(data, many=True)
        return Response({
            'asset_id': asset_id,
            'check_item_code': check_item_code,
            'days': days,
            'data': serializer.data,
        })

    @action(detail=False, methods=['get'])
    def overview(self, request):
        """监控概览 - 各指标最新值（每资产每指标只返回一条最新记录）"""
        from django.db.models import Window
        from django.db.models.functions import RowNumber as RN

        queryset = MonitoringDataPoint.objects.all()

        # 查询参数过滤
        protocol = request.query_params.get('protocol')
        customer_id = request.query_params.get('customer')
        asset_type = request.query_params.get('asset_type')
        if protocol:
            queryset = queryset.filter(protocol=protocol)
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        if asset_type:
            queryset = queryset.filter(asset__asset_type_id=asset_type)

        # 使用窗口函数：按(asset, check_item_code)分组，取recorded_at最大的那条
        ranked = queryset.annotate(
            _rank=Window(
                expression=RN(),
                partition_by=['asset_id', 'check_item_code'],
                order_by=F('recorded_at').desc()
            )
        )
        overview = ranked.filter(_rank=1).select_related('asset', 'customer').order_by('-recorded_at', 'asset__asset_name', 'check_item_code')

        serializer = self.get_serializer(overview, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_asset(self, request):
        """按资产查看所有监控指标"""
        asset_id = request.query_params.get('asset')
        if not asset_id:
            return Response({'error': '需要 asset 参数'}, status=400)

        from django.db.models import Max

        latest_ids = MonitoringDataPoint.objects.filter(
            asset_id=asset_id,
            check_item_code=OuterRef('check_item_code'),
        ).order_by('-recorded_at').values('id')[:1]

        data = MonitoringDataPoint.objects.filter(
            id__in=Subquery(latest_ids)
        ).order_by('check_item_code')

        serializer = self.get_serializer(data, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def batch_delete(self, request):
        """批量删除监控数据点"""
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': '需要 ids 参数'}, status=400)
        count, _ = MonitoringDataPoint.objects.filter(id__in=ids).delete()
        return Response({'deleted': count})