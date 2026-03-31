from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from django.db.models import Count, Q

from .models import MonitoringTask, MonitoringResult, AlertRule, Alert
from .serializers import (
    MonitoringTaskSerializer, MonitoringResultSerializer,
    AlertRuleSerializer, AlertSerializer, AlertStatisticsSerializer
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