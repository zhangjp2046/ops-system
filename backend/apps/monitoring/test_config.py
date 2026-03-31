"""
监控测试配置和结果模型
"""
from django.db import models
from apps.users.models import User


class MonitorTestConfig(models.Model):
    """监控测试配置"""
    
    PROTOCOL_CHOICES = [
        ('ping', 'Ping'),
        ('port', '端口检测'),
        ('ssh', 'SSH'),
        ('snmp', 'SNMP'),
        ('mysql', 'MySQL'),
        ('postgresql', 'PostgreSQL'),
        ('mssql', 'MSSQL'),
        ('oracle', 'Oracle'),
    ]
    
    # 基本信息
    name = models.CharField('配置名称', max_length=100)
    description = models.TextField('描述', blank=True)
    
    # 关联
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE,
        related_name='test_configs', verbose_name='客户'
    )
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='test_configs', verbose_name='资产'
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_test_configs', verbose_name='创建人'
    )
    
    # 配置
    protocol = models.CharField('协议', max_length=20, choices=PROTOCOL_CHOICES)
    host = models.CharField('主机', max_length=200)
    port = models.IntegerField('端口', null=True, blank=True)
    
    # 协议特定配置 (JSON)
    config = models.JSONField('协议配置', default=dict)
    """
    协议配置示例:
    Ping: {}
    SSH: {'username': 'root', 'password': 'xxx', 'key_file': '/path/to/key'}
    SNMP: {'community': 'public', 'version': '2c', 'oid': '1.3.6.1.2.1.1.1.0'}
    MySQL: {'username': 'root', 'password': 'xxx', 'database': 'mysql'}
    """
    
    # 测试间隔(秒)
    interval = models.IntegerField('检测间隔', default=300)
    
    # 是否启用
    is_enabled = models.BooleanField('是否启用', default=True)
    
    # 状态
    last_test_status = models.CharField('上次状态', max_length=20, blank=True)
    last_test_time = models.DateTimeField('上次测试时间', null=True, blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'monitor_test_config'
        verbose_name = '监控测试配置'
        verbose_name_plural = '监控测试配置'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} ({self.get_protocol_display()})'


class MonitorTestResult(models.Model):
    """监控测试结果"""
    
    STATUS_CHOICES = [
        ('success', '成功'),
        ('failed', '失败'),
        ('timeout', '超时'),
        ('error', '错误'),
    ]
    
    # 关联
    config = models.ForeignKey(
        MonitorTestConfig, on_delete=models.CASCADE,
        related_name='results', verbose_name='配置'
    )
    
    # 测试结果
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES)
    response_time = models.FloatField('响应时间(ms)', null=True, blank=True)
    error_message = models.TextField('错误信息', blank=True)
    
    # 返回数据 (JSON)
    data = models.JSONField('返回数据', default=dict)
    
    # 元数据
    test_duration = models.FloatField('测试耗时(ms)', null=True, blank=True)
    remote_addr = models.GenericIPAddressField('来源IP', null=True, blank=True)
    
    created_at = models.DateTimeField('测试时间', auto_now_add=True)
    
    class Meta:
        db_table = 'monitor_test_result'
        verbose_name = '监控测试结果'
        verbose_name_plural = '监控测试结果'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['config', 'created_at']),
        ]
    
    def __str__(self):
        return f'{self.config.name} - {self.status} ({self.created_at})'
