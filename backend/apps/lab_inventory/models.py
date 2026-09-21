"""
Lab Inventory 科室库存管理系统

设计说明：
1. 复用原有 material 表结构 -> lab_reagent（试剂台账）
   复用原有 materialcategory 表结构 -> lab_reagent_category（试剂分类）
2. 科室库存表 DeptStock：lab_reagent 出库到科室后，在此进行库存和消耗管理
3. 其他业务表（订单、消耗记录等）独立创建
"""

from django.db import models
from decimal import Decimal


# ============================================================
# 复用层：Material / MaterialCategory（已有表则引用，无则新建）
# ============================================================

class MaterialCategory(models.Model):
    """物资分类 - 复用原有 materialcategory 表，表名为 lab_reagent_category"""
    
    name = models.CharField('分类名称', max_length=100)
    parent = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='children', verbose_name='上级分类'
    )
    code = models.CharField('分类编码', max_length=50, blank=True)
    description = models.TextField('描述', blank=True)
    sort_order = models.IntegerField('排序', default=0)
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'lab_reagent_category'
        verbose_name = '试剂分类'
        verbose_name_plural = '试剂分类'
        ordering = ['sort_order', 'name']
    
    def __str__(self):
        return self.name


class Material(models.Model):
    """试剂台账 - 复用原有 material 表，表名为 lab_reagent"""
    
    UNIT_CHOICES = [
        ('个', '个'),
        ('盒', '盒'),
        ('瓶', '瓶'),
        ('支', '支'),
        ('袋', '袋'),
        ('箱', '箱'),
        ('套', '套'),
        ('卷', '卷'),
        ('kg', '千克'),
        ('g', '克'),
        ('L', '升'),
        ('mL', '毫升'),
    ]
    
    category = models.ForeignKey(
        MaterialCategory, on_delete=models.SET_NULL, null=True,
        related_name='materials', verbose_name='试剂分类'
    )
    code = models.CharField('试剂编码', max_length=50, unique=True)
    name = models.CharField('试剂名称', max_length=200)
    spec = models.CharField('规格型号', max_length=200, blank=True)
    unit = models.CharField('单位', max_length=20, choices=UNIT_CHOICES, default='个')
    
    # 库存管理相关
    min_stock = models.DecimalField('最低库存', max_digits=10, decimal_places=2, default=0)
    max_stock = models.DecimalField('最高库存', max_digits=10, decimal_places=2, default=0)
    
    # 财务相关
    unit_price = models.DecimalField('单价', max_digits=10, decimal_places=2, default=0)
    
    # 试剂特有字段
    cas_no = models.CharField('CAS号', max_length=50, blank=True, help_text='化学物质登记号')
    purity = models.CharField('纯度', max_length=50, blank=True)
    manufacturer = models.CharField('生产厂家', max_length=200, blank=True)
    supplier = models.CharField('供应商', max_length=200, blank=True)
    storage_condition = models.CharField('储存条件', max_length=200, blank=True)
    dangerous_level = models.CharField('危险等级', max_length=50, blank=True)
    
    # 其他信息
    description = models.TextField('描述', blank=True)
    
    is_active = models.BooleanField('是否启用', default=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'lab_reagent'
        verbose_name = '试剂台账'
        verbose_name_plural = '试剂台账'
        ordering = ['code']
    
    def __str__(self):
        return f'{self.code} - {self.name}'


# ============================================================
# 科室库存管理（核心新增）
# ============================================================

class DeptStockManager(models.Manager):
    """科室库存管理器 - 提供库存业务方法"""
    
    def get_or_create_stock(self, material, department):
        """获取或创建科室库存记录"""
        stock, created = self.get_or_create(
            material=material,
            department=department,
            defaults={
                'quantity': Decimal('0'),
                'frozen_quantity': Decimal('0'),
            }
        )
        return stock
    
    def add_stock(self, material, department, quantity, order_no='', remark=''):
        """入库操作"""
        stock = self.get_or_create_stock(material, department)
        stock.quantity += Decimal(str(quantity))
        stock.save()
        
        # 记录明细
        DeptStockRecord.objects.create(
            stock=stock,
            direction='IN',
            quantity=quantity,
            order_no=order_no,
            remark=remark,
        )
        return stock
    
    def consume_stock(self, material, department, quantity, consume_type='', remark=''):
        """消耗操作"""
        stock = self.get_or_create_stock(material, department)
        if stock.quantity < Decimal(str(quantity)):
            raise ValueError(f'库存不足：当前 {stock.quantity}，需要 {quantity}')
        stock.quantity -= Decimal(str(quantity))
        stock.save()
        
        # 记录明细
        DeptStockRecord.objects.create(
            stock=stock,
            direction='OUT',
            quantity=quantity,
            consume_type=consume_type,
            remark=remark,
        )
        return stock
    
    def get_dept_stocks(self, department, material_code=''):
        """获取科室库存列表"""
        qs = self.filter(department=department)
        if material_code:
            qs = qs.filter(material__code__icontains=material_code)
        return qs.select_related('material')


class DeptStock(models.Model):
    """
    科室试剂库存表
    说明：lab_reagent 出库到科室后，开始进行此系统的库存和消耗管理
    """
    
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT,
        related_name='dept_stocks', verbose_name='物资'
    )
    department = models.CharField('科室', max_length=100, db_index=True)
    
    quantity = models.DecimalField('库存数量', max_digits=10, decimal_places=2, default=0)
    frozen_quantity = models.DecimalField('冻结数量', max_digits=10, decimal_places=2, default=0)
    
    # 库存警戒
    min_stock_alert = models.BooleanField('库存预警', default=False)
    
    # 审计
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    objects = DeptStockManager()
    
    class Meta:
        db_table = 'lab_dept_stock'
        verbose_name = '科室库存'
        verbose_name_plural = '科室库存'
        unique_together = ['material', 'department']
        ordering = ['department', 'material__code']
    
    def __str__(self):
        return f'{self.department} - {self.material.name} ({self.quantity})'
    
    @property
    def available_quantity(self):
        """可用数量 = 库存 - 冻结"""
        return self.quantity - self.frozen_quantity


class DeptStockRecord(models.Model):
    """
    科室库存明细流水
    记录每次入库/消耗操作
    """
    
    DIRECTION_CHOICES = [
        ('IN', '入库'),
        ('OUT', '消耗'),
    ]
    
    stock = models.ForeignKey(
        DeptStock, on_delete=models.CASCADE,
        related_name='records', verbose_name='库存'
    )
    direction = models.CharField('方向', max_length=10, choices=DIRECTION_CHOICES)
    quantity = models.DecimalField('数量', max_digits=10, decimal_places=2)
    
    # 来源/用途
    order_no = models.CharField('单号', max_length=50, blank=True, db_index=True)
    consume_type = models.CharField('消耗类型', max_length=50, blank=True,
                                    help_text='如：检验/盘点/报损')
    
    # 批次信息
    batch_no = models.CharField('批号', max_length=50, blank=True)
    expire_date = models.DateField('有效期', null=True, blank=True)
    
    remark = models.TextField('备注', blank=True)
    operator = models.CharField('操作人', max_length=50, blank=True)
    created_at = models.DateTimeField('操作时间', auto_now_add=True)
    
    class Meta:
        db_table = 'lab_dept_stock_record'
        verbose_name = '库存明细'
        verbose_name_plural = '库存明细'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['stock', '-created_at']),
            models.Index(fields=['order_no']),
        ]
    
    def __str__(self):
        return f'{self.stock} {self.direction} {self.quantity}'


# ============================================================
# 其他独立业务表
# ============================================================

class MaterialOrder(models.Model):
    """
    物资采购/入库单
    """
    
    ORDER_TYPE_CHOICES = [
        ('PURCHASE', '采购入库'),
        ('RETURN', '退货'),
        ('TRANSFER_IN', '调拨入库'),
        ('ADJUST', '调整'),
    ]
    
    order_no = models.CharField('单号', max_length=50, unique=True)
    order_type = models.CharField('类型', max_length=20, choices=ORDER_TYPE_CHOICES)
    
    supplier = models.CharField('供应商', max_length=200, blank=True)
    total_amount = models.DecimalField('总金额', max_digits=12, decimal_places=2, default=0)
    
    applicant = models.CharField('申请人', max_length=50, blank=True)
    approver = models.CharField('审批人', max_length=50, blank=True)
    approve_time = models.DateTimeField('审批时间', null=True, blank=True)
    
    status = models.CharField('状态', max_length=20, default='DRAFT',
                              choices=[
                                  ('DRAFT', '草稿'),
                                  ('SUBMITTED', '已提交'),
                                  ('APPROVED', '已审批'),
                                  ('COMPLETED', '已完成'),
                              ])
    
    remark = models.TextField('备注', blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        db_table = 'lab_material_order'
        verbose_name = '物资单据'
        verbose_name_plural = '物资单据'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.order_no} ({self.order_type})'


class MaterialOrderItem(models.Model):
    """单据明细"""
    
    order = models.ForeignKey(
        MaterialOrder, on_delete=models.CASCADE,
        related_name='items', verbose_name='单据'
    )
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT,
        related_name='order_items', verbose_name='物资'
    )
    
    quantity = models.DecimalField('数量', max_digits=10, decimal_places=2)
    unit_price = models.DecimalField('单价', max_digits=10, decimal_places=2)
    subtotal = models.DecimalField('小计', max_digits=12, decimal_places=2)
    
    batch_no = models.CharField('批号', max_length=50, blank=True)
    expire_date = models.DateField('有效期', null=True, blank=True)
    
    remark = models.TextField('备注', blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'lab_material_order_item'
        verbose_name = '单据明细'
        verbose_name_plural = '单据明细'
    
    def save(self, *args, **kwargs):
        self.subtotal = self.quantity * self.unit_price
        super().save(*args, **kwargs)


class ConsumptionRecord(models.Model):
    """
    科室消耗记录
    记录各科室物资消耗情况
    """
    
    CONSUME_TYPE_CHOICES = [
        ('INSPECTION', '检验'),
        ('PRODUCTION', '生产'),
        ('MAINTENANCE', '维护'),
        ('OFFICE', '办公'),
        ('OTHER', '其他'),
    ]
    
    material = models.ForeignKey(
        Material, on_delete=models.PROTECT,
        related_name='consumptions', verbose_name='物资'
    )
    department = models.CharField('科室', max_length=100)
    
    consume_type = models.CharField('消耗类型', max_length=20, choices=CONSUME_TYPE_CHOICES)
    quantity = models.DecimalField('消耗数量', max_digits=10, decimal_places=2)
    
    # 关联库存记录
    stock_record = models.ForeignKey(
        DeptStockRecord, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='consumption', verbose_name='库存明细'
    )
    
    operator = models.CharField('操作人', max_length=50, blank=True)
    consume_date = models.DateField('消耗日期', auto_now_add=True)
    remark = models.TextField('备注', blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'lab_consumption_record'
        verbose_name = '消耗记录'
        verbose_name_plural = '消耗记录'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['department', '-created_at']),
            models.Index(fields=['material']),
        ]
    
    def __str__(self):
        return f'{self.department} {self.material.name} {self.quantity}'


class StockAlert(models.Model):
    """
    库存预警记录
    当科室库存低于最低警戒线时触发
    """
    
    ALERT_TYPE_CHOICES = [
        ('LOW_STOCK', '库存不足'),
        ('EXPIRE_SOON', '即将过期'),
        ('OVER_STOCK', '库存溢出'),
    ]
    
    material = models.ForeignKey(
        Material, on_delete=models.CASCADE,
        related_name='alerts', verbose_name='物资'
    )
    department = models.CharField('科室', max_length=100)
    
    alert_type = models.CharField('预警类型', max_length=20, choices=ALERT_TYPE_CHOICES)
    current_quantity = models.DecimalField('当前库存', max_digits=10, decimal_places=2)
    threshold_value = models.DecimalField('阈值', max_digits=10, decimal_places=2)
    
    is_resolved = models.BooleanField('已处理', default=False)
    resolved_at = models.DateTimeField('处理时间', null=True, blank=True)
    resolved_by = models.CharField('处理人', max_length=50, blank=True)
    resolution = models.TextField('处理方案', blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    
    class Meta:
        db_table = 'lab_stock_alert'
        verbose_name = '库存预警'
        verbose_name_plural = '库存预警'
        ordering = ['-created_at']
    
    def __str__(self):
        return f'{self.department} {self.material.name} {self.alert_type}'