from django.db import models
from django.utils import timezone


class ScheduledTask(models.Model):
    """计划任务模型"""
    
    TASK_TYPES = [
        ('monitoring', '监控任务'),
        ('inspection', '巡检任务'),
        ('backup', '备份任务'),
        ('report', '报表任务'),
        ('cleanup', '清理任务'),
        ('sync', '同步任务'),
    ]
    
    TARGET_TYPES = [
        ('asset', '资产'),
        ('customer', '客户'),
        ('all', '全部'),
    ]
    
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失败'),
        ('running', '运行中'),
        ('timeout', '超时'),
    ]
    
    # 基本信息
    name = models.CharField('任务名称', max_length=200, unique=True)
    description = models.TextField('任务描述', blank=True)
    task_type = models.CharField('任务类型', max_length=50, choices=TASK_TYPES)
    
    # 目标配置
    target_type = models.CharField('目标类型', max_length=50, choices=TARGET_TYPES, default='all')
    target_id = models.BigIntegerField('目标ID', null=True, blank=True)
    
    # 任务配置
    config = models.JSONField('任务配置', default=dict, blank=True)
    cron_expression = models.CharField('Cron表达式', max_length=100, blank=True)
    interval_seconds = models.IntegerField('间隔秒数', null=True, blank=True)
    
    # 状态
    is_enabled = models.BooleanField('是否启用', default=True)
    is_running = models.BooleanField('是否运行中', default=False)
    
    # 执行时间
    last_run_time = models.DateTimeField('上次运行时间', null=True, blank=True)
    next_run_time = models.DateTimeField('下次运行时间', null=True, blank=True)
    
    # 结果
    last_status = models.CharField('上次状态', max_length=20, choices=STATUS_CHOICES, null=True, blank=True)
    last_result = models.TextField('上次结果', blank=True)
    
    # 统计
    success_count = models.IntegerField('成功次数', default=0)
    failure_count = models.IntegerField('失败次数', default=0)
    total_runs = models.IntegerField('总运行次数', default=0)
    
    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'scheduled_tasks'
        verbose_name = '计划任务'
        verbose_name_plural = '计划任务管理'
        ordering = ['-created_at']
        app_label = 'scheduler'
    
    def __str__(self):
        return f'{self.name} ({self.get_task_type_display()})'
    
    def calculate_next_run_time(self):
        """计算下次运行时间"""
        if self.cron_expression:
            # TODO: 实现Cron表达式解析
            pass
        elif self.interval_seconds:
            from datetime import timedelta
            self.next_run_time = timezone.now() + timedelta(seconds=self.interval_seconds)
        return self.next_run_time


class ScheduledTaskExecution(models.Model):
    """计划任务执行记录模型"""
    
    STATUS_CHOICES = [
        ('running', '运行中'),
        ('success', '成功'),
        ('failed', '失败'),
        ('timeout', '超时'),
    ]
    
    # 关联
    task = models.ForeignKey(
        ScheduledTask, on_delete=models.CASCADE,
        related_name='executions', verbose_name='任务'
    )
    
    # 时间
    start_time = models.DateTimeField('开始时间', auto_now_add=True)
    end_time = models.DateTimeField('结束时间', null=True, blank=True)
    duration_ms = models.IntegerField('持续时间(毫秒)', null=True, blank=True)
    
    # 状态
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='running')
    
    # 结果
    result_data = models.JSONField('结果数据', default=dict, blank=True)
    error_message = models.TextField('错误信息', blank=True)
    output = models.TextField('输出日志', blank=True)
    
    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'scheduled_task_executions'
        verbose_name = '执行记录'
        verbose_name_plural = '执行记录'
        ordering = ['-start_time']
        app_label = 'scheduler'
    
    def __str__(self):
        return f'{self.task.name} - {self.start_time}'
    
    def mark_completed(self, status, result_data=None, error_message=None, output=None):
        """标记任务完成"""
        self.end_time = timezone.now()
        self.duration_ms = int((self.end_time - self.start_time).total_seconds() * 1000)
        self.status = status
        self.result_data = result_data or {}
        self.error_message = error_message or ''
        self.output = output or ''
        self.save()
        
        # 更新任务状态
        self.task.is_running = False
        self.task.last_run_time = self.start_time
        self.task.total_runs += 1
        
        if status == 'success':
            self.task.success_count += 1
            self.task.last_status = 'success'
        else:
            self.task.failure_count += 1
            self.task.last_status = 'failed'
        
        self.task.last_result = str(result_data)[:500] if result_data else ''
        self.task.calculate_next_run_time()
        self.task.save()