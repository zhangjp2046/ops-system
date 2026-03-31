from django.db import models
from django.core.validators import MinValueValidator


class WorkOrder(models.Model):
    """工单模型"""
    
    STATUS_CHOICES = [
        (0, '新建'),
        (1, '处理中'),
        (2, '搁置'),
        (3, '已完成'),
    ]
    
    TYPE_CHOICES = [
        (1, '技术'),
        (2, '销售'),
        (3, '其他'),
    ]
    
    PRIORITY_CHOICES = [
        (0, '普通'),
        (1, '紧急'),
        (2, '重要'),
    ]
    
    # 基本信息
    title = models.CharField('工单标题', max_length=200)
    resume = models.CharField('摘要', max_length=500, blank=True, null=True)
    
    # 关联信息
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='work_orders', verbose_name='客户'
    )
    contact_name = models.CharField('联系人', max_length=50, blank=True)
    contact_phone = models.CharField('联系电话', max_length=20, blank=True)
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='work_orders', verbose_name='关联资产'
    )
    
    # 工单信息
    order_type = models.IntegerField('工单类型', choices=TYPE_CHOICES, null=True, blank=True)
    priority = models.IntegerField('优先级', choices=PRIORITY_CHOICES, default=0)
    status = models.IntegerField('状态', choices=STATUS_CHOICES, default=0)
    
    # 人员信息
    creator = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, related_name='created_orders', verbose_name='创建人'
    )
    handler = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='handled_orders', verbose_name='处理人'
    )
    
    # 时间信息
    occdate = models.DateTimeField('发生时间', null=True, blank=True)
    cttime = models.DateTimeField('创建时间', auto_now_add=True)
    updatetime = models.DateTimeField('更新时间', auto_now=True)
    
    # 描述
    description = models.TextField('详细描述', blank=True)
    
    class Meta:
        db_table = 'work_orders'
        verbose_name = '工单'
        verbose_name_plural = '工单管理'
        ordering = ['-cttime']
    
    def __str__(self):
        return self.title
    
    @property
    def status_name(self):
        return dict(self.STATUS_CHOICES).get(self.status, '')
    
    @property
    def type_name(self):
        return dict(self.TYPE_CHOICES).get(self.order_type, '')
    
    @property
    def priority_name(self):
        return dict(self.PRIORITY_CHOICES).get(self.priority, '')
    
    @property
    def customer_name(self):
        return self.customer.name if self.customer else ''
    
    @property
    def creator_name(self):
        return self.creator.username if self.creator else ''
    
    @property
    def handler_name(self):
        return self.handler.username if self.handler else ''
    
    @property
    def step_count(self):
        return self.steps.count()


class WorkOrderStep(models.Model):
    """工单步骤/跟进记录模型"""
    
    STATUS_CHOICES = [
        (0, '新建'),
        (1, '处理中'),
        (2, '搁置'),
        (3, '已完成'),
    ]
    
    # 基本信息
    order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE,
        related_name='steps', verbose_name='工单'
    )
    
    # 步骤信息
    status = models.IntegerField('状态', choices=STATUS_CHOICES, default=0)
    step_type = models.CharField('步骤类型', max_length=50, default='followup')  # followup, handling, completed
    
    # 人员信息
    handler = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, related_name='order_steps', verbose_name='处理人'
    )
    
    # 内容
    title = models.CharField('步骤标题', max_length=200, blank=True)
    description = models.TextField('处理描述', blank=True)
    
    # 附件
    attachment = models.CharField('附件路径', max_length=500, blank=True)
    
    # 时间
    flow_time = models.DateTimeField('跟进时间', null=True, blank=True)
    cttime = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'work_order_steps'
        verbose_name = '工单步骤'
        verbose_name_plural = '工单步骤管理'
        ordering = ['-cttime']
    
    def __str__(self):
        return f'{self.order.title} - {self.title or "步骤"}'
    
    @property
    def handler_name(self):
        return self.handler.username if self.handler else ''


class WorkOrderComment(models.Model):
    """工单评论/备注模型"""
    
    order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE,
        related_name='comments', verbose_name='工单'
    )
    
    user = models.ForeignKey(
        'users.User', on_delete=models.SET_NULL,
        null=True, related_name='order_comments', verbose_name='评论人'
    )
    
    content = models.TextField('评论内容')
    
    cttime = models.DateTimeField('评论时间', auto_now_add=True)
    
    class Meta:
        db_table = 'work_order_comments'
        verbose_name = '工单评论'
        verbose_name_plural = '工单评论管理'
        ordering = ['-cttime']
