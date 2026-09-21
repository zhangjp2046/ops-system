from django.db import models


class PushLog(models.Model):
    """推送日志 - 记录每次推送到 ops-center 的情况"""

    PUSH_TYPE_CHOICES = [
        ('inspection', '巡检结果'),
        ('alert', '告警'),
        ('asset_status', '资产状态'),
        ('heartbeat', '心跳检测'),
        ('monitoring_data', '监控数据'),
    ]
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失败'),
        ('partial', '部分成功'),
        ('retrying', '重试中'),
    ]

    push_type = models.CharField('推送类型', max_length=20, choices=PUSH_TYPE_CHOICES, db_index=True)
    status = models.CharField('状态', max_length=10, choices=STATUS_CHOICES, default='success')
    records_count = models.IntegerField('推送记录数', default=0, help_text='本次推送的记录条数')
    error_message = models.TextField('错误信息', blank=True, default='')

    # 推送详情
    endpoint = models.CharField('目标端点', max_length=200, blank=True, default='')
    request_data_size = models.IntegerField('请求数据大小(B)', default=0)

    # 重试相关
    retry_count = models.IntegerField('重试次数', default=0)
    last_retry_at = models.DateTimeField('最后重试时间', null=True, blank=True)
    next_retry_at = models.DateTimeField('下次重试时间', null=True, blank=True)

    # 原始推送数据（用于重试）
    request_payload = models.JSONField('推送数据', null=True, blank=True, help_text='原始推送数据，支持重试')

    # 时间
    created_at = models.DateTimeField('推送时间', auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'push_logs'
        ordering = ['-created_at']
        verbose_name = '推送日志'
        verbose_name_plural = '推送日志'

    def __str__(self):
        return f'{self.get_push_type_display()} - {self.status} @ {self.created_at}'
