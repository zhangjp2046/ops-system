from rest_framework import serializers
from .models import Customer


class CustomerSerializer(serializers.ModelSerializer):
    """客户序列化器"""
    asset_count = serializers.IntegerField(read_only=True)
    active_asset_count = serializers.IntegerField(read_only=True)
    critical_asset_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = Customer
        fields = [
            'id', 'customer_code', 'customer_name', 'customer_type', 'industry',
            'contact_person', 'contact_phone', 'contact_email', 'address',
            'config', 'plugins', 'status',
            'contract_start', 'contract_end',
            'asset_count', 'active_asset_count', 'critical_asset_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'asset_count', 'active_asset_count', 'critical_asset_count', 'created_at', 'updated_at']