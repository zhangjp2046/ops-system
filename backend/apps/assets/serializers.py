from rest_framework import serializers
from django.db import transaction
from .models import Asset, AssetType, AssetField, AssetData
from apps.customers.models import Customer
from apps.users.models import User


class AssetTypeSerializer(serializers.ModelSerializer):
    """资产类型序列化器"""
    
    class Meta:
        model = AssetType
        fields = [
            'id', 'customer', 'type_code', 'type_name', 'parent_type',
            'plugin_id', 'icon', 'color', 'description', 'sort_order',
            'is_system', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AssetFieldSerializer(serializers.ModelSerializer):
    """资产字段序列化器"""
    
    class Meta:
        model = AssetField
        fields = [
            'id', 'asset_type', 'field_code', 'field_name', 'field_type',
            'is_required', 'is_unique', 'is_searchable', 'is_filterable',
            'field_label', 'placeholder', 'help_text', 'sort_order',
            'validation_rules', 'default_value', 'options',
        ]
        read_only_fields = ['id']


class AssetDataSerializer(serializers.ModelSerializer):
    """资产数据序列化器"""
    field_code = serializers.CharField(source='field.field_code', read_only=True)
    field_label = serializers.CharField(source='field.field_label', read_only=True)
    field_type = serializers.CharField(source='field.field_type', read_only=True)
    
    class Meta:
        model = AssetData
        fields = [
            'id', 'asset', 'field', 'field_code', 'field_label', 'field_type',
            'string_value', 'number_value', 'boolean_value', 'date_value',
            'datetime_value', 'json_value', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class AssetSerializer(serializers.ModelSerializer):
    """资产序列化器"""
    customer_name = serializers.CharField(source='customer.customer_name', read_only=True)
    asset_type_name = serializers.CharField(source='asset_type.type_name', read_only=True)
    field_data = serializers.SerializerMethodField()
    
    class Meta:
        model = Asset
        fields = [
            'id', 'customer', 'customer_name', 'asset_type', 'asset_type_name',
            'asset_code', 'asset_name', 'description',
            'ip_address', 'online', 'last_check_time',
            'location', 'room', 'rack', 'position',
            'status', 'importance_level',
            'protocol', 'db_type', 'port', 'username', 'password', 'database',
            'purchase_date', 'warranty_end', 'decommission_date',
            'owner', 'department', 'vendor',
            'field_data',
            'created_at', 'updated_at',
            'created_by', 'updated_by'
        ]
        read_only_fields = [
            'id', 'customer_name', 'asset_type_name', 'field_data',
            'online', 'last_check_time',
            'created_at', 'updated_at', 'created_by', 'updated_by'
        ]
    
    def get_field_data(self, obj):
        """获取字段数据"""
        field_data = {}
        for data in obj.field_values.all():
            field_data[data.field.field_code] = {
                'value': data.get_value(),
                'label': data.field.field_label,
                'type': data.field.field_type
            }
        return field_data


class AssetCreateSerializer(serializers.ModelSerializer):
    """资产创建序列化器"""
    field_values = serializers.JSONField(write_only=True, required=False, default=dict)
    
    class Meta:
        model = Asset
        fields = [
            'customer', 'asset_type', 'asset_code', 'asset_name', 'description',
            'ip_address',
            'location', 'room', 'rack', 'position',
            'status', 'importance_level',
            'protocol', 'db_type', 'port', 'username', 'password', 'database',
            'purchase_date', 'warranty_end', 'decommission_date',
            'owner', 'department', 'vendor',
            'field_values'
        ]
    
    def validate(self, data):
        """验证数据"""
        # 验证资产编号唯一性
        customer = data.get('customer')
        asset_code = data.get('asset_code')
        
        if customer and asset_code:
            if Asset.objects.filter(customer=customer, asset_code=asset_code).exists():
                raise serializers.ValidationError({
                    'asset_code': f'资产编号 {asset_code} 已存在'
                })
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """创建资产"""
        field_values = validated_data.pop('field_values', {})
        request = self.context.get('request')
        
        # 设置创建人和更新人
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
            validated_data['updated_by'] = request.user
        
        # 创建资产
        asset = Asset.objects.create(**validated_data)
        
        # 创建字段数据
        self._create_field_data(asset, field_values)
        
        return asset
    
    def _create_field_data(self, asset, field_values):
        """创建字段数据"""
        asset_type = asset.asset_type
        required_fields = asset_type.fields.filter(is_required=True)
        
        # 检查必填字段
        for field in required_fields:
            if field.field_code not in field_values:
                raise serializers.ValidationError({
                    field.field_code: f'字段 {field.field_label} 是必填项'
                })
        
        # 创建字段数据
        for field in asset_type.fields.all():
            field_code = field.field_code
            value = field_values.get(field_code, field.default_value)
            
            if value is not None:
                asset_data = AssetData(asset=asset, field=field)
                asset_data.set_value(value)
                asset_data.save()


class AssetUpdateSerializer(serializers.ModelSerializer):
    """资产更新序列化器"""
    field_values = serializers.JSONField(write_only=True, required=False)
    
    class Meta:
        model = Asset
        fields = [
            'asset_name', 'description',
            'ip_address',
            'location', 'room', 'rack', 'position',
            'status', 'importance_level',
            'protocol', 'db_type', 'port', 'username', 'password', 'database',
            'purchase_date', 'warranty_end', 'decommission_date',
            'owner', 'department', 'vendor',
            'field_values'
        ]
    
    @transaction.atomic
    def update(self, instance, validated_data):
        """更新资产"""
        field_values = validated_data.pop('field_values', {})
        request = self.context.get('request')
        
        # 设置更新人
        if request and request.user.is_authenticated:
            validated_data['updated_by'] = request.user
        
        # 更新资产基本信息
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # 更新字段数据
        if field_values:
            self._update_field_data(instance, field_values)
        
        return instance
    
    def _update_field_data(self, asset, field_values):
        """更新字段数据"""
        for field_code, value in field_values.items():
            try:
                field = asset.asset_type.fields.get(field_code=field_code)
                asset_data, created = AssetData.objects.get_or_create(
                    asset=asset,
                    field=field,
                    defaults={'string_value': str(value)}
                )
                if not created:
                    asset_data.set_value(value)
                    asset_data.save()
            except AssetField.DoesNotExist:
                # 忽略不存在的字段
                pass


class AssetImportSerializer(serializers.Serializer):
    """资产导入序列化器"""
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.all())
    asset_type = serializers.PrimaryKeyRelatedField(queryset=AssetType.objects.all())
    assets = serializers.ListField(child=serializers.JSONField(), required=True)
    
    def validate(self, data):
        """验证导入数据"""
        customer = data['customer']
        asset_type = data['asset_type']
        assets = data['assets']
        
        # 检查资产类型是否属于该客户
        if asset_type.customer != customer:
            raise serializers.ValidationError({
                'asset_type': '资产类型不属于该客户'
            })
        
        # 验证每个资产
        for i, asset_data in enumerate(assets):
            if 'asset_code' not in asset_data:
                raise serializers.ValidationError({
                    f'assets[{i}]': '缺少 asset_code 字段'
                })
            
            # 检查资产编号是否已存在
            asset_code = asset_data['asset_code']
            if Asset.objects.filter(customer=customer, asset_code=asset_code).exists():
                raise serializers.ValidationError({
                    f'assets[{i}].asset_code': f'资产编号 {asset_code} 已存在'
                })
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """批量导入资产"""
        customer = validated_data['customer']
        asset_type = validated_data['asset_type']
        assets_data = validated_data['assets']
        request = self.context.get('request')
        user = request.user if request and request.user.is_authenticated else None
        
        created_assets = []
        errors = []
        
        for i, asset_data in enumerate(assets_data):
            try:
                # 创建资产
                asset = Asset.objects.create(
                    customer=customer,
                    asset_type=asset_type,
                    asset_code=asset_data.get('asset_code'),
                    asset_name=asset_data.get('asset_name', ''),
                    description=asset_data.get('description', ''),
                    location=asset_data.get('location', ''),
                    room=asset_data.get('room', ''),
                    rack=asset_data.get('rack', ''),
                    position=asset_data.get('position', ''),
                    status=asset_data.get('status', 'ACTIVE'),
                    importance_level=asset_data.get('importance_level', 'MEDIUM'),
                    purchase_date=asset_data.get('purchase_date'),
                    warranty_end=asset_data.get('warranty_end'),
                    decommission_date=asset_data.get('decommission_date'),
                    owner=asset_data.get('owner', ''),
                    department=asset_data.get('department', ''),
                    vendor=asset_data.get('vendor', ''),
                    created_by=user,
                    updated_by=user
                )
                
                # 创建字段数据
                field_values = asset_data.get('field_values', {})
                for field_code, value in field_values.items():
                    try:
                        field = asset_type.fields.get(field_code=field_code)
                        asset_data_obj = AssetData(asset=asset, field=field)
                        asset_data_obj.set_value(value)
                        asset_data_obj.save()
                    except AssetField.DoesNotExist:
                        pass
                
                created_assets.append(asset)
                
            except Exception as e:
                errors.append({
                    'index': i,
                    'asset_code': asset_data.get('asset_code', '未知'),
                    'error': str(e)
                })
        
        return {
            'created_count': len(created_assets),
            'error_count': len(errors),
            'errors': errors,
            'assets': AssetSerializer(created_assets, many=True).data
        }