from rest_framework import serializers
from .models import InspectionPlan, InspectionTask, InspectionResult, InspectionRecord


class InspectionPlanSerializer(serializers.ModelSerializer):
    """巡检计划序列化器"""
    
    cycle_display = serializers.CharField(source='get_cycle_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    task_count = serializers.SerializerMethodField()
    
    class Meta:
        model = InspectionPlan
        fields = [
            'id', 'name', 'code', 'description',
            'cycle', 'cycle_display', 'scheduled_time', 'is_auto_execute',
            'status', 'status_display', 'check_items', 'task_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_task_count(self, obj):
        return obj.tasks.count()


class InspectionTaskSerializer(serializers.ModelSerializer):
    """巡检任务序列化器"""
    
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    asset_name = serializers.CharField(source='asset.asset_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    executor_name = serializers.CharField(source='executor.username', read_only=True)
    
    class Meta:
        model = InspectionTask
        fields = [
            'id', 'plan', 'plan_name', 'asset', 'asset_name',
            'scheduled_time', 'executed_time', 'priority', 'priority_display',
            'status', 'status_display', 'executor', 'executor_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class InspectionResultSerializer(serializers.ModelSerializer):
    """巡检结果序列化器"""
    
    asset_name = serializers.CharField(source='asset.asset_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = InspectionResult
        fields = [
            'id', 'task', 'asset', 'asset_name',
            'check_item', 'check_item_code', 'status', 'status_display',
            'result_value', 'result_message',
            'expected_value', 'threshold_min', 'threshold_max',
            'suggestion', 'executed_at'
        ]
        read_only_fields = ['id', 'executed_at']


class InspectionRecordSerializer(serializers.ModelSerializer):
    """巡检记录序列化器"""
    
    asset_name = serializers.CharField(source='asset.asset_name', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    overall_status_display = serializers.CharField(source='get_overall_status_display', read_only=True)
    executor_name = serializers.CharField(source='executor.username', read_only=True)
    
    class Meta:
        model = InspectionRecord
        fields = [
            'id', 'task', 'asset', 'asset_name',
            'total_checks', 'pass_checks', 'warning_checks', 'fail_checks', 'skip_checks',
            'status', 'status_display', 'overall_status', 'overall_status_display',
            'summary', 'executor', 'executor_name',
            'started_at', 'completed_at', 'duration', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class InspectionRecordDetailSerializer(InspectionRecordSerializer):
    """巡检记录详情序列化器（包含巡检结果）"""
    
    results = InspectionResultSerializer(many=True, read_only=True)
    
    class Meta(InspectionRecordSerializer.Meta):
        fields = InspectionRecordSerializer.Meta.fields + ['results']
