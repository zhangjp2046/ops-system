from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters import rest_framework as django_filters
from django.utils import timezone
from datetime import timedelta

from .models import ScheduledTask, ScheduledTaskExecution
from .serializers import (
    ScheduledTaskSerializer, ScheduledTaskExecutionSerializer,
    ScheduledTaskCreateSerializer, ScheduledTaskUpdateSerializer
)


class ScheduledTaskFilter(django_filters.FilterSet):
    """计划任务过滤器"""
    
    task_type = django_filters.CharFilter(field_name='task_type')
    is_enabled = django_filters.BooleanFilter()
    is_running = django_filters.BooleanFilter()
    
    class Meta:
        model = ScheduledTask
        fields = ['task_type', 'is_enabled', 'is_running']


class ScheduledTaskViewSet(viewsets.ModelViewSet):
    """计划任务视图集"""
    
    queryset = ScheduledTask.objects.all()
    serializer_class = ScheduledTaskSerializer
    permission_classes = []
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ScheduledTaskFilter
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at', 'last_run_time', 'next_run_time']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ScheduledTaskCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ScheduledTaskUpdateSerializer
        return ScheduledTaskSerializer
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """手动执行计划任务"""
        task = self.get_object()
        
        if task.is_running:
            return Response(
                {'error': '任务正在执行中'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 创建执行记录
        execution = ScheduledTaskExecution.objects.create(
            task=task,
            status='running'
        )
        
        # 更新任务状态
        task.is_running = True
        task.save()
        
        # 这里可以添加实际的执行逻辑
        # 目前只是模拟
        try:
            # 模拟执行
            result_data = {'executed': True, 'message': '任务已加入执行队列'}
            
            execution.mark_completed(
                status='success',
                result_data=result_data,
                output='任务执行成功'
            )
            
            return Response({
                'message': '任务执行成功',
                'execution_id': execution.id
            })
            
        except Exception as e:
            execution.mark_completed(
                status='failed',
                error_message=str(e)
            )
            
            return Response(
                {'error': f'任务执行失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """启用任务"""
        task = self.get_object()
        task.is_enabled = True
        task.calculate_next_run_time()
        task.save()
        return Response({'message': '任务已启用'})
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """禁用任务"""
        task = self.get_object()
        task.is_enabled = False
        task.is_running = False
        task.save()
        return Response({'message': '任务已禁用'})
    
    @action(detail=False, methods=['get'])
    def due_tasks(self, request):
        """获取待执行的任务"""
        now = timezone.now()
        tasks = ScheduledTask.objects.filter(
            is_enabled=True,
            is_running=False
        ).filter(
            models.Q(next_run_time__lte=now) | models.Q(next_run_time__isnull=True)
        )
        
        serializer = self.get_serializer(tasks, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取统计信息"""
        stats = {
            'total': ScheduledTask.objects.count(),
            'enabled': ScheduledTask.objects.filter(is_enabled=True).count(),
            'running': ScheduledTask.objects.filter(is_running=True).count(),
            'total_executions': ScheduledTaskExecution.objects.count(),
            'successful_executions': ScheduledTaskExecution.objects.filter(status='success').count(),
            'failed_executions': ScheduledTaskExecution.objects.filter(status='failed').count(),
        }
        return Response(stats)


class ScheduledTaskExecutionFilter(django_filters.FilterSet):
    """执行记录过滤器"""
    
    task = django_filters.NumberFilter(field_name='task__id')
    status = django_filters.CharFilter(field_name='status')
    start_time = django_filters.DateTimeFilter(field_name='start_time')
    
    class Meta:
        model = ScheduledTaskExecution
        fields = ['task', 'status', 'start_time']


class ScheduledTaskExecutionViewSet(viewsets.ModelViewSet):
    """计划任务执行记录视图集"""
    
    queryset = ScheduledTaskExecution.objects.all()
    serializer_class = ScheduledTaskExecutionSerializer
    permission_classes = []
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ScheduledTaskExecutionFilter
    ordering_fields = ['start_time', 'status', 'duration_ms']
    ordering = ['-start_time']
    http_method_names = ['get', 'delete']
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """获取最近的执行记录"""
        limit = int(request.query_params.get('limit', 20))
        executions = self.get_queryset()[:limit]
        serializer = self.get_serializer(executions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def task_executions(self, request):
        """获取指定任务的执行记录"""
        task_id = request.query_params.get('task_id')
        if not task_id:
            return Response({'error': '需要task_id参数'}, status=400)
        
        executions = self.get_queryset().filter(task_id=task_id)[:50]
        serializer = self.get_serializer(executions, many=True)
        return Response(serializer.data)


# 添加需要的import
from django.db import models