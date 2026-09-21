from rest_framework import serializers
from .models import DiscoveryTask, DiscoveredDevice, TopologyNode, TopologyEdge


class DiscoveredDeviceSerializer(serializers.ModelSerializer):
    """发现的设备序列化器"""

    class Meta:
        model = DiscoveredDevice
        fields = [
            'id', 'ip_address', 'mac_address', 'hostname',
            'device_type', 'os_type', 'vendor', 'model',
            'open_ports', 'response_time',
            'snmp_sysDescr', 'snmp_sysName', 'snmp_sysLocation',
            'ssh_banner', 'http_title',
            'is_online', 'is_imported', 'imported_asset',
            'discovered_at', 'raw_data'
        ]
        read_only_fields = ['id', 'discovered_at']


class DiscoveryTaskSerializer(serializers.ModelSerializer):
    """发现任务序列化器"""
    found_devices = serializers.SerializerMethodField()
    progress = serializers.SerializerMethodField()

    class Meta:
        model = DiscoveryTask
        fields = [
            'id', 'name', 'description', 'scan_type',
            'target_ranges', 'ports', 'timeout', 'snmp_community',
            'status', 'total_ips', 'scanned_ips', 'found_devices',
            'created_at', 'started_at', 'completed_at', 'created_by',
            'progress'
        ]
        read_only_fields = ['id', 'status', 'total_ips', 'scanned_ips',
                          'found_devices', 'created_at', 'started_at',
                          'completed_at', 'created_by']

    def get_found_devices(self, obj):
        return obj.devices.count()

    def get_progress(self, obj):
        if obj.total_ips == 0:
            return 0
        return int(obj.scanned_ips / obj.total_ips * 100)


class DiscoveryTaskCreateSerializer(serializers.ModelSerializer):
    """创建发现任务的序列化器"""

    class Meta:
        model = DiscoveryTask
        fields = [
            'name', 'description', 'scan_type',
            'target_ranges', 'ports', 'timeout', 'snmp_community',
            'customer', 'created_by'
        ]

    def validate_target_ranges(self, value):
        if not value:
            raise serializers.ValidationError('请指定扫描目标')
        if not isinstance(value, list):
            raise serializers.ValidationError('目标格式错误')
        return value

    def validate_ports(self, value):
        if value:
            if not isinstance(value, list):
                raise serializers.ValidationError('端口格式错误')
            if not all(isinstance(p, int) and 0 < p < 65536 for p in value):
                raise serializers.ValidationError('端口号必须在1-65535之间')
        return value


class TopologyNodeSerializer(serializers.ModelSerializer):
    """拓扑节点序列化器"""
    asset_name = serializers.CharField(source='asset.asset_name', read_only=True, default='')
    ip_address_str = serializers.IPAddressField(source='ip_address', read_only=True, allow_null=True)

    class Meta:
        model = TopologyNode
        fields = [
            'id', 'name', 'node_type', 'asset', 'asset_name',
            'discovered_device', 'ip_address', 'ip_address_str',
            'mac_address', 'location', 'device_type',
            'is_online', 'x_position', 'y_position',
            'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class TopologyEdgeSerializer(serializers.ModelSerializer):
    """拓扑连线序列化器"""
    source_name = serializers.CharField(source='source.name', read_only=True)
    target_name = serializers.CharField(source='target.name', read_only=True)

    class Meta:
        model = TopologyEdge
        fields = [
            'id', 'source', 'target', 'source_name', 'target_name',
            'edge_type', 'bandwidth', 'latency',
            'source_port', 'target_port',
            'description', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class TopologyGraphSerializer(serializers.Serializer):
    """拓扑图完整序列化器"""
    nodes = TopologyNodeSerializer(many=True)
    edges = TopologyEdgeSerializer(many=True)
