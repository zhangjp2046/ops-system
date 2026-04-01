from django.db import models
from django.core.validators import MinValueValidator


class InspectionPlan(models.Model):
    """巡检计划模型"""
    
    CYCLE_CHOICES = [
        ('daily', '每天'),
        ('weekly', '每周'),
        ('monthly', '每月'),
        ('quarterly', '每季度'),
    ]
    
    STATUS_CHOICES = [
        ('draft', '草稿'),
        ('active', '启用'),
        ('paused', '暂停'),
        ('archived', '归档'),
    ]
    
    # 关联客户
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.CASCADE,
        related_name='inspection_plans', verbose_name='所属客户',
        null=True, blank=True
    )
    
    # 基本信息
    name = models.CharField('计划名称', max_length=200)
    code = models.CharField('计划编码', max_length=50, unique=True)
    description = models.TextField('计划描述', blank=True)
    
    # 巡检配置
    cycle = models.CharField('执行周期', max_length=20, choices=CYCLE_CHOICES, default='daily')
    scheduled_time = models.TimeField('计划执行时间')
    is_auto_execute = models.BooleanField('是否自动执行', default=False)
    
    # 状态
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # 巡检项目（JSON配置）
    check_items = models.JSONField('巡检项目配置', default=list, blank=True)
    
    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'inspection_plans'
        verbose_name = '巡检计划'
        verbose_name_plural = '巡检计划管理'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.name} ({self.get_cycle_display()})'


class InspectionTask(models.Model):
    """巡检任务模型"""
    
    STATUS_CHOICES = [
        ('pending', '待巡检'),
        ('in_progress', '巡检中'),
        ('completed', '已完成'),
        ('failed', '巡检失败'),
        ('cancelled', '已取消'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', '低'),
        ('medium', '中'),
        ('high', '高'),
        ('urgent', '紧急'),
    ]
    
    # 基本信息
    plan = models.ForeignKey(
        InspectionPlan, on_delete=models.CASCADE,
        related_name='tasks', verbose_name='巡检计划'
    )
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.CASCADE,
        related_name='inspection_tasks', verbose_name='巡检资产'
    )
    
    # 执行配置
    scheduled_time = models.DateTimeField('计划巡检时间')
    executed_time = models.DateTimeField('实际巡检时间', null=True, blank=True)
    priority = models.CharField('优先级', max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # 状态
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # 执行人
    executor = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='inspection_tasks', verbose_name='执行人'
    )
    
    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'inspection_tasks'
        verbose_name = '巡检任务'
        verbose_name_plural = '巡检任务管理'
        ordering = ['-scheduled_time']
    
    def __str__(self):
        return f'{self.plan.name} - {self.asset.asset_name}'


class InspectionResult(models.Model):
    """巡检结果模型"""
    
    STATUS_CHOICES = [
        ('pass', '通过'),
        ('warning', '警告'),
        ('fail', '不合格'),
        ('skip', '跳过'),
    ]
    
    # 关联
    task = models.ForeignKey(
        InspectionTask, on_delete=models.CASCADE,
        related_name='results', verbose_name='巡检任务'
    )
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.CASCADE,
        related_name='inspection_results', verbose_name='资产'
    )
    
    # 检查项信息
    check_item = models.CharField('检查项', max_length=100)
    check_item_code = models.CharField('检查项编码', max_length=50)
    
    # 结果
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES)
    result_value = models.CharField('检查值', max_length=500, blank=True)
    result_message = models.TextField('结果说明', blank=True)
    
    # 期望值和阈值
    expected_value = models.CharField('期望值', max_length=200, blank=True)
    threshold_min = models.CharField('最小阈值', max_length=100, blank=True)
    threshold_max = models.CharField('最大阈值', max_length=100, blank=True)
    
    # 建议
    suggestion = models.TextField('处理建议', blank=True)
    
    # 执行时间
    executed_at = models.DateTimeField('执行时间', auto_now_add=True)
    
    class Meta:
        db_table = 'inspection_results'
        verbose_name = '巡检结果'
        verbose_name_plural = '巡检结果管理'
        ordering = ['-executed_at']
    
    def __str__(self):
        return f'{self.asset.asset_name} - {self.check_item}: {self.get_status_display()}'


class InspectionRecord(models.Model):
    """巡检记录模型（汇总）"""
    
    STATUS_CHOICES = [
        ('completed', '已完成'),
        ('partial', '部分完成'),
        ('failed', '失败'),
    ]
    
    # 基本信息
    task = models.OneToOneField(
        InspectionTask, on_delete=models.CASCADE,
        related_name='record', verbose_name='巡检任务'
    )
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.CASCADE,
        related_name='inspection_records', verbose_name='资产'
    )
    
    # 汇总统计
    total_checks = models.IntegerField('总检查项', default=0)
    pass_checks = models.IntegerField('通过项', default=0)
    warning_checks = models.IntegerField('警告项', default=0)
    fail_checks = models.IntegerField('不合格项', default=0)
    skip_checks = models.IntegerField('跳过项', default=0)
    
    # 状态
    status = models.CharField('巡检状态', max_length=20, choices=STATUS_CHOICES)
    
    # 总体评价
    overall_status = models.CharField('总体评价', max_length=20, choices=InspectionResult.STATUS_CHOICES)
    summary = models.TextField('巡检总结', blank=True)
    
    # 执行信息
    executor = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='inspection_records', verbose_name='执行人'
    )
    started_at = models.DateTimeField('开始时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    duration = models.IntegerField('持续时间(秒)', null=True, blank=True)
    
    # 创建时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'inspection_records'
        verbose_name = '巡检记录'
        verbose_name_plural = '巡检记录管理'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.asset.asset_name} - {self.created_at.strftime("%Y-%m-%d %H:%M")}'
