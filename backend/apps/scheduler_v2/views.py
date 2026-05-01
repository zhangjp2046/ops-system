"""
Scheduler V2 Views
"""
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Q, Count
from django_filters import rest_framework as django_filters
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

from .models import Plan, PlanTask, PlanExecution, TaskInstance, TaskTemplate, AdhocTask
from .serializers import (
    PlanSerializer, PlanCreateSerializer, PlanUpdateSerializer,
    PlanTaskSerializer, PlanTaskCreateSerializer,
    PlanExecutionSerializer, PlanExecutionListSerializer,
    TaskInstanceSerializer, TaskTemplateSerializer, TaskTemplateCreateSerializer,
    AdhocTaskSerializer, AdhocTaskCreateSerializer
)
from .executor import TaskExecutor


# 全局调度线程池（限制最大并发调度数）
_scheduler_executor = None


def get_scheduler_pool():
    global _scheduler_executor
    if _scheduler_executor is None:
        max_workers = int(os.environ.get('SCHEDULER_POOL_SIZE', '5'))
        _scheduler_executor = ThreadPoolExecutor(max_workers=max_workers)
    return _scheduler_executor


class PlanFilter(django_filters.FilterSet):
    """计划过滤器"""
    plan_type = django_filters.CharFilter(field_name='plan_type')
    status = django_filters.CharFilter(field_name='status')
    is_enabled = django_filters.BooleanFilter()
    
    class Meta:
        model = Plan
        fields = ['plan_type', 'status', 'is_enabled']


class PlanViewSet(viewsets.ModelViewSet):
    """计划视图集"""
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer
    permission_classes = []
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = PlanFilter
    ordering_fields = ['name', 'created_at', 'last_run_time', 'next_run_time']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PlanCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PlanUpdateSerializer
        return PlanSerializer
    
    def perform_create(self, serializer):
        instance = serializer.save()
        instance.calculate_next_run_time()
        instance.save()
        
        # 自动创建 PlanTask（如果是巡检类型）
        if instance.plan_type == 'inspection' and instance.inspection_plan:
            # 如果还没有任务，创建默认任务
            if not instance.tasks.exists():
                from apps.inspection.models import InspectionPlan
                try:
                    # 获取 inspection_plan 的 ID 和名称
                    if isinstance(instance.inspection_plan, int):
                        ip_id = instance.inspection_plan
                        ip_obj = InspectionPlan.objects.get(id=ip_id)
                    else:
                        ip_id = instance.inspection_plan.id
                        ip_obj = instance.inspection_plan
                    inspection_plan_name = ip_obj.name
                except:
                    ip_id = instance.inspection_plan
                    inspection_plan_name = instance.inspection_plan_name or '巡检'
                
                PlanTask.objects.create(
                    plan=instance,
                    task_type='inspection',
                    name='执行巡检',
                    description=f'执行 {inspection_plan_name} 巡检',
                    task_config={'inspection_plan_id': ip_id},
                    is_enabled=True,
                    execution_order=0,
                )
                # 更新 inspection_plan_name
                if not instance.inspection_plan_name:
                    instance.inspection_plan_name = inspection_plan_name
                    instance.save()
    
    def perform_update(self, serializer):
        instance = serializer.save()
        instance.calculate_next_run_time()
        instance.save()
    
    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """手动执行计划"""
        plan = self.get_object()
        
        # 检查是否有正在运行的执行
        running = PlanExecution.objects.filter(plan=plan, status__in=['pending', 'running']).exists()
        if running:
            return Response({'error': '有执行中的实例，请稍后再试'}, status=status.HTTP_400_BAD_REQUEST)
        
        # 创建执行记录
        execution = PlanExecution.objects.create(
            plan=plan,
            status='running',
            trigger='manual',
            total_tasks=plan.tasks.filter(is_enabled=True).count()
        )
        
        # 异步执行（简单实现）
        self._run_plan_async(execution.id)
        
        return Response({
            'message': '计划已开始执行',
            'execution_id': execution.id
        })
    
    def _run_plan_async(self, execution_id):
        """异步执行计划，使用线程池限制并发数"""
        pool = get_scheduler_pool()
        pool.submit(self._run_plan_sync, execution_id)

    def _run_plan_sync(self, execution_id):
        """同步执行计划（在线程池中运行）"""
        execution = PlanExecution.objects.get(id=execution_id)
        try:
            tasks = list(execution.plan.tasks.filter(is_enabled=True).order_by('execution_order'))
            execution.total_tasks = len(tasks)
            execution.save()

            success_count = 0
            failed_count = 0

            for task in tasks:
                instance = TaskInstance.objects.create(
                    plan_execution=execution,
                    plan_task=task,
                    status='running',
                    start_time=timezone.now()
                )
                try:
                    result = TaskExecutor.execute(task.task_type, task.task_config or {})
                    if result.get('success'):
                        instance.mark_completed('success', result)
                        success_count += 1
                    else:
                        instance.mark_completed('failed', error_message=result.get('error'))
                        failed_count += 1
                except Exception as e:
                    instance.mark_completed('failed', error_message=str(e))
                    failed_count += 1

            execution.completed_tasks = len(tasks)
            execution.success_tasks = success_count
            execution.failed_tasks = failed_count
            execution.mark_completed('success' if failed_count == 0 else 'failed')

        except Exception as e:
            execution.mark_completed('failed', error_message=str(e))
    
    @action(detail=True, methods=['post'])
    def enable(self, request, pk=None):
        """启用计划"""
        plan = self.get_object()
        plan.is_enabled = True
        plan.calculate_next_run_time()
        plan.save()
        return Response({'message': '计划已启用'})
    
    @action(detail=True, methods=['post'])
    def disable(self, request, pk=None):
        """禁用计划"""
        plan = self.get_object()
        plan.is_enabled = False
        plan.save()
        return Response({'message': '计划已禁用'})
    
    @action(detail=True, methods=['get'])
    def executions(self, request, pk=None):
        """获取计划的执行记录"""
        plan = self.get_object()
        executions = plan.executions.all()[:50]
        serializer = PlanExecutionListSerializer(executions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """获取统计信息"""
        stats = {
            'total_plans': Plan.objects.count(),
            'enabled_plans': Plan.objects.filter(is_enabled=True).count(),
            'active_plans': Plan.objects.filter(status='active', is_enabled=True).count(),
            'total_executions': PlanExecution.objects.count(),
            'executions_today': PlanExecution.objects.filter(
                start_time__date=timezone.now().date()
            ).count(),
            'success_rate': 0,
        }
        
        total = PlanExecution.objects.count()
        if total > 0:
            success = PlanExecution.objects.filter(status='success').count()
            stats['success_rate'] = round(success * 100 / total, 1)
        
        return Response(stats)
    
    @action(detail=False, methods=['get'])
    def schedule_presets(self, request):
        """获取调度预设"""
        presets = [
            {'label': '每天凌晨', 'cron': '0 1 * * *'},
            {'label': '每天上午9点', 'cron': '0 9 * * *'},
            {'label': '每天中午12点', 'cron': '0 12 * * *'},
            {'label': '每天下午6点', 'cron': '0 18 * * *'},
            {'label': '每6小时', 'cron': '0 */6 * * *'},
            {'label': '每12小时', 'cron': '0 */12 * * *'},
            {'label': '每周一', 'cron': '0 9 * * 1'},
            {'label': '每月1号', 'cron': '0 9 1 * *'},
        ]
        return Response(presets)
    
    @action(detail=False, methods=['get'])
    def linked_inspection(self, request):
        """获取已关联巡检的计划"""
        plans = Plan.objects.filter(
            inspection_plan__isnull=False
        ).values(
            'inspection_plan', 'inspection_plan_name'
        ).annotate(count=Count('id'))
        return Response(list(plans))
    
    @action(detail=True, methods=['post'])
    def sync_schedule(self, request, pk=None):
        """同步调度时间到巡检计划"""
        plan = self.get_object()
        direction = request.data.get('direction', 'to_inspection')
        
        if not plan.inspection_plan:
            return Response({'error': '未关联巡检计划'}, status=400)
        
        if direction == 'to_inspection':
            plan.inspection_plan.cron_expression = plan.cron_expression
            plan.inspection_plan.save()
            return Response({'message': '已同步到巡检计划'})
        else:
            plan.cron_expression = plan.inspection_plan.cron_expression
            plan.save()
            return Response({'message': '已从巡检计划同步'})
    
    @action(detail=False, methods=['post'])
    def from_inspection(self, request):
        """从巡检计划创建"""
        inspection_plan_id = request.data.get('inspection_plan_id')
        plan_name = request.data.get('plan_name', '')
        
        if not inspection_plan_id:
            return Response({'error': '缺少 inspection_plan_id'}, status=400)
        
        from apps.inspection.models import InspectionPlan
        try:
            inspection_plan = InspectionPlan.objects.get(id=inspection_plan_id)
        except InspectionPlan.DoesNotExist:
            return Response({'error': '巡检计划不存在'}, status=404)
        
        # 创建计划
        plan = Plan.objects.create(
            name=plan_name or f'{inspection_plan.name} - 调度',
            description=f'基于巡检计划 {inspection_plan.name} 创建',
            plan_type='inspection',
            status='draft',
            inspection_plan=inspection_plan,
            inspection_plan_name=inspection_plan.name,
            trigger_mode='schedule',
            cron_expression=inspection_plan.cron_expression,
        )
        
        # 创建任务
        PlanTask.objects.create(
            plan=plan,
            task_type='inspection',
            name='执行巡检',
            task_config={'inspection_plan_id': inspection_plan.id},
            execution_order=0
        )
        
        return Response({
            'plan_id': plan.id,
            'message': '调度计划已创建'
        })


class PlanTaskViewSet(viewsets.ModelViewSet):
    """计划任务视图集"""
    queryset = PlanTask.objects.all()
    serializer_class = PlanTaskSerializer
    permission_classes = []
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['plan', 'task_type', 'is_enabled']
    ordering_fields = ['execution_order', 'created_at']
    ordering = ['execution_order']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return PlanTaskCreateSerializer
        return PlanTaskSerializer
    
    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """重新排序任务"""
        ordering = request.data.get('ordering', [])
        for item in ordering:
            PlanTask.objects.filter(id=item['id']).update(execution_order=item['order'])
        return Response({'message': '已重新排序'})


class ExecutionFilter(django_filters.FilterSet):
    """执行记录过滤器"""
    plan = django_filters.NumberFilter(field_name='plan')
    status = django_filters.CharFilter(field_name='status')
    start_time = django_filters.DateTimeFilter(field_name='start_time')
    
    class Meta:
        model = PlanExecution
        fields = ['plan', 'status', 'start_time']


class PlanExecutionViewSet(viewsets.ReadOnlyModelViewSet):
    """计划执行记录视图集"""
    queryset = PlanExecution.objects.all()
    serializer_class = PlanExecutionSerializer
    permission_classes = []
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = ExecutionFilter
    ordering_fields = ['start_time', 'status']
    ordering = ['-start_time']
    http_method_names = ['get', 'delete']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return PlanExecutionListSerializer
        return PlanExecutionSerializer
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """获取最近的执行记录"""
        limit = int(request.query_params.get('limit', 20))
        executions = self.get_queryset()[:limit]
        serializer = PlanExecutionListSerializer(executions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def process_due(self, request):
        """处理到期的计划"""
        now = timezone.now()
        due_plans = Plan.objects.filter(
            is_enabled=True,
            status='active',
            next_run_time__lte=now
        )
        
        results = []
        for plan in due_plans:
            # 检查是否有正在运行的执行
            running = PlanExecution.objects.filter(plan=plan, status__in=['pending', 'running']).exists()
            if running:
                continue
            
            # 创建执行
            execution = PlanExecution.objects.create(
                plan=plan,
                status='running',
                trigger='schedule',
                total_tasks=plan.tasks.filter(is_enabled=True).count()
            )
            
            # 触发执行
            PlanViewSet()._run_plan_async(execution.id)
            results.append({'plan_id': plan.id, 'execution_id': execution.id})
        
        return Response({
            'processed': len(results),
            'plans': results
        })


class TaskTemplateViewSet(viewsets.ModelViewSet):
    """任务模板视图集"""
    queryset = TaskTemplate.objects.all()
    serializer_class = TaskTemplateSerializer
    permission_classes = []
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['name', 'usage_count', 'created_at']
    ordering = ['-usage_count']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TaskTemplateCreateSerializer
        return TaskTemplateSerializer
    
    @action(detail=True, methods=['post'])
    def use_template(self, request, pk=None):
        """使用模板创建计划"""
        template = self.get_object()
        data = request.data
        plan_name = data.get('plan_name', f'{template.name} - 计划')
        
        # 创建计划
        plan = Plan.objects.create(
            name=plan_name,
            description=template.description,
            plan_type=template.category,
            status='draft',
        )
        
        # 创建任务
        config = data.get('config', template.default_config)
        PlanTask.objects.create(
            plan=plan,
            task_type=template.task_type,
            name=template.name,
            task_config=config,
            execution_order=0
        )
        
        # 更新使用次数
        template.usage_count += 1
        template.save()
        
        return Response({
            'plan_id': plan.id,
            'message': '计划已创建'
        })


class AdhocTaskFilter(django_filters.FilterSet):
    """临时任务过滤器"""
    status = django_filters.CharFilter(field_name='status')
    
    class Meta:
        model = AdhocTask
        fields = ['status']


class AdhocTaskViewSet(viewsets.ModelViewSet):
    """临时任务视图集"""
    queryset = AdhocTask.objects.all()
    serializer_class = AdhocTaskSerializer
    permission_classes = []
    filter_backends = [django_filters.DjangoFilterBackend, filters.OrderingFilter]
    filterset_class = AdhocTaskFilter
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    http_method_names = ['get', 'post', 'delete']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AdhocTaskCreateSerializer
        return AdhocTaskSerializer
    
    def perform_create(self, serializer):
        serializer.save(triggered_by=str(self.request.user) if self.request.user.is_authenticated else 'anonymous')
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消临时任务"""
        task = self.get_object()
        if task.status in ['pending', 'running']:
            task.mark_completed('cancelled')
            return Response({'message': '任务已取消'})
        return Response({'error': '任务无法取消'}, status=400)
    
    @action(detail=True, methods=['post'])
    def rerun(self, request, pk=None):
        """重新执行临时任务"""
        task = self.get_object()
        if task.status not in ['success', 'failed', 'cancelled']:
            return Response({'error': '任务无法重新执行'}, status=400)
        
        # 创建新任务
        new_task = AdhocTask.objects.create(
            name=task.name,
            task_type=task.task_type,
            task_config=task.task_config,
            triggered_by=task.triggered_by
        )
        
        # 执行
        self._run_adhoc_async(new_task.id)
        
        return Response({
            'task_id': new_task.id,
            'message': '任务已重新提交'
        })
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """获取待执行的任务"""
        tasks = self.get_queryset().filter(status__in=['pending', 'running'])[:50]
        serializer = AdhocTaskSerializer(tasks, many=True)
        return Response(serializer.data)
    
    def _run_adhoc_async(self, task_id):
        """异步执行临时任务，使用线程池"""
        pool = get_scheduler_pool()
        pool.submit(self._run_adhoc_sync, task_id)

    def _run_adhoc_sync(self, task_id):
        """同步执行临时任务（在线程池中运行）"""
        task = AdhocTask.objects.get(id=task_id)
        try:
            result = TaskExecutor.execute(task.task_type, task.task_config or {})
            if result.get('success'):
                task.mark_completed('success', result)
            else:
                task.mark_completed('failed', error_message=result.get('error'))
        except Exception as e:
            task.mark_completed('failed', error_message=str(e))
