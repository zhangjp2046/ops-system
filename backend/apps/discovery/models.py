from django.db import models
from django.utils import timezone
from apps.customers.models import Customer


class DiscoveryTask(models.Model):
    """网络发现任务"""

    STATUS_CHOICES = [
        ('pending', '待执行'),
        ('running', '执行中'),
        ('completed', '已完成'),
        ('failed', '执行失败'),
        ('cancelled', '已取消'),
    ]

    SCAN_TYPE_CHOICES = [
        ('ping', 'Ping扫描'),
        ('tcp', 'TCP端口扫描'),
        ('snmp', 'SNMP扫描'),
        ('full', '完整扫描'),
        ('arp', 'ARP扫描'),
    ]

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE,
        related_name='discovery_tasks', verbose_name='客户'
    )

    name = models.CharField('任务名称', max_length=200)
    description = models.TextField('任务描述', blank=True)

    # 扫描配置
    scan_type = models.CharField('扫描类型', max_length=20, choices=SCAN_TYPE_CHOICES, default='full')
    target_ranges = models.JSONField('目标网段', default=list, help_text='如 ["192.168.1.1-254", "10.0.0.1-254"]')
    ports = models.JSONField('扫描端口', default=list, blank=True,
        help_text='如 [22, 23, 80, 443, 161, 3306, 5432]')
    timeout = models.IntegerField('超时时间(秒)', default=5)

    # SNMP配置
    snmp_community = models.CharField('SNMP Community', max_length=100, blank=True, default='public')

    # 状态
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')

    # 进度
    total_ips = models.IntegerField('总IP数', default=0)
    scanned_ips = models.IntegerField('已扫描IP数', default=0)
    found_devices = models.IntegerField('发现设备数', default=0)

    # 时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    started_at = models.DateTimeField('开始时间', null=True, blank=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    created_by = models.CharField('创建人', max_length=100, default='SYSTEM')

    class Meta:
        db_table = 'discovery_tasks'
        verbose_name = '网络发现任务'
        verbose_name_plural = '网络发现任务'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.get_status_display()})'


class DiscoveredDevice(models.Model):
    """发现的设备"""

    DEVICE_TYPE_CHOICES = [
        ('unknown', '未知'),
        ('server', '服务器'),
        ('router', '路由器'),
        ('switch', '交换机'),
        ('firewall', '防火墙'),
        ('loadbalancer', '负载均衡器'),
        ('storage', '存储设备'),
        ('printer', '打印机'),
        ('camera', '摄像头'),
        ('access_point', '无线AP'),
        ('workstation', '工作站'),
        ('virtual', '虚拟机'),
        ('cloud', '云资源'),
    ]

    OS_TYPE_CHOICES = [
        ('unknown', '未知'),
        ('linux', 'Linux'),
        ('windows', 'Windows'),
        ('cisco_ios', 'Cisco IOS'),
        ('hp_procurve', 'HP ProCurve'),
        ('juniper_junos', 'Juniper JunOS'),
        ('fortinet', 'Fortinet'),
        ('dell_os10', 'Dell OS10'),
        ('vmware_esxi', 'VMware ESXi'),
        ('hyperv', 'Hyper-V'),
        ('aix', 'AIX'),
        ('solaris', 'Solaris'),
        ('freebsd', 'FreeBSD'),
    ]

    task = models.ForeignKey(
        DiscoveryTask, on_delete=models.CASCADE,
        related_name='devices', verbose_name='发现任务'
    )
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE,
        related_name='discovered_devices', verbose_name='客户'
    )

    # 识别信息
    ip_address = models.GenericIPAddressField('IP地址')
    mac_address = models.CharField('MAC地址', max_length=17, blank=True, default='')
    hostname = models.CharField('主机名', max_length=200, blank=True, default='')

    # 设备分类
    device_type = models.CharField('设备类型', max_length=20, choices=DEVICE_TYPE_CHOICES, default='unknown')
    os_type = models.CharField('操作系统', max_length=20, choices=OS_TYPE_CHOICES, default='unknown')
    vendor = models.CharField('厂商', max_length=100, blank=True, default='')
    model = models.CharField('型号', max_length=100, blank=True, default='')

    # 网络信息
    open_ports = models.JSONField('开放端口', default=list)
    response_time = models.FloatField('响应时间(ms)', null=True, blank=True)

    # SNMP信息
    snmp_sysDescr = models.TextField('SNMP sysDescr', blank=True, default='')
    snmp_sysName = models.CharField('SNMP sysName', max_length=200, blank=True, default='')
    snmp_sysLocation = models.CharField('SNMP sysLocation', max_length=200, blank=True, default='')

    # SSH/Banner信息
    ssh_banner = models.TextField('SSH Banner', blank=True, default='')
    http_title = models.CharField('HTTP Title', max_length=200, blank=True, default='')

    # 在线状态
    is_online = models.BooleanField('是否在线', default=True)

    # 原始数据
    raw_data = models.JSONField('原始数据', default=dict)

    # 是否已导入为资产
    imported_asset = models.ForeignKey(
        'assets.Asset', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='discovery_records',
        verbose_name='导入的资产'
    )
    is_imported = models.BooleanField('是否已导入', default=False)

    # 时间
    discovered_at = models.DateTimeField('发现时间', auto_now_add=True)

    class Meta:
        db_table = 'discovered_devices'
        verbose_name = '发现的设备'
        verbose_name_plural = '发现的设备'
        ordering = ['ip_address']
        indexes = [
            models.Index(fields=['ip_address']),
            models.Index(fields=['customer', 'ip_address']),
        ]

    def __str__(self):
        return f'{self.ip_address} ({self.hostname or self.device_type})'


class TopologyNode(models.Model):
    """拓扑图节点"""

    NODE_TYPE_CHOICES = [
        ('asset', '资产'),
        ('subnet', '子网'),
        ('internet', '互联网'),
        ('cloud', '云'),
    ]

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE,
        related_name='topology_nodes', verbose_name='客户'
    )

    # 基本信息
    name = models.CharField('节点名称', max_length=200)
    node_type = models.CharField('节点类型', max_length=20, choices=NODE_TYPE_CHOICES, default='asset')

    # 关联资产（如果是asset类型）
    asset = models.ForeignKey(
        'assets.Asset', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='topology_nodes',
        verbose_name='关联资产'
    )
    discovered_device = models.ForeignKey(
        DiscoveredDevice, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='topology_nodes',
        verbose_name='关联发现设备'
    )

    # 位置
    ip_address = models.GenericIPAddressField('IP地址', null=True, blank=True)
    mac_address = models.CharField('MAC地址', max_length=17, blank=True, default='')
    location = models.CharField('位置', max_length=200, blank=True, default='')

    # 拓扑属性
    device_type = models.CharField('设备类型', max_length=20, default='unknown')
    is_online = models.BooleanField('是否在线', default=True)

    # 可视化属性
    x_position = models.FloatField('X坐标', null=True, blank=True)
    y_position = models.FloatField('Y坐标', null=True, blank=True)

    # 元数据
    metadata = models.JSONField('元数据', default=dict)

    # 时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    class Meta:
        db_table = 'topology_nodes'
        verbose_name = '拓扑节点'
        verbose_name_plural = '拓扑节点'
        ordering = ['node_type', 'name']

    def __str__(self):
        return f'{self.name} ({self.node_type})'


class TopologyEdge(models.Model):
    """拓扑图连线"""

    EDGE_TYPE_CHOICES = [
        ('wired', '有线'),
        ('wireless', '无线'),
        ('logical', '逻辑'),
        ('vlan', 'VLAN'),
    ]

    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE,
        related_name='topology_edges', verbose_name='客户'
    )

    # 节点关联
    source = models.ForeignKey(
        TopologyNode, on_delete=models.CASCADE,
        related_name='outgoing_edges', verbose_name='源节点'
    )
    target = models.ForeignKey(
        TopologyNode, on_delete=models.CASCADE,
        related_name='incoming_edges', verbose_name='目标节点'
    )

    # 连线属性
    edge_type = models.CharField('连线类型', max_length=20, choices=EDGE_TYPE_CHOICES, default='wired')
    bandwidth = models.CharField('带宽', max_length=50, blank=True, default='')
    latency = models.IntegerField('延迟(ms)', null=True, blank=True)

    # 端口信息
    source_port = models.CharField('源端口', max_length=50, blank=True, default='')
    target_port = models.CharField('目标端口', max_length=50, blank=True, default='')

    # 描述
    description = models.CharField('描述', max_length=200, blank=True, default='')

    # 元数据
    metadata = models.JSONField('元数据', default=dict)

    # 时间
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        db_table = 'topology_edges'
        verbose_name = '拓扑连线'
        verbose_name_plural = '拓扑连线'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.source.name} → {self.target.name}'
