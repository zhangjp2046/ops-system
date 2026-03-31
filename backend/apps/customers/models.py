from django.db import models
from apps.users.models import User


class Customer(models.Model):
    """客户模型"""
    
    # 基本信息
    customer_code = models.CharField('客户编码', max_length=50, unique=True)
    customer_name = models.CharField('客户名称', max_length=100)
    customer_type = models.CharField('客户类型', max_length=50, blank=True)
    industry = models.CharField('行业', max_length=50, blank=True)
    
    # 联系信息
    contact_person = models.CharField('联系人', max_length=50, blank=True)
    contact_phone = models.CharField('联系电话', max_length=20, blank=True)
    contact_email = models.EmailField('联系邮箱', max_length=100, blank=True)
    address = models.TextField('地址', blank=True)
    
    # 配置信息
    config = models.JSONField('客户配置', default=dict, blank=True)
    plugins = models.JSONField('启用的插件', default=list, blank=True)
    
    # API认证（用于本地监控系统认证）
    api_key = models.CharField('API Key', max_length=64, blank=True, unique=True, null=True)
    api_secret = models.CharField('API Secret', max_length=128, blank=True, null=True)
    
    # 本地部署配置
    is_local_deployment = models.BooleanField('本地部署', default=False)
    local_endpoint = models.URLField('本地端点', max_length=500, blank=True, null=True)
    
    # 状态信息
    status = models.CharField('状态', max_length=20, default='ACTIVE')
    contract_start = models.DateField('合同开始', null=True, blank=True)
    contract_end = models.DateField('合同结束', null=True, blank=True)
    
    # 审计信息
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='created_customers', verbose_name='创建人'
    )
    updated_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        related_name='updated_customers', verbose_name='更新人'
    )
    
    class Meta:
        db_table = 'customers'
        verbose_name = '客户'
        verbose_name_plural = '客户管理'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.customer_name} ({self.customer_code})'
    
    @property
    def asset_count(self):
        """资产数量"""
        from apps.assets.models import Asset
        return Asset.objects.filter(customer=self).count()
    
    @property
    def active_asset_count(self):
        """活跃资产数量"""
        from apps.assets.models import Asset
        return Asset.objects.filter(customer=self, status='ACTIVE').count()
    
    @property
    def critical_asset_count(self):
        """关键资产数量"""
        from apps.assets.models import Asset
        return Asset.objects.filter(
            customer=self, 
            status='ACTIVE',
            importance_level='CRITICAL'
        ).count()