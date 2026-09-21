from django.db import models
from django.utils import timezone
from apps.inspection.models import InspectionPlan


class Plan(models.Model):
    """任务计划"""
    
    PLAN_TYPES = [
        ('inspection', '巡检计划'),
        ('push', '推送计划'),
        ('monitoring', '监控计划'),
        ('discovery', '发现计划'),
        ('mixed', '综合计划'),
    ]
    
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('active', '启用'),
        ('paused', '暂停'),
        ('archived', '归档'),
    ]
    
    TRIGGER_MODES = [
        ('schedule', '定时调度'),
        ('adhoc', '临时执行'),
        ('manual', '手动触发'),
    ]
    
    name = models.CharField('计划名称', max_length=200)
    description = models.TextField('描述', blank=True)
    plan_type = models.CharField('计划类型', max_length=50, choices=PLAN_TYPES, default='mixed')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # 关联巡检计划
    inspection_plan = models.ForeignKey(
        InspectionPlan, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='scheduler_plans'
    )
    inspection_plan_name = models.CharField('关联巡检名称', max_length=200, blank=True)
    
    # 调度配置
    trigger_mode = models.CharField('触发模式', max_length=20, choices=TRIGGER_MODES, default='schedule')
    cron_expression = models.CharField('Cron表达式', max_length=100, blank=True)
    interval_seconds = models.IntegerField('间隔秒数', null=True, blank=True)
    
    # 执行配置
    is_enabled = models.BooleanField('是否启用', default=True)
    max_concurrent = models.IntegerField('最大并发', default=1)
    timeout_seconds = models.IntegerField('超时秒数', default=3600)
    
    # 时间
    next_run_time = models.DateTimeField('下次运行时间', null=True, blank=True)
    last_run_time = models.DateTimeField('上次运行时间', null=True, blank=True)
    
    # 统计
    total_executions = models.IntegerField('总执行次数', default=0)
    success_count = models.IntegerField('成功次数', default=0)
    failure_count = models.IntegerField('失败次数', default=0)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'scheduler_v2_plans'
        verbose_name = '任务计划'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} ({self.get_plan_type_display()})'
    
    def calculate_next_run_time(self):
        """计算下次运行时间"""
        if self.cron_expression and self.is_enabled:
            try:
                from croniter import croniter
                cron = croniter(self.cron_expression, timezone.now())
                self.next_run_time = cron.get_next(type(self.next_run_time or timezone.now()))
            except Exception:
                self.next_run_time = None
        elif self.interval_seconds and self.is_enabled:
            from datetime import timedelta
            self.next_run_time = timezone.now() + timedelta(seconds=self.interval_seconds)
        return self.next_run_time


class PlanTask(models.Model):
    """计划任务"""
    
    TASK_TYPES = [
        ('inspection', '巡检任务'),
        ('push_alert', '告警推送'),
        ('push_inspection', '巡检结果推送'),
        ('push_status', '状态推送'),
        ('status_refresh', '状态刷新'),
        ('discovery_scan', '发现扫描'),
        ('cleanup', '数据清理'),
        ('report', '生成报表'),
        ('dashboard_refresh', '仪表盘刷新'),
    ]
    
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='tasks')
    task_type = models.CharField('任务类型', max_length=50, choices=TASK_TYPES)
    name = models.CharField('任务名称', max_length=200)
    description = models.TextField('描述', blank=True)
    
    # 配置
    task_config = models.JSONField('任务配置', default=dict)
    is_enabled = models.BooleanField('是否启用', default=True)
    execution_order = models.IntegerField('执行顺序', default=0)
    timeout_seconds = models.IntegerField('超时秒数', default=300)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'scheduler_v2_plan_tasks'
        verbose_name = '计划任务'
        ordering = ['execution_order']
    
    def __str__(self):
        return f'{self.plan.name} - {self.name}'


class PlanExecution(models.Model):
    """计划执行记录"""
    
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
        ('timeout', '超时'),
    ]
    
    TRIGGER_CHOICES = [
        ('schedule', '定时调度'),
        ('adhoc', '临时执行'),
        ('manual', '手动触发'),
    ]
    
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='executions')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    trigger = models.CharField('触发方式', max_length=20, choices=TRIGGER_CHOICES, default='manual')
    
    # 统计
    total_tasks = models.IntegerField('总任务数', default=0)
    completed_tasks = models.IntegerField('完成任务数', default=0)
    success_tasks = models.IntegerField('成功任务数', default=0)
    failed_tasks = models.IntegerField('失败任务数', default=0)
    
    # 时间
    start_time = models.DateTimeField('开始时间', auto_now_add=True)
    end_time = models.DateTimeField('结束时间', null=True, blank=True)
    duration_ms = models.IntegerField('持续时间(ms)', null=True, blank=True)
    
    # 结果
    result_data = models.JSONField('结果数据', default=dict)
    error_message = models.TextField('错误信息', blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'scheduler_v2_plan_executions'
        verbose_name = '计划执行记录'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.plan.name} - {self.start_time}'
    
    def mark_completed(self, status, result_data=None, error_message=None):
        self.end_time = timezone.now()
        self.duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)
        self.status = status
        self.result_data = result_data or {}
        self.error_message = error_message or ''
        self.save()
        
        # 更新计划统计
        self.plan.total_executions += 1
        self.plan.last_run_time = self.start_time
        if status == 'success':
            self.plan.success_count += 1
        else:
            self.plan.failure_count += 1
        self.plan.calculate_next_run_time()
        self.plan.save()


class TaskInstance(models.Model):
    """任务实例（执行中的单个任务）"""
    
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
        ('timeout', '超时'),
    ]
    
    plan_execution = models.ForeignKey(PlanExecution, on_delete=models.CASCADE, related_name='task_instances')
    plan_task = models.ForeignKey(PlanTask, on_delete=models.CASCADE, related_name='instances')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # 时间
    start_time = models.DateTimeField('开始时间', null=True, blank=True)
    end_time = models.DateTimeField('结束时间', null=True, blank=True)
    duration_ms = models.IntegerField('持续时间(ms)', null=True, blank=True)
    
    # 结果
    result_data = models.JSONField('结果数据', default=dict)
    error_message = models.TextField('错误信息', blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'scheduler_v2_task_instances'
        verbose_name = '任务实例'
        ordering = ['id']
    
    def mark_completed(self, status, result_data=None, error_message=None):
        self.end_time = timezone.now()
        if self.start_time:
            self.duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)
        self.status = status
        self.result_data = result_data or {}
        self.error_message = error_message or ''
        self.save()


class TaskTemplate(models.Model):
    """任务模板"""
    
    CATEGORIES = [
        ('inspection', '巡检'),
        ('push', '推送'),
        ('monitoring', '监控'),
        ('discovery', '发现'),
        ('maintenance', '维护'),
    ]
    
    name = models.CharField('模板名称', max_length=200, unique=True)
    description = models.TextField('描述', blank=True)
    category = models.CharField('类别', max_length=50, choices=CATEGORIES)
    icon = models.CharField('图标', max_length=50, default='Setting')
    color = models.CharField('颜色', max_length=20, default='#409EFF')
    
    # 模板配置
    task_type = models.CharField('任务类型', max_length=50)
    default_config = models.JSONField('默认配置', default=dict)
    
    # 统计
    usage_count = models.IntegerField('使用次数', default=0)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'scheduler_v2_task_templates'
        verbose_name = '任务模板'
    
    def __str__(self):
        return self.name


class AdhocTask(models.Model):
    """临时任务"""
    
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('running', '运行中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('cancelled', '已取消'),
    ]
    
    name = models.CharField('任务名称', max_length=200)
    task_type = models.CharField('任务类型', max_length=50)
    task_config = models.JSONField('任务配置', default=dict)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # 执行信息
    triggered_by = models.CharField('触发者', max_length=100, blank=True)
    start_time = models.DateTimeField('开始时间', auto_now_add=True)
    end_time = models.DateTimeField('结束时间', null=True, blank=True)
    duration_ms = models.IntegerField('持续时间(ms)', null=True, blank=True)
    
    # 结果
    result_data = models.JSONField('结果数据', default=dict)
    error_message = models.TextField('错误信息', blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'scheduler_v2_adhoc_tasks'
        verbose_name = '临时任务'
        ordering = ['-created_at']
    
    def mark_completed(self, status, result_data=None, error_message=None):
        self.end_time = timezone.now()
        self.duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)
        self.status = status
        self.result_data = result_data or {}
        self.error_message = error_message or ''
        self.save()
