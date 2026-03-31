from rest_framework import serializers
from .models import MonitoringTask, MonitoringResult, AlertRule, Alert
from .test_config import MonitorTestConfig, MonitorTestResult


class MonitoringTaskSerializer(serializers.ModelSerializer):
    """监控任务序列化器"""
    
    asset_name = serializers.CharField(source='asset.asset_name', read_only=True)
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = MonitoringTask
        fields = [
            'id', 'name', 'description', 'task_type', 'task_type_display',
            'asset', 'asset_name', 'config', 'interval', 
            'is_enabled', 'is_critical', 'status', 'status_display',
            'last_run_time', 'next_run_time',
            'success_count', 'failure_count', 'last_success_time', 'last_failure_time',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MonitoringResultSerializer(serializers.ModelSerializer):
    """监控结果序列化器"""
    
    asset_name = serializers.CharField(source='asset.asset_name', read_only=True)
    task_name = serializers.CharField(source='task.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = MonitoringResult
        fields = [
            'id', 'task', 'task_name', 'asset', 'asset_name', 'status', 'status_display',
            'response_time', 'uptime', 'cpu_usage', 'memory_usage', 'disk_usage',
            'network_in', 'network_out', 'port_check',
            'error_message', 'error_details', 'raw_data',
            'start_time', 'end_time', 'duration'
        ]
        read_only_fields = ['id', 'start_time']


class AlertRuleSerializer(serializers.ModelSerializer):
    """告警规则序列化器"""
    
    asset_type_name = serializers.CharField(source='asset_type.type_name', read_only=True)
    condition_display = serializers.CharField(source='get_condition_display', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    
    class Meta:
        model = AlertRule
        fields = [
            'id', 'name', 'description', 'metric_name', 'condition', 'condition_display',
            'threshold', 'severity', 'severity_display', 'asset_type', 'asset_type_name',
            'is_enabled', 'check_interval', 'notify_enabled', 'notify_channels', 'notify_recipients',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AlertSerializer(serializers.ModelSerializer):
    """告警记录序列化器"""
    
    asset_name = serializers.CharField(source='asset.asset_name', read_only=True)
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = Alert
        fields = [
            'id', 'title', 'message', 'severity', 'severity_display', 'status', 'status_display',
            'asset', 'asset_name', 'alert_rule', 'monitoring_result',
            'trigger_value', 'threshold',
            'occurred_at', 'acknowledged_at', 'resolved_at',
            'acknowledged_by', 'resolved_by', 'resolution_note'
        ]
        read_only_fields = ['id', 'occurred_at']


class AlertStatisticsSerializer(serializers.Serializer):
    """告警统计序列化器"""
    
    total = serializers.IntegerField()
    open = serializers.IntegerField()
    acknowledged = serializers.IntegerField()
    resolved = serializers.IntegerField()
    closed = serializers.IntegerField()
    by_severity = serializers.DictField()
    by_asset = serializers.ListField()

class MonitorTestConfigSerializer(serializers.ModelSerializer):
    """监控测试配置序列化器"""
    
    customer_name = serializers.CharField(source='customer.customer_name', read_only=True)
    asset_name = serializers.CharField(source='asset.asset_name', read_only=True)
    protocol_display = serializers.CharField(source='get_protocol_display', read_only=True)
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    
    class Meta:
        model = MonitorTestConfig
        fields = [
            'id', 'name', 'description',
            'customer', 'customer_name',
            'asset', 'asset_name',
            'protocol', 'protocol_display',
            'host', 'port', 'config', 'interval',
            'is_enabled', 'last_test_status', 'last_test_time',
            'created_by', 'created_by_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_test_status', 'last_test_time', 'created_at', 'updated_at']


class MonitorTestResultSerializer(serializers.ModelSerializer):
    """监控测试结果序列化器"""
    
    config_name = serializers.CharField(source='config.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = MonitorTestResult
        fields = [
            'id', 'config', 'config_name',
            'status', 'status_display',
            'response_time', 'error_message', 'data',
            'test_duration', 'remote_addr',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
