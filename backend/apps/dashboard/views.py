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
from apps.scheduler_v2.models import Plan as ScheduledTask
from apps.scheduler_v2.models import PlanExecution as ScheduledTaskExecution


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
        
        # 获取最近检查时间
        last_check = Asset.objects.filter(
            last_check_time__isnull=False
        ).order_by('-last_check_time').values_list('last_check_time', flat=True).first()
        
        return Response({
            'success': True,
            'data': {
                'overview': {
                    'total_customers': customer_count,
                    'total_assets': asset_total,
                    'active_assets': asset_active,
                    'online_assets': asset_online,
                    'offline_assets': asset_offline,
                    'last_check_time': last_check,
                },
                'status_distribution': list(status_stats),
                'importance_distribution': list(importance_stats),
                'type_distribution': list(type_stats),
                'customer_distribution': list(customer_stats),
                # 推送统计
                'push_stats': _get_push_stats(),
                'push_enabled': _is_push_enabled(),
                # 补丁版本信息
                'patch_info': _get_patch_info(),
                # 今日巡检任务
                'today_inspection_tasks': _get_today_inspection_tasks(),
            }
        })


def _get_push_stats():
    """获取推送统计"""
    from apps.dashboard.models import PushLog
    from datetime import datetime, timedelta
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    today_logs = PushLog.objects.filter(
        created_at__gte=today_start,
        created_at__lt=today_end
    )
    last_success = PushLog.objects.filter(status='success').order_by('-created_at').first()
    last_fail = PushLog.objects.filter(status='failed').order_by('-created_at').first()
    return {
        'today_total': today_logs.count(),
        'today_success': today_logs.filter(status='success').count(),
        'today_failed': today_logs.filter(status='failed').count(),
        'last_push_at': last_success.created_at.isoformat() if last_success else None,
        'last_fail_at': last_fail.created_at.isoformat() if last_fail else None,
        'last_fail_error': last_fail.error_message if last_fail else None,
    }


def _is_push_enabled():
    """检查推送是否启用"""
    try:
        from apps.system.models import SystemSetting
        return SystemSetting.get('push.enabled', 'false').lower() == 'true'
    except Exception:
        return False


def _get_patch_info():
    """获取本地补丁版本信息，以及是否有新版本"""
    import os, json
    info = {
        'local_version': '',
        'needs_update': False,
        'latest_version': '',
        'changelog': [],
    }
    # 读取补丁检查缓存（由 push_service._deferred_patch_check 写入）
    cache_path = os.path.expanduser('~/.openclaw/patches/patch_check_cache.json')
    if os.path.exists(cache_path):
        try:
            cached = json.load(open(cache_path))
            info.update(cached)
        except Exception:
            pass
    # 如果缓存不存在，至少读本地版本文件
    if not info['local_version']:
        ver_file = os.path.expanduser('~/.openclaw/patches/patch_version.txt')
        if os.path.exists(ver_file):
            try:
                info['local_version'] = open(ver_file).read().strip()
            except Exception:
                pass
    return info


def _get_today_inspection_tasks():
    """获取今日巡检任务统计（基于 InspectionRecord）"""
    today = timezone.now().date()
    records_today = InspectionRecord.objects.filter(created_at__date=today)
    return {
        'total': records_today.count(),
        'completed': records_today.filter(status='completed').count(),
        'pending': records_today.filter(status='pending').count(),
        'failed': records_today.filter(overall_status='fail').count(),
    }


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
        from apps.alerts.models import Alert as AlertModel
        
        # 告警总体统计
        alert_total = AlertModel.objects.count()
        
        # 按状态统计（使用实际的 STATUS_CHOICES）
        status_stats = {}
        for code, label in AlertModel.STATUS_CHOICES:
            status_stats[code] = AlertModel.objects.filter(status=code).count()
        
        # 未处理告警数 = NEW + ACKNOWLEDGED + IN_PROGRESS
        unhandled_count = sum(
            status_stats.get(s, 0) for s in ['NEW', 'ACKNOWLEDGED', 'IN_PROGRESS']
        )
        
        # 按严重程度统计
        severity_stats = list(AlertModel.objects.values('severity').annotate(count=Count('id')))
        
        # 按来源统计
        source_stats = list(AlertModel.objects.values('source').annotate(count=Count('id')))
        
        # 今日新增告警
        today = timezone.now().date()
        alert_today = AlertModel.objects.filter(occurred_at__date=today).count()
        
        # 最近24小时告警
        yesterday = timezone.now() - timedelta(hours=24)
        alert_recent_24h = AlertModel.objects.filter(occurred_at__gte=yesterday).count()
        
        # 高危告警（严重程度>=3 且未处理）
        critical_count = AlertModel.objects.filter(
            severity__gte=3,
            status__in=['NEW', 'ACKNOWLEDGED', 'IN_PROGRESS']
        ).count()
        
        # 未处理的告警（最新10条）
        unhandled_alerts = AlertModel.objects.filter(
            status__in=['NEW', 'ACKNOWLEDGED', 'IN_PROGRESS']
        ).select_related('asset', 'customer').order_by('-occurred_at')[:10]
        
        return Response({
            'success': True,
            'data': {
                'total': alert_total,
                'unhandled_count': unhandled_count,
                'by_status': status_stats,
                'by_severity': {item['severity']: item['count'] for item in severity_stats},
                'by_source': {item['source']: item['count'] for item in source_stats},
                'today_count': alert_today,
                'recent_24h_count': alert_recent_24h,
                'critical_count': critical_count,
                'unhandled_alerts': [{
                    'id': a.id,
                    'title': a.title,
                    'severity': a.get_severity_display(),
                    'severity_code': a.severity,
                    'status': a.status,
                    'status_display': a.get_status_display(),
                    'source': a.source,
                    'source_display': a.get_source_display(),
                    'alert_type': a.alert_type,
                    'asset_name': a.asset.asset_name if a.asset else None,
                    'customer_name': a.customer.customer_name if a.customer else None,
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
        task_enabled = ScheduledTask.objects.filter(status='active').count()
        task_running = ScheduledTask.objects.filter(status='active').count()
        
        # 按任务类型统计
        type_stats = ScheduledTask.objects.values('plan_type').annotate(
            total=Count('id'),
            enabled=Count('id', filter=Q(status='active')),
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
                    'task_name': getattr(e.plan, 'name', None) if e.plan else None,
                    'task_type': getattr(e.plan, 'plan_type', None) if e.plan else None,
                    'status': e.status,
                    'start_time': e.start_time,
                    'end_time': e.end_time,
                    'duration': e.duration_ms,
                    'error_message': e.error_message,
                } for e in recent_executions],
            }
        })


class AssetHealthView(APIView):
    """资产健康状态 - Ping检测"""
    
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
        
        # 最近检查时间
        last_check = Asset.objects.filter(
            last_check_time__isnull=False
        ).order_by('-last_check_time').values_list('last_check_time', flat=True).first()
        
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
                'last_check_time': last_check,
            }
        })
    
    def post(self, request):
        """
        刷新所有资产在线状态（Ping检测）
        使用并发ping，更新Asset.online字段
        """
        from .ping_service import check_all_assets
        
        # 获取参数
        max_workers = int(request.data.get('max_workers', 20))
        
        # 执行检测
        result = check_all_assets(max_workers=max_workers)
        
        return Response({
            'success': True,
            'data': {
                'total': result['total'],
                'online': result['online'],
                'offline': result['offline'],
                'skipped': result['skipped'],
                'updated': result['updated'],
                'elapsed_seconds': result['elapsed_seconds'],
            },
            'message': f'检测完成: 在线{result["online"]}台, 离线{result["offline"]}台, 耗时{result["elapsed_seconds"]}秒'
        })

class PushRetryView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        from apps.dashboard.models import PushLog
        push_type = request.query_params.get('type')
        status = request.query_params.get('status', 'failed')
        pending_only = request.query_params.get('pending') == '1'
        qs = PushLog.objects.filter(status=status)
        if push_type:
            qs = qs.filter(push_type=push_type)
        if pending_only:
            qs = qs.filter(retry_count__lt=5).filter(Q(next_retry_at__isnull=True) | Q(next_retry_at__lte=timezone.now()))
        logs = qs[:50]
        return Response({'success': True, 'count': logs.count(), 'logs': [{
            'id': log.id, 'push_type': log.push_type, 'status': log.status,
            'endpoint': log.endpoint, 'records_count': log.records_count,
            'error_message': log.error_message, 'retry_count': log.retry_count,
            'next_retry_at': log.next_retry_at.isoformat() if log.next_retry_at else None,
            'created_at': log.created_at.isoformat(),
        } for log in logs]})
    def post(self, request):
        from .push_service import retry_failed
        log_id = request.data.get('log_id')
        push_type = request.query_params.get('type')
        if not log_id and not push_type:
            return Response({'success': False, 'message': '请指定 log_id 或 type 参数'}, status=400)
        success, failed = retry_failed(log_id=log_id, push_type=push_type, limit=20)
        return Response({'success': True, 'message': f'重试完成: {success} 成功, {failed} 失败',
            'success_count': success, 'failed_count': failed})


class PushReportView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        from .push_service import get_config, _post
        enabled, url, api_key, timeout = get_config()
        if not enabled or not url:
            return Response({'success': False, 'message': '推送未启用或未配置中心地址'}, status=400)
        from apps.assets.models import Asset
        from apps.monitoring.models import Alert
        assets = Asset.objects.all()
        total = assets.count()
        active_assets = assets.filter(online=True).count()
        open_alerts = Alert.objects.filter(status__in=['new', 'acknowledged']).count()
        payload = {
            'report_type': 'asset_inventory',
            'generated_at': timezone.now().isoformat(),
            'summary': {
                'total_assets': total, 'active_assets': active_assets,
                'offline_assets': total - active_assets, 'open_alerts': open_alerts,
            },
            'assets': [{
                'id': a.id, 'name': a.asset_name, 'ip': a.ip_address or '',
                'type': str(a.asset_type) if a.asset_type else '',
                'status': a.status or '', 'online': a.online,
            } for a in assets[:200]],
        }
        result = _post('reports/', payload, push_type='report')
        if result:
            return Response({'success': True, 'message': f'资产报表已推送 (总资产: {total}, 在线: {active_assets})',
                'total_assets': total, 'active_assets': active_assets})
        else:
            return Response({'success': False, 'message': '推送失败'}, status=502)
