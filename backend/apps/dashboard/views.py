#!/usr/bin/env python3
"""
驾驶舱视图
提供首页看板所需的各类统计数据
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.assets.models import Asset, AssetType, AssetData
from apps.customers.models import Customer
from apps.monitoring.models import MonitoringTask, MonitoringResult, Alert
from apps.inspection.models import InspectionPlan, InspectionTask, InspectionRecord
from apps.scheduler.models import ScheduledTask, ScheduledTaskExecution


class DashboardStatsView(APIView):
    """驾驶舱统计数据"""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """获取所有统计数据"""
        # 基础统计
        customer_count = Customer.objects.count()
        asset_total = Asset.objects.count()
        asset_active = Asset.objects.filter(status='ACTIVE').count()
        # 在线/离线以 Asset.online 字段为准（ping 结果）
        asset_online = Asset.objects.filter(online=True).count()
        asset_offline = Asset.objects.filter(online=False).count()
        
        # 按状态统计
        status_stats = Asset.objects.values('status').annotate(count=Count('id'))
        
        # 按重要等级统计
        importance_stats = Asset.objects.values('importance_level').annotate(count=Count('id'))
        
        # 按资产类型统计
        type_stats = Asset.objects.values(
            'asset_type__type_name',
            'asset_type__type_code'
        ).annotate(count=Count('id'))
        
        # 按客户统计
        customer_stats = Asset.objects.values(
            'customer__customer_name',
            'customer__customer_code'
        ).annotate(count=Count('id'))
        
        return Response({
            'success': True,
            'data': {
                'overview': {
                    'total_customers': customer_count,
                    'total_assets': asset_total,
                    'active_assets': asset_active,
                    'online_assets': asset_online,
                    'offline_assets': asset_offline,
                },
                'status_distribution': list(status_stats),
                'importance_distribution': list(importance_stats),
                'type_distribution': list(type_stats),
                'customer_distribution': list(customer_stats),
            }
        })


class MonitoringStatsView(APIView):
    """监控统计"""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """获取监控统计数据"""
        # 监控任务统计
        task_total = MonitoringTask.objects.count()
        task_enabled = MonitoringTask.objects.filter(is_enabled=True).count()
        task_running = MonitoringTask.objects.filter(status='running').count()
        
        # 今日监控结果统计
        today = timezone.now().date()
        today_results = MonitoringResult.objects.filter(
            start_time__date=today
        )
        result_today_total = today_results.count()
        result_today_success = today_results.filter(status='success').count()
        result_today_failed = today_results.filter(status='failed').count()
        
        # 最近24小时监控结果统计
        yesterday = timezone.now() - timedelta(hours=24)
        recent_results = MonitoringResult.objects.filter(
            start_time__gte=yesterday
        )
        result_recent_total = recent_results.count()
        result_recent_success = recent_results.filter(status='success').count()
        result_recent_failed = recent_results.filter(status='failed').count()
        
        # 计算可用率
        availability_rate = 0
        if result_recent_total > 0:
            availability_rate = round(result_recent_success / result_recent_total * 100, 2)
        
        # 按任务类型统计
        task_type_stats = MonitoringTask.objects.values(
            'task_type'
        ).annotate(
            total=Count('id'),
            enabled=Count('id', filter=Q(is_enabled=True))
        )
        
        return Response({
            'success': True,
            'data': {
                'task_stats': {
                    'total': task_total,
                    'enabled': task_enabled,
                    'running': task_running,
                },
                'today_stats': {
                    'total': result_today_total,
                    'success': result_today_success,
                    'failed': result_today_failed,
                },
                'recent_24h_stats': {
                    'total': result_recent_total,
                    'success': result_recent_success,
                    'failed': result_recent_failed,
                    'availability_rate': availability_rate,
                },
                'task_type_stats': list(task_type_stats),
            }
        })


class AlertStatsView(APIView):
    """告警统计"""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """获取告警统计数据"""
        # 告警总体统计
        alert_total = Alert.objects.count()
        alert_open = Alert.objects.filter(status='open').count()
        alert_acknowledged = Alert.objects.filter(status='acknowledged').count()
        alert_resolved = Alert.objects.filter(status='resolved').count()
        alert_closed = Alert.objects.filter(status='closed').count()
        
        # 按严重程度统计
        severity_stats = Alert.objects.values('severity').annotate(count=Count('id'))
        
        # 今日新增告警
        today = timezone.now().date()
        alert_today = Alert.objects.filter(occurred_at__date=today).count()
        
        # 最近7天告警趋势
        week_ago = timezone.now() - timedelta(days=7)
        recent_alerts = Alert.objects.filter(occurred_at__gte=week_ago)
        
        # 最近24小时告警
        yesterday = timezone.now() - timedelta(hours=24)
        alert_recent_24h = Alert.objects.filter(occurred_at__gte=yesterday).count()
        
        # 未处理的告警
        unhandled_alerts = Alert.objects.filter(
            status__in=['open', 'acknowledged']
        ).order_by('-occurred_at')[:10]
        
        # 高危告警
        critical_alerts = Alert.objects.filter(
            severity='CRITICAL',
            status__in=['open', 'acknowledged']
        ).count()
        
        return Response({
            'success': True,
            'data': {
                'total': alert_total,
                'by_status': {
                    'open': alert_open,
                    'acknowledged': alert_acknowledged,
                    'resolved': alert_resolved,
                    'closed': alert_closed,
                },
                'by_severity': list(severity_stats),
                'today_count': alert_today,
                'recent_24h_count': alert_recent_24h,
                'critical_count': critical_alerts,
                'unhandled_alerts': [{
                    'id': a.id,
                    'title': a.title,
                    'severity': a.severity,
                    'status': a.status,
                    'asset_name': a.asset.asset_name if a.asset else None,
                    'occurred_at': a.occurred_at,
                } for a in unhandled_alerts],
            }
        })


class InspectionStatsView(APIView):
    """巡检统计"""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """获取巡检统计数据"""
        # 巡检总体统计
        inspection_total = InspectionRecord.objects.count()
        inspection_completed = InspectionRecord.objects.filter(status='completed').count()
        inspection_failed = InspectionRecord.objects.filter(overall_status='fail').count()
        
        # 今日巡检统计
        today = timezone.now().date()
        inspection_today = InspectionRecord.objects.filter(created_at__date=today)
        inspection_today_total = inspection_today.count()
        inspection_today_passed = inspection_today.filter(overall_status='pass').count()
        inspection_today_failed = inspection_today.filter(overall_status='fail').count()
        
        # 按资产类型统计
        type_stats = InspectionRecord.objects.values('asset__asset_type__type_name').annotate(
            total=Count('id'),
            passed=Count('id', filter=Q(overall_status='pass')),
        )
        
        # 最近巡检记录
        recent_inspections = InspectionRecord.objects.select_related('asset', 'task').order_by('-created_at')[:10]
        
        return Response({
            'success': True,
            'data': {
                'total': inspection_total,
                'completed': inspection_completed,
                'failed': inspection_failed,
                'today_stats': {
                    'total': inspection_today_total,
                    'passed': inspection_today_passed,
                    'failed': inspection_today_failed,
                },
                'type_stats': list(type_stats),
                'recent_inspections': [{
                    'id': i.id,
                    'asset_name': i.asset.asset_name if i.asset else None,
                    'status': i.overall_status,
                    'pass_checks': i.pass_checks,
                    'fail_checks': i.fail_checks,
                    'created_at': i.created_at,
                } for i in recent_inspections],
            }
        })


class TaskStatsView(APIView):
    """任务统计"""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """获取任务统计数据"""
        # 定时任务统计
        task_total = ScheduledTask.objects.count()
        task_enabled = ScheduledTask.objects.filter(is_enabled=True).count()
        task_running = ScheduledTask.objects.filter(is_running=True).count()
        
        # 按任务类型统计
        type_stats = ScheduledTask.objects.values('task_type').annotate(
            total=Count('id'),
            enabled=Count('id', filter=Q(is_enabled=True)),
        )
        
        # 今日执行统计
        today = timezone.now().date()
        execution_today = ScheduledTaskExecution.objects.filter(
            start_time__date=today
        )
        execution_today_total = execution_today.count()
        execution_today_success = execution_today.filter(status='success').count()
        execution_today_failed = execution_today.filter(status='failed').count()
        
        # 最近执行记录
        recent_executions = ScheduledTaskExecution.objects.order_by('-start_time')[:10]
        
        return Response({
            'success': True,
            'data': {
                'task_stats': {
                    'total': task_total,
                    'enabled': task_enabled,
                    'running': task_running,
                },
                'execution_today': {
                    'total': execution_today_total,
                    'success': execution_today_success,
                    'failed': execution_today_failed,
                },
                'type_stats': list(type_stats),
                'recent_executions': [{
                    'id': e.id,
                    'task_name': e.task.name if e.task else None,
                    'task_type': e.task.task_type if e.task else None,
                    'status': e.status,
                    'start_time': e.start_time,
                    'end_time': e.end_time,
                    'duration': e.duration_ms,
                    'error_message': e.error_message,
                } for e in recent_executions],
            }
        })


class AssetHealthView(APIView):
    """资产健康状态"""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        """获取资产健康状态"""
        # 正常资产（状态ACTIVE且在线）
        healthy_assets = Asset.objects.filter(
            status='ACTIVE',
            online=True
        ).count()
        
        # 离线资产（状态ACTIVE但不在线）
        offline_assets = Asset.objects.filter(
            status='ACTIVE',
            online=False
        ).count()
        
        # 停用资产
        inactive_assets = Asset.objects.filter(status='INACTIVE').count()
        
        # 维护中资产
        maintenance_assets = Asset.objects.filter(status='MAINTENANCE').count()
        
        # 最近状态变更的资产
        recent_changes = Asset.objects.filter(
            status_history__isnull=False
        ).order_by('-status_history__created_at')[:10]
        
        # 计算健康度
        total_active = Asset.objects.filter(status='ACTIVE').count()
        health_rate = 0
        if total_active > 0:
            health_rate = round(healthy_assets / total_active * 100, 2)
        
        return Response({
            'success': True,
            'data': {
                'healthy_assets': healthy_assets,
                'offline_assets': offline_assets,
                'inactive_assets': inactive_assets,
                'maintenance_assets': maintenance_assets,
                'health_rate': health_rate,
                'recent_changes': [{
                    'asset_name': a.asset_name,
                    'asset_code': a.asset_code,
                    'status': a.status,
                    'online': a.online,
                    'last_check_time': a.last_check_time,
                } for a in recent_changes],
            }
        })
    
    def post(self, request):
        """刷新所有资产在线状态（Ping检测）"""
        import concurrent.futures
        import subprocess
        from django.utils import timezone
        
        def ping_asset(asset):
            """Ping单个资产，返回是否在线"""
            ip = getattr(asset, '_ping_ip', None) or asset.ip_address
            if not ip:
                return asset.id, False
            try:
                result = subprocess.run(
                    ['ping', '-c', '1', '-W', '2', ip],
                    capture_output=True,
                    timeout=3
                )
                return asset.id, result.returncode == 0
            except:
                return asset.id, False
        
        # 获取所有有IP的资产（优先用Asset.ip_address，否则查AssetData）
        all_assets = Asset.objects.all()
        assets_with_ip = []
        for asset in all_assets:
            ip = asset.ip_address
            if not ip:
                try:
                    ip_data = AssetData.objects.filter(
                        asset=asset, field__field_code='ip_address'
                    ).first()
                    ip = ip_data.string_value if ip_data else None
                except:
                    ip = None
            if ip:
                # 临时给 asset 对象挂上 _ping_ip 属性
                asset._ping_ip = ip
                assets_with_ip.append(asset)
        
        # 并发ping
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(ping_asset, a): a for a in assets_with_ip}
            for future in concurrent.futures.as_completed(futures, timeout=30):
                asset_id, is_online = future.result()
                results[asset_id] = is_online
        
        # 批量更新
        now = timezone.now()
        updated = 0
        for asset in assets_with_ip:
            new_online = results.get(asset.id, False)
            if asset.online != new_online:
                asset.online = new_online
                asset.last_check_time = now
                asset.save(update_fields=['online', 'last_check_time'])
                updated += 1
            else:
                asset.last_check_time = now
                asset.save(update_fields=['last_check_time'])
        
        online_count = sum(1 for v in results.values() if v)
        
        return Response({
            'success': True,
            'data': {
                'total': len(assets_with_ip),
                'online': online_count,
                'offline': len(assets_with_ip) - online_count,
                'updated': updated,
            },
            'message': f'检测完成，在线{online_count}，离线{len(assets_with_ip) - online_count}'
        })
