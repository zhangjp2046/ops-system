#!/usr/bin/env python3
"""
告警阈值配置序列化器
"""
from rest_framework import serializers
from .threshold_models import AlertThreshold, AlertThresholdRule, AlertThresholdTemplate


class AlertThresholdRuleSerializer(serializers.ModelSerializer):
    """阈值规则序列化器"""
    
    severity_display = serializers.CharField(source='get_severity_display', read_only=True)
    operator_display = serializers.CharField(source='get_operator_display', read_only=True)
    
    class Meta:
        model = AlertThresholdRule
        fields = [
            'id', 'threshold', 'severity', 'severity_display', 
            'operator', 'operator_display', 'threshold_value',
            'rule_name', 'description', 'sort_order', 'is_active'
        ]


class AlertThresholdSerializer(serializers.ModelSerializer):
    """告警阈值序列化器"""
    
    customer_name = serializers.CharField(source='customer.customer_name', read_only=True, default='')
    asset_type_name = serializers.CharField(source='asset_type.type_name', read_only=True, default='')
    protocol_display = serializers.CharField(source='get_protocol_display', read_only=True)
    direction_display = serializers.CharField(source='get_threshold_direction_display', read_only=True)
    value_type_display = serializers.CharField(source='get_value_type_display', read_only=True)
    
    rules = AlertThresholdRuleSerializer(many=True, read_only=True)
    
    class Meta:
        model = AlertThreshold
        fields = [
            'id', 'customer', 'customer_name', 'asset_type', 'asset_type_name',
            'check_item_code', 'check_item_name', 'protocol', 'protocol_display',
            'threshold_direction', 'direction_display', 'value_type', 'value_type_display',
            'warning_threshold', 'error_threshold', 'critical_threshold',
            'unit', 'description', 'config', 'is_active', 'is_monitoring_item',
            'rules', 'created_at', 'updated_at'
        ]


class AlertThresholdCreateSerializer(serializers.ModelSerializer):
    """创建/更新阈值序列化器"""
    
    rules = AlertThresholdRuleSerializer(many=True, required=False)
    
    class Meta:
        model = AlertThreshold
        fields = [
            'customer', 'asset_type', 'check_item_code', 'check_item_name',
            'protocol', 'threshold_direction', 'value_type',
            'warning_threshold', 'error_threshold', 'critical_threshold',
            'unit', 'description', 'config', 'is_active', 'is_monitoring_item', 'rules'
        ]
    
    def create(self, validated_data):
        rules_data = validated_data.pop('rules', [])
        threshold = AlertThreshold.objects.create(**validated_data)
        
        for rule_data in rules_data:
            AlertThresholdRule.objects.create(threshold=threshold, **rule_data)
        
        return threshold
    
    def update(self, instance, validated_data):
        rules_data = validated_data.pop('rules', None)
        
        # 更新主记录
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # 更新规则（如果提供）
        if rules_data is not None:
            instance.rules.all().delete()
            for rule_data in rules_data:
                AlertThresholdRule.objects.create(threshold=instance, **rule_data)
        
        return instance


class AlertThresholdTemplateSerializer(serializers.ModelSerializer):
    """阈值模板序列化器"""
    
    class Meta:
        model = AlertThresholdTemplate
        fields = [
            'id', 'name', 'protocol', 'check_item_code', 'check_item_name',
            'default_config', 'description', 'is_system', 'created_at'
        ]


class ThresholdCheckSerializer(serializers.Serializer):
    """阈值检查请求序列化器"""
    
    check_item_code = serializers.CharField(max_length=50)
    value = serializers.CharField(max_length=500)
    customer_id = serializers.IntegerField(required=False)
    asset_type_id = serializers.IntegerField(required=False)
    
    def validate(self, data):
        """验证并返回严重程度"""
        check_item_code = data['check_item_code']
        value = data['value']
        customer_id = data.get('customer_id')
        asset_type_id = data.get('asset_type_id')
        
        # 查找匹配的阈值配置
        threshold = self._find_threshold(check_item_code, customer_id, asset_type_id)
        
        if not threshold:
            # 没有配置阈值，返回默认
            data['severity'] = 1
            data['severity_name'] = '信息'
            data['threshold_found'] = False
            return data
        
        severity, severity_name = threshold.get_severity(value)
        data['severity'] = severity
        data['severity_name'] = severity_name
        data['threshold_found'] = True
        data['threshold_id'] = threshold.id
        
        return data
    
    def _find_threshold(self, check_item_code, customer_id=None, asset_type_id=None):
        """查找最匹配的阈值配置"""
        # 优先级: 客户+资产类型 > 客户 > 全局
        queries = []
        
        if customer_id and asset_type_id:
            queries.append({
                'customer_id': customer_id,
                'asset_type_id': asset_type_id,
                'check_item_code': check_item_code,
                'is_active': True
            })
        
        if customer_id:
            queries.append({
                'customer_id': customer_id,
                'asset_type_id__isnull': True,
                'check_item_code': check_item_code,
                'is_active': True
            })
        
        queries.append({
            'customer_id__isnull': True,
            'asset_type_id__isnull': True,
            'check_item_code': check_item_code,
            'is_active': True
        })
        
        for query in queries:
            threshold = AlertThreshold.objects.filter(**query).first()
            if threshold:
                return threshold
        
        return None
