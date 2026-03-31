#!/usr/bin/env python3
"""
计划任务执行器
用于执行计划中的监控任务
"""

import os
import sys
import django

# 设置Django环境
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.utils import timezone
from django.db import models
from datetime import datetime, timedelta
from apps.scheduler.models import ScheduledTask, ScheduledTaskExecution
from apps.monitoring.executors import MonitoringExecutor


class TaskExecutor:
    """任务执行器"""
    
    @classmethod
    def execute_scheduled_task(cls, task_id):
        """执行指定的计划任务"""
        try:
            task = ScheduledTask.objects.get(id=task_id)
        except ScheduledTask.DoesNotExist:
            raise ValueError(f'计划任务 {task_id} 不存在')
        
        # 创建执行记录
        execution = ScheduledTaskExecution.objects.create(
            task=task,
            status='running'
        )
        
        # 更新任务状态
        task.is_running = True
        task.save()
        
        try:
            # 根据任务类型执行
            if task.task_type == 'monitoring':
                result = cls.execute_monitoring_task(task, execution)
            elif task.task_type == 'inspection':
                # 根据巡检类型选择执行器
                config = task.config or {}
                inspection_type = config.get('inspection_type', 'SNMP')
                if inspection_type == 'DATABASE':
                    result = cls.execute_database_inspection_task(task, execution)
                else:
                    result = cls.execute_inspection_task(task, execution)
            elif task.task_type == 'status_refresh':
                result = cls.execute_status_refresh_task(task, execution)
            elif task.task_type == 'cleanup':
                result = cls.execute_cleanup_task(task, execution)
            elif task.task_type == 'report':
                result = cls.execute_report_task(task, execution)
            else:
                raise ValueError(f'不支持的任务类型: {task.task_type}')
            
            # 标记成功
            execution.mark_completed(
                status='success',
                result_data=result,
                output=f'任务执行成功'
            )
            
            return result
            
        except Exception as e:
            # 标记失败
            execution.mark_completed(
                status='failed',
                error_message=str(e)
            )
            raise
    
    @classmethod
    def execute_monitoring_task(cls, task, execution):
        """执行监控任务"""
        config = task.config or {}
        monitor_task_type = config.get('task_type', 'ping')
        
        # 根据目标执行不同的任务
        if task.target_type == 'all':
            # 执行所有启用的监控任务
            results = MonitoringExecutor.execute_all_enabled_tasks(task_type=monitor_task_type)
            
            return {
                'executed_count': len(results),
                'success_count': sum(1 for r in results if r.status == 'success'),
                'failed_count': sum(1 for r in results if r.status != 'success'),
            }
        
        elif task.target_type == 'asset' and task.target_id:
            # 执行指定资产的监控任务
            results = MonitoringExecutor.execute_asset_tasks(task.target_id)
            
            return {
                'asset_id': task.target_id,
                'executed_count': len(results),
                'success_count': sum(1 for r in results if r.status == 'success'),
            }
        
        return {'executed_count': 0}
    
    @classmethod
    def execute_inspection_task(cls, task, execution):
        """执行巡检任务"""
        from apps.inspection.models import Inspection, InspectionTemplate, InspectionItem
        from apps.inspection.executors import run_inspection
        from apps.assets.models import Asset
        
        config = task.config or {}
        inspection_type = config.get('inspection_type', 'SNMP')
        
        results = []
        
        # 根据目标类型执行巡检
        if task.target_type == 'all':
            # 对所有适用资产执行巡检
            asset_types = Asset.objects.filter(status='ACTIVE').values_list('asset_type', flat=True).distinct()
            
            for asset_type_id in asset_types:
                # 获取该类型的资产
                assets = Asset.objects.filter(asset_type_id=asset_type_id, status='ACTIVE')
                
                for asset in assets:
                    try:
                        # 创建巡检记录
                        inspection = Inspection.objects.create(
                            name=f'定时巡检-{asset.asset_name}',
                            description=f'自动定时巡检',
                            inspection_type=inspection_type,
                            customer=asset.customer,
                            asset=asset,
                            asset_type=asset.asset_type,
                            status='RUNNING',
                            started_at=timezone.now()
                        )
                        
                        # 执行巡检
                        result = run_inspection(inspection.id)
                        results.append({
                            'asset_id': asset.id,
                            'asset_name': asset.asset_name,
                            'status': result.status,
                            'passed': result.passed_items,
                            'warning': result.warning_items,
                            'failed': result.failed_items
                        })
                    except Exception as e:
                        results.append({
                            'asset_id': asset.id,
                            'asset_name': asset.asset_name,
                            'status': 'failed',
                            'error': str(e)
                        })
        
        elif task.target_type == 'customer' and task.target_id:
            # 对指定客户的所有资产执行巡检
            assets = Asset.objects.filter(customer_id=task.target_id, status='ACTIVE')
            
            for asset in assets:
                try:
                    inspection = Inspection.objects.create(
                        name=f'定时巡检-{asset.asset_name}',
                        description=f'自动定时巡检',
                        inspection_type=inspection_type,
                        customer=asset.customer,
                        asset=asset,
                        asset_type=asset.asset_type,
                        status='RUNNING',
                        started_at=timezone.now()
                    )
                    
                    result = run_inspection(inspection.id)
                    results.append({
                        'asset_id': asset.id,
                        'asset_name': asset.asset_name,
                        'status': result.status,
                        'passed': result.passed_items,
                        'warning': result.warning_items,
                        'failed': result.failed_items
                    })
                except Exception as e:
                    results.append({
                        'asset_id': asset.id,
                        'asset_name': asset.asset_name,
                        'status': 'failed',
                        'error': str(e)
                    })
        
        elif task.target_type == 'asset' and task.target_id:
            # 对指定资产执行巡检
            asset = Asset.objects.get(id=task.target_id)
            
            inspection = Inspection.objects.create(
                name=f'定时巡检-{asset.asset_name}',
                description=f'自动定时巡检',
                inspection_type=inspection_type,
                customer=asset.customer,
                asset=asset,
                asset_type=asset.asset_type,
                status='RUNNING',
                started_at=timezone.now()
            )
            
            result = run_inspection(inspection.id)
            results.append({
                'asset_id': asset.id,
                'asset_name': asset.asset_name,
                'status': result.status,
                'passed': result.passed_items,
                'warning': result.warning_items,
                'failed': result.failed_items
            })
        
        return {
            'inspection_count': len(results),
            'success_count': sum(1 for r in results if r.get('status') == 'COMPLETED'),
            'failed_count': sum(1 for r in results if r.get('status') == 'failed'),
            'results': results
        }
    
    @classmethod
    def execute_database_inspection_task(cls, task, execution):
        """执行数据库巡检任务"""
        from apps.inspection.models import Inspection
        from apps.inspection.db_inspector import run_database_inspection
        from apps.assets.models import Asset
        
        config = task.config or {}
        
        results = []
        
        # 根据目标类型执行巡检
        if task.target_type == 'all':
            # 对所有资产执行数据库巡检
            assets = Asset.objects.filter(status='ACTIVE')
            
            for asset in assets:
                try:
                    inspection = Inspection.objects.create(
                        name=f'定时数据库巡检-{asset.asset_name}',
                        description=f'自动定时数据库巡检',
                        inspection_type='DATABASE',
                        customer=asset.customer,
                        asset=asset,
                        asset_type=asset.asset_type,
                        status='RUNNING',
                        started_at=timezone.now()
                    )
                    
                    result = run_database_inspection(inspection.id)
                    results.append({
                        'asset_id': asset.id,
                        'asset_name': asset.asset_name,
                        'status': result.status,
                        'passed': result.passed_items,
                        'warning': result.warning_items,
                        'failed': result.failed_items
                    })
                except Exception as e:
                    results.append({
                        'asset_id': asset.id,
                        'asset_name': asset.asset_name,
                        'status': 'failed',
                        'error': str(e)
                    })
        
        elif task.target_type == 'customer' and task.target_id:
            # 对指定客户的资产执行巡检
            assets = Asset.objects.filter(customer_id=task.target_id, status='ACTIVE')
            
            for asset in assets:
                try:
                    inspection = Inspection.objects.create(
                        name=f'定时数据库巡检-{asset.asset_name}',
                        description=f'自动定时数据库巡检',
                        inspection_type='DATABASE',
                        customer=asset.customer,
                        asset=asset,
                        asset_type=asset.asset_type,
                        status='RUNNING',
                        started_at=timezone.now()
                    )
                    
                    result = run_database_inspection(inspection.id)
                    results.append({
                        'asset_id': asset.id,
                        'asset_name': asset.asset_name,
                        'status': result.status,
                        'passed': result.passed_items,
                        'warning': result.warning_items,
                        'failed': result.failed_items
                    })
                except Exception as e:
                    results.append({
                        'asset_id': asset.id,
                        'asset_name': asset.asset_name,
                        'status': 'failed',
                        'error': str(e)
                    })
        
        elif task.target_type == 'asset' and task.target_id:
            # 对指定资产执行巡检
            asset = Asset.objects.get(id=task.target_id)
            
            inspection = Inspection.objects.create(
                name=f'定时数据库巡检-{asset.asset_name}',
                description=f'自动定时数据库巡检',
                inspection_type='DATABASE',
                customer=asset.customer,
                asset=asset,
                asset_type=asset.asset_type,
                status='RUNNING',
                started_at=timezone.now()
            )
            
            result = run_database_inspection(inspection.id)
            results.append({
                'asset_id': asset.id,
                'asset_name': asset.asset_name,
                'status': result.status,
                'passed': result.passed_items,
                'warning': result.warning_items,
                'failed': result.failed_items
            })
        
        return {
            'inspection_count': len(results),
            'success_count': sum(1 for r in results if r.get('status') == 'COMPLETED'),
            'failed_count': sum(1 for r in results if r.get('status') == 'failed'),
            'results': results
        }
    
    @classmethod
    def execute_status_refresh_task(cls, task, execution):
        """执行设备状态刷新任务"""
        from apps.assets.status_refresher import DeviceStatusRefresher
        
        refresher = DeviceStatusRefresher()
        
        if task.target_type == 'all':
            result = refresher.refresh_all()
        elif task.target_type == 'customer' and task.target_id:
            result = refresher.refresh_customer_assets(task.target_id)
        elif task.target_type == 'asset' and task.target_id:
            from apps.assets.models import Asset
            asset = Asset.objects.get(id=task.target_id)
            result = refresher.check_asset_status(asset)
            return {
                'asset_id': asset.id,
                'asset_name': asset.asset_name,
                'address': result.get('address'),
                'online': result.get('online'),
                'error': result.get('error')
            }
        else:
            result = refresher.refresh_all()
        
        return {
            'total': result.get('total', 0),
            'online': result.get('online', 0),
            'offline': result.get('offline', 0),
            'message': f'设备状态刷新完成'
        }
    
    @classmethod
    def execute_cleanup_task(cls, task, execution):
        """执行清理任务"""
        from apps.monitoring.models import MonitoringResult, Alert
        
        config = task.config or {}
        retention_days = config.get('retention_days', 90)
        
        # 计算过期时间
        from datetime import timedelta
        expired_time = timezone.now() - timedelta(days=retention_days)
        
        # 清理过期的监控结果
        deleted_results = MonitoringResult.objects.filter(
            start_time__lt=expired_time
        ).delete()[0]
        
        # 清理已关闭的告警
        deleted_alerts = Alert.objects.filter(
            status='closed',
            occurred_at__lt=expired_time
        ).delete()[0]
        
        return {
            'deleted_results': deleted_results,
            'deleted_alerts': deleted_alerts,
            'retention_days': retention_days
        }
    
    @classmethod
    def execute_report_task(cls, task, execution):
        """执行报表任务"""
        config = task.config or {}
        report_type = config.get('report_type', 'asset_summary')
        
        if report_type == 'asset_summary':
            from apps.assets.models import Asset
            from apps.monitoring.models import Alert
            
            total_assets = Asset.objects.count()
            active_assets = Asset.objects.filter(status='ACTIVE').count()
            open_alerts = Alert.objects.filter(status__in=['open', 'acknowledged']).count()
            
            return {
                'report_type': 'asset_summary',
                'total_assets': total_assets,
                'active_assets': active_assets,
                'open_alerts': open_alerts,
                'generated_at': timezone.now().isoformat()
            }
        
        return {'report_type': report_type}
    
    @classmethod
    def process_due_tasks(cls):
        """处理所有到期的任务"""
        now = timezone.now()
        
        # 查找所有到期的任务
        tasks = ScheduledTask.objects.filter(
            is_enabled=True,
            is_running=False
        ).filter(
            models.Q(next_run_time__lte=now) | models.Q(next_run_time__isnull=True)
        )
        
        results = []
        for task in tasks:
            try:
                result = cls.execute_scheduled_task(task.id)
                results.append({
                    'task_id': task.id,
                    'task_name': task.name,
                    'status': 'success',
                    'result': result
                })
            except Exception as e:
                results.append({
                    'task_id': task.id,
                    'task_name': task.name,
                    'status': 'failed',
                    'error': str(e)
                })
        
        return results


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='计划任务执行器')
    parser.add_argument('--task-id', type=int, help='执行指定任务ID')
    parser.add_argument('--process-due', action='store_true', help='处理所有到期任务')
    
    args = parser.parse_args()
    
    if args.task_id:
        print(f'执行计划任务 {args.task_id}...')
        result = TaskExecutor.execute_scheduled_task(args.task_id)
        print(f'结果: {result}')
    
    elif args.process_due:
        print('处理所有到期任务...')
        results = TaskExecutor.process_due_tasks()
        print(f'处理了 {len(results)} 个任务:')
        for r in results:
            status = r['status']
            print(f"  - {r['task_name']}: {status}")
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()