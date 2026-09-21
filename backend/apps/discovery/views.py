import threading
import json
import subprocess
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone

from .models import DiscoveryTask, DiscoveredDevice, TopologyNode, TopologyEdge
from .serializers import (
    DiscoveryTaskSerializer, DiscoveryTaskCreateSerializer,
    DiscoveredDeviceSerializer, TopologyNodeSerializer,
    TopologyEdgeSerializer, TopologyGraphSerializer
)
from . import network_scanner


class DiscoveryTaskViewSet(viewsets.ModelViewSet):
    """网络发现任务视图集"""

    queryset = DiscoveryTask.objects.all()
    serializer_class = DiscoveryTaskSerializer

    def get_serializer_class(self):
        if self.action == 'create':
            return DiscoveryTaskCreateSerializer
        return DiscoveryTaskSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        task_status = self.request.query_params.get('status')
        if task_status:
            queryset = queryset.filter(status=task_status)
        scan_type = self.request.query_params.get('scan_type')
        if scan_type:
            queryset = queryset.filter(scan_type=scan_type)
        return queryset

    def create(self, request, *args, **kwargs):
        """创建发现任务"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        task = serializer.save()
        return Response(
            DiscoveryTaskSerializer(task).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """启动扫描任务"""
        task = self.get_object()

        if task.status == 'running':
            return Response({'success': False, 'message': '任务已在执行中'})

        if task.status == 'completed':
            return Response({'success': False, 'message': '任务已完成，请创建新任务'})

        # 重置状态
        task.status = 'running'
        task.started_at = timezone.now()
        task.scanned_ips = 0
        task.found_devices = 0
        task.save()

        # 在后台线程执行扫描
        thread = threading.Thread(target=self._run_scan, args=(task.id,))
        thread.daemon = True
        thread.start()

        return Response({'success': True, 'message': '扫描已启动', 'task_id': task.id})

    def _run_scan(self, task_id):
        """后台执行扫描"""
        from django.db import close_old_connections

        try:
            task = DiscoveryTask.objects.get(id=task_id)
            task_obj = task

            # 解析所有目标IP
            all_ips = []
            for range_str in task.target_ranges:
                all_ips.extend(network_scanner.parse_ip_range(range_str))
            all_ips = list(set(all_ips))
            total = len(all_ips)

            task_obj.total_ips = total
            task_obj.save(update_fields=['total_ips'])
            close_old_connections()

            # 进度回调
            def progress_callback(scanned, total_ips, found):
                try:
                    task_obj.scanned_ips = scanned
                    task_obj.found_devices = found
                    task_obj.save(update_fields=['scanned_ips', 'found_devices'])
                    close_old_connections()
                except:
                    pass

            # 执行扫描
            devices = network_scanner.run_discovery(
                target_ranges=task.target_ranges,
                ports=task.ports if task.ports else None,
                scan_type=task.scan_type,
                timeout=task.timeout,
                snmp_community=task.snmp_community,
                progress_callback=progress_callback
            )

            # 保存发现的设备
            for dev in devices:
                DiscoveredDevice.objects.create(
                    task=task_obj,
                    customer=task_obj.customer,
                    ip_address=dev['ip'],
                    mac_address=dev.get('mac', ''),
                    hostname=dev.get('hostname', ''),
                    device_type=dev.get('device_type', 'unknown'),
                    os_type=dev.get('os_type', 'unknown'),
                    vendor=dev.get('vendor', 'Unknown'),
                    open_ports=dev.get('open_ports', []),
                    response_time=dev.get('response_time'),
                    snmp_sysDescr=dev.get('snmp_data', {}).get('sysDescr', ''),
                    ssh_banner=dev.get('ssh_banner', ''),
                    http_title=dev.get('http_title', ''),
                    is_online=dev.get('is_online', True),
                    raw_data=dev
                )

            # 更新任务状态
            task_obj.status = 'completed'
            task_obj.completed_at = timezone.now()
            task_obj.found_devices = len(devices)
            task_obj.scanned_ips = total
            task_obj.save(update_fields=['status', 'completed_at', 'found_devices', 'scanned_ips'])

        except Exception as e:
            try:
                task_obj.status = 'failed'
                task_obj.completed_at = timezone.now()
                task_obj.save(update_fields=['status', 'completed_at'])
            except:
                pass

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """取消扫描任务"""
        task = self.get_object()
        if task.status == 'running':
            task.status = 'cancelled'
            task.completed_at = timezone.now()
            task.save()
            return Response({'success': True, 'message': '任务已取消'})
        return Response({'success': False, 'message': '任务不在执行中'})

    @action(detail=True, methods=['get'])
    def devices(self, request, pk=None):
        """获取任务发现的设备列表，附带资产库比对结果"""
        task = self.get_object()
        devices = task.devices.all()

        # 获取已有资产IP映射
        from apps.assets.models import Asset
        existing_ip_map = {
            str(a.ip_address): {'id': a.id, 'code': a.asset_code, 'name': a.asset_name, 'status': a.status}
            for a in Asset.objects.filter(customer=task.customer, ip_address__isnull=False)
        }

        result = []
        for dev in devices:
            ip = str(dev.ip_address)
            is_known = ip in existing_ip_map
            item = {
                'id': dev.id,
                'ip_address': ip,
                'mac_address': dev.mac_address,
                'hostname': dev.hostname,
                'device_type': dev.device_type,
                'os_type': dev.os_type,
                'vendor': dev.vendor,
                'open_ports': dev.open_ports,
                'response_time': dev.response_time,
                'is_online': dev.is_online,
                'is_imported': dev.is_imported,
                'imported_asset': dev.imported_asset_id,
                # 比对结果
                'is_known': is_known,
                'asset_id': existing_ip_map[ip]['id'] if is_known else None,
                'asset_code': existing_ip_map[ip]['code'] if is_known else None,
                'asset_name': existing_ip_map[ip]['name'] if is_known else None,
            }
            result.append(item)

        return Response({
            'success': True,
            'count': len(result),
            'devices': result
        })

    @action(detail=False, methods=['get'])
    def quick_scan(self, request):
        """快速扫描（同步），用于测试"""
        target = request.query_params.get('target', '192.168.1.1-10')
        scan_type = request.query_params.get('scan_type', 'full')
        timeout = int(request.query_params.get('timeout', 3))

        devices = network_scanner.run_discovery(
            target_ranges=[target],
            scan_type=scan_type,
            timeout=timeout
        )

        return Response({
            'success': True,
            'target': target,
            'found': len(devices),
            'devices': devices
        })

    @action(detail=False, methods=['get'])
    def ports_scan(self, request):
        """端口扫描"""
        ip = request.query_params.get('ip', '')
        ports_str = request.query_params.get('ports', '')  # 逗号分隔

        if not ip:
            return Response({'success': False, 'message': '请指定IP'})

        ports = []
        if ports_str:
            try:
                ports = [int(p.strip()) for p in ports_str.split(',') if p.strip().isdigit()]
            except:
                pass

        timeout = int(request.query_params.get('timeout', 3))
        open_ports = network_scanner.scan_ports(ip, ports or network_scanner.DEFAULT_PORTS, timeout=timeout)

        return Response({
            'success': True,
            'ip': ip,
            'open_ports': open_ports,
            'services': {p: network_scanner.get_service_name(p) for p in open_ports}
        })

    @action(detail=False, methods=['get'])
    def analyze_subnets(self, request):
        """分析已有资产的IP，推断所在网段"""
        customer_id = request.query_params.get('customer')
        if not customer_id:
            return Response({'success': False, 'message': '请指定客户ID'}, status=400)

        from apps.assets.models import Asset

        # 获取该客户所有有IP的资产
        assets = Asset.objects.filter(customer_id=customer_id, ip_address__isnull=False)

        subnets = {}
        asset_ips = []

        for asset in assets:
            ip = str(asset.ip_address)
            asset_ips.append({
                'ip': ip,
                'name': asset.asset_name,
                'code': asset.asset_code,
                'asset_id': asset.id,
                'status': asset.status,
                'online': asset.online,
            })

            # 推断网段 /24
            parts = ip.split('.')
            if len(parts) == 4:
                subnet = f'{parts[0]}.{parts[1]}.{parts[2]}.0/24'
                if subnet not in subnets:
                    subnets[subnet] = {
                        'subnet': subnet,
                        'asset_count': 0,
                        'asset_ips': [],
                        'inferred_assets': []
                    }
                subnets[subnet]['asset_count'] += 1
                subnets[subnet]['asset_ips'].append(ip)
                subnets[subnet]['inferred_assets'].append({
                    'ip': ip,
                    'name': asset.asset_name,
                    'id': asset.id
                })

        # 同时分析已发现的设备中的网段
        discovered = DiscoveredDevice.objects.filter(
            customer_id=customer_id, is_online=True
        )
        for dev in discovered:
            ip = str(dev.ip_address)
            parts = ip.split('.')
            if len(parts) == 4:
                subnet = f'{parts[0]}.{parts[1]}.{parts[2]}.0/24'
                if subnet not in subnets:
                    subnets[subnet] = {
                        'subnet': subnet,
                        'asset_count': 0,
                        'asset_ips': [],
                        'inferred_assets': [],
                        'from_discovery': True
                    }
                # 不重复计数已知的

        subnet_list = sorted(subnets.values(), key=lambda x: x['subnet'])

        return Response({
            'success': True,
            'subnets': subnet_list,
            'total_assets': len(asset_ips),
            'total_subnets': len(subnet_list),
            'all_asset_ips': asset_ips
        })

    @action(detail=False, methods=['post'])
    def smart_scan(self, request):
        """智能扫描：创建后台任务，扫描指定网段，对比资产库"""
        customer_id = request.data.get('customer_id') or request.query_params.get('customer')
        subnets = request.data.get('subnets', [])  # 如 ["192.168.1.0/24"]
        scan_type = request.data.get('scan_type', 'ping')
        timeout = int(request.data.get('timeout', 3))

        if not customer_id:
            return Response({'success': False, 'message': '请指定客户ID'}, status=400)
        if not subnets:
            return Response({'success': False, 'message': '请指定要扫描的网段'}, status=400)

        # 创建发现任务（作为智能扫描的载体）
        from apps.customers.models import Customer
        customer = Customer.objects.get(id=customer_id)

        task = DiscoveryTask.objects.create(
            customer=customer,
            name=f'智能扫描-{timezone.now().strftime("%m%d %H:%M")}',
            description=f'智能扫描网段: {", ".join(subnets)}',
            scan_type=scan_type,
            target_ranges=subnets,
            timeout=timeout,
            status='running',
            started_at=timezone.now()
        )

        # 在后台执行扫描
        thread = threading.Thread(target=self._run_smart_scan, args=(task.id, customer_id, scan_type, timeout))
        thread.daemon = True
        thread.start()

        return Response({
            'success': True,
            'task_id': task.id,
            'message': '智能扫描已启动，请稍后查询结果'
        })

    def _run_smart_scan(self, task_id, customer_id, scan_type, timeout):
        """后台执行智能扫描"""
        from django.db import close_old_connections
        from apps.assets.models import Asset

        try:
            task = DiscoveryTask.objects.get(id=task_id)

            # 解析所有IP
            all_ips = []
            for r in task.target_ranges:
                all_ips.extend(network_scanner.parse_ip_range(r))
            all_ips = list(set(all_ips))
            task.total_ips = len(all_ips)
            task.save(update_fields=['total_ips'])
            close_old_connections()

            # 获取已有资产IP列表
            existing_assets = Asset.objects.filter(customer_id=customer_id, ip_address__isnull=False)
            existing_ip_map = {
                str(a.ip_address): {'id': a.id, 'code': a.asset_code, 'name': a.asset_name, 'status': a.status}
                for a in existing_assets
            }

            # 进度回调
            def progress_callback(scanned, total, found):
                try:
                    task.scanned_ips = scanned
                    task.found_devices = found
                    task.save(update_fields=['scanned_ips', 'found_devices'])
                    close_old_connections()
                except:
                    pass

            # 执行扫描
            devices = network_scanner.run_discovery(
                target_ranges=task.target_ranges,
                scan_type=scan_type,
                timeout=timeout,
                progress_callback=progress_callback
            )

            # 对比资产库并保存
            known_devices = []
            new_devices = []

            for dev in devices:
                ip = dev['ip']
                is_known = ip in existing_ip_map

                device = DiscoveredDevice.objects.create(
                    task=task,
                    customer_id=customer_id,
                    ip_address=ip,
                    mac_address=dev.get('mac', ''),
                    hostname=dev.get('hostname', ''),
                    device_type=dev.get('device_type', 'unknown'),
                    os_type=dev.get('os_type', 'unknown'),
                    vendor=dev.get('vendor', 'Unknown'),
                    open_ports=dev.get('open_ports', []),
                    response_time=dev.get('response_time'),
                    is_online=dev.get('is_online', True),
                    raw_data=dev
                )

                result = {
                    'id': device.id,
                    'ip': ip,
                    'mac': dev.get('mac', ''),
                    'hostname': dev.get('hostname', ''),
                    'device_type': dev.get('device_type', 'unknown'),
                    'os_type': dev.get('os_type', 'unknown'),
                    'vendor': dev.get('vendor', 'Unknown'),
                    'open_ports': dev.get('open_ports', []),
                    'response_time': dev.get('response_time'),
                    'is_online': dev.get('is_online', True),
                    'is_known': is_known,
                    'asset_id': None,
                    'asset_code': None,
                    'asset_name': None,
                }

                if is_known:
                    result['asset_id'] = existing_ip_map[ip]['id']
                    result['asset_code'] = existing_ip_map[ip]['code']
                    result['asset_name'] = existing_ip_map[ip]['name']
                    result['asset_status'] = existing_ip_map[ip]['status']
                    known_devices.append(result)
                else:
                    new_devices.append(result)

            # 保存结果到task描述
            task.status = 'completed'
            task.completed_at = timezone.now()
            task.found_devices = len(devices)
            task.scanned_ips = task.total_ips
            task.description = json.dumps({
                'known_count': len(known_devices),
                'new_count': len(new_devices),
                'known_devices': known_devices,
                'new_devices': new_devices
            }, ensure_ascii=False)
            task.save()

        except Exception as e:
            try:
                task.status = 'failed'
                task.completed_at = timezone.now()
                task.description = f'扫描失败: {str(e)}'
                task.save()
            except:
                pass

    @action(detail=True, methods=['get'])
    def smart_scan_result(self, request, pk=None):
        """查询智能扫描结果"""
        task = self.get_object()

        if task.status == 'running':
            return Response({
                'status': 'running',
                'scanned_ips': task.scanned_ips,
                'total_ips': task.total_ips,
                'found_devices': task.found_devices,
                'progress': int(task.scanned_ips / task.total_ips * 100) if task.total_ips > 0 else 0
            })

        if task.status != 'completed':
            return Response({
                'status': task.status,
                'message': task.description
            })

        # 解析保存的结果
        try:
            result_data = json.loads(task.description)
            return Response({
                'status': 'completed',
                'scanned_subnets': task.target_ranges,
                'total_found': task.found_devices,
                'known_count': result_data.get('known_count', 0),
                'new_count': result_data.get('new_count', 0),
                'known_devices': result_data.get('known_devices', []),
                'new_devices': result_data.get('new_devices', []),
                'all_devices': result_data.get('known_devices', []) + result_data.get('new_devices', [])
            })
        except:
            # 兼容旧格式：直接从devices关系获取
            devices = task.devices.all()
            from apps.assets.models import Asset
            existing_ips = set(str(a.ip_address) for a in Asset.objects.filter(customer=task.customer))

            known = []
            new = []
            for d in devices:
                is_known = str(d.ip_address) in existing_ips
                item = {
                    'id': d.id, 'ip': str(d.ip_address), 'mac': d.mac_address,
                    'hostname': d.hostname, 'device_type': d.device_type,
                    'os_type': d.os_type, 'vendor': d.vendor,
                    'open_ports': d.open_ports, 'response_time': d.response_time,
                    'is_online': d.is_online, 'is_known': is_known
                }
                if is_known:
                    known.append(item)
                else:
                    new.append(item)

            return Response({
                'status': 'completed',
                'scanned_subnets': task.target_ranges,
                'total_found': devices.count(),
                'known_count': len(known),
                'new_count': len(new),
                'known_devices': known,
                'new_devices': new,
                'all_devices': known + new
            })

    @action(detail=False, methods=['post'])
    def import_new_devices(self, request):
        """批量导入新发现的设备为资产"""
        customer_id = request.data.get('customer_id')
        devices = request.data.get('devices', [])  # 设备列表

        if not customer_id:
            return Response({'success': False, 'message': '请指定客户ID'}, status=400)

        if not devices:
            return Response({'success': False, 'message': '没有要导入的设备'}, status=400)

        from apps.assets.models import Asset, AssetType
        import uuid

        # 获取或创建默认服务器类型
        asset_type, _ = AssetType.objects.get_or_create(
            customer_id=customer_id,
            type_code='SERVER',
            defaults={'type_name': '服务器', 'is_system': True}
        )

        imported = []
        skipped = []

        for dev in devices:
            ip = dev.get('ip')
            if not ip:
                continue

            # 检查是否已存在
            if Asset.objects.filter(customer_id=customer_id, ip_address=ip).exists():
                skipped.append(ip)
                continue

            asset_code = f'DISC-{ip.replace(".", "-")}-{uuid.uuid4().hex[:6]}'

            asset = Asset.objects.create(
                customer_id=customer_id,
                asset_type=asset_type,
                asset_code=asset_code,
                asset_name=dev.get('hostname') or f'Device-{ip}',
                ip_address=ip,
                status='ACTIVE' if dev.get('is_online') else 'INACTIVE',
                vendor=dev.get('vendor', ''),
                device_type=dev.get('device_type', ''),
                description=f"智能发现导入 | MAC: {dev.get('mac', '')} | 类型: {dev.get('device_type', '')}"
            )

            imported.append({
                'ip': ip,
                'asset_id': asset.id,
                'asset_code': asset.asset_code,
                'asset_name': asset.asset_name
            })

        return Response({
            'success': True,
            'imported_count': len(imported),
            'skipped_count': len(skipped),
            'imported': imported,
            'skipped': skipped
        })


class DiscoveredDeviceViewSet(viewsets.ReadOnlyModelViewSet):
    """发现的设备视图集（只读）"""

    queryset = DiscoveredDevice.objects.all()
    serializer_class = DiscoveredDeviceSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        task_id = self.request.query_params.get('task')
        if task_id:
            queryset = queryset.filter(task_id=task_id)
        device_type = self.request.query_params.get('device_type')
        if device_type:
            queryset = queryset.filter(device_type=device_type)
        is_imported = self.request.query_params.get('is_imported')
        if is_imported is not None:
            queryset = queryset.filter(is_imported=is_imported.lower() == 'true')
        return queryset

    @action(detail=True, methods=['post'])
    def import_asset(self, request, pk=None):
        """将发现设备导入为资产"""
        device = self.get_object()

        if device.is_imported:
            return Response({'success': False, 'message': '该设备已导入'})

        from apps.assets.models import Asset, AssetType

        # 获取或创建默认服务器类型
        asset_type, _ = AssetType.objects.get_or_create(
            customer=device.customer,
            type_code='SERVER',
            defaults={
                'type_name': '服务器',
                'is_system': True
            }
        )

        # 生成资产编号
        import uuid
        asset_code = f'DISC-{device.ip_address.replace(".", "-")}-{uuid.uuid4().hex[:6]}'

        # 创建资产
        asset = Asset.objects.create(
            customer=device.customer,
            asset_type=asset_type,
            asset_code=asset_code,
            asset_name=device.hostname or f'Device-{device.ip_address}',
            ip_address=device.ip_address,
            location=device.snmp_sysLocation or '',
            status='ACTIVE' if device.is_online else 'INACTIVE',
            protocol=self._guess_protocol(device),
            vendor=device.vendor,
            description=f"自动发现导入 | MAC: {device.mac_address} | OS: {device.os_type}"
        )

        # 标记为已导入
        device.is_imported = True
        device.imported_asset = asset
        device.save()

        return Response({
            'success': True,
            'message': '资产创建成功',
            'asset_id': asset.id,
            'asset_code': asset.asset_code
        })

    def _guess_protocol(self, device):
        """根据开放端口猜测协议"""
        ports = device.open_ports
        if 3306 in ports:
            return 'mysql'
        if 5432 in ports:
            return 'postgresql'
        if 1433 in ports:
            return 'mssql'
        if 1521 in ports:
            return 'oracle'
        if 22 in ports:
            return 'ssh'
        if 161 in ports:
            return 'snmp'
        return 'ping'


class TopologyViewSet(viewsets.ModelViewSet):
    """网络拓扑视图集"""

    queryset = TopologyNode.objects.all()
    serializer_class = TopologyNodeSerializer

    http_method_names = ['get', 'post', 'delete', 'head']

    def get_queryset(self):
        queryset = super().get_queryset()
        customer_id = self.request.query_params.get('customer')
        if customer_id:
            queryset = queryset.filter(customer_id=customer_id)
        return queryset

    @action(detail=False, methods=['get'])
    def graph(self, request):
        """获取拓扑图完整数据"""
        customer_id = request.query_params.get('customer')
        if not customer_id:
            return Response({'success': False, 'message': '请指定客户ID'})

        nodes = TopologyNode.objects.filter(customer_id=customer_id)
        node_ids = [n.id for n in nodes]
        edges = TopologyEdge.objects.filter(customer_id=customer_id, source_id__in=node_ids, target_id__in=node_ids)

        return Response({
            'success': True,
            'nodes': TopologyNodeSerializer(nodes, many=True).data,
            'edges': TopologyEdgeSerializer(edges, many=True).data
        })

    @action(detail=False, methods=['post'])
    def build_from_discovery(self, request):
        """从发现任务构建拓扑，同时包含同网段的已有资产"""
        task_id = request.data.get('task_id')
        customer_id = request.data.get('customer_id')

        if not task_id:
            return Response({'success': False, 'message': '请指定任务ID'})

        task = DiscoveryTask.objects.get(id=task_id)
        devices = task.devices.filter(is_online=True)

        # 推断所有涉及的网段
        subnets = set()
        for device in devices:
            ip = str(device.ip_address)
            parts = ip.split('.')
            if len(parts) == 4:
                subnets.add('.'.join(parts[:3]) + '.0/24')

        # 收集这些网段内已有的资产
        from apps.assets.models import Asset
        existing_assets_by_ip = {}
        if subnets:
            for subnet in subnets:
                base = subnet.split('.0/24')[0]
                for asset in Asset.objects.filter(customer=task.customer, ip_address__isnull=False):
                    asset_ip = str(asset.ip_address)
                    if asset_ip.rsplit('.', 1)[0] == base:
                        existing_assets_by_ip[asset_ip] = asset

        created_nodes = []
        all_node_ips = set()

        # 处理发现设备
        for device in devices:
            ip = str(device.ip_address)
            all_node_ips.add(ip)
            node, created = TopologyNode.objects.update_or_create(
                customer=task.customer,
                ip_address=device.ip_address,
                defaults={
                    'name': device.hostname or f'{device.ip_address}',
                    'node_type': 'asset',
                    'asset': existing_assets_by_ip.get(ip),
                    'discovered_device': device,
                    'mac_address': device.mac_address,
                    'device_type': device.device_type,
                    'is_online': device.is_online,
                    'metadata': {**(device.raw_data or {}), 'source': 'discovery'}
                }
            )
            created_nodes.append(node)

        # 处理同网段已有资产（不在发现列表中的）
        for ip, asset in existing_assets_by_ip.items():
            if ip in all_node_ips:
                continue
            node, created = TopologyNode.objects.update_or_create(
                customer=task.customer,
                ip_address=ip,
                defaults={
                    'name': asset.asset_name,
                    'node_type': 'asset',
                    'asset': asset,
                    'discovered_device': None,
                    'device_type': 'server',
                    'is_online': asset.online,
                    'metadata': {'source': 'asset', 'asset_id': asset.id, 'asset_code': asset.asset_code}
                }
            )
            created_nodes.append(node)

        # 自动生成连线（基于同一网段）
        self._generate_edges(created_nodes, task.customer)

        return Response({
            'success': True,
            'message': f'拓扑已构建，共 {len(created_nodes)} 个节点（包含 {len(existing_assets_by_ip)} 个已有资产）',
            'node_count': len(created_nodes),
            'discovered_count': devices.count(),
            'existing_count': len(existing_assets_by_ip)
        })

    def _generate_edges(self, nodes, customer):
        """基于同一网段生成连线"""
        # 按网段分组
        subnets = {}
        for node in nodes:
            if node.ip_address:
                ip = str(node.ip_address)
                subnet = '.'.join(ip.split('.')[:3]) + '.0/24'
                if subnet not in subnets:
                    subnets[subnet] = []
                subnets[subnet].append(node)

        # 在同一网段的节点之间创建全互联拓扑（星型，以第一个节点为中心）
        for subnet, subnet_nodes in subnets.items():
            if len(subnet_nodes) > 1:
                center = subnet_nodes[0]
                for peripheral in subnet_nodes[1:]:
                    # 检查连线是否已存在
                    exists = TopologyEdge.objects.filter(
                        customer=customer,
                        source=center,
                        target=peripheral
                    ).exists()
                    if not exists:
                        TopologyEdge.objects.create(
                            customer=customer,
                            source=center,
                            target=peripheral,
                            edge_type='wired',
                            description=f'同一网段 {subnet}'
                        )

    @action(detail=True, methods=['post'])
    def update_position(self, request, pk=None):
        """更新节点位置"""
        node = self.get_object()
        x = request.data.get('x')
        y = request.data.get('y')
        if x is not None:
            node.x_position = x
        if y is not None:
            node.y_position = y
        node.save()
        return Response({'success': True})

    @action(detail=False, methods=['post'])
    def add_edge(self, request):
        """添加连线"""
        serializer = TopologyEdgeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'success': True, 'edge': serializer.data}, status=201)
        return Response({'success': False, 'errors': serializer.errors}, status=400)

    @action(detail=False, methods=['delete'])
    def remove_edge(self, request):
        """删除连线"""
        edge_id = request.data.get('edge_id')
        if not edge_id:
            return Response({'success': False, 'message': '请指定edge_id'})
        try:
            edge = TopologyEdge.objects.get(id=edge_id)
            edge.delete()
            return Response({'success': True})
        except TopologyEdge.DoesNotExist:
            return Response({'success': False, 'message': '连线不存在'})

    @action(detail=False, methods=['get'])
    def export_graph(self, request):
        """导出拓扑图数据（用于可视化）"""
        customer_id = request.query_params.get('customer')
        if not customer_id:
            return Response({'success': False, 'message': '请指定客户ID'})

        nodes = TopologyNode.objects.filter(customer_id=customer_id)
        edges = TopologyEdge.objects.filter(customer_id=customer_id)

        # D3.js兼容格式
        graph = {
            'nodes': [
                {
                    'id': node.id,
                    'name': node.name,
                    'type': node.node_type,
                    'ip': str(node.ip_address) if node.ip_address else '',
                    'deviceType': node.device_type,
                    'online': node.is_online,
                    'x': node.x_position,
                    'y': node.y_position,
                    'metadata': node.metadata
                }
                for node in nodes
            ],
            'links': [
                {
                    'id': edge.id,
                    'source': edge.source_id,
                    'target': edge.target_id,
                    'type': edge.edge_type,
                    'bandwidth': edge.bandwidth,
                    'sourcePort': edge.source_port,
                    'targetPort': edge.target_port
                }
                for edge in edges
            ]
        }

        return Response(graph)
