"""
推送类技能：告警推送、巡检结果推送、状态推送
"""
import time
from typing import Any, Dict

from .base import Skill, SkillResult
from .registry import SkillRegistry


@SkillRegistry.register
class AlertPushSkill(Skill):
    """告警推送技能"""

    code = "push_alert"
    name = "告警推送"
    description = "将告警信息推送到外部系统"

    param_schema = {
        "type": "object",
        "properties": {
            "alert_ids": {
                "type": "array",
                "items": {"type": "integer"},
                "description": "指定告警ID列表（可选）"
            },
            "customer_id": {
                "type": "integer",
                "description": "客户ID（未指定 alert_ids 时使用，推送该客户所有未关闭告警）"
            }
        }
    }

    def execute(self, config: dict, context: dict) -> SkillResult:
        start_time = time.time()
        from apps.dashboard.push_service import push_alerts

        alert_ids = config.get('alert_ids')
        customer_id = config.get('customer_id') or context.get('customer_id')

        result = push_alerts(customer_id=customer_id, alert_ids=alert_ids)
        return SkillResult.ok(
            data={'pushed': result.get('sent_count', 0), 'result': result},
            duration_ms=int((time.time() - start_time) * 1000)
        )


@SkillRegistry.register
class InspectionResultPushSkill(Skill):
    """巡检结果推送技能"""

    code = "push_inspection"
    name = "巡检结果推送"
    description = "将巡检结果推送到外部系统"

    param_schema = {
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "integer",
                "description": "客户ID（可选，不指定则推送所有）"
            },
            "limit": {
                "type": "integer",
                "default": 50,
                "description": "最多推送条数"
            }
        }
    }

    def execute(self, config: dict, context: dict) -> SkillResult:
        start_time = time.time()
        from apps.dashboard.push_service import push_inspection_result
        from apps.inspection.models import InspectionTask

        customer_id = config.get('customer_id') or context.get('customer_id')
        limit = config.get('limit', 50)

        if customer_id:
            inspections = InspectionTask.objects.filter(
                plan__customer_id=customer_id
            ).select_related('plan', 'asset').order_by('-id')[:limit]
        else:
            inspections = InspectionTask.objects.select_related('plan', 'asset').order_by('-id')[:limit]

        inspections = list(inspections)
        if not inspections:
            return SkillResult.ok(
                data={'message': '没有可推送的巡检结果', 'count': 0},
                duration_ms=int((time.time() - start_time) * 1000)
            )

        results = []
        for inspection in inspections:
            result = push_inspection_result(inspection)
            results.append(result)
        
        return SkillResult.ok(
            data={'pushed': len(inspections), 'results': results},
            duration_ms=int((time.time() - start_time) * 1000)
        )


@SkillRegistry.register
class StatusPushSkill(Skill):
    """状态推送技能"""

    code = "push_status"
    name = "状态推送"
    description = "推送资产状态到外部系统"

    param_schema = {
        "type": "object",
        "properties": {
            "customer_id": {
                "type": "integer",
                "description": "客户ID（可选，不指定则推送所有）"
            },
            "limit": {
                "type": "integer",
                "default": 100,
                "description": "最多推送数量"
            }
        }
    }

    def execute(self, config: dict, context: dict) -> SkillResult:
        start_time = time.time()
        from apps.dashboard.push_service import push_asset_statuses
        from apps.assets.models import Asset

        customer_id = config.get('customer_id') or context.get('customer_id')
        limit = config.get('limit', 100)

        if customer_id:
            assets = Asset.objects.filter(customer_id=customer_id)[:limit]
        else:
            assets = Asset.objects.all()[:limit]

        assets = list(assets)
        result = push_asset_statuses(assets)
        return SkillResult.ok(
            data={'pushed': len(assets), 'result': result},
            duration_ms=int((time.time() - start_time) * 1000)
        )
