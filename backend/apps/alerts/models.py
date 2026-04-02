from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class Alert(models.Model):
    """告警记录模型"""
    
    SEVERITY_CHOICES = [
        (1, '信息'),
        (2, '警告'),
        (3, '错误'),
        (4, '严重'),
    ]
    
    STATUS_CHOICES = [
        ('NEW', '新告警'),
        ('ACKNOWLEDGED', '已确认'),
        ('IN_PROGRESS', '处理中'),
        ('RESOLVED', '已解决'),
        ('CLOSED', '已关闭'),
    ]
    
    SOURCE_CHOICES = [
        ('PING', '连通性检测'),
        ('INSPECTION', '巡检结果'),
        ('LOCAL', '本地监控'),
        ('MANUAL', '手动'),
        ('SCHEDULED', '定时任务'),
    ]
    
    # 基本信息
    title = models.CharField('告警标题', max_length=200)
    description = models.TextField('告警描述', blank=True)
    
    # 关联信息
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE,
        related_name='customer_alerts', verbose_name='客户'
    )
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='asset_alerts', verbose_name='资产'
    )
    
    # 告警信息
    severity = models.IntegerField('严重程度', choices=SEVERITY_CHOICES, default=2)
    alert_type = models.CharField('告警类型', max_length=50, blank=True)
    source = models.CharField('告警来源', max_length=20, choices=SOURCE_CHOICES, default='LOCAL')
    
    # 状态
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='NEW')
    
    # 告警详情（JSON）
    alert_data = models.JSONField('告警详情', default=dict, blank=True)
    
    # 触发条件
    metric_name = models.CharField('指标名称', max_length=100, blank=True)
    metric_value = models.CharField('指标值', max_length=100, blank=True)
    threshold = models.CharField('阈值', max_length=100, blank=True)
    
    # 时间
    occurred_at = models.DateTimeField('发生时间', null=True, blank=True)
    acknowledged_at = models.DateTimeField('确认时间', null=True, blank=True)
    resolved_at = models.DateTimeField('解决时间', null=True, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'alerts_alert'
        verbose_name = '告警'
        verbose_name_plural = '告警管理'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f'{self.title} ({self.get_severity_display()})'


class AlertRule(models.Model):
    """告警规则模型"""
    
    STATUS_CHOICES = [
        ('ACTIVE', '启用'),
        ('INACTIVE', '停用'),
    ]
    
    # 基本信息
    name = models.CharField('规则名称', max_length=100)
    description = models.TextField('规则描述', blank=True)
    
    # 关联
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE,
        related_name='alert_rules', verbose_name='客户'
    )
    
    # 规则配置
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    severity = models.IntegerField('告警严重程度', choices=Alert.SEVERITY_CHOICES, default=2)
    
    # 触发条件（JSON）
    conditions = models.JSONField('触发条件', default=list)
    """
    conditions格式示例:
    [
        {'metric': 'cpu_usage', 'operator': '>', 'value': 80},
        {'metric': 'memory_usage', 'operator': '>', 'value': 90}
    ]
    """
    
    # 自动创建工单
    auto_create_workorder = models.BooleanField('自动创建工单', default=True)
    workorder_template = models.JSONField('工单模板', default=dict, blank=True)
    
    # 通知配置
    notify_enabled = models.BooleanField('启用通知', default=False)
    notify_channels = models.JSONField('通知渠道', default=list)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'alerts_alert_rules'
        verbose_name = '告警规则'
        verbose_name_plural = '告警规则管理'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} ({self.customer.customer_name})'


class AlertSubscription(models.Model):
    """告警订阅模型（通知渠道配置）"""
    
    CHANNEL_CHOICES = [
        ('EMAIL', '邮件'),
        ('SMS', '短信'),
        ('WECHAT', '企业微信'),
        ('DINGTALK', '钉钉'),
        ('WEBHOOK', 'Webhook'),
    ]
    
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE,
        related_name='alert_subscriptions', verbose_name='客户'
    )
    
    name = models.CharField('订阅名称', max_length=100)
    channel = models.CharField('通知渠道', max_length=20, choices=CHANNEL_CHOICES)
    config = models.JSONField('渠道配置', default=dict)
    """
    配置示例:
    EMAIL: {'recipients': ['admin@example.com']}
    DINGTALK: {'webhook_url': 'https://oapi.dingtalk.com/...' }
    """
    
    severity_filter = models.JSONField('严重程度过滤', default=list, blank=True)
    alert_type_filter = models.JSONField('告警类型过滤', default=list, blank=True)
    
    is_active = models.BooleanField('是否启用', default=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'alert_subscriptions'
        verbose_name = '告警订阅'
        verbose_name_plural = '告警订阅管理'
    
    def __str__(self):
        return f'{self.name} ({self.get_channel_display()})'
