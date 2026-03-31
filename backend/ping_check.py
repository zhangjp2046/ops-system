#!/usr/bin/env python3
"""
Ping检测脚本 - 更新设备在线状态
用法: python3 ping_check.py
"""
import os
import sys
import django
import subprocess
from datetime import datetime

# 设置Django环境
sys.path.insert(0, '/home/zhang/botcode/ops-system/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.assets.models import Asset, AssetData

def ping_host(ip, timeout=2):
    """Ping检测主机，返回(是否在线, 响应时间ms)"""
    try:
        result = subprocess.run(
            ['ping', '-c', '1', '-W', str(timeout), ip],
            capture_output=True,
            text=True,
            timeout=timeout + 5
        )
        if result.returncode == 0:
            # 解析响应时间
            for line in result.stdout.split('\n'):
                if 'time=' in line:
                    ms = line.split('time=')[1].split()[0].replace('ms', '')
                    return True, ms
            return True, None
        return False, None
    except Exception as e:
        print(f"  ping错误: {e}")
        return False, None

def main():
    print("=" * 50)
    print(f"Ping检测 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 获取所有活跃资产
    assets = Asset.objects.filter(status__in=['ACTIVE', 'ONLINE', 'OFFLINE'])
    print(f"\n检测 {assets.count()} 个资产...\n")
    
    online_list = []
    offline_list = []
    
    for asset in assets:
        # 获取IP地址
        ip_data = AssetData.objects.filter(asset=asset, field__field_code='ip_address').first()
        if not ip_data or not ip_data.string_value:
            continue
            
        ip = ip_data.string_value.strip()
        if not ip or ip in ['0.0.0.0', '127.0.0.1', '']:
            continue
            
        is_online, response_time = ping_host(ip)
        
        if is_online:
            asset.status = 'ONLINE'
            asset.online = True
            online_list.append((asset.asset_name, ip, response_time))
            print(f"  ✅ {asset.asset_name} ({ip}) - 在线", end='')
            if response_time:
                print(f" {response_time}ms")
            else:
                print()
        else:
            asset.status = 'OFFLINE'
            asset.online = False
            offline_list.append((asset.asset_name, ip))
            print(f"  ❌ {asset.asset_name} ({ip}) - 离线")
        
        asset.save()
    
    # 统计
    print(f"\n{'=' * 50}")
    print(f"📊 检测结果:")
    print(f"   在线: {len(online_list)} 台")
    print(f"   离线: {len(offline_list)} 台")
    print(f"{'=' * 50}")
    
    # 保存在线统计到数据库
    from apps.monitoring.models import MonitoringTask
    for name, ip, rt in online_list:
        task = MonitoringTask.objects.filter(name__contains=name).first()
        if task:
            task.last_success_time = datetime.now()
            task.save()
    
    return len(online_list), len(offline_list)

if __name__ == '__main__':
    main()
