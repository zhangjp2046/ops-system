#!/usr/bin/env python3
import os
import sys
import django
from django.conf import settings

# 完全禁用系统检查
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# 手动配置，跳过 check
settings._wrapped = None

import conflocal as local_settings
for attr in dir(local_settings):
    if not attr.startswith('_'):
        setattr(settings, attr, getattr(local_settings, attr))

# 重新设置
from django.conf import settings
if not settings.configured:
    settings.configure(
        DEBUG=False,
        DATABASES=settings.DATABASES,
        INSTALLED_APPS=settings.INSTALLED_APPS,
        DEFAULT_AUTO_FIELD='django.db.models.AutoField',
    )

django.setup()

from apps.inspection.models import InspectionTask
from apps.scheduler_v2.models import Plan, PlanTask
from django.utils import timezone
from datetime import timedelta

print('开始迁移...\n')

tasks = InspectionTask.objects.filter(is_active=True).exclude(
    interval_minutes__in=['0', '', None]
).order_by('id')
task_list = list(tasks)
print(f'找到 {len(task_list)} 个定期巡检任务\n')

for itask in task_list:
    interval_str = getattr(itask, 'interval_minutes', '0') or '0'
    try:
        interval = int(interval_str)
    except (ValueError, TypeError):
        interval = 0
    if interval <= 0:
        continue
    if Plan.objects.filter(name=itask.name).exists():
        print(f'跳过: {itask.name} (已存在)')
        continue

    cron_map = {
        15: '*/15 * * * *', 30: '*/30 * * * *',
        60: '0 * * * *', 120: '0 */2 * * *',
        240: '0 */4 * * *', 480: '0 */8 * * *',
        720: '0 */12 * * *', 1440: '0 0 * * *'
    }
    cron = cron_map.get(interval, f'0 */{max(interval//60, 1)} * * *')

    customer_obj = getattr(itask, 'customer', None)
    customer_pk = customer_obj.pk if customer_obj else None
    insp_type = getattr(itask, 'inspection_type', 'SNMP') or 'SNMP'

    plan = Plan.objects.create(
        name=itask.name,
        description=f'从巡检任务迁移 (原ID:{itask.id})',
        plan_type='inspection',
        customer_id=customer_pk,
        is_enabled=bool(itask.is_active),
        cron_expression=cron,
        conflict_strategy='queue',
        notify_on_failure=True,
        notify_channels=['log']
    )
    plan.next_run_time = timezone.now() + timedelta(seconds=max(interval * 60, 300))
    plan.save()

    PlanTask.objects.create(
        plan=plan,
        name=f'{itask.name} - 巡检',
        task_type='inspection',
        execution_order=0,
        execution_mode='parallel',
        task_config={'customer_id': customer_pk, 'inspection_type': insp_type},
        timeout_seconds=300,
        max_retries=2,
        retry_interval_seconds=60,
        is_enabled=bool(itask.is_active)
    )

    print(f'✅ [{plan.id}] {plan.name} | 每{interval}min → {cron}')

count = Plan.objects.filter(description__contains='迁移').count()
print(f'\n🎉 完成! 共创建 {count} 个定时计划')
