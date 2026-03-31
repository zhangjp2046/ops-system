from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class MonitoringTask(models.Model):
    """监控任务模型"""
    
    TASK_TYPES = [
        ('ping', 'Ping检测'),
        ('port', '端口检测'),
        ('snmp', 'SNMP检测'),
        ('http', 'HTTP检测'),
        ('ssl', 'SSL证书检测'),
        ('performance', '性能采集'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('completed', '已完成'),
        ('failed', '执行失败'),
    ]
    
    INTERVAL_CHOICES = [
        (60, '1分钟'),
        (300, '5分钟'),
        (600, '10分钟'),
        (1800, '30分钟'),
        (3600, '1小时'),
        (86400, '每天'),
    ]
    
    # 基本信息
    name = models.CharField('任务名称', max_length=200)
    description = models.TextField('任务描述', blank=True)
    task_type = models.CharField('任务类型', max_length=20, choices=TASK_TYPES)
    
    # 资产关联
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.CASCADE,
        related_name='monitoring_tasks', verbose_name='监控资产'
    )
    
    # 任务配置
    config = models.JSONField('任务配置', default=dict, blank=True)
    
    # 执行配置
    interval = models.IntegerField(
        '执行间隔(秒)', 
        choices=INTERVAL_CHOICES,
        default=300,
        validators=[MinValueValidator(60)]
    )
    is_enabled = models.BooleanField('是否启用', default=True)
    is_critical = models.BooleanField('是否关键任务', default=False)
    
    # 状态
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    last_run_time = models.DateTimeField('上次执行时间', null=True, blank=True)
    next_run_time = models.DateTimeField('下次执行时间', null=True, blank=True)
    
    # 统计
    success_count = models.IntegerField('成功次数', default=0)
    failure_count = models.IntegerField('失败次数', default=0)
    last_success_time = models.DateTimeField('上次成功时间', null=True, blank=True)
    last_failure_time = models.DateTimeField('上次失败时间', null=True, blank=True)
    
    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'monitoring_tasks'
        verbose_name = '监控任务'
        verbose_name_plural = '监控任务管理'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} ({self.get_task_type_display()})'


class MonitoringResult(models.Model):
    """监控结果模型"""
    
    STATUS_CHOICES = [
        ('success', '成功'),
        ('warning', '警告'),
        ('critical', '严重'),
        ('timeout', '超时'),
        ('error', '错误'),
        ('unknown', '未知'),
    ]
    
    # 关联
    task = models.ForeignKey(
        MonitoringTask, on_delete=models.CASCADE,
        related_name='results', verbose_name='监控任务'
    )
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.CASCADE,
        related_name='monitoring_results', verbose_name='资产'
    )
    
    # 状态
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='unknown')
    
    # 性能指标
    response_time = models.FloatField('响应时间(ms)', null=True, blank=True)
    uptime = models.FloatField('可用率(%)', null=True, blank=True)
    cpu_usage = models.FloatField('CPU使用率(%)', null=True, blank=True)
    memory_usage = models.FloatField('内存使用率(%)', null=True, blank=True)
    disk_usage = models.FloatField('磁盘使用率(%)', null=True, blank=True)
    network_in = models.FloatField('入流量(Mbps)', null=True, blank=True)
    network_out = models.FloatField('出流量(Mbps)', null=True, blank=True)
    
    # 端口检测
    port_check = models.JSONField('端口检测结果', default=dict, blank=True)
    
    # 错误信息
    error_message = models.TextField('错误信息', blank=True)
    error_details = models.JSONField('错误详情', default=dict, blank=True)
    
    # 原始数据
    raw_data = models.JSONField('原始数据', default=dict, blank=True)
    
    # 执行时间
    start_time = models.DateTimeField('开始时间', auto_now_add=True)
    end_time = models.DateTimeField('结束时间', null=True, blank=True)
    duration = models.IntegerField('持续时间(ms)', null=True, blank=True)
    
    class Meta:
        db_table = 'monitoring_results'
        verbose_name = '监控结果'
        verbose_name_plural = '监控结果管理'
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['asset', 'status']),
            models.Index(fields=['start_time']),
        ]
    
    def __str__(self):
        return f'{self.asset.asset_name} - {self.get_status_display()}'


class AlertRule(models.Model):
    """告警规则模型"""
    
    CONDITION_TYPES = [
        ('gt', '大于'),
        ('lt', '小于'),
        ('eq', '等于'),
        ('ne', '不等于'),
        ('gte', '大于等于'),
        ('lte', '小于等于'),
    ]
    
    SEVERITY_CHOICES = [
        ('info', '信息'),
        ('warning', '警告'),
        ('critical', '严重'),
    ]
    
    # 基本信息
    name = models.CharField('规则名称', max_length=200)
    description = models.TextField('规则描述', blank=True)
    metric_name = models.CharField('指标名称', max_length=100)
    condition = models.CharField('条件', max_length=10, choices=CONDITION_TYPES)
    threshold = models.FloatField('阈值')
    severity = models.CharField('严重程度', max_length=20, choices=SEVERITY_CHOICES, default='warning')
    
    # 关联
    asset_type = models.ForeignKey(
        'assets.AssetType', on_delete=models.CASCADE,
        related_name='alert_rules', verbose_name='资产类型'
    )
    
    # 配置
    is_enabled = models.BooleanField('是否启用', default=True)
    check_interval = models.IntegerField('检查间隔(秒)', default=300)
    
    # 通知配置
    notify_enabled = models.BooleanField('是否通知', default=True)
    notify_channels = models.JSONField('通知渠道', default=list, blank=True)
    notify_recipients = models.JSONField('通知人', default=list, blank=True)
    
    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'alert_rules'
        verbose_name = '告警规则'
        verbose_name_plural = '告警规则管理'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} ({self.get_severity_display()})'


class Alert(models.Model):
    """告警记录模型"""
    
    STATUS_CHOICES = [
        ('open', '未处理'),
        ('acknowledged', '已确认'),
        ('resolved', '已解决'),
        ('closed', '已关闭'),
    ]
    
    SEVERITY_CHOICES = [
        ('info', '信息'),
        ('warning', '警告'),
        ('critical', '严重'),
    ]
    
    # 基本信息
    title = models.CharField('告警标题', max_length=200)
    message = models.TextField('告警信息')
    severity = models.CharField('严重程度', max_length=20, choices=SEVERITY_CHOICES, default='warning')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='open')
    
    # 关联
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.CASCADE,
        related_name='alerts', verbose_name='资产'
    )
    alert_rule = models.ForeignKey(
        AlertRule, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='alerts', verbose_name='告警规则'
    )
    monitoring_result = models.ForeignKey(
        MonitoringResult, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='alerts', verbose_name='监控结果'
    )
    
    # 触发值
    trigger_value = models.FloatField('触发值', null=True, blank=True)
    threshold = models.FloatField('阈值', null=True, blank=True)
    
    # 时间
    occurred_at = models.DateTimeField('发生时间', auto_now_add=True)
    acknowledged_at = models.DateTimeField('确认时间', null=True, blank=True)
    resolved_at = models.DateTimeField('解决时间', null=True, blank=True)
    
    # 处理信息
    acknowledged_by = models.CharField('确认人', max_length=100, blank=True)
    resolved_by = models.CharField('解决人', max_length=100, blank=True)
    resolution_note = models.TextField('处理备注', blank=True)
    
    class Meta:
        db_table = 'alerts'
        verbose_name = '告警记录'
        verbose_name_plural = '告警记录管理'
        ordering = ['-occurred_at']
        indexes = [
            models.Index(fields=['asset', 'status']),
            models.Index(fields=['severity', 'status']),
            models.Index(fields=['occurred_at']),
        ]
    
    def __str__(self):
        return f'{self.title} - {self.asset.asset_name}'