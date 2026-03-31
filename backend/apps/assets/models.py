from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.customers.models import Customer
from apps.users.models import User


class AssetType(models.Model):
    """资产类型模型"""
    
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE,
        related_name='asset_types', verbose_name='客户'
    )
    type_code = models.CharField('类型代码', max_length=50)
    type_name = models.CharField('类型名称', max_length=100)
    parent_type = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='children', verbose_name='父类型'
    )
    plugin_id = models.CharField('插件ID', max_length=100, blank=True)
    
    # 配置信息
    icon = models.CharField('图标', max_length=50, blank=True)
    color = models.CharField('颜色', max_length=20, blank=True)
    description = models.TextField('描述', blank=True)
    
    # 显示配置
    sort_order = models.IntegerField('排序', default=0)
    is_system = models.BooleanField('是否系统类型', default=False)
    is_active = models.BooleanField('是否激活', default=True)
    
    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'asset_types'
        verbose_name = '资产类型'
        verbose_name_plural = '资产类型管理'
        unique_together = ['customer', 'type_code']
        ordering = ['sort_order', 'type_name']
    
    def __str__(self):
        return f'{self.type_name} ({self.type_code})'


class AssetField(models.Model):
    """资产字段模型"""
    
    FIELD_TYPES = [
        ('string', '字符串'),
        ('number', '数字'),
        ('boolean', '布尔值'),
        ('date', '日期'),
        ('datetime', '日期时间'),
        ('select', '下拉选择'),
        ('textarea', '文本域'),
        ('password', '密码'),
    ]
    
    asset_type = models.ForeignKey(
        AssetType, on_delete=models.CASCADE,
        related_name='fields', verbose_name='资产类型'
    )
    field_code = models.CharField('字段代码', max_length=50)
    field_name = models.CharField('字段名称', max_length=100)
    field_type = models.CharField('字段类型', max_length=20, choices=FIELD_TYPES)
    
    # 字段配置
    is_required = models.BooleanField('是否必填', default=False)
    is_unique = models.BooleanField('是否唯一', default=False)
    is_searchable = models.BooleanField('是否可搜索', default=True)
    is_filterable = models.BooleanField('是否可过滤', default=True)
    
    # 显示配置
    field_label = models.CharField('显示标签', max_length=100)
    placeholder = models.CharField('占位符', max_length=200, blank=True)
    help_text = models.TextField('帮助文本', blank=True)
    sort_order = models.IntegerField('排序', default=0)
    
    # 验证配置
    validation_rules = models.JSONField('验证规则', default=dict, blank=True)
    default_value = models.TextField('默认值', blank=True)
    options = models.JSONField('选项列表', default=list, blank=True)
    
    class Meta:
        db_table = 'asset_fields'
        verbose_name = '资产字段'
        verbose_name_plural = '资产字段管理'
        unique_together = ['asset_type', 'field_code']
        ordering = ['sort_order', 'field_name']
    
    def __str__(self):
        return f'{self.field_label} ({self.field_code})'


class Asset(models.Model):
    """资产主模型"""
    
    STATUS_CHOICES = [
        ('ACTIVE', '活跃'),
        ('INACTIVE', '停用'),
        ('ONLINE', '在线'),
        ('OFFLINE', '离线'),
        ('MAINTENANCE', '维护中'),
        ('DECOMMISSIONED', '已退役'),
    ]
    
    IMPORTANCE_CHOICES = [
        ('LOW', '低'),
        ('MEDIUM', '中'),
        ('HIGH', '高'),
        ('CRITICAL', '关键'),
    ]
    
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE,
        related_name='assets', verbose_name='客户'
    )
    asset_type = models.ForeignKey(
        AssetType, on_delete=models.PROTECT,
        related_name='assets', verbose_name='资产类型'
    )
    
    # 基本信息
    asset_code = models.CharField('资产编号', max_length=100)
    asset_name = models.CharField('资产名称', max_length=200)
    description = models.TextField('描述', blank=True)
    
    # 位置信息
    location = models.CharField('位置', max_length=200, blank=True)
    room = models.CharField('机房', max_length=100, blank=True)
    rack = models.CharField('机柜', max_length=100, blank=True)
    position = models.CharField('位置', max_length=50, blank=True)
    
    # 状态信息
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    importance_level = models.CharField('重要等级', max_length=20, choices=IMPORTANCE_CHOICES, default='MEDIUM')
    
    # 在线状态（用于实时监控）
    online = models.BooleanField('是否在线', default=False, db_index=True)
    last_check_time = models.DateTimeField('最后检查时间', null=True, blank=True)
    
    # IP地址（用于监控）
    ip_address = models.GenericIPAddressField('IP地址', null=True, blank=True)
    
    # 时间信息
    purchase_date = models.DateField('购买日期', null=True, blank=True)
    warranty_end = models.DateField('保修到期', null=True, blank=True)
    decommission_date = models.DateField('退役日期', null=True, blank=True)
    
    # 责任人
    owner = models.CharField('负责人', max_length=100, blank=True)
    department = models.CharField('部门', max_length=100, blank=True)
    vendor = models.CharField('供应商', max_length=100, blank=True)
    
    # 审计信息
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_assets', verbose_name='创建人'
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='updated_assets', verbose_name='更新人'
    )
    
    class Meta:
        db_table = 'assets'
        verbose_name = '资产'
        verbose_name_plural = '资产管理'
        unique_together = ['customer', 'asset_code']
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['asset_code']),
            models.Index(fields=['status']),
            models.Index(fields=['asset_type']),
            models.Index(fields=['customer', 'status']),
        ]
    
    def __str__(self):
        return f'{self.asset_name} ({self.asset_code})'
    
    @property
    def field_data(self):
        """获取字段数据"""
        return {
            data.field.field_code: data.get_value()
            for data in self.field_values.all()
        }
    
    def get_field_value(self, field_code):
        """获取指定字段的值"""
        try:
            field_data = self.field_values.get(field__field_code=field_code)
            return field_data.get_value()
        except AssetData.DoesNotExist:
            return None


class AssetData(models.Model):
    """资产数据模型（动态字段值）"""
    
    asset = models.ForeignKey(
        Asset, on_delete=models.CASCADE,
        related_name='field_values', verbose_name='资产'
    )
    field = models.ForeignKey(
        AssetField, on_delete=models.CASCADE,
        related_name='field_values', verbose_name='字段'
    )
    
    # 数据值
    string_value = models.TextField('字符串值', blank=True)
    number_value = models.DecimalField('数字值', max_digits=20, decimal_places=6, null=True, blank=True)
    boolean_value = models.BooleanField('布尔值', null=True, blank=True)
    date_value = models.DateField('日期值', null=True, blank=True)
    datetime_value = models.DateTimeField('日期时间值', null=True, blank=True)
    json_value = models.JSONField('JSON值', null=True, blank=True)
    
    # 审计信息
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'asset_data'
        verbose_name = '资产数据'
        verbose_name_plural = '资产数据管理'
        unique_together = ['asset', 'field']
        indexes = [
            models.Index(fields=['asset']),
            models.Index(fields=['field']),
        ]
    
    def __str__(self):
        return f'{self.asset.asset_name} - {self.field.field_label}'
    
    def get_value(self):
        """根据字段类型获取值"""
        if self.field.field_type == 'string':
            return self.string_value
        elif self.field.field_type == 'number':
            return float(self.number_value) if self.number_value else None
        elif self.field.field_type == 'boolean':
            return self.boolean_value
        elif self.field.field_type == 'date':
            return self.date_value
        elif self.field.field_type == 'datetime':
            return self.datetime_value
        elif self.field.field_type == 'select':
            return self.string_value
        elif self.field.field_type == 'textarea':
            return self.string_value
        elif self.field.field_type == 'password':
            return '********'  # 密码不返回明文
        else:
            return self.json_value
    
    def set_value(self, value):
        """根据字段类型设置值"""
        field_type = self.field.field_type
        
        if value is None or value == '':
            # 空值处理
            if field_type == 'number':
                self.number_value = None
            elif field_type in ('boolean',):
                self.boolean_value = None
            elif field_type in ('date', 'datetime'):
                setattr(self, f'{field_type}_value', None)
            else:
                self.string_value = ''
            self.save()
            return
        
        if field_type == 'string':
            self.string_value = str(value)
        elif field_type == 'number':
            try:
                self.number_value = Decimal(str(value)) if value != '' else None
            except:
                self.number_value = None
        elif field_type == 'boolean':
            self.boolean_value = bool(value)
        elif field_type == 'date':
            self.date_value = value
        elif field_type == 'datetime':
            self.datetime_value = value
        elif field_type == 'select':
            self.string_value = str(value)
        elif field_type == 'textarea':
            self.string_value = str(value)
        elif field_type == 'password':
            self.string_value = str(value)  # 实际应该加密
        else:
            self.json_value = value
        
        self.save()

class AssetStatusHistory(models.Model):
    """资产状态变更历史"""
    
    asset = models.ForeignKey(
        Asset, on_delete=models.CASCADE,
        related_name='status_history', verbose_name='资产'
    )
    status = models.CharField('状态', max_length=20, choices=Asset.STATUS_CHOICES)
    changed_by = models.CharField('变更人', max_length=100, default='SYSTEM')
    change_reason = models.TextField('变更原因', blank=True)
    created_at = models.DateTimeField('变更时间', auto_now_add=True)
    
    class Meta:
        db_table = 'asset_status_history'
        verbose_name = '资产状态历史'
        verbose_name_plural = '资产状态历史'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['asset', 'created_at']),
        ]
    
    def __str__(self):
        return f'{self.asset.asset_name} - {self.status} ({self.created_at})'
