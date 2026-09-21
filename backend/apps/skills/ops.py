"""
运维类技能：状态刷新、发现扫描、清理、报表
"""
import time
from datetime import timedelta
from typing import Any, Dict

from django.utils import timezone

from .base import Skill, SkillResult
from .registry import SkillRegistry


@SkillRegistry.register
class StatusRefreshSkill(Skill):
    """状态刷新技能"""

    code = "status_refresh"
    name = "状态刷新"
    description = "刷新资产状态（在线/离线等）"

    param_schema = {
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "integer",
                "description": "客户ID（可选，不指定则刷新所有）"
            }
        }
    }

    def execute(self, config: dict, context: dict) -> SkillResult:
        start_time = time.time()
        from apps.assets.status_refresher import DeviceStatusRefresher

        customer_id = config.get('customer_id') or context.get('customer_id')
        refresher = DeviceStatusRefresher()

        if customer_id:
            result = refresher.refresh_customer_assets(customer_id)
        else:
            result = refresher.refresh_all()

        return SkillResult.ok(
            data=result,
            duration_ms=int((time.time() - start_time) * 1000)
        )


@SkillRegistry.register
class DiscoveryScanSkill(Skill):
    """网络发现扫描技能"""

    code = "discovery_scan"
    name = "发现扫描"
    description = "扫描网段发现设备"

    param_schema = {
        "type": "object",
        "properties": {
            "subnets": {
                "type": "array",
                "items": {"type": "string"},
                "description": "扫描网段列表，如 ['192.168.1.0/24']"
            },
            "scan_type": {
                "type": "string",
                "enum": ["ping", "tcp", "all"],
                "default": "ping",
                "description": "扫描方式"
            },
            "customer_id": {
                "type": "integer",
                "description": "客户ID（可选）"
            }
        },
        "required": ["subnets"]
    }

    def validate_config(self, config: dict) -> str:
        if not config.get('subnets'):
            return "必须指定扫描网段 subnets"
        return None

    def execute(self, config: dict, context: dict) -> SkillResult:
        start_time = time.time()
        from apps.discovery.network_scanner import run_discovery

        subnets = config.get('subnets', [])
        scan_type = config.get('scan_type', 'ping')
        timeout = config.get('timeout', 10)

        if not subnets:
            return SkillResult.fail("必须指定扫描网段")

        devices = run_discovery(
            target_ranges=subnets,
            scan_type=scan_type,
            timeout=min(timeout, 10)
        )

        return SkillResult.ok(
            data={
                'scanned': len(devices),
                'subnets': subnets,
                'devices': [{'ip': d['ip'], 'device_type': d.get('device_type')} for d in devices]
            },
            duration_ms=int((time.time() - start_time) * 1000)
        )


@SkillRegistry.register
class CleanupSkill(Skill):
    """清理过期数据技能"""

    code = "cleanup"
    name = "数据清理"
    description = "清理过期的监控结果和告警记录"

    param_schema = {
        "type": "object",
        "properties": {
            "retention_days": {
                "type": "integer",
                "default": 90,
                "description": "保留天数（超过此天数的记录将被删除）"
            }
        }
    }

    def execute(self, config: dict, context: dict) -> SkillResult:
        start_time = time.time()
        from apps.monitoring.models import MonitoringResult, Alert

        retention_days = config.get('retention_days', 90)
        expired = timezone.now() - timedelta(days=retention_days)

        deleted_results = MonitoringResult.objects.filter(start_time__lt=expired).delete()[0]
        deleted_alerts = Alert.objects.filter(status='closed', occurred_at__lt=expired).delete()[0]

        return SkillResult.ok(
            data={
                'deleted_results': deleted_results,
                'deleted_alerts': deleted_alerts,
                'retention_days': retention_days
            },
            duration_ms=int((time.time() - start_time) * 1000)
        )


@SkillRegistry.register
class ReportSkill(Skill):
    """生成报表技能"""

    code = "report"
    name = "生成报表"
    description = "生成资产和告警统计报表"

    param_schema = {
        "type": "object",
        "properties": {
            "report_type": {
                "type": "string",
                "enum": ["summary", "detailed"],
                "default": "summary",
                "description": "报表类型"
            },
            "customer_id": {
                "type": "integer",
                "description": "客户ID（可选，不指定则生成全局报表）"
            },
            "dry_run": {
                "type": "boolean",
                "default": False,
                "description": "预览模式，仅返回内容不发送"
            }
        }
    }

    def execute(self, config: dict, context: dict) -> SkillResult:
        start_time = time.time()
        from apps.assets.models import Asset
        from apps.monitoring.models import Alert
        from django.utils import timezone

        report_type = config.get('report_type', 'summary')
        customer_id = config.get('customer_id') or context.get('customer_id')
        dry_run = config.get('dry_run', False)

        # 获取资产数据
        if customer_id:
            assets = Asset.objects.filter(customer_id=customer_id)
            total = assets.count()
            active = assets.filter(status='ACTIVE').count()
            open_alerts = Alert.objects.filter(customer_id=customer_id, status__in=['open', 'acknowledged']).count()
        else:
            assets = Asset.objects.all()
            total = assets.count()
            active = assets.filter(status='ACTIVE').count()
            open_alerts = Alert.objects.filter(status__in=['open', 'acknowledged']).count()

        # 生成明文报表
        lines = []
        lines.append("=" * 60)
        lines.append("运维系统 - 资产统计报表")
        lines.append("=" * 60)
        lines.append(f"生成时间: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"报表类型: {'详细' if report_type == 'detailed' else '概要'}")
        if customer_id:
            lines.append(f"客户ID: {customer_id}")
        lines.append("")
        lines.append("-" * 60)
        lines.append("【统计摘要】")
        lines.append("-" * 60)
        lines.append(f"资产总数: {total}")
        lines.append(f"活跃资产: {active}")
        lines.append(f"离线资产: {total - active}")
        lines.append(f"未关闭告警: {open_alerts}")
        lines.append("")

        # 详细模式下，列出所有资产
        if report_type == 'detailed':
            lines.append("-" * 60)
            lines.append("【资产明细】")
            lines.append("-" * 60)
            lines.append(f"{'序号':<4} {'资产名称':<30} {'IP地址':<15} {'类型':<12} {'状态':<8} {'在线':<6}")
            lines.append("-" * 60)
            for idx, asset in enumerate(assets[:200], 1):  # 最多200条
                online_str = "在线" if asset.online else "离线"
                status_str = asset.status or ""
                asset_type = str(asset.asset_type) if asset.asset_type else ""
                lines.append(
                    f"{idx:<4} "
                    f"{asset.asset_name:<30} "
                    f"{(asset.ip_address or '-'):<15} "
                    f"{asset_type:<12} "
                    f"{status_str:<8} "
                    f"{online_str:<6}"
                )
            if assets.count() > 200:
                lines.append(f"... (共 {assets.count()} 条，仅显示前200条)")

        lines.append("")
        lines.append("=" * 60)
        lines.append("报表生成完成")
        lines.append("=" * 60)

        plain_text = "\n".join(lines)

        # 如果是预览模式，直接返回内容
        if dry_run:
            return SkillResult.ok(
                data={
                    'preview': plain_text,
                    'asset_count': total,
                    'alert_count': open_alerts,
                    'generated_at': timezone.now().isoformat()
                },
                duration_ms=int((time.time() - start_time) * 1000)
            )

        # 发送到 ops-center（不含敏感字段）
        from apps.dashboard.push_service import _post
        payload = {
            'report_type': 'asset_inventory',
            'generated_at': timezone.now().isoformat(),
            'summary': {
                'total_assets': total,
                'active_assets': active,
                'offline_assets': total - active,
                'open_alerts': open_alerts,
            },
            'plain_text': plain_text,
            'assets': [
                {
                    'id': a.id,
                    'name': a.asset_name,
                    'ip': a.ip_address or '',
                    'type': str(a.asset_type) if a.asset_type else '',
                    'status': a.status or '',
                    'online': a.online,
                    # 排除敏感字段：username, password, description等
                }
                for a in (assets[:200] if report_type == 'detailed' else [])
            ]
        }

        result = _post('reports/', payload, push_type='report')

        return SkillResult.ok(
            data={
                'report_type': report_type,
                'total_assets': total,
                'active_assets': active,
                'open_alerts': open_alerts,
                'sent_to_opscenter': result is not None,
                'generated_at': timezone.now().isoformat(),
                'preview': plain_text,  # 也返回预览供确认
            },
            duration_ms=int((time.time() - start_time) * 1000)
        )
