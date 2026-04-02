#!/usr/bin/env python3
"""
Ping检测服务 - 定时检测所有资产IP在线状态
使用子进程ping，支持并发检测，更新Asset.online字段
"""
import subprocess
import concurrent.futures
import logging
from datetime import datetime
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


def ping_host(ip, timeout=2):
    """
    Ping检测单个主机
    返回: (是否在线, 响应时间ms)
    """
    if not ip or ip in ('0.0.0.0', '127.0.0.1', 'localhost', ''):
        return False, None
    
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', str(timeout), ip],
            capture_output=True,
            text=True,
            timeout=timeout + 3
        )
        
        if result.returncode == 0:
            # 解析响应时间
            for line in result.stdout.split('\n'):
                if 'time=' in line:
                    try:
                        ms = line.split('time=')[1].split()[0].replace('ms', '')
                        return True, float(ms)
                    except (IndexError, ValueError):
                        return True, None
            return True, None
        return False, None
        
    except subprocess.TimeoutExpired:
        logger.warning(f"Ping超时: {ip}")
        return False, None
    except Exception as e:
        logger.error(f"Ping错误 {ip}: {e}")
        return False, None


import re


def extract_ip_from_name(name):
    """
    从资产名称中提取IP地址
    例如: "Oracle-172.26.11.50" -> "172.26.11.50"
    """
    if not name:
        return None
    # 匹配IPv4地址
    pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
    match = re.search(pattern, name)
    if match:
        ip = match.group()
        # 验证IP地址有效性
        parts = ip.split('.')
        if all(0 <= int(p) <= 255 for p in parts):
            return ip
    return None


def get_asset_ip(asset):
    """
    获取资产的IP地址
    优先级: Asset.ip_address > AssetData.ip_address > 资产名称提取
    """
    # 1. 优先使用Asset模型的ip_address字段
    if asset.ip_address:
        return asset.ip_address.strip()
    
    # 2. 从AssetData中查找ip_address字段
    try:
        from apps.assets.models import AssetData
        ip_data = AssetData.objects.filter(
            asset=asset,
            field__field_code='ip_address'
        ).first()
        if ip_data and ip_data.string_value:
            return ip_data.string_value.strip()
    except Exception as e:
        logger.error(f"获取资产IP失败 {asset.asset_name}: {e}")
    
    # 3. 从资产名称中提取IP
    ip_from_name = extract_ip_from_name(asset.asset_name)
    if ip_from_name:
        return ip_from_name
    
    return None


def check_single_asset(asset):
    """
    检测单个资产的在线状态
    返回: (asset_id, asset_name, ip, is_online, response_time)
    """
    ip = get_asset_ip(asset)
    if not ip:
        return asset.id, asset.asset_name, None, False, None
    
    is_online, response_time = ping_host(ip)
    return asset.id, asset.asset_name, ip, is_online, response_time


def check_all_assets(max_workers=20, status_filter=None):
    """
    并发检测所有资产的在线状态
    
    参数:
        max_workers: 最大并发数
        status_filter: 状态过滤，默认检测ACTIVE资产
    
    返回: {
        'total': 总数,
        'online': 在线数,
        'offline': 离线数,
        'skipped': 跳过数(无IP),
        'details': [(asset_id, name, ip, is_online, response_time), ...]
    }
    """
    from apps.assets.models import Asset
    
    # 获取需要检测的资产
    if status_filter is None:
        status_filter = ['ACTIVE']
    
    assets = Asset.objects.filter(status__in=status_filter)
    total = assets.count()
    
    if total == 0:
        return {
            'total': 0,
            'online': 0,
            'offline': 0,
            'skipped': 0,
            'details': []
        }
    
    logger.info(f"开始Ping检测 {total} 个资产，并发数: {max_workers}")
    start_time = datetime.now()
    
    results = []
    skipped = 0
    
    # 并发检测
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_asset = {
            executor.submit(check_single_asset, asset): asset 
            for asset in assets
        }
        
        for future in concurrent.futures.as_completed(future_to_asset, timeout=60):
            try:
                result = future.result()
                asset_id, name, ip, is_online, response_time = result
                
                if ip is None:
                    skipped += 1
                    logger.debug(f"跳过 {name}: 无IP地址")
                else:
                    results.append(result)
                    status = "在线" if is_online else "离线"
                    rt_info = f" ({response_time}ms)" if response_time else ""
                    logger.debug(f"{name} ({ip}): {status}{rt_info}")
                    
            except Exception as e:
                asset = future_to_asset[future]
                logger.error(f"检测异常 {asset.asset_name}: {e}")
                results.append((asset.id, asset.asset_name, None, False, None))
    
    # 统计结果
    online_count = sum(1 for _, _, ip, online, _ in results if online)
    offline_count = len(results) - online_count
    
    # 批量更新数据库
    now = timezone.now()
    updated_count = 0
    
    with transaction.atomic():
        for asset_id, name, ip, is_online, response_time in results:
            try:
                asset = Asset.objects.get(id=asset_id)
                if asset.online != is_online:
                    asset.online = is_online
                    asset.last_check_time = now
                    asset.save(update_fields=['online', 'last_check_time'])
                    updated_count += 1
                    logger.info(f"状态变更: {name} -> {'在线' if is_online else '离线'}")
                else:
                    # 即使状态没变，也更新检查时间
                    asset.last_check_time = now
                    asset.save(update_fields=['last_check_time'])
            except Asset.DoesNotExist:
                logger.warning(f"资产不存在: {asset_id}")
            except Exception as e:
                logger.error(f"更新资产失败 {name}: {e}")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    logger.info(f"Ping检测完成: 在线{online_count}, 离线{offline_count}, "
                f"跳过{skipped}, 更新{updated_count}, 耗时{elapsed:.2f}秒")
    
    # 生成 Ping 告警
    try:
        from apps.alerts.alert_generator import generate_ping_alerts
        ping_alert_data = [
            {
                'asset_id': asset_id,
                'asset_name': name,
                'ip': ip,
                'is_online': is_online,
                'response_time': response_time,
            }
            for asset_id, name, ip, is_online, response_time in results
        ]
        generate_ping_alerts(ping_alert_data)
    except Exception as e:
        logger.error(f'生成Ping告警失败: {e}')
    
    # 推送到 ops-center
    try:
        from apps.dashboard.push_service import push_ping_results
        push_ping_results(ping_alert_data)
    except Exception as e:
        logger.error(f'推送Ping结果失败: {e}')
    
    return {
        'total': total,
        'online': online_count,
        'offline': offline_count,
        'skipped': skipped,
        'updated': updated_count,
        'elapsed_seconds': round(elapsed, 2),
        'details': results
    }
