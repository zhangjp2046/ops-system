#!/usr/bin/env python3
"""
设备状态刷新器
定时刷新设备的在线/离线状态
"""

import os
import sys
import socket
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.assets.models import Asset, AssetStatusHistory
from django.utils import timezone


class DeviceStatusRefresher:
    """设备状态刷新器"""
    
    def __init__(self):
        self.results = []
    
    def ping_host(self, host, timeout=3):
        """Ping检测主机是否可达"""
        try:
            # 使用socket检测端口连通性（更可靠）
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            # 尝试连接常用端口
            for port in [22, 80, 443, 3306, 1433, 1521]:
                try:
                    result = sock.connect_ex((host, port))
                    sock.close()
                    if result == 0:
                        return True
                except:
                    continue
            sock.close()
            # 如果所有端口都连不上，尝试ICMP ping
            return os.system(f'ping -c 1 -W {timeout} {host} > /dev/null 2>&1') == 0
        except:
            return False
    
    def check_asset_status(self, asset):
        """检查单个资产状态"""
        # 获取资产地址（优先使用ip_address，其次location）
        address = asset.ip_address or asset.location
        
        if not address:
            return {
                'asset_id': asset.id,
                'asset_name': asset.asset_name,
                'address': None,
                'online': None,
                'error': '无有效地址'
            }
        
        try:
            online = self.ping_host(address)
            return {
                'asset_id': asset.id,
                'asset_name': asset.asset_name,
                'address': address,
                'online': online,
                'error': None
            }
        except Exception as e:
            return {
                'asset_id': asset.id,
                'asset_name': asset.asset_name,
                'address': address,
                'online': False,
                'error': str(e)
            }
    
    def refresh_all(self, batch_size=50):
        """刷新所有资产状态"""
        assets = Asset.objects.filter(status='ACTIVE')
        total = assets.count()
        
        print(f'开始刷新 {total} 个设备状态...')
        
        online_count = 0
        offline_count = 0
        
        for i, asset in enumerate(assets):
            result = self.check_asset_status(asset)
            self.results.append(result)
            
            old_status = asset.status
            
            # 更新资产状态
            from django.utils import timezone
            now = timezone.now()
            
            if result['online']:
                asset.status = 'ACTIVE'
                asset.online = True
                online_count += 1
            else:
                asset.status = 'INACTIVE'
                asset.online = False
                offline_count += 1
            
            asset.last_check_time = now
            
            # 记录状态变更历史
            if old_status != asset.status:
                AssetStatusHistory.objects.create(
                    asset=asset,
                    status=asset.status,
                    changed_by='SYSTEM',
                    change_reason='定时状态刷新'
                )
            
            asset.save()
            
            if (i + 1) % 10 == 0:
                print(f'已处理 {i + 1}/{total}')
        
        return {
            'total': total,
            'online': online_count,
            'offline': offline_count,
            'results': self.results
        }
    
    def refresh_customer_assets(self, customer_id):
        """刷新指定客户的资产状态"""
        assets = Asset.objects.filter(customer_id=customer_id, status='ACTIVE')
        total = assets.count()
        
        print(f'开始刷新客户 {customer_id} 的 {total} 个设备状态...')
        
        online_count = 0
        offline_count = 0
        
        for asset in assets:
            result = self.check_asset_status(asset)
            self.results.append(result)
            
            old_status = asset.status
            
            if result['online']:
                asset.status = 'ACTIVE'
                asset.online = True
                online_count += 1
            else:
                asset.status = 'INACTIVE'
                asset.online = False
                offline_count += 1
            
            if old_status != asset.status:
                AssetStatusHistory.objects.create(
                    asset=asset,
                    status=asset.status,
                    changed_by='SYSTEM',
                    change_reason='定时状态刷新'
                )
            
            asset.save()
        
        return {
            'total': total,
            'online': online_count,
            'offline': offline_count,
            'results': self.results
        }


def run_status_refresh():
    """运行设备状态刷新"""
    refresher = DeviceStatusRefresher()
    result = refresher.refresh_all()
    
    print(f'\\n=== 刷新完成 ===')
    print(f'总设备数: {result["total"]}')
    print(f'在线: {result["online"]}')
    print(f'离线: {result["offline"]}')
    
    return result


if __name__ == '__main__':
    run_status_refresh()
