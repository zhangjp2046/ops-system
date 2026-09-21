#!/usr/bin/env python3
"""
初始化告警阈值模板
创建常用的阈值配置模板，方便快速应用到客户
"""
import os
import sys
import django

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.alerts.threshold_models import AlertThresholdTemplate


def init_threshold_templates():
    """初始化阈值模板"""
    
    templates = [
        # ==================== MySQL ====================
        {
            'name': 'MySQL会话连接数',
            'protocol': 'mysql',
            'check_item_code': 'SESSIONS',
            'check_item_name': '会话连接数',
            'description': 'MySQL当前连接数阈值，超过阈值告警',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'number',
                'unit': '个',
                'warning_threshold': '100',
                'error_threshold': '200',
                'critical_threshold': '300',
                'description': 'MySQL当前连接数阈值'
            }
        },
        {
            'name': 'MySQL缓冲池命中率',
            'protocol': 'mysql',
            'check_item_code': 'BUFFER_HIT',
            'check_item_name': '缓冲池命中率',
            'description': 'InnoDB缓冲池命中率，低于阈值告警',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'lower',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '95',
                'error_threshold': '90',
                'critical_threshold': '80',
                'description': 'InnoDB缓冲池命中率阈值'
            }
        },
        {
            'name': 'MySQL数据库大小',
            'protocol': 'mysql',
            'check_item_code': 'DB_SIZE',
            'check_item_name': '数据库大小',
            'description': 'MySQL数据库大小阈值（GB）',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'number',
                'unit': 'GB',
                'warning_threshold': '50',
                'error_threshold': '100',
                'critical_threshold': '200',
                'description': 'MySQL数据库大小阈值'
            }
        },
        
        # ==================== Oracle ====================
        {
            'name': 'Oracle表空间使用率',
            'protocol': 'oracle',
            'check_item_code': 'TABLESPACE',
            'check_item_name': '表空间使用率',
            'description': 'Oracle表空间使用率阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '80',
                'error_threshold': '90',
                'critical_threshold': '95',
                'description': 'Oracle表空间使用率阈值'
            }
        },
        {
            'name': 'Oracle会话连接数',
            'protocol': 'oracle',
            'check_item_code': 'SESSIONS',
            'check_item_name': '会话连接数',
            'description': 'Oracle当前会话数阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'number',
                'unit': '个',
                'warning_threshold': '200',
                'error_threshold': '400',
                'critical_threshold': '500',
                'description': 'Oracle当前会话数阈值'
            }
        },
        {
            'name': 'Oracle缓冲命中率',
            'protocol': 'oracle',
            'check_item_code': 'BUFFER_HIT',
            'check_item_name': '缓冲命中率',
            'description': 'Buffer Cache命中率阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'lower',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '95',
                'error_threshold': '90',
                'critical_threshold': '80',
                'description': 'Buffer Cache命中率阈值'
            }
        },
        
        # ==================== MSSQL ====================
        {
            'name': 'MSSQL会话连接数',
            'protocol': 'mssql',
            'check_item_code': 'SESSIONS',
            'check_item_name': '会话连接数',
            'description': 'MSSQL当前会话数阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'number',
                'unit': '个',
                'warning_threshold': '150',
                'error_threshold': '300',
                'critical_threshold': '450',
                'description': 'MSSQL当前会话数阈值'
            }
        },
        {
            'name': 'MSSQL缓冲命中率',
            'protocol': 'mssql',
            'check_item_code': 'BUFFER_HIT',
            'check_item_name': '缓冲命中率',
            'description': 'Buffer Cache命中率阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'lower',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '95',
                'error_threshold': '90',
                'critical_threshold': '80',
                'description': 'Buffer Cache命中率阈值'
            }
        },
        
        # ==================== PostgreSQL ====================
        {
            'name': 'PostgreSQL会话连接数',
            'protocol': 'postgresql',
            'check_item_code': 'SESSIONS',
            'check_item_name': '会话连接数',
            'description': 'PostgreSQL当前连接数阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'number',
                'unit': '个',
                'warning_threshold': '100',
                'error_threshold': '200',
                'critical_threshold': '300',
                'description': 'PostgreSQL当前连接数阈值'
            }
        },
        {
            'name': 'PostgreSQL缓冲命中率',
            'protocol': 'postgresql',
            'check_item_code': 'BUFFER_HIT',
            'check_item_name': '缓冲命中率',
            'description': 'Shared Buffer命中率阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'lower',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '95',
                'error_threshold': '90',
                'critical_threshold': '80',
                'description': 'Shared Buffer命中率阈值'
            }
        },
        
        # ==================== SNMP设备 ====================
        {
            'name': '设备CPU使用率',
            'protocol': 'snmp',
            'check_item_code': 'CPU_USAGE',
            'check_item_name': 'CPU使用率',
            'description': 'SNMP设备CPU使用率阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '80',
                'error_threshold': '90',
                'critical_threshold': '95',
                'description': '设备CPU使用率阈值'
            }
        },
        {
            'name': '设备内存使用率',
            'protocol': 'snmp',
            'check_item_code': 'MEM_USAGE',
            'check_item_name': '内存使用率',
            'description': 'SNMP设备内存使用率阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '80',
                'error_threshold': '90',
                'critical_threshold': '95',
                'description': '设备内存使用率阈值'
            }
        },
        {
            'name': '设备磁盘使用率',
            'protocol': 'snmp',
            'check_item_code': 'DISK_USAGE',
            'check_item_name': '磁盘使用率',
            'description': 'SNMP设备磁盘使用率阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '80',
                'error_threshold': '90',
                'critical_threshold': '95',
                'description': '设备磁盘使用率阈值'
            }
        },
        
        # ==================== SSH服务器 ====================
        {
            'name': '服务器CPU使用率',
            'protocol': 'ssh',
            'check_item_code': 'CPU_USAGE',
            'check_item_name': 'CPU使用率',
            'description': '服务器CPU使用率阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '80',
                'error_threshold': '90',
                'critical_threshold': '95',
                'description': '服务器CPU使用率阈值'
            }
        },
        {
            'name': '服务器内存使用率',
            'protocol': 'ssh',
            'check_item_code': 'MEM_USAGE',
            'check_item_name': '内存使用率',
            'description': '服务器内存使用率阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '80',
                'error_threshold': '90',
                'critical_threshold': '95',
                'description': '服务器内存使用率阈值'
            }
        },
        {
            'name': '服务器磁盘使用率',
            'protocol': 'ssh',
            'check_item_code': 'DISK_USAGE',
            'check_item_name': '磁盘使用率',
            'description': '服务器磁盘使用率阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '80',
                'error_threshold': '90',
                'critical_threshold': '95',
                'description': '服务器磁盘使用率阈值'
            }
        },
        {
            'name': '服务器系统负载',
            'protocol': 'ssh',
            'check_item_code': 'LOAD_AVERAGE',
            'check_item_name': '系统负载',
            'description': '系统平均负载阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'number',
                'unit': '',
                'warning_threshold': '4',
                'error_threshold': '8',
                'critical_threshold': '16',
                'description': '系统平均负载阈值（建议设为CPU核心数）'
            }
        },
        {
            'name': '服务器进程数',
            'protocol': 'ssh',
            'check_item_code': 'PROCESS_COUNT',
            'check_item_name': '进程数',
            'description': '当前进程数阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'number',
                'unit': '个',
                'warning_threshold': '200',
                'error_threshold': '500',
                'critical_threshold': '1000',
                'description': '当前进程数阈值'
            }
        },
        
        # ==================== Ping检测 ====================
        {
            'name': 'Ping响应延迟',
            'protocol': 'ping',
            'check_item_code': 'PING_LATENCY',
            'check_item_name': '响应延迟',
            'description': 'Ping响应延迟阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'number',
                'unit': 'ms',
                'warning_threshold': '100',
                'error_threshold': '500',
                'critical_threshold': '1000',
                'description': 'Ping响应延迟阈值'
            }
        },
        {
            'name': 'Ping丢包率',
            'protocol': 'ping',
            'check_item_code': 'PING_PACKET_LOSS',
            'check_item_name': '丢包率',
            'description': 'Ping丢包率阈值',
            'is_system': True,
            'default_config': {
                'threshold_direction': 'upper',
                'value_type': 'percentage',
                'unit': '%',
                'warning_threshold': '1',
                'error_threshold': '5',
                'critical_threshold': '10',
                'description': 'Ping丢包率阈值'
            }
        },
    ]
    
    created_count = 0
    updated_count = 0
    
    for template_data in templates:
        obj, created = AlertThresholdTemplate.objects.update_or_create(
            name=template_data['name'],
            protocol=template_data['protocol'],
            check_item_code=template_data['check_item_code'],
            defaults={
                'check_item_name': template_data['check_item_name'],
                'description': template_data['description'],
                'is_system': template_data['is_system'],
                'default_config': template_data['default_config'],
            }
        )
        
        if created:
            created_count += 1
            print(f'✅ 创建模板: {obj.name}')
        else:
            updated_count += 1
            print(f'🔄 更新模板: {obj.name}')
    
    print(f'\n📊 完成! 创建: {created_count}, 更新: {updated_count}')


if __name__ == '__main__':
    print('🚀 开始初始化告警阈值模板...\n')
    init_threshold_templates()
