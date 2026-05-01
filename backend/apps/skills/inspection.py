"""
巡检技能 - 薄层封装，直接调用现有巡检计划的任务执行逻辑
"""
import time
from typing import Any, Dict

from django.utils import timezone

from .base import Skill, SkillResult
from .registry import SkillRegistry


@SkillRegistry.register
class InspectionSkill(Skill):
    """巡检技能（薄层，直接调用现有 InspectionTaskViewSet.execute 逻辑）"""

    code = "inspection"
    name = "巡检"
    description = "执行巡检计划，遍历关联的任务并调用原有的执行逻辑"

    param_schema = {
        "type": "object",
        "properties": {
            "inspection_plan_id": {
                "type": "integer",
                "description": "关联的巡检计划ID"
            },
            "force": {
                "type": "boolean",
                "default": False,
                "description": "强制重新执行（忽略今日已执行的限制）"
            }
        },
        "required": ["inspection_plan_id"]
    }

    def validate_config(self, config: dict) -> str:
        if not config.get('inspection_plan_id'):
            return "必须指定 inspection_plan_id"
        return None

    def execute(self, config: dict, context: dict) -> SkillResult:
        start_time = time.time()
        plan_id = config.get('inspection_plan_id')
        force = config.get('force', False)

        try:
            plan = self._get_plan(plan_id)
            if plan is None:
                return SkillResult.fail(f"巡检计划 {plan_id} 不存在")

            results = self._execute_plan_tasks(plan, force=force)
            return SkillResult.ok(
                data={'plan_id': plan_id, 'plan_name': plan.name, 'results': results},
                duration_ms=int((time.time() - start_time) * 1000)
            )
        except Exception as e:
            import traceback
            return SkillResult.fail(f"巡检执行异常: {str(e)}\n{traceback.format_exc()[:500]}")

    def _get_plan(self, plan_id: int):
        from apps.inspection.models import InspectionPlan
        try:
            return InspectionPlan.objects.get(id=plan_id)
        except InspectionPlan.DoesNotExist:
            return None

    def _execute_plan_tasks(self, plan, force: bool = False):
        """
        执行计划下所有任务，使用线程池并发执行。
        """
        from apps.inspection.models import InspectionTask
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import os

        all_tasks = list(InspectionTask.objects.filter(
            plan_id=plan.id
        ).select_related('asset', 'plan', 'asset__customer'))


        if not all_tasks:
            return [{'error': '计划没有关联任何巡检任务'}]

        # 根据任务数动态调整线程池大小，最多20个并发
        max_workers = min(len(all_tasks), int(os.environ.get('INSPECTION_POOL_SIZE', '10')))
        results = []

        def execute_single_task(task):
            """在子线程中执行单个任务"""
            try:
                result = self._execute_task_via_viewset(task)
                return {
                    'task_id': task.id,
                    'asset_name': task.asset.asset_name if task.asset else None,
                    'status': result.get('status', 'completed'),
                    'message': result.get('message', ''),
                    'passed': result.get('passed', 0),
                    'warning': result.get('warning', 0),
                    'failed': result.get('failed', 0),
                }
            except Exception as e:
                return {
                    'task_id': task.id,
                    'asset_name': task.asset.asset_name if task.asset else None,
                    'status': 'failed',
                    'message': str(e)[:200]
                }

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {pool.submit(execute_single_task, task): task for task in all_tasks}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    task = futures[future]
                    results.append({
                        'task_id': task.id,
                        'asset_name': task.asset.asset_name if task.asset else None,
                        'status': 'failed',
                        'message': str(e)[:200]
                    })

        return results

    def _execute_task_via_viewset(self, task):
        """
        通过 InspectionTaskViewSet 执行单个任务，复用原有代码路径。
        """
        from apps.inspection.views import InspectionTaskViewSet
        from rest_framework.test import APIRequestFactory
        from django.contrib.auth.models import AnonymousUser

        factory = APIRequestFactory()
        request = factory.post(f'/api/inspection/tasks/{task.id}/execute/')
        request.user = AnonymousUser()

        view = InspectionTaskViewSet.as_view({'post': 'execute'})
        response = view(request, pk=task.id)

        if response.status_code == 200:
            return response.data
        else:
            raise Exception(f"执行失败: {response.status_code} - {response.data}")
