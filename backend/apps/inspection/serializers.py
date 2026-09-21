from rest_framework import serializers
from .models import InspectionPlan, InspectionTask, InspectionResult, InspectionRecord, Inspection
from .check_items import get_check_items_by_protocol, get_all_protocols, get_protocol_categories


class InspectionPlanSerializer(serializers.ModelSerializer):
    """巡检计划序列化器"""
    
    cycle_display = serializers.CharField(source='get_cycle_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    protocol_display = serializers.CharField(source='get_protocol_display', read_only=True)
    task_count = serializers.SerializerMethodField()
    customer_name = serializers.CharField(source='customer.customer_name', read_only=True)
    available_checks = serializers.SerializerMethodField()
    # 设备类型名称（从 asset_type_ids 解析）
    asset_type_names = serializers.SerializerMethodField()
    
    class Meta:
        model = InspectionPlan
        fields = [
            'id', 'name', 'code', 'description',
            'protocol', 'protocol_display',
            'customer', 'customer_name',
            'cycle', 'cycle_display', 'scheduled_time', 'is_auto_execute',
            'status', 'status_display', 'check_items', 'task_count',
            'available_checks',
            'asset_type_ids', 'asset_type_names', 'asset_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
        extra_kwargs = {
            'scheduled_time': {'required': False, 'allow_null': True},
            'cycle': {'required': False, 'allow_null': True},
        }
    
    def get_task_count(self, obj):
        return obj.tasks.count()
    
    def get_available_checks(self, obj):
        """返回该协议可用的巡检项目列表"""
        return get_check_items_by_protocol(obj.protocol)
    
    def get_asset_type_names(self, obj):
        """从 asset_type_ids 获取资产类型名称列表"""
        if not obj.asset_type_ids:
            return []
        try:
            from apps.assets.models import AssetType
            types = AssetType.objects.filter(id__in=obj.asset_type_ids)
            return [{'id': t.id, 'name': t.type_name} for t in types]
        except Exception:
            return []


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
            'check_item', 'check_item_code', 'status', 'status_display', 'severity',
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
    
    results = serializers.SerializerMethodField()
    
    class Meta(InspectionRecordSerializer.Meta):
        fields = InspectionRecordSerializer.Meta.fields + ['results']
    
    def get_results(self, obj):
        """通过 task 获取巡检结果"""
        results = InspectionResult.objects.filter(task=obj.task)
        return InspectionResultSerializer(results, many=True).data


class InspectionSerializer(serializers.ModelSerializer):
    """巡检执行记录（调度执行器使用）"""
    items = serializers.SerializerMethodField()
    asset_name = serializers.CharField(source='asset.asset_name', read_only=True, default='')
    
    class Meta:
        model = Inspection
        fields = [
            'id', 'name', 'description', 'inspection_type',
            'customer', 'asset', 'asset_name', 'asset_type',
            'status', 'started_at', 'completed_at',
            'total_items', 'passed_items', 'warning_items', 'failed_items',
            'duration_ms', 'summary', 'items',
            'created_at'
        ]
    
    def get_items(self, obj):
        # 优先从 InspectionItem 读（有 FK 到 Inspection）
        items = list(obj.items.all().order_by('id'))
        
        if items:
            return [
                {
                    'item_name': r.item_name,
                    'code': r.item_code,
                    'result': r.result,
                    'severity': r.severity,
                    'message': r.message,
                    'actual_value': r.actual_value,
                    'category': r.category,
                }
                for r in items
            ]
        
        # InspectionItem 为空时，从 InspectionResult 读（按 asset 关联）
        if obj.asset_id:
            from apps.inspection.models import InspectionResult as IR
            results = IR.objects.filter(asset_id=obj.asset_id).order_by('-id')[:20]
            sev_map = {1: 'OK', 2: 'WARNING', 3: 'FAIL', 4: 'CRITICAL'}
            status_map = {'pass': 'PASS', 'warning': 'WARNING', 'fail': 'FAIL', 'skip': 'SKIP'}
            return [
                {
                    'item_name': r.check_item or '',
                    'code': r.check_item_code or '',
                    'result': status_map.get(r.status, r.status or 'PASS').upper(),
                    'severity': sev_map.get(r.severity, 'INFO'),
                    'message': r.result_message or '',
                    'actual_value': r.result_value or '',
                    'category': 'snmp',
                }
                for r in results
            ]
        return []
