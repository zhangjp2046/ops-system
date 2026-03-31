from rest_framework import serializers
from .models import WorkOrder, WorkOrderStep, WorkOrderComment


class WorkOrderStepSerializer(serializers.ModelSerializer):
    """工单步骤序列化器"""
    
    handler_name = serializers.CharField(source='handler.username', read_only=True)
    status_name = serializers.SerializerMethodField()
    
    class Meta:
        model = WorkOrderStep
        fields = [
            'id', 'order', 'status', 'status_name', 'step_type',
            'handler', 'handler_name', 'title', 'description',
            'attachment', 'flow_time', 'cttime'
        ]
        read_only_fields = ['id', 'cttime']
    
    def get_status_name(self, obj):
        return dict(obj.STATUS_CHOICES).get(obj.status, '')


class WorkOrderCommentSerializer(serializers.ModelSerializer):
    """工单评论序列化器"""
    
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = WorkOrderComment
        fields = ['id', 'order', 'user', 'user_name', 'content', 'cttime']
        read_only_fields = ['id', 'cttime']


class WorkOrderListSerializer(serializers.ModelSerializer):
    """工单列表序列化器（简化）"""
    
    customer_name = serializers.CharField(source='customer.name', read_only=True)
    handler_name = serializers.CharField(source='handler.username', read_only=True)
    creator_name = serializers.CharField(source='creator.username', read_only=True)
    status_name = serializers.CharField(source='get_status_display', read_only=True)
    type_name = serializers.CharField(source='get_order_type_display', read_only=True)
    priority_name = serializers.CharField(source='get_priority_display', read_only=True)
    step_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = WorkOrder
        fields = [
            'id', 'title', 'resume', 'order_type', 'type_name',
            'priority', 'priority_name', 'status', 'status_name',
            'customer', 'customer_name', 'handler', 'handler_name',
            'creator', 'creator_name', 'occdate', 'cttime',
            'step_count'
        ]
        read_only_fields = ['id', 'cttime']


class WorkOrderDetailSerializer(WorkOrderListSerializer):
    """工单详情序列化器"""
    
    steps = WorkOrderStepSerializer(many=True, read_only=True)
    comments = WorkOrderCommentSerializer(many=True, read_only=True)
    
    class Meta(WorkOrderListSerializer.Meta):
        fields = WorkOrderListSerializer.Meta.fields + [
            'steps', 'comments', 'description'
        ]


class WorkOrderCreateSerializer(serializers.ModelSerializer):
    """工单创建/更新序列化器"""
    
    class Meta:
        model = WorkOrder
        fields = [
            'id', 'title', 'resume', 'order_type', 'priority', 'status',
            'customer', 'contact_name', 'contact_phone', 'asset', 'handler', 'occdate', 'description'
        ]
        read_only_fields = ['id']
    
    def create(self, validated_data):
        # 设置创建人
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['creator'] = request.user
        return super().create(validated_data)
