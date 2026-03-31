from rest_framework import serializers
from .models import Alert, AlertRule, AlertSubscription


class AlertSerializer(serializers.ModelSerializer):
    """告警序列化器"""
    
    customer_name = serializers.CharField(source='customer.customer_name', read_only=True)
    asset_name = serializers.CharField(source='asset.asset_name', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)
    
    class Meta:
        model = Alert
        fields = [
            'id', 'title', 'description',
            'customer', 'customer_name', 'asset', 'asset_name',
            'severity', 'severity_display', 'alert_type', 'source', 'source_display',
            'status', 'status_display',
            'alert_data', 'metric_name', 'metric_value', 'threshold',
            'occurred_at', 'acknowledged_at', 'resolved_at', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class AlertRuleSerializer(serializers.ModelSerializer):
    """告警规则序列化器"""
    
    customer_name = serializers.CharField(source='customer.customer_name', read_only=True)
    
    class Meta:
        model = AlertRule
        fields = [
            'id', 'name', 'description', 'customer', 'customer_name',
            'status', 'severity', 'conditions',
            'auto_create_workorder', 'workorder_template',
            'notify_enabled', 'notify_channels',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AlertSubscriptionSerializer(serializers.ModelSerializer):
    """告警订阅序列化器"""
    
    customer_name = serializers.CharField(source='customer.customer_name', read_only=True)
    channel_display = serializers.CharField(source='get_channel_display', read_only=True)
    
    class Meta:
        model = AlertSubscription
        fields = [
            'id', 'name', 'customer', 'customer_name',
            'channel', 'channel_display', 'config',
            'severity_filter', 'alert_type_filter', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AlertReceiveSerializer(serializers.Serializer):
    """接收告警序列化器（用于本地监控上报）"""
    
    title = serializers.CharField(required=True, max_length=200, help_text='告警标题')
    description = serializers.CharField(required=False, allow_blank=True, default='')
    severity = serializers.IntegerField(required=False, default=2, help_text='1-信息 2-警告 3-错误 4-严重')
    alert_type = serializers.CharField(required=False, allow_blank=True, default='')
    metric_name = serializers.CharField(required=False, allow_blank=True, default='')
    metric_value = serializers.CharField(required=False, allow_blank=True, default='')
    threshold = serializers.CharField(required=False, allow_blank=True, default='')
    occurred_at = serializers.DateTimeField(required=False, allow_null=True)
    asset_identifier = serializers.CharField(required=False, allow_blank=True, help_text='资产标识(IP/主机名/资产ID)')
    alert_data = serializers.JSONField(required=False, default=dict)
