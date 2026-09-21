#!/usr/bin/env python3
"""
告警阈值配置模型
支持按客户、资产类型、检查项配置不同的告警阈值
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class AlertThreshold(models.Model):
    """告警阈值配置模型"""
    
    DIRECTION_CHOICES = [
        ('upper', '越高越严重'),      # 如：CPU使用率、内存使用率
        ('lower', '越低越严重'),      # 如：缓冲命中率、可用空间
        ('range', '偏离范围严重'),    # 如：响应时间、温度
        ('exact', '精确匹配'),        # 如：状态码、错误类型
    ]
    
    VALUE_TYPE_CHOICES = [
        ('number', '数值'),
        ('percentage', '百分比'),
        ('string', '字符串'),
        ('boolean', '布尔值'),
    ]
    
    PROTOCOL_CHOICES = [
        ('mysql', 'MySQL'),
        ('mssql', 'MSSQL'),
        ('oracle', 'Oracle'),
        ('postgresql', 'PostgreSQL'),
        ('snmp', 'SNMP'),
        ('ssh', 'SSH'),
        ('ping', 'Ping'),
        ('port', '端口检测'),
        ('ntp', 'NTP时间同步'),
    ]
    
    # 关联
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE,
        related_name='alert_thresholds', verbose_name='客户',
        null=True, blank=True
    )
    asset_type = models.ForeignKey(
        'assets.AssetType', on_delete=models.CASCADE,
        related_name='alert_thresholds', verbose_name='资产类型',
        null=True, blank=True
    )
    
    # 检查项标识
    check_item_code = models.CharField('检查项编码', max_length=50)
    check_item_name = models.CharField('检查项名称', max_length=100)
    protocol = models.CharField('协议类型', max_length=20, choices=PROTOCOL_CHOICES)
    
    # 阈值方向和类型
    threshold_direction = models.CharField(
        '阈值方向', max_length=10, choices=DIRECTION_CHOICES, default='upper'
    )
    value_type = models.CharField(
        '值类型', max_length=20, choices=VALUE_TYPE_CHOICES, default='number'
    )
    
    # 基础阈值（简化配置）
    warning_threshold = models.CharField('警告阈值', max_length=100, blank=True)
    error_threshold = models.CharField('错误阈值', max_length=100, blank=True)
    critical_threshold = models.CharField('严重阈值', max_length=100, blank=True)
    
    # 单位
    unit = models.CharField('单位', max_length=20, blank=True, default='%')
    
    # 描述
    description = models.TextField('描述', blank=True)
    
    # 扩展配置
    config = models.JSONField('扩展配置', default=dict, blank=True)
    """
    config示例:
    {
        "check_interval": 300,           // 检查间隔（秒）
        "consecutive_count": 3,          // 连续触发次数
        "recovery_threshold": 70,        // 恢复阈值
        "enable_auto_recovery": true,    // 启用自动恢复
        "notification_channels": ["email", "wechat"]  // 通知渠道
    }
    """
    
    # 状态
    is_active = models.BooleanField('是否启用', default=True)

    # 是否为监控项：开启后每次巡检将记录该指标值到监控中心
    is_monitoring_item = models.BooleanField('是否监控项', default=False, db_index=True,
        help_text='开启后每次巡检将记录该指标的时间序列数据，便于观察变化趋势')

    # 审计
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    created_by = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, verbose_name='创建人'
    )
    
    class Meta:
        db_table = 'alert_thresholds'
        verbose_name = '告警阈值'
        verbose_name_plural = '告警阈值配置'
        ordering = ['protocol', 'check_item_code']
        unique_together = ['customer', 'asset_type', 'check_item_code']
        indexes = [
            models.Index(fields=['customer', 'is_active']),
            models.Index(fields=['protocol']),
            models.Index(fields=['check_item_code']),
        ]
    
    def __str__(self):
        customer_name = self.customer.customer_name if self.customer else '全局'
        asset_type_name = self.asset_type.type_name if self.asset_type else '所有类型'
        return f'{customer_name} - {asset_type_name} - {self.check_item_name}'
    
    def has_effective_threshold(self):
        """本行是否真的定义了可用于判定的阈值。

        三个基础阈值全空、且没有启用中的复杂规则 → 这行不参与严重程度判定。

        ⚠️ 为什么需要这个：`get_severity()` 在 direction 不匹配 /
        没有阈值可比时，会一路 fallthrough 到函数末尾 `return 1, '信息'`。
        所以「行存在但没配任何阈值」会**吃掉**调用方已经算好的状态，
        把本该是警告/错误的告警压成「信息」。

        典型场景：「时间同步」的阈值配在巡检计划里（10/60/180 秒），
        阈值配置表里的这一行只用于在页面上可见、以及作为监控项开关，
        不该参与严重程度判定。
        """
        if self.warning_threshold or self.error_threshold or self.critical_threshold:
            return True
        return self.rules.filter(is_active=True).exists()

    def get_severity(self, value):
        """
        根据值判断严重程度
        返回: (severity_level, severity_name)
        """
        try:
            numeric_value = float(value)
        except (ValueError, TypeError):
            # 非数值类型，使用字符串匹配
            return self._get_severity_string(value)
        
        # 使用复杂规则
        rules = self.rules.filter(is_active=True).order_by('-severity')
        for rule in rules:
            if rule.matches(numeric_value):
                return rule.severity, rule.get_severity_display()
        
        # 使用基础阈值
        return self._get_severity_numeric(numeric_value)
    
    def _get_severity_numeric(self, value):
        """数值类型严重程度判断"""
        if self.threshold_direction == 'upper':
            if self.critical_threshold and value >= float(self.critical_threshold):
                return 4, '严重'
            elif self.error_threshold and value >= float(self.error_threshold):
                return 3, '错误'
            elif self.warning_threshold and value >= float(self.warning_threshold):
                return 2, '警告'
        elif self.threshold_direction == 'lower':
            if self.critical_threshold and value <= float(self.critical_threshold):
                return 4, '严重'
            elif self.error_threshold and value <= float(self.error_threshold):
                return 3, '错误'
            elif self.warning_threshold and value <= float(self.warning_threshold):
                return 2, '警告'
        elif self.threshold_direction == 'range':
            # 范围类型需要配置center和deviation
            center = self.config.get('center', 0)
            deviation = self.config.get('deviation', 0)
            if abs(value - center) > deviation * 2:
                return 4, '严重'
            elif abs(value - center) > deviation * 1.5:
                return 3, '错误'
            elif abs(value - center) > deviation:
                return 2, '警告'
        
        return 1, '信息'
    
    def _get_severity_string(self, value):
        """字符串类型严重程度判断"""
        # 字符串匹配规则在config中定义
        string_rules = self.config.get('string_rules', {})
        for severity_name, patterns in string_rules.items():
            if any(pattern in str(value) for pattern in patterns):
                severity_map = {'critical': 4, 'error': 3, 'warning': 2, 'info': 1}
                return severity_map.get(severity_name, 1), severity_name
        return 1, '信息'


class AlertThresholdRule(models.Model):
    """复杂阈值规则模型（支持多级阈值）"""
    
    SEVERITY_CHOICES = [
        (1, '信息'),
        (2, '警告'),
        (3, '错误'),
        (4, '严重'),
    ]
    
    OPERATOR_CHOICES = [
        ('>', '大于'),
        ('<', '小于'),
        ('>=', '大于等于'),
        ('<=', '小于等于'),
        ('=', '等于'),
        ('!=', '不等于'),
        ('contains', '包含'),
        ('not_contains', '不包含'),
        ('regex', '正则匹配'),
    ]
    
    threshold = models.ForeignKey(
        AlertThreshold, on_delete=models.CASCADE,
        related_name='rules', verbose_name='阈值配置'
    )
    
    # 规则配置
    severity = models.IntegerField('严重程度', choices=SEVERITY_CHOICES)
    operator = models.CharField('操作符', max_length=20, choices=OPERATOR_CHOICES)
    threshold_value = models.CharField('阈值', max_length=100)
    
    # 规则描述
    rule_name = models.CharField('规则名称', max_length=100, blank=True)
    description = models.TextField('规则描述', blank=True)
    
    # 排序和状态
    sort_order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('是否启用', default=True)
    
    class Meta:
        db_table = 'alert_threshold_rules'
        verbose_name = '阈值规则'
        verbose_name_plural = '阈值规则'
        ordering = ['threshold', '-severity', 'sort_order']
        indexes = [
            models.Index(fields=['threshold', 'severity']),
        ]
    
    def __str__(self):
        return f'{self.threshold.check_item_name} - {self.get_severity_display()} {self.operator} {self.threshold_value}'
    
    def matches(self, value):
        """检查值是否匹配规则"""
        try:
            numeric_value = float(value)
            numeric_threshold = float(self.threshold_value)
        except (ValueError, TypeError):
            # 字符串比较
            return self._matches_string(str(value), str(self.threshold_value))
        
        if self.operator == '>':
            return numeric_value > numeric_threshold
        elif self.operator == '<':
            return numeric_value < numeric_threshold
        elif self.operator == '>=':
            return numeric_value >= numeric_threshold
        elif self.operator == '<=':
            return numeric_value <= numeric_threshold
        elif self.operator == '=':
            return numeric_value == numeric_threshold
        elif self.operator == '!=':
            return numeric_value != numeric_threshold
        
        return False
    
    def _matches_string(self, value, threshold):
        """字符串匹配"""
        import re
        
        if self.operator == 'contains':
            return threshold in value
        elif self.operator == 'not_contains':
            return threshold not in value
        elif self.operator == '=':
            return value == threshold
        elif self.operator == '!=':
            return value != threshold
        elif self.operator == 'regex':
            try:
                return bool(re.search(threshold, value))
            except re.error:
                return False
        
        return False


class AlertThresholdTemplate(models.Model):
    """告警阈值模板（预定义的常用阈值配置）"""
    
    name = models.CharField('模板名称', max_length=100)
    protocol = models.CharField('协议类型', max_length=20)
    check_item_code = models.CharField('检查项编码', max_length=50)
    check_item_name = models.CharField('检查项名称', max_length=100)
    
    # 默认阈值
    default_config = models.JSONField('默认配置', default=dict)
    """
    default_config示例:
    {
        "threshold_direction": "upper",
        "value_type": "number",
        "unit": "%",
        "warning_threshold": "80",
        "error_threshold": "90",
        "critical_threshold": "95",
        "description": "CPU使用率阈值配置"
    }
    """
    
    # 描述
    description = models.TextField('描述', blank=True)
    is_system = models.BooleanField('是否系统模板', default=False)
    
    # 审计
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'alert_threshold_templates'
        verbose_name = '阈值模板'
        verbose_name_plural = '阈值模板'
        ordering = ['protocol', 'check_item_code']
    
    def __str__(self):
        return f'{self.name} ({self.protocol})'
