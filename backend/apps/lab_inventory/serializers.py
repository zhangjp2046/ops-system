from rest_framework import serializers
from .models import (
    MaterialCategory, Material,
    DeptStock, DeptStockRecord,
    MaterialOrder, MaterialOrderItem,
    ConsumptionRecord, StockAlert,
)


class MaterialCategorySerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    
    class Meta:
        model = MaterialCategory
        fields = ['id', 'name', 'parent', 'code', 'description', 
                  'sort_order', 'is_active', 'children']
    
    def get_children(self, obj):
        children = obj.children.filter(is_active=True)
        return MaterialCategorySerializer(children, many=True).data


class MaterialSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    class Meta:
        model = Material
        fields = ['id', 'code', 'name', 'category', 'category_name',
                  'spec', 'unit', 'min_stock', 'max_stock',
                  'unit_price', 'manufacturer', 'supplier',
                  'description', 'is_active', 'created_at']


class DeptStockSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name', read_only=True)
    material_code = serializers.CharField(source='material.code', read_only=True)
    available_quantity = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = DeptStock
        fields = ['id', 'material', 'material_name', 'material_code',
                  'department', 'quantity', 'frozen_quantity',
                  'available_quantity', 'min_stock_alert', 'updated_at']


class DeptStockRecordSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='stock.material.name', read_only=True)
    department = serializers.CharField(source='stock.department', read_only=True)
    
    class Meta:
        model = DeptStockRecord
        fields = ['id', 'stock', 'material_name', 'department',
                  'direction', 'quantity', 'order_no', 'consume_type',
                  'batch_no', 'expire_date', 'remark', 'operator', 'created_at']


class MaterialOrderItemSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name', read_only=True)
    
    class Meta:
        model = MaterialOrderItem
        fields = ['id', 'order', 'material', 'material_name',
                  'quantity', 'unit_price', 'subtotal',
                  'batch_no', 'expire_date', 'remark']


class MaterialOrderSerializer(serializers.ModelSerializer):
    items = MaterialOrderItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = MaterialOrder
        fields = ['id', 'order_no', 'order_type', 'supplier',
                  'total_amount', 'applicant', 'approver',
                  'approve_time', 'status', 'remark',
                  'items', 'created_at', 'updated_at']


class ConsumptionRecordSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name', read_only=True)
    
    class Meta:
        model = ConsumptionRecord
        fields = ['id', 'material', 'material_name', 'department',
                  'consume_type', 'quantity', 'stock_record',
                  'operator', 'consume_date', 'remark', 'created_at']


class StockAlertSerializer(serializers.ModelSerializer):
    material_name = serializers.CharField(source='material.name', read_only=True)
    
    class Meta:
        model = StockAlert
        fields = ['id', 'material', 'material_name', 'department',
                  'alert_type', 'current_quantity', 'threshold_value',
                  'is_resolved', 'resolved_at', 'resolved_by',
                  'resolution', 'created_at']