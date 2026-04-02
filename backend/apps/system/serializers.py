from rest_framework import serializers
from .models import SystemSetting


class SystemSettingSerializer(serializers.ModelSerializer):
    display_value = serializers.SerializerMethodField()

    class Meta:
        model = SystemSetting
        fields = [
            'id', 'key', 'value', 'display_value',
            'category', 'label', 'description',
            'field_type', 'options', 'is_sensitive',
            'updated_at', 'updated_by',
        ]
        read_only_fields = ['id', 'updated_at']

    def get_display_value(self, obj):
        if obj.is_sensitive and obj.value:
            v = obj.value
            if len(v) > 8:
                return v[:4] + '****' + v[-4:]
            return '****'
        return obj.value


class SystemSettingWriteSerializer(serializers.Serializer):
    """批量更新设置"""
    settings = serializers.DictField(child=serializers.CharField(allow_blank=True))
