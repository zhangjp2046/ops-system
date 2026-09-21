"""
调度计划同步触发命令
每分钟由系统 crontab 调用，检查并执行到期的 Plan。
用法: python manage.py scheduler_sync
"""
import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.scheduler_v2.models import Plan, PlanTask, PlanExecution, TaskInstance

logger = logging.getLogger(__name__)


def run_plan_sync(plan_id):
    """同步执行计划，等待完成"""
    from apps.scheduler_v2.executor import TaskExecutor

    try:
        plan = Plan.objects.get(id=plan_id)
    except Plan.DoesNotExist:
        return {'error': f'Plan {plan_id} 不存在'}

    # 检查是否有正在运行的执行
    running = PlanExecution.objects.filter(plan=plan, status__in=['running', 'pending']).exists()
    if running:
        return {'error': '有执行中的实例，跳过'}

    # 创建执行记录
    execution = PlanExecution.objects.create(
        plan=plan,
        status='running',
        trigger='schedule'
    )

    try:
        tasks = list(plan.tasks.filter(is_enabled=True).order_by('execution_order'))
        execution.total_tasks = len(tasks)
        execution.save()

        for task in tasks:
            inst = TaskInstance.objects.create(
                plan_execution=execution,
                plan_task=task,
                status='running',
                start_time=timezone.now()
            )
            try:
                result = TaskExecutor.execute(task.task_type, task.task_config or {}, None)
                if result.get('success', False):
                    inst.mark_completed('success', result)
                else:
                    inst.mark_completed('failed', error_message=result.get('error', 'Unknown error'))
            except Exception as e:
                inst.mark_completed('failed', error_message=str(e))

        instances = execution.task_instances.all()
        execution.success_tasks = instances.filter(status='success').count()
        execution.failed_tasks = instances.filter(status='failed').count()
        execution.completed_tasks = execution.success_tasks + execution.failed_tasks

        if execution.failed_tasks == 0:
            execution.mark_completed('success')
        elif execution.success_tasks > 0:
            execution.mark_completed('failed')
        else:
            execution.mark_completed('failed')

        return {
            'execution_id': execution.id,
            'success': execution.success_tasks,
            'failed': execution.failed_tasks
        }

    except Exception as e:
        execution.mark_completed('failed', error_message=str(e))
        return {'error': str(e)}


class Command(BaseCommand):
    help = '检查并执行到期的调度计划'

    def handle(self, *args, **options):
        now = timezone.now()
        plans = Plan.objects.filter(is_enabled=True, next_run_time__lte=now)

        if not plans.exists():
            self.stdout.write(f'[{now}] No plans due')
            return

        for plan in plans:
            self.stdout.write(f'触发: {plan.name} (next_run={plan.next_run_time})')
            result = run_plan_sync(plan.id)
            self.stdout.write(f'  结果: {result}')

            plan.last_run_time = now
            plan.calculate_next_run_time()
            plan.save()
            self.stdout.write(f'  下次执行: {plan.next_run_time}')
