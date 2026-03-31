from rest_framework import serializers
from .models import ScheduledTask, ScheduledTaskExecution


class ScheduledTaskSerializer(serializers.ModelSerializer):
    """计划任务序列化器"""
    
    task_type_display = serializers.CharField(source='get_task_type_display', read_only=True)
    target_type_display = serializers.CharField(source='get_target_type_display', read_only=True)
    last_status_display = serializers.CharField(source='get_last_status_display', read_only=True)
    
    class Meta:
        model = ScheduledTask
        fields = [
            'id', 'name', 'description', 'task_type', 'task_type_display',
            'target_type', 'target_type_display', 'target_id',
            'config', 'cron_expression', 'interval_seconds',
            'is_enabled', 'is_running',
            'last_run_time', 'next_run_time', 'last_status', 'last_status_display', 'last_result',
            'success_count', 'failure_count', 'total_runs',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ScheduledTaskExecutionSerializer(serializers.ModelSerializer):
    """计划任务执行记录序列化器"""
    
    task_name = serializers.CharField(source='task.name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = ScheduledTaskExecution
        fields = [
            'id', 'task', 'task_name', 'start_time', 'end_time', 'duration_ms',
            'status', 'status_display', 'result_data', 'error_message', 'output',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ScheduledTaskCreateSerializer(serializers.ModelSerializer):
    """计划任务创建序列化器"""
    
    class Meta:
        model = ScheduledTask
        fields = [
            'name', 'description', 'task_type', 'target_type', 'target_id',
            'config', 'cron_expression', 'interval_seconds', 'is_enabled'
        ]
    
    def validate(self, data):
        """验证数据"""
        if not data.get('cron_expression') and not data.get('interval_seconds'):
            raise serializers.ValidationError('必须提供cron_expression或interval_seconds')
        return data


class ScheduledTaskUpdateSerializer(serializers.ModelSerializer):
    """计划任务更新序列化器"""
    
    class Meta:
        model = ScheduledTask
        fields = [
            'name', 'description', 'config', 'cron_expression', 'interval_seconds',
            'is_enabled'
        ]