from django.db import models


class ScheduledTask(models.Model):
    """（旧版）定时任务 - 兼容层，已迁移到 scheduler_v2"""

    name = models.CharField('任务名称', max_length=200)
    task_type = models.CharField('任务类型', max_length=50, default='')
    description = models.TextField('描述', blank=True)
    is_enabled = models.BooleanField('是否启用', default=True)
    is_running = models.BooleanField('是否运行中', default=False)
    cron_expression = models.CharField('Cron表达式', max_length=100, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'scheduler_tasks'
        managed = False
        verbose_name = '定时任务（旧版）'

    def __str__(self):
        return self.name


class ScheduledTaskExecution(models.Model):
    """（旧版）任务执行 - 兼容层，已迁移到 scheduler_v2"""

    task = models.ForeignKey(ScheduledTask, on_delete=models.CASCADE, null=True)
    status = models.CharField('状态', max_length=20, default='pending')
    start_time = models.DateTimeField('开始时间')
    end_time = models.DateTimeField('结束时间', null=True)
    duration_ms = models.IntegerField('耗时(ms)', null=True)
    error_message = models.TextField('错误信息', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'scheduler_task_executions'
        managed = False
        verbose_name = '任务执行记录（旧版）'

    def __str__(self):
        return f'{self.task} - {self.status}'
