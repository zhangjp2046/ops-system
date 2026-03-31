#!/usr/bin/env python3
"""
巡检执行器
执行各类巡检任务：SNMP巡检、数据库巡检等
"""

import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.inspection.models import Inspection, InspectionItem, InspectionTemplate
from apps.assets.models import Asset, AssetData
from apps.monitoring.models import MonitoringTask, MonitoringResult


class BaseInspectionExecutor:
    """巡检执行器基类"""
    
    def __init__(self, inspection):
        self.inspection = inspection
        self.items = []
    
    def execute(self):
        """执行巡检"""
        raise NotImplementedError
    
    def add_item(self, item_code, item_name, category, result, severity='OK', 
                 actual_value='', expected_value='', message='', details=None):
        """添加巡检项目"""
        self.items.append({
            'inspection': self.inspection,
            'item_code': item_code,
            'item_name': item_name,
            'category': category,
            'result': result,
            'severity': severity,
            'actual_value': str(actual_value),
            'expected_value': str(expected_value),
            'message': message,
            'details': details or {}
        })
    
    def check_threshold(self, value, threshold_config, item_type='max'):
        """检查阈值"""
        if not threshold_config:
            return 'PASS'
        
        try:
            val = float(value)
            
            if 'max' in threshold_config and val > threshold_config['max']:
                return 'FAIL'
            if 'min' in threshold_config and val < threshold_config['min']:
                return 'FAIL'
            if 'max' in threshold_config and val > threshold_config['max'] * 0.8:
                return 'WARNING'
            
            return 'PASS'
        except (ValueError, TypeError):
            return 'WARNING'


class SNMPInspectionExecutor(BaseInspectionExecutor):
    """SNMP巡检执行器"""
    
    def execute(self):
        """执行SNMP巡检"""
        asset = self.inspection.asset
        if not asset:
            self.add_item('ASSET', '资产信息', 'asset', 'FAIL', 
                          severity='CRITICAL', message='未指定巡检资产')
            return
        
        # 获取资产IP地址
        ip_address = self._get_asset_field(asset, 'ip_address') or asset.location
        
        # 执行各项巡检
        self._check_snmp_connectivity(ip_address)
        self._check_cpu_usage()
        self._check_memory_usage()
        self._check_disk_usage()
        self._check_network_interfaces()
        self._check_system_uptime()
        self._check_device_info()
        
        return self.items
    
    def _get_asset_field(self, asset, field_code):
        """获取资产字段值"""
        try:
            data = AssetData.objects.filter(
                asset=asset,
                field__field_code=field_code
            ).first()
            if data:
                return data.get_value()
        except:
            pass
        return None
    
    def _check_snmp_connectivity(self, ip_address):
        """检查SNMP连通性"""
        try:
            from apps.monitoring.snmp_client import SNMPClient
            
            client = SNMPClient(host=ip_address, community='public', timeout=3, retries=1)
            result = client.get('1.3.6.1.2.1.1.1.0')
            
            if result:
                self.add_item(
                    'SNMP_CONNECT', 'SNMP连接', 'snmp',
                    'PASS', severity='OK',
                    actual_value='可达',
                    expected_value='可达',
                    message='SNMP连接正常'
                )
            else:
                self.add_item(
                    'SNMP_CONNECT', 'SNMP连接', 'snmp',
                    'FAIL', severity='CRITICAL',
                    actual_value='无响应',
                    expected_value='正常响应',
                    message='SNMP设备无响应'
                )
        except Exception as e:
            self.add_item(
                'SNMP_CONNECT', 'SNMP连接', 'snmp',
                'FAIL', severity='CRITICAL',
                actual_value=str(e),
                expected_value='正常响应',
                message=f'SNMP连接失败: {str(e)}'
            )
    
    def _check_cpu_usage(self):
        """检查CPU使用率"""
        # 模拟数据，实际应该从SNMP获取
        cpu_usage = 25
        
        threshold = {'max': 80}
        result = self.check_threshold(cpu_usage, threshold)
        
        severity = 'OK'
        if result == 'FAIL':
            severity = 'CRITICAL'
        elif result == 'WARNING':
            severity = 'WARNING'
        
        self.add_item(
            'CPU_USAGE', 'CPU使用率', 'cpu',
            result, severity=severity,
            actual_value=f'{cpu_usage}%',
            expected_value='< 80%',
            message=f'CPU使用率{result}',
            details={'threshold': threshold}
        )
    
    def _check_memory_usage(self):
        """检查内存使用率"""
        # 模拟数据
        memory_usage = 88
        
        threshold = {'max': 85}
        result = self.check_threshold(memory_usage, threshold)
        
        severity = 'OK'
        if result == 'FAIL':
            severity = 'CRITICAL'
        elif result == 'WARNING':
            severity = 'WARNING'
        
        self.add_item(
            'MEMORY_USAGE', '内存使用率', 'memory',
            result, severity=severity,
            actual_value=f'{memory_usage}%',
            expected_value='< 85%',
            message=f'内存使用率偏高' if result != 'PASS' else '内存使用率正常',
            details={'threshold': threshold}
        )
    
    def _check_disk_usage(self):
        """检查磁盘使用率"""
        # 模拟数据
        disk_usage = 75
        
        threshold = {'max': 90}
        result = self.check_threshold(disk_usage, threshold)
        
        severity = 'OK'
        if result == 'FAIL':
            severity = 'CRITICAL'
        elif result == 'WARNING':
            severity = 'WARNING'
        
        self.add_item(
            'DISK_USAGE', '磁盘使用率', 'disk',
            result, severity=severity,
            actual_value=f'{disk_usage}%',
            expected_value='< 90%',
            message=f'磁盘空间正常',
            details={'threshold': threshold}
        )
    
    def _check_network_interfaces(self):
        """检查网络接口状态"""
        # 模拟数据
        total_ports = 24
        up_ports = 22
        down_ports = 2
        
        if down_ports > 0:
            result = 'WARNING'
            severity = 'WARNING'
            message = f'发现{down_ports}个接口故障'
        else:
            result = 'PASS'
            severity = 'OK'
            message = '所有接口正常'
        
        self.add_item(
            'NETWORK_INTERFACE', '网络接口状态', 'network',
            result, severity=severity,
            actual_value=f'{up_ports}/{total_ports} UP, {down_ports} DOWN',
            expected_value='所有接口UP',
            message=message,
            details={'total': total_ports, 'up': up_ports, 'down': down_ports}
        )
    
    def _check_system_uptime(self):
        """检查系统运行时间"""
        # 模拟数据
        uptime_seconds = 2592000  # 30天
        
        threshold = {'min': 86400}  # 至少运行1天
        result = self.check_threshold(uptime_seconds, threshold)
        
        days = uptime_seconds // 86400
        hours = (uptime_seconds % 86400) // 3600
        
        self.add_item(
            'SYSTEM_UPTIME', '系统运行时间', 'system',
            result, severity='INFO',
            actual_value=f'{days}天{hours}小时',
            expected_value='> 1天',
            message=f'系统已连续运行{days}天',
            details={'uptime_seconds': uptime_seconds}
        )
    
    def _check_device_info(self):
        """获取设备信息"""
        asset = self.inspection.asset
        
        self.add_item(
            'DEVICE_INFO', '设备信息', 'info',
            'PASS', severity='INFO',
            actual_value=f'{asset.asset_name} ({asset.asset_code})',
            expected_value='',
            message=f'设备型号: {asset.vendor or "未知"}',
            details={'asset_code': asset.asset_code, 'location': asset.location}
        )


class DatabaseInspectionExecutor(BaseInspectionExecutor):
    """数据库巡检执行器"""
    
    # 支持的数据库类型
    DB_TYPES = ['MSSQL', 'ORACLE', 'MYSQL']
    
    def execute(self):
        """执行数据库巡检"""
        asset = self.inspection.asset
        if not asset:
            self.add_item('ASSET', '资产信息', 'asset', 'FAIL',
                          severity='CRITICAL', message='未指定巡检资产')
            return
        
        # 获取数据库类型
        db_type = self._get_asset_field(asset, 'database_type') or 'MYSQL'
        
        # 执行各项巡检
        self._check_connection()
        self._check_tablespace(db_type)
        self._check_buffer_hit_ratio(db_type)
        self._check_active_sessions()
        self._check_error_logs()
        self._check_backup_status()
        
        return self.items
    
    def _get_asset_field(self, asset, field_code):
        """获取资产字段值"""
        try:
            data = AssetData.objects.filter(
                asset=asset,
                field__field_code=field_code
            ).first()
            if data:
                return data.get_value()
        except:
            pass
        return None
    
    def _check_connection(self):
        """检查数据库连接"""
        # 模拟数据
        connection_count = 25
        max_connections = 100
        
        usage_percent = (connection_count / max_connections) * 100
        threshold = {'max': 80}
        result = self.check_threshold(usage_percent, threshold)
        
        severity = 'OK'
        if result == 'FAIL':
            severity = 'CRITICAL'
        elif result == 'WARNING':
            severity = 'WARNING'
        
        self.add_item(
            'DB_CONNECTION', '数据库连接', 'connection',
            result, severity=severity,
            actual_value=f'{connection_count}/{max_connections} ({usage_percent:.1f}%)',
            expected_value=f'< 80%',
            message='连接数正常' if result == 'PASS' else '连接数偏高',
            details={'current': connection_count, 'max': max_connections}
        )
    
    def _check_tablespace(self, db_type):
        """检查表空间使用率"""
        # 模拟数据
        usage_percent = 78
        
        threshold = {'max': 85}
        result = self.check_threshold(usage_percent, threshold)
        
        severity = 'OK'
        if result == 'FAIL':
            severity = 'CRITICAL'
        elif result == 'WARNING':
            severity = 'WARNING'
        
        self.add_item(
            'TABLESPACE_USAGE', f'{db_type}表空间使用率', 'storage',
            result, severity=severity,
            actual_value=f'{usage_percent}%',
            expected_value=f'< 85%',
            message='表空间使用正常' if result == 'PASS' else '表空间使用偏高',
            details={'db_type': db_type}
        )
    
    def _check_buffer_hit_ratio(self, db_type):
        """检查缓冲池命中率"""
        # 模拟数据
        hit_ratio = 98.5
        
        threshold = {'min': 95}
        result = self.check_threshold(hit_ratio, threshold)
        
        severity = 'OK'
        if result == 'FAIL':
            severity = 'CRITICAL'
        elif result == 'WARNING':
            severity = 'WARNING'
        
        self.add_item(
            'BUFFER_HIT_RATIO', '缓冲池命中率', 'performance',
            result, severity=severity,
            actual_value=f'{hit_ratio}%',
            expected_value='> 95%',
            message='命中率优秀' if result == 'PASS' else '命中率偏低',
            details={'hit_ratio': hit_ratio}
        )
    
    def _check_active_sessions(self):
        """检查活跃会话数"""
        # 模拟数据
        active_sessions = 12
        threshold = {'max': 50}
        result = self.check_threshold(active_sessions, threshold)
        
        self.add_item(
            'ACTIVE_SESSIONS', '活跃会话数', 'session',
            result, severity='OK',
            actual_value=str(active_sessions),
            expected_value='< 50',
            message='会话数正常'
        )
    
    def _check_error_logs(self):
        """检查错误日志"""
        # 模拟数据
        error_count = 2
        threshold = {'max': 10}
        result = self.check_threshold(error_count, threshold)
        
        severity = 'OK'
        if result == 'FAIL':
            severity = 'CRITICAL'
        elif result == 'WARNING':
            severity = 'WARNING'
        
        self.add_item(
            'ERROR_LOG', '错误日志', 'log',
            result, severity=severity,
            actual_value=f'{error_count}条/小时',
            expected_value='< 10条/小时',
            message='错误日志正常' if result == 'PASS' else '错误日志过多'
        )
    
    def _check_backup_status(self):
        """检查备份状态"""
        # 模拟数据
        last_backup_hours = 24
        backup_status = 'SUCCESS'
        
        severity = 'OK'
        result = 'PASS'
        message = '上次备份成功'
        
        if backup_status != 'SUCCESS':
            severity = 'CRITICAL'
            result = 'FAIL'
            message = '备份失败'
        elif last_backup_hours > 48:
            severity = 'WARNING'
            result = 'WARNING'
            message = '超过48小时未备份'
        
        self.add_item(
            'BACKUP_STATUS', '备份状态', 'backup',
            result, severity=severity,
            actual_value=f'{backup_status} ({last_backup_hours}小时前)',
            expected_value='SUCCESS',
            message=message
        )


def run_inspection(inspection_id):
    """运行巡检"""
    try:
        inspection = Inspection.objects.get(id=inspection_id)
    except Inspection.DoesNotExist:
        raise ValueError(f'巡检记录 {inspection_id} 不存在')
    
    # 创建执行器
    if inspection.inspection_type == 'SNMP':
        executor = SNMPInspectionExecutor(inspection)
    elif inspection.inspection_type == 'DATABASE':
        executor = DatabaseInspectionExecutor(inspection)
    else:
        raise ValueError(f'不支持的巡检类型: {inspection.inspection_type}')
    
    # 执行巡检
    items = executor.execute()
    
    # 保存巡检结果
    passed = 0
    warning = 0
    failed = 0
    
    for item_data in items:
        item = InspectionItem.objects.create(**item_data)
        
        if item.result == 'PASS':
            passed += 1
        elif item.result == 'WARNING':
            warning += 1
        elif item.result == 'FAIL':
            failed += 1
    
    # 更新巡检记录
    from django.utils import timezone
    inspection.total_items = len(items)
    inspection.passed_items = passed
    inspection.warning_items = warning
    inspection.failed_items = failed
    inspection.status = 'COMPLETED'
    inspection.completed_at = timezone.now()
    if inspection.started_at:
        duration = inspection.completed_at - inspection.started_at
        inspection.duration_ms = int(duration.total_seconds() * 1000)
    else:
        inspection.duration_ms = 0
    
    if failed > 0:
        inspection.summary = f'发现{failed}项异常，需要关注'
    elif warning > 0:
        inspection.summary = f'发现{warning}项警告，建议检查'
    else:
        inspection.summary = f'巡检通过，所有项目正常'
    
    inspection.save()
    
    return inspection


def run_auto_inspection(template_id, asset_id):
    """根据模板自动创建并执行巡检"""
    try:
        template = InspectionTemplate.objects.get(id=template_id)
    except InspectionTemplate.DoesNotExist:
        raise ValueError(f'巡检模板 {template_id} 不存在')
    
    try:
        asset = Asset.objects.get(id=asset_id)
    except Asset.DoesNotExist:
        raise ValueError(f'资产 {asset_id} 不存在')
    
    # 创建巡检记录
    inspection = Inspection.objects.create(
        name=f'{template.name} - {asset.asset_name}',
        description=template.description,
        inspection_type=template.inspection_type,
        customer=asset.customer,
        asset=asset,
        asset_type=template.asset_type,
        config={'template_id': template.id, 'items': template.items},
        status='RUNNING',
        started_at=datetime.now()
    )
    
    # 执行巡检
    return run_inspection(inspection.id)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='巡检执行器')
    parser.add_argument('--inspection-id', type=int, help='巡检记录ID')
    parser.add_argument('--template-id', type=int, help='模板ID')
    parser.add_argument('--asset-id', type=int, help='资产ID')
    
    args = parser.parse_args()
    
    if args.inspection_id:
        print(f'执行巡检 {args.inspection_id}...')
        result = run_inspection(args.inspection_id)
        print(f'巡检完成: {result.summary}')
    elif args.template_id and args.asset_id:
        print(f'根据模板{args.template_id}对资产{args.asset_id}执行巡检...')
        result = run_auto_inspection(args.template_id, args.asset_id)
        print(f'巡检完成: {result.summary}')
    else:
        parser.print_help()
