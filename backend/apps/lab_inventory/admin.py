from django.contrib import admin
from .models import (
    MaterialCategory, Material,
    DeptStock, DeptStockRecord,
    MaterialOrder, MaterialOrderItem,
    ConsumptionRecord, StockAlert,
)


@admin.register(MaterialCategory)
class MaterialCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'code', 'sort_order', 'is_active']
    search_fields = ['name', 'code']
    list_filter = ['is_active']


@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'category', 'spec', 'unit', 'unit_price', 'cas_no', 'is_active']
    search_fields = ['code', 'name', 'spec', 'cas_no']
    list_filter = ['category', 'is_active']
    list_per_page = 50


@admin.register(DeptStock)
class DeptStockAdmin(admin.ModelAdmin):
    list_display = ['department', 'material', 'quantity', 'frozen_quantity', 'min_stock_alert']
    search_fields = ['department', 'material__name']
    list_filter = ['department', 'min_stock_alert']
    raw_id_fields = ['material']


@admin.register(DeptStockRecord)
class DeptStockRecordAdmin(admin.ModelAdmin):
    list_display = ['stock', 'direction', 'quantity', 'order_no', 'created_at']
    search_fields = ['order_no', 'stock__department']
    list_filter = ['direction', 'consume_type']
    date_hierarchy = 'created_at'


@admin.register(MaterialOrder)
class MaterialOrderAdmin(admin.ModelAdmin):
    list_display = ['order_no', 'order_type', 'supplier', 'total_amount', 'status', 'created_at']
    search_fields = ['order_no', 'supplier']
    list_filter = ['order_type', 'status']
    date_hierarchy = 'created_at'


@admin.register(MaterialOrderItem)
class MaterialOrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'material', 'quantity', 'unit_price', 'subtotal']
    search_fields = ['order__order_no', 'material__name']
    raw_id_fields = ['order', 'material']


@admin.register(ConsumptionRecord)
class ConsumptionRecordAdmin(admin.ModelAdmin):
    list_display = ['department', 'material', 'consume_type', 'quantity', 'operator', 'created_at']
    search_fields = ['department', 'material__name']
    list_filter = ['department', 'consume_type']
    date_hierarchy = 'created_at'


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = ['material', 'department', 'alert_type', 'current_quantity', 'is_resolved', 'created_at']
    search_fields = ['department', 'material__name']
    list_filter = ['alert_type', 'is_resolved']
    date_hierarchy = 'created_at'