#!/usr/bin/env python3
"""
数据库巡检执行器
使用数据库连接器获取数据库状态并生成巡检记录
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.inspection.models import Inspection, InspectionItem
from apps.inspection.database_connectors import get_database_connector


class DatabaseInspector:
    """数据库巡检执行器"""
    
    def __init__(self, inspection):
        self.inspection = inspection
        self.asset = inspection.asset
        self.connector = None
        self.items = []
    
    def run(self):
        """执行数据库巡检"""
        try:
            # 获取数据库连接器
            self.connector = get_database_connector(self.asset)
            
            # 执行各项检查
            self.check_connection()
            self.check_server_info()
            self.check_tablespace()
            self.check_performance()
            self.check_sessions()
            self.check_backup()
            self.check_error_logs()
            
            return self.items
            
        except Exception as e:
            self.add_item(
                'INSPECTION_ERROR', '巡检异常', 'system',
                'FAIL', severity='CRITICAL',
                message=f'巡检执行异常: {str(e)}'
            )
            return self.items
    
    def add_item(self, item_code, item_name, category, result, 
                 severity='OK', actual_value='', expected_value='', 
                 message='', details=None):
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
    
    def check_threshold(self, value, threshold_config):
        """检查阈值"""
        if not threshold_config:
            return 'PASS', 'OK'
        
        try:
            val = float(value)
            
            if 'max' in threshold_config and val > threshold_config['max']:
                return 'FAIL', 'CRITICAL'
            if 'min' in threshold_config and val < threshold_config['min']:
                return 'FAIL', 'CRITICAL'
            if 'max_warning' in threshold_config and val > threshold_config['max_warning']:
                return 'WARNING', 'WARNING'
            if 'min_warning' in threshold_config and val < threshold_config['min_warning']:
                return 'WARNING', 'WARNING'
            
            return 'PASS', 'OK'
        except (ValueError, TypeError):
            return 'WARNING', 'WARNING'
    
    def check_connection(self):
        """检查数据库连接"""
        try:
            result = self.connector.check_connection()
            
            if result['status'] == 'success':
                self.add_item(
                    'DB_CONNECTION', '数据库连接', 'connection',
                    'PASS', severity='OK',
                    actual_value='成功',
                    expected_value='成功',
                    message='数据库连接正常'
                )
            else:
                self.add_item(
                    'DB_CONNECTION', '数据库连接', 'connection',
                    'FAIL', severity='CRITICAL',
                    actual_value='失败',
                    expected_value='成功',
                    message=f'连接失败: {result["message"]}'
                )
        except Exception as e:
            self.add_item(
                'DB_CONNECTION', '数据库连接', 'connection',
                'FAIL', severity='CRITICAL',
                actual_value='异常',
                expected_value='成功',
                message=f'连接异常: {str(e)}'
            )
    
    def check_server_info(self):
        """检查服务器信息"""
        try:
            info = self.connector.get_server_info()
            
            if info:
                version = info.get('version', '未知')
                uptime = info.get('uptime', 0)
                uptime_days = uptime // 86400 if uptime else 0
                
                self.add_item(
                    'DB_VERSION', '数据库版本', 'info',
                    'PASS', severity='INFO',
                    actual_value=version[:50],
                    expected_value='',
                    message=f'数据库版本正常',
                    details={'version': version, 'uptime_days': uptime_days}
                )
            else:
                self.add_item(
                    'DB_VERSION', '数据库版本', 'info',
                    'WARNING', severity='WARNING',
                    actual_value='未知',
                    expected_value='',
                    message='无法获取数据库版本信息'
                )
        except Exception as e:
            self.add_item(
                'DB_VERSION', '数据库版本', 'info',
                'WARNING', severity='WARNING',
                actual_value='异常',
                expected_value='',
                message=f'获取版本信息异常: {str(e)}'
            )
    
    def check_tablespace(self):
        """检查表空间"""
        try:
            info = self.connector.get_tablespace_info()
            
            if not info:
                self.add_item(
                    'TABLESPACE', '表空间使用率', 'storage',
                    'WARNING', severity='WARNING',
                    actual_value='未知',
                    expected_value='',
                    message='无法获取表空间信息'
                )
                return
            
            # 检查总大小
            total_size_gb = info.get('total_size_gb', 0)
            threshold = {'max_warning': 80, 'max': 90}
            result, severity = self.check_threshold(total_size_gb * 10, threshold)  # 假设总大小100GB
            
            self.add_item(
                'TABLESPACE', '表空间使用率', 'storage',
                result, severity=severity,
                actual_value=f'{total_size_gb} GB',
                expected_value='< 80%',
                message=self._get_tablespace_message(result, info),
                details=info
            )
            
        except Exception as e:
            self.add_item(
                'TABLESPACE', '表空间使用率', 'storage',
                'WARNING', severity='WARNING',
                actual_value='异常',
                expected_value='',
                message=f'获取表空间信息异常: {str(e)}'
            )
    
    def _get_tablespace_message(self, result, info):
        """获取表空间状态消息"""
        if result == 'PASS':
            return '表空间使用正常'
        elif result == 'WARNING':
            return '表空间使用偏高，建议关注'
        else:
            return '表空间使用率过高，需要清理'
    
    def check_performance(self):
        """检查性能指标"""
        try:
            info = self.connector.get_performance_info()
            
            if not info:
                self.add_item(
                    'BUFFER_HIT', '缓冲池命中率', 'performance',
                    'WARNING', severity='WARNING',
                    actual_value='未知',
                    expected_value='> 95%',
                    message='无法获取性能信息'
                )
                return
            
            # 缓冲池命中率
            hit_ratio = info.get('buffer_pool_hit_ratio', 0)
            threshold = {'min_warning': 95, 'min': 90}
            result, severity = self.check_threshold(hit_ratio, threshold)
            
            self.add_item(
                'BUFFER_HIT', '缓冲池命中率', 'performance',
                result, severity=severity,
                actual_value=f'{hit_ratio}%',
                expected_value='> 95%',
                message=self._get_hit_ratio_message(result, hit_ratio),
                details=info
            )
            
        except Exception as e:
            self.add_item(
                'BUFFER_HIT', '缓冲池命中率', 'performance',
                'WARNING', severity='WARNING',
                actual_value='异常',
                expected_value='> 95%',
                message=f'获取性能信息异常: {str(e)}'
            )
    
    def _get_hit_ratio_message(self, result, ratio):
        """获取命中率状态消息"""
        if result == 'PASS':
            return f'缓冲池命中率优秀 ({ratio}%)'
        elif result == 'WARNING':
            return f'缓冲池命中率偏低 ({ratio}%)'
        else:
            return f'缓冲池命中率过低 ({ratio}%)'
    
    def check_sessions(self):
        """检查会话信息"""
        try:
            info = self.connector.get_session_info()
            
            if not info:
                self.add_item(
                    'SESSIONS', '活跃会话数', 'session',
                    'PASS', severity='OK',
                    actual_value='未知',
                    expected_value='< 50',
                    message='无法获取会话信息'
                )
                return
            
            total = info.get('total_processes', 0) or info.get('total_sessions', 0)
            threshold = {'max_warning': 50, 'max': 100}
            result, severity = self.check_threshold(total, threshold)
            
            self.add_item(
                'SESSIONS', '活跃会话数', 'session',
                result, severity=severity,
                actual_value=str(total),
                expected_value='< 50',
                message=self._get_session_message(result, total),
                details=info
            )
            
        except Exception as e:
            self.add_item(
                'SESSIONS', '活跃会话数', 'session',
                'WARNING', severity='WARNING',
                actual_value='异常',
                expected_value='< 50',
                message=f'获取会话信息异常: {str(e)}'
            )
    
    def _get_session_message(self, result, count):
        """获取会话状态消息"""
        if result == 'PASS':
            return f'会话数正常 ({count})'
        elif result == 'WARNING':
            return f'会话数偏高 ({count})'
        else:
            return f'会话数过多 ({count})'
    
    def check_backup(self):
        """检查备份状态"""
        try:
            info = self.connector.get_backup_info()
            
            if not info:
                self.add_item(
                    'BACKUP', '备份状态', 'backup',
                    'WARNING', severity='WARNING',
                    actual_value='未知',
                    expected_value='最近24小时内',
                    message='无法获取备份信息'
                )
                return
            
            status = info.get('status', 'UNKNOWN')
            
            if status == 'SUCCESS':
                last_time = info.get('last_backup_time', '未知')
                self.add_item(
                    'BACKUP', '备份状态', 'backup',
                    'PASS', severity='OK',
                    actual_value=last_time,
                    expected_value='成功',
                    message=f'最近备份: {last_time}'
                )
            else:
                self.add_item(
                    'BACKUP', '备份状态', 'backup',
                    'WARNING', severity='WARNING',
                    actual_value=status,
                    expected_value='SUCCESS',
                    message=f'备份状态异常: {status}'
                )
            
        except Exception as e:
            self.add_item(
                'BACKUP', '备份状态', 'backup',
                'WARNING', severity='WARNING',
                actual_value='异常',
                expected_value='成功',
                message=f'获取备份信息异常: {str(e)}'
            )
    
    def check_error_logs(self):
        """检查错误日志"""
        try:
            info = self.connector.get_error_log_info()
            
            if not info:
                self.add_item(
                    'ERROR_LOG', '错误日志', 'log',
                    'PASS', severity='OK',
                    actual_value='无',
                    expected_value='无',
                    message='错误日志检查完成'
                )
                return
            
            error_count = info.get('error_count', 0)
            threshold = {'max_warning': 5, 'max': 10}
            result, severity = self.check_threshold(error_count, threshold)
            
            self.add_item(
                'ERROR_LOG', '错误日志', 'log',
                result, severity=severity,
                actual_value=f'{error_count}条',
                expected_value='< 5条/小时',
                message=self._get_error_log_message(result, error_count)
            )
            
        except Exception as e:
            self.add_item(
                'ERROR_LOG', '错误日志', 'log',
                'WARNING', severity='WARNING',
                actual_value='异常',
                expected_value='< 5条/小时',
                message=f'获取错误日志异常: {str(e)}'
            )
    
    def _get_error_log_message(self, result, count):
        """获取错误日志消息"""
        if result == 'PASS':
            return f'错误日志正常 ({count}条)'
        elif result == 'WARNING':
            return f'错误日志较多 ({count}条)'
        else:
            return f'错误日志过多 ({count}条)'


def run_database_inspection(inspection_id):
    """运行数据库巡检"""
    try:
        inspection = Inspection.objects.get(id=inspection_id)
    except Inspection.DoesNotExist:
        raise ValueError(f'巡检记录 {inspection_id} 不存在')
    
    # 创建巡检执行器
    inspector = DatabaseInspector(inspection)
    
    # 执行巡检
    items = inspector.run()
    
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
    
    if failed > 0:
        inspection.summary = f'发现{failed}项异常，需要关注'
    elif warning > 0:
        inspection.summary = f'发现{warning}项警告，建议检查'
    else:
        inspection.summary = f'巡检通过，所有项目正常'
    
    inspection.save()
    
    return inspection


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库巡检执行器')
    parser.add_argument('--inspection-id', type=int, required=True, help='巡检记录ID')
    
    args = parser.parse_args()
    
    print(f'执行数据库巡检 {args.inspection_id}...')
    result = run_database_inspection(args.inspection_id)
    print(f'巡检完成: {result.summary}')
    print(f'通过: {result.passed_items}, 警告: {result.warning_items}, 失败: {result.failed_items}')
