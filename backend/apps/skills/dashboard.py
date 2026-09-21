"""
仪表盘刷新技能
定时刷新 Dashboard 数据，包括告警、巡检摘要、监控状态、统计概览
"""
import time
import datetime
from typing import Any, Dict

from .base import Skill, SkillResult
from .registry import SkillRegistry


@SkillRegistry.register
class DashboardRefreshSkill(Skill):
    """仪表盘刷新技能"""

    code = "dashboard_refresh"
    name = "仪表盘刷新"
    description = "刷新 Dashboard 数据，同时触发告警推送、巡检摘要计算等后台任务"

    param_schema = {
        "type": "object",
        "properties": {
            "refresh_alerts": {
                "type": "boolean",
                "default": True,
                "description": "刷新告警数据"
            },
            "refresh_inspection": {
                "type": "boolean",
                "default": True,
                "description": "刷新巡检摘要"
            },
            "refresh_monitoring": {
                "type": "boolean",
                "default": True,
                "description": "刷新监控状态"
            },
            "refresh_stats": {
                "type": "boolean",
                "default": True,
                "description": "刷新统计概览"
            },
            "refresh_tasks": {
                "type": "boolean",
                "default": True,
                "description": "刷新待处理任务"
            }
        }
    }

    def execute(self, config: dict, context: dict) -> SkillResult:
        start_time = time.time()
        results = {}

        try:
            if config.get('refresh_alerts', True):
                results['alerts'] = self._refresh_alerts()

            if config.get('refresh_inspection', True):
                results['inspection'] = self._refresh_inspection()

            if config.get('refresh_monitoring', True):
                results['monitoring'] = self._refresh_monitoring()

            if config.get('refresh_stats', True):
                results['stats'] = self._refresh_stats()

            if config.get('refresh_tasks', True):
                results['tasks'] = self._get_pending_tasks()

            return SkillResult.ok(
                data=results,
                duration_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            import traceback
            return SkillResult.fail(
                f"刷新异常: {str(e)}\n{traceback.format_exc()[:500]}"
            )

    def _refresh_alerts(self) -> dict:
        """刷新告警数据"""
        from apps.monitoring.models import Alert
        from django.db.models import Count

        open_count = Alert.objects.filter(status='open').count()
        acknowledged_count = Alert.objects.filter(status='acknowledged').count()
        critical_count = Alert.objects.filter(severity__gte=3, status='open').count()

        # 按严重程度分布
        by_severity = dict(
            Alert.objects.filter(status='open')
            .values('severity')
            .annotate(c=Count('id'))
            .values_list('severity', 'c')
        )

        # 按状态分布
        by_status = dict(
            Alert.objects.values('status').annotate(c=Count('id')).values_list('status', 'c')
        )

        # 最近告警
        recent = list(
            Alert.objects.filter(status='open').order_by('-occurred_at')[:5].values(
                'id', 'title', 'severity', 'status', 'asset__asset_name', 'occurred_at'
            )
        )

        return {
            'total_open': open_count,
            'total_acknowledged': acknowledged_count,
            'critical_count': critical_count,
            'by_severity': by_severity,
            'by_status': by_status,
            'recent': recent,
        }

    def _refresh_inspection(self) -> dict:
        """刷新巡检摘要"""
        from apps.inspection.models import Inspection
        from django.db.models import Count, Avg
        from django.utils import timezone
        from datetime import timedelta
        import django.db.models

        now = timezone.now()
        today = now.date()

        # 今日巡检统计
        today_insp = Inspection.objects.filter(started_at__date=today)
        today_total = today_insp.count()
        today_pass = today_insp.filter(status='COMPLETED').count()
        today_fail = today_insp.filter(status='FAILED').count()
        today_warning = today_insp.filter(status='WARNING').count()

        # 近7天趋势
        week_ago = today - timedelta(days=7)
        week_stats = Inspection.objects.filter(
            started_at__date__gte=week_ago
        ).aggregate(
            total=Count('id'),
            avg_duration=Avg('duration_ms')
        )

        # 最近巡检记录
        recent = list(
            Inspection.objects.order_by('-started_at')[:10].values(
                'id', 'asset__asset_name', 'status', 'total_items',
                'passed_items', 'warning_items', 'failed_items', 'started_at'
            )
        )

        return {
            'today': {
                'total': today_total,
                'passed': today_pass,
                'failed': today_fail,
                'warning': today_warning,
            },
            'week': week_stats,
            'recent': recent,
        }

    def _refresh_monitoring(self) -> dict:
        """刷新监控状态"""
        from apps.assets.status_refresher import DeviceStatusRefresher
        refresher = DeviceStatusRefresher()
        return refresher.refresh_all()

    def _refresh_stats(self) -> dict:
        """刷新统计概览"""
        from apps.assets.models import Asset
        from apps.monitoring.models import Alert
        from apps.inspection.models import Inspection
        from django.db.models import Count

        return {
            'total_assets': Asset.objects.count(),
            'active_assets': Asset.objects.filter(status='ACTIVE').count(),
            'online_assets': Asset.objects.filter(online=True).count(),
            'offline_assets': Asset.objects.filter(online=False).count(),
            'total_alerts': Alert.objects.filter(status__in=['open', 'acknowledged']).count(),
            'open_alerts': Alert.objects.filter(status='open').count(),
            'total_inspections': Inspection.objects.count(),
            'failed_inspections': Inspection.objects.filter(status='FAILED').count(),
        }

    def _get_pending_tasks(self) -> dict:
        """获取待处理任务（来自 scheduler_v2）"""
        from apps.scheduler_v2.models import PlanExecution
        from django.utils import timezone

        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.datetime(today.year, today.month, today.day, 0, 0, 0))

        pending = PlanExecution.objects.filter(status='pending', start_time__gte=today_start).count()
        in_progress = PlanExecution.objects.filter(status='running', start_time__gte=today_start).count()
        failed = PlanExecution.objects.filter(status='failed', start_time__gte=today_start).count()

        return {
            'pending': pending,
            'in_progress': in_progress,
            'failed': failed,
        }
