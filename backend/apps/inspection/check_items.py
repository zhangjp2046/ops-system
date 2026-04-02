#!/usr/bin/env python3
"""
巡检项目字典 - 按协议类型定义可用的巡检检查项
用于前端展示和后端执行时的项目选择
"""

# 巡检项目字典
INSPECTION_CHECK_ITEMS = {
    'mysql': {
        'name': 'MySQL',
        'icon': '🐬',
        'category': 'database',
        'checks': [
            {'code': 'DB_CONNECTION', 'name': '数据库连接', 'method': 'check_connection', 'description': '测试数据库连接是否正常'},
            {'code': 'DB_VERSION', 'name': '数据库版本', 'method': 'get_server_info', 'description': '获取MySQL版本和运行信息'},
            {'code': 'DB_SIZE', 'name': '数据库大小', 'method': 'get_database_sizes', 'description': '各数据库占用空间统计'},
            {'code': 'SESSIONS', 'name': '会话连接', 'method': 'get_session_info', 'description': '当前连接数和活跃会话'},
            {'code': 'BUFFER_HIT', 'name': '缓冲池命中率', 'method': 'get_performance_info', 'description': 'InnoDB缓冲池命中率'},
            {'code': 'SLOW_QUERIES', 'name': '慢查询', 'method': 'get_slow_queries', 'description': '最近慢查询记录'},
            {'code': 'BACKUP', 'name': '备份状态', 'method': 'get_backup_info', 'description': '备份执行情况'},
            {'code': 'ERROR_LOG', 'name': '错误日志', 'method': 'get_error_logs', 'description': '错误日志分析'},
            {'code': 'LOCK_INFO', 'name': '锁信息', 'method': 'get_lock_info', 'description': '当前锁等待情况'},
        ]
    },
    'mssql': {
        'name': 'MSSQL',
        'icon': '🗄️',
        'category': 'database',
        'checks': [
            {'code': 'DB_CONNECTION', 'name': '数据库连接', 'method': 'check_connection', 'description': '测试数据库连接是否正常'},
            {'code': 'DB_VERSION', 'name': '数据库版本', 'method': 'get_server_info', 'description': '获取SQL Server版本信息'},
            {'code': 'DB_LIST', 'name': '数据库列表', 'method': 'get_databases', 'description': '列出所有数据库'},
            {'code': 'DB_SIZE', 'name': '数据库文件大小', 'method': 'get_database_sizes', 'description': '数据文件和日志文件大小'},
            {'code': 'SESSIONS', 'name': '会话信息', 'method': 'get_session_info', 'description': '当前会话和连接'},
            {'code': 'BUFFER_HIT', 'name': '缓冲命中率', 'method': 'get_performance_info', 'description': 'Buffer Cache命中率'},
            {'code': 'BACKUP', 'name': '备份状态', 'method': 'get_backup_info', 'description': '最近备份记录'},
            {'code': 'SLOW_QUERIES', 'name': '慢查询', 'method': 'get_slow_queries', 'description': '最耗时查询TOP10'},
            {'code': 'LOCK_INFO', 'name': '锁信息', 'method': 'get_lock_info', 'description': '当前锁等待情况'},
            {'code': 'ERROR_LOG', 'name': '错误日志', 'method': 'get_error_logs', 'description': 'SQL Server错误日志'},
        ]
    },
    'oracle': {
        'name': 'Oracle',
        'icon': '🔴',
        'category': 'database',
        'checks': [
            {'code': 'DB_CONNECTION', 'name': '数据库连接', 'method': 'check_connection', 'description': '测试数据库连接是否正常'},
            {'code': 'DB_VERSION', 'name': '数据库版本', 'method': 'get_server_info', 'description': '获取Oracle版本和实例信息'},
            {'code': 'TABLESPACE', 'name': '表空间使用率', 'method': 'get_tablespace_info', 'description': '表空间使用率检查'},
            {'code': 'DB_SIZE', 'name': '数据文件大小', 'method': 'get_database_sizes', 'description': '数据文件大小统计'},
            {'code': 'SESSIONS', 'name': '会话信息', 'method': 'get_session_info', 'description': '当前会话和连接'},
            {'code': 'BUFFER_HIT', 'name': '缓冲命中率', 'method': 'get_performance_info', 'description': 'Buffer Cache命中率'},
            {'code': 'ARCHIVE_LOG', 'name': '归档日志', 'method': 'get_archive_logs', 'description': '归档日志使用情况'},
            {'code': 'BACKUP', 'name': 'RMAN备份', 'method': 'get_backup_info', 'description': 'RMAN备份状态'},
            {'code': 'ERROR_LOG', 'name': '错误日志', 'method': 'get_error_logs', 'description': 'ORA-错误日志'},
            {'code': 'SLOW_SQL', 'name': '资源消耗SQL', 'method': 'get_slow_queries', 'description': '最耗资源SQL'},
            {'code': 'LOCK_INFO', 'name': '锁信息', 'method': 'get_lock_info', 'description': '锁等待情况'},
        ]
    },
    'postgresql': {
        'name': 'PostgreSQL',
        'icon': '🐘',
        'category': 'database',
        'checks': [
            {'code': 'DB_CONNECTION', 'name': '数据库连接', 'method': 'check_connection', 'description': '测试数据库连接是否正常'},
            {'code': 'DB_VERSION', 'name': '数据库版本', 'method': 'get_server_info', 'description': '获取PostgreSQL版本'},
            {'code': 'DB_SIZE', 'name': '数据库大小', 'method': 'get_database_sizes', 'description': '数据库大小统计'},
            {'code': 'SESSIONS', 'name': '会话连接', 'method': 'get_session_info', 'description': '当前连接数'},
            {'code': 'BUFFER_HIT', 'name': '缓冲命中率', 'method': 'get_performance_info', 'description': 'Shared Buffer命中率'},
            {'code': 'SLOW_QUERIES', 'name': '慢查询', 'method': 'get_slow_queries', 'description': '慢查询记录'},
            {'code': 'BACKUP', 'name': '备份状态', 'method': 'get_backup_info', 'description': '备份状态'},
        ]
    },
    'snmp': {
        'name': 'SNMP设备',
        'icon': '📡',
        'category': 'device',
        'checks': [
            {'code': 'SNMP_REACHABLE', 'name': 'SNMP可达性', 'method': 'snmp_get', 'description': 'sysDescr.0 (1.3.6.1.2.1.1.1.0)'},
            {'code': 'SYS_DESCR', 'name': '系统描述', 'method': 'snmp_get', 'description': 'sysDescr.0 - 设备型号和系统版本'},
            {'code': 'SYS_UPTIME', 'name': '运行时间', 'method': 'snmp_get', 'description': 'sysUpTime.0 (1.3.6.1.2.1.1.3.0)'},
            {'code': 'CPU_USAGE', 'name': 'CPU使用率', 'method': 'snmp_get', 'description': 'UCD-SNMP: ssCpuUser/System/Idle + HOST-MIB: hrProcessorLoad'},
            {'code': 'MEM_USAGE', 'name': '内存使用率', 'method': 'snmp_walk', 'description': 'HOST-MIB: hrStorageRam + UCD-SNMP: memTotalReal/memAvailReal'},
            {'code': 'DISK_USAGE', 'name': '磁盘使用率', 'method': 'snmp_walk', 'description': 'HOST-MIB: hrStorageFixedDisk + UCD-SNMP: dskPercent'},
            {'code': 'INTERFACE_STATUS', 'name': '接口状态', 'method': 'snmp_walk', 'description': 'IF-MIB: ifDescr + ifOperStatus'},
            {'code': 'INTERFACE_TRAFFIC', 'name': '接口流量', 'method': 'snmp_walk', 'description': 'IF-MIB: ifInOctets + ifOutOctets'},
            {'code': 'TRAP_STATUS', 'name': 'Trap告警', 'method': 'snmp_trap', 'description': '需配置SNMP Trap Receiver'},
        ]
    },
    'ssh': {
        'name': 'SSH服务器',
        'icon': '🖥️',
        'category': 'server',
        'checks': [
            {'code': 'SSH_CONNECTION', 'name': 'SSH连接', 'description': 'SSH连接是否正常'},
            {'code': 'SYS_INFO', 'name': '系统信息', 'description': '操作系统版本'},
            {'code': 'CPU_USAGE', 'name': 'CPU使用率', 'description': 'CPU负载情况'},
            {'code': 'MEM_USAGE', 'name': '内存使用率', 'description': '内存使用情况'},
            {'code': 'DISK_USAGE', 'name': '磁盘使用率', 'description': '磁盘空间使用'},
            {'code': 'LOAD_AVERAGE', 'name': '系统负载', 'description': '系统平均负载'},
            {'code': 'PROCESS_COUNT', 'name': '进程数', 'description': '当前进程数'},
            {'code': 'SERVICE_STATUS', 'name': '服务状态', 'description': '关键服务运行状态'},
            {'code': 'LOG_CHECK', 'name': '日志检查', 'description': '系统日志异常'},
        ]
    },
    'ping': {
        'name': 'Ping检测',
        'icon': '🌐',
        'category': 'network',
        'checks': [
            {'code': 'PING_REACHABLE', 'name': '主机可达性', 'description': 'Ping检测是否通'},
            {'code': 'PING_LATENCY', 'name': '响应延迟', 'description': 'Ping响应时间'},
            {'code': 'PING_PACKET_LOSS', 'name': '丢包率', 'description': 'Ping丢包情况'},
        ]
    },
    'port': {
        'name': '端口检测',
        'icon': '🔌',
        'category': 'network',
        'checks': [
            {'code': 'PORT_OPEN', 'name': '端口开放', 'description': '指定端口是否开放'},
            {'code': 'PORT_RESPONSE', 'name': '端口响应', 'description': '端口响应时间'},
        ]
    },
}


def get_check_items_by_protocol(protocol):
    """获取指定协议的巡检项目"""
    return INSPECTION_CHECK_ITEMS.get(protocol, {}).get('checks', [])


def get_all_protocols():
    """获取所有协议分类"""
    return [
        {
            'code': code,
            'name': info['name'],
            'icon': info['icon'],
            'category': info['category'],
            'check_count': len(info['checks']),
            'checks': info['checks'],
        }
        for code, info in INSPECTION_TEMPLATES.items()  # 兼容旧代码
    ] if False else [
        {
            'code': code,
            'name': info['name'],
            'icon': info['icon'],
            'category': info['category'],
            'check_count': len(info['checks']),
        }
        for code, info in INSPECTION_CHECK_ITEMS.items()
    ]


def get_protocol_categories():
    """获取协议分类（数据库、设备、网络）"""
    categories = {}
    for code, info in INSPECTION_CHECK_ITEMS.items():
        cat = info['category']
        if cat not in categories:
            categories[cat] = {
                'code': cat,
                'name': {'database': '数据库', 'device': '设备', 'server': '服务器', 'network': '网络'}.get(cat, cat),
                'protocols': []
            }
        categories[cat]['protocols'].append({
            'code': code,
            'name': info['name'],
            'icon': info['icon'],
            'check_count': len(info['checks']),
        })
    return list(categories.values())
