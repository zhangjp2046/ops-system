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

    # 协议和连接信息
    PROTOCOL_CHOICES = [
        ('snmp', 'SNMP'),
        ('ssh', 'SSH'),
        ('ping', 'Ping'),
        ('mysql', 'MySQL'),
        ('mssql', 'MSSQL'),
        ('oracle', 'Oracle'),
        ('postgresql', 'PostgreSQL'),
        ('port', '端口检测'),
        ('ntp', 'NTP时间同步'),
    ]
    protocol = models.CharField('采集协议', max_length=20, choices=PROTOCOL_CHOICES, blank=True, default='')
    db_type = models.CharField('数据库类型', max_length=20, blank=True, default='')
    port = models.CharField('端口', max_length=10, blank=True, default='')
    username = models.CharField('用户名', max_length=100, blank=True, default='')
    password = models.CharField('密码', max_length=200, blank=True, default='')
    database = models.CharField('数据库名', max_length=100, blank=True, default='')
    
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


class AssetTransfer(models.Model):
    """资产调拨模型"""
    
    STATUS_CHOICES = [
        ('PENDING', '待调拨'),
        ('APPROVED', '已审批'),
        ('REJECTED', '已拒绝'),
        ('COMPLETED', '已完成'),
        ('CANCELLED', '已取消'),
    ]
    
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE,
        related_name='asset_transfers', verbose_name='客户'
    )
    asset = models.ForeignKey(
        'Asset', on_delete=models.CASCADE,
        related_name='transfers', verbose_name='资产'
    )
    
    # 调拨信息
    transfer_no = models.CharField('调拨单号', max_length=50, unique=True)
    from_department = models.CharField('调出部门', max_length=100)
    to_department = models.CharField('调入部门', max_length=100)
    from_location = models.CharField('调出位置', max_length=200, blank=True)
    to_location = models.CharField('调入位置', max_length=200, blank=True)
    reason = models.TextField('调拨原因', blank=True)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # 审批信息
    applicant = models.CharField('申请人', max_length=100)
    approver = models.CharField('审批人', max_length=100, blank=True)
    approve_time = models.DateTimeField('审批时间', null=True, blank=True)
    approve_comment = models.TextField('审批意见', blank=True)
    
    # 执行信息
    executor = models.CharField('执行人', max_length=100, blank=True)
    execute_time = models.DateTimeField('执行时间', null=True, blank=True)
    
    # 时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'asset_transfers'
        verbose_name = '资产调拨'
        verbose_name_plural = '资产调拨管理'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.transfer_no} - {self.asset.asset_name}'


class AssetRepair(models.Model):
    """资产维修模型"""
    
    STATUS_CHOICES = [
        ('APPLIED', '已申请'),
        ('ASSIGNED', '已派工'),
        ('ACCEPTED', '已接单'),
        ('PROCESSING', '维修中'),
        ('COMPLETED', '已完成'),
        ('QUALIFIED', '已验收'),
        ('REJECTED', '已拒绝'),
    ]
    
    PRIORITY_CHOICES = [
        ('LOW', '低'),
        ('MEDIUM', '中'),
        ('HIGH', '高'),
        ('URGENT', '紧急'),
    ]
    
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE,
        related_name='asset_repairs', verbose_name='客户'
    )
    asset = models.ForeignKey(
        'Asset', on_delete=models.CASCADE,
        related_name='repairs', verbose_name='资产'
    )
    
    # 维修单信息
    repair_no = models.CharField('维修单号', max_length=50, unique=True)
    fault_description = models.TextField('故障描述')
    fault_time = models.DateTimeField('故障时间', null=True, blank=True)
    repair_type = models.CharField('维修类型', max_length=50, blank=True)
    priority = models.CharField('优先级', max_length=20, choices=PRIORITY_CHOICES, default='MEDIUM')
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='APPLIED')
    
    # 费用信息
    repair_cost = models.DecimalField('维修费用', max_digits=10, decimal_places=2, default=0)
    parts_cost = models.DecimalField('配件费用', max_digits=10, decimal_places=2, default=0)
    total_cost = models.DecimalField('总费用', max_digits=10, decimal_places=2, default=0)
    
    # 维修人员
    assignee = models.CharField('维修人员', max_length=100, blank=True)
    assignee_phone = models.CharField('维修电话', max_length=50, blank=True)
    
    # 维修结果
    repair_result = models.TextField('维修结果', blank=True)
    repair_time = models.DateTimeField('维修时间', null=True, blank=True)
    repair_duration = models.IntegerField('维修时长(小时)', default=0)
    
    # 验收
    accept_result = models.CharField('验收结果', max_length=100, blank=True)
    accept_comment = models.TextField('验收意见', blank=True)
    accept_time = models.DateTimeField('验收时间', null=True, blank=True)
    accept_by = models.CharField('验收人', max_length=100, blank=True)
    
    # 时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'asset_repairs'
        verbose_name = '资产维修'
        verbose_name_plural = '资产维修管理'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.repair_no} - {self.asset.asset_name}'


class AssetScrap(models.Model):
    """资产报废模型"""
    
    STATUS_CHOICES = [
        ('APPLIED', '已申请'),
        ('APPROVED', '已审批'),
        ('REJECTED', '已拒绝'),
        ('SCRAPPED', '已报废'),
    ]
    
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE,
        related_name='asset_scraps', verbose_name='客户'
    )
    asset = models.ForeignKey(
        'Asset', on_delete=models.CASCADE,
        related_name='scraps', verbose_name='资产'
    )
    
    # 报废单信息
    scrap_no = models.CharField('报废单号', max_length=50, unique=True)
    scrap_reason = models.TextField('报废原因')
    scrap_type = models.CharField('报废类型', max_length=50, blank=True)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='APPLIED')
    
    # 资产原值
    original_value = models.DecimalField('原值', max_digits=12, decimal_places=2, default=0)
    net_value = models.DecimalField('净值', max_digits=12, decimal_places=2, default=0)
    depreciation_rate = models.DecimalField('折旧率(%)', max_digits=5, decimal_places=2, default=0)
    
    # 处理信息
    handler = models.CharField('处理人', max_length=100, blank=True)
    handler_phone = models.CharField('处理人电话', max_length=50, blank=True)
    disposal_method = models.CharField('处理方式', max_length=100, blank=True)
    disposal_result = models.TextField('处理结果', blank=True)
    
    # 审批信息
    approver = models.CharField('审批人', max_length=100, blank=True)
    approve_time = models.DateTimeField('审批时间', null=True, blank=True)
    approve_comment = models.TextField('审批意见', blank=True)
    
    # 执行信息
    scrap_time = models.DateTimeField('报废时间', null=True, blank=True)
    scrap_by = models.CharField('报废执行人', max_length=100, blank=True)
    
    # 时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'asset_scraps'
        verbose_name = '资产报废'
        verbose_name_plural = '资产报废管理'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.scrap_no} - {self.asset.asset_name}'


class AssetLend(models.Model):
    """资产出借模型"""
    
    STATUS_CHOICES = [
        ('PENDING', '待审批'),
        ('APPROVED', '已审批'),
        ('REJECTED', '已拒绝'),
        ('OUT', '已借出'),
        ('RETURNED', '已归还'),
        ('OVERDUE', '已逾期'),
        ('CANCELLED', '已取消'),
    ]
    
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE,
        related_name='asset_lends', verbose_name='客户'
    )
    asset = models.ForeignKey(
        'Asset', on_delete=models.CASCADE,
        related_name='lends', verbose_name='资产'
    )
    
    # 出借单信息
    lend_no = models.CharField('出借单号', max_length=50, unique=True)
    from_department = models.CharField('借出部门', max_length=100)
    to_department = models.CharField('借往部门', max_length=100)
    to_location = models.CharField('借往地点', max_length=200, blank=True)
    lendee = models.CharField('借用人', max_length=100)
    lendee_phone = models.CharField('联系电话', max_length=50, blank=True)
    reason = models.TextField('出借原因', blank=True)
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='PENDING')
    
    # 审批信息
    approver = models.CharField('审批人', max_length=100, blank=True)
    approve_time = models.DateTimeField('审批时间', null=True, blank=True)
    approve_comment = models.TextField('审批意见', blank=True)
    
    # 借出信息
    lend_date = models.DateField('借出日期', null=True, blank=True)
    lend_executor = models.CharField('借出执行人', max_length=100, blank=True)
    
    # 归还信息
    expected_return_date = models.DateField('预计归还日期', null=True, blank=True)
    actual_return_date = models.DateField('实际归还日期', null=True, blank=True)
    return_acceptance = models.TextField('归还验收', blank=True)
    return_acceptor = models.CharField('归还接收人', max_length=100, blank=True)
    return_executor = models.CharField('归还执行人', max_length=100, blank=True)
    
    # 时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'asset_lends'
        verbose_name = '资产出借'
        verbose_name_plural = '资产出借管理'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.lend_no} - {self.asset.asset_name}'
