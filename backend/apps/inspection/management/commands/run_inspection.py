#!/usr/bin/env python3
"""
巡检管理命令
用于定时任务或手工触发巡检
"""

import os
import sys
import argparse
from datetime import datetime

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.inspection.models import Inspection
from apps.inspection.executors import run_inspection
from apps.inspection.db_inspector import run_database_inspection
from apps.assets.models import Asset
from apps.assets.status_refresher import DeviceStatusRefresher


def run_snmp_inspection(asset_id=None, customer_id=None):
    """执行SNMP设备巡检"""
    if asset_id:
        assets = Asset.objects.filter(id=asset_id, status='ACTIVE')
    elif customer_id:
        assets = Asset.objects.filter(customer_id=customer_id, status='ACTIVE')
    else:
        assets = Asset.objects.filter(status='ACTIVE')
    
    results = []
    for asset in assets:
        print(f'巡检资产: {asset.asset_name}...')
        
        inspection = Inspection.objects.create(
            name=f'巡检-{asset.asset_name}',
            description=f'SNMP设备巡检',
            inspection_type='SNMP',
            customer=asset.customer,
            asset=asset,
            asset_type=asset.asset_type,
            status='RUNNING',
            started_at=django.utils.timezone.now()
        )
        
        try:
            result = run_inspection(inspection.id)
            results.append({
                'asset_name': asset.asset_name,
                'status': result.status,
                'passed': result.passed_items,
                'warning': result.warning_items,
                'failed': result.failed_items
            })
            print(f'  ✓ 完成: 通过={result.passed_items}, 警告={result.warning_items}, 失败={result.failed_items}')
        except Exception as e:
            print(f'  ✗ 失败: {str(e)}')
            results.append({
                'asset_name': asset.asset_name,
                'status': 'failed',
                'error': str(e)
            })
    
    return results


def run_database_inspection_task(asset_id=None, customer_id=None):
    """执行数据库巡检"""
    if asset_id:
        assets = Asset.objects.filter(id=asset_id, status='ACTIVE')
    elif customer_id:
        assets = Asset.objects.filter(customer_id=customer_id, status='ACTIVE')
    else:
        assets = Asset.objects.filter(status='ACTIVE')
    
    results = []
    for asset in assets:
        print(f'巡检数据库: {asset.asset_name}...')
        
        inspection = Inspection.objects.create(
            name=f'数据库巡检-{asset.asset_name}',
            description=f'数据库状态巡检',
            inspection_type='DATABASE',
            customer=asset.customer,
            asset=asset,
            asset_type=asset.asset_type,
            status='RUNNING',
            started_at=django.utils.timezone.now()
        )
        
        try:
            result = run_database_inspection(inspection.id)
            results.append({
                'asset_name': asset.asset_name,
                'status': result.status,
                'passed': result.passed_items,
                'warning': result.warning_items,
                'failed': result.failed_items
            })
            print(f'  ✓ 完成: 通过={result.passed_items}, 警告={result.warning_items}, 失败={result.failed_items}')
        except Exception as e:
            print(f'  ✗ 失败: {str(e)}')
            results.append({
                'asset_name': asset.asset_name,
                'status': 'failed',
                'error': str(e)
            })
    
    return results


def refresh_device_status():
    """刷新设备状态"""
    print('开始刷新设备状态...')
    refresher = DeviceStatusRefresher()
    result = refresher.refresh_all()
    
    print(f'\\n刷新完成:')
    print(f'  总设备数: {result["total"]}')
    print(f'  在线: {result["online"]}')
    print(f'  离线: {result["offline"]}')
    
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='巡检管理命令')
    subparsers = parser.add_subparsers(dest='command', help='子命令')
    
    # SNMP巡检
    snmp_parser = subparsers.add_parser('snmp', help='执行SNMP设备巡检')
    snmp_parser.add_argument('--asset-id', type=int, help='资产ID')
    snmp_parser.add_argument('--customer-id', type=int, help='客户ID')
    
    # 数据库巡检
    db_parser = subparsers.add_parser('database', help='执行数据库巡检')
    db_parser.add_argument('--asset-id', type=int, help='资产ID')
    db_parser.add_argument('--customer-id', type=int, help='客户ID')
    
    # 状态刷新
    subparsers.add_parser('status', help='刷新设备状态')
    
    # 全部巡检
    all_parser = subparsers.add_parser('all', help='执行所有巡检')
    all_parser.add_argument('--customer-id', type=int, help='客户ID')
    
    args = parser.parse_args()
    
    if args.command == 'snmp':
        results = run_snmp_inspection(args.asset_id, args.customer_id)
    elif args.command == 'database':
        results = run_database_inspection_task(args.asset_id, args.customer_id)
    elif args.command == 'status':
        results = refresh_device_status()
    elif args.command == 'all':
        print('=== 执行SNMP设备巡检 ===')
        snmp_results = run_snmp_inspection(customer_id=args.customer_id)
        print('\\n=== 执行数据库巡检 ===')
        db_results = run_database_inspection_task(customer_id=args.customer_id)
        results = {'snmp': snmp_results, 'database': db_results}
    else:
        parser.print_help()
        sys.exit(1)
    
    print(f'\\n执行完成: {datetime.now()}')
