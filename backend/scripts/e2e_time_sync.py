#!/usr/bin/env python3
"""端到端验证：建一个 SNMP 巡检计划（含时间同步 + 阈值），对真实服务器执行一次，
检查 InspectionResult 落库结果。用完自动清理测试数据。"""
import os, json, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from apps.assets.models import Asset
from apps.inspection.models import InspectionPlan, InspectionTask, InspectionResult

ASSET_IP = '192.168.0.18'          # SNMP 可达
THRESHOLD = 60                      # 秒
PLAN_CODE = 'zz-e2e-time-sync'

asset = Asset.objects.filter(ip_address=ASSET_IP).first()
if not asset:
    print(f'❌ 找不到资产 {ASSET_IP}'); raise SystemExit(1)
print(f'目标资产: id={asset.id} {asset.asset_name} ({asset.ip_address}) protocol={asset.protocol}')

# 清理上次残留
for code in (PLAN_CODE,):
    InspectionPlan.objects.filter(code=code).delete()

# 登录（session 认证）
c = Client()
from apps.users.models import User
u = User.objects.filter(username='admin').first()
c.force_login(u)
print('已登录 admin')

# 1) 建计划：snmp + 时间同步（阈值 60 秒）
payload = {
    'name': 'E2E 时间同步检查',
    'code': PLAN_CODE,
    'description': '自动化验证用，可删除',
    'protocol': 'snmp',
    'cycle': 'daily',
    'scheduled_time': '03:00',
    'status': 'active',
    'check_items': [
        {'code': 'SNMP_REACHABLE', 'name': 'SNMP可达性'},
        {'code': 'TIME_SYNC', 'name': '时间同步', 'threshold': THRESHOLD},
    ],
}
r = c.post('/api/inspection/plans/', data=json.dumps(payload),
           content_type='application/json')
print(f'建计划 HTTP {r.status_code}')
plan = InspectionPlan.objects.filter(code=PLAN_CODE).first()
if not plan:
    print('❌ 计划未创建:', r.content[:300]); raise SystemExit(1)
print(f'  计划 id={plan.id}  check_items={plan.check_items}')

# 2) 建任务
from django.utils import timezone
task = InspectionTask.objects.create(plan=plan, asset=asset,
                                     scheduled_time=timezone.now(), status='pending')
print(f'建任务 id={task.id}')

# 3) 执行巡检
r = c.post(f'/api/inspection/tasks/{task.id}/execute/',
           data=json.dumps({}), content_type='application/json')
print(f'执行巡检 HTTP {r.status_code}')

# 4) 校验结果
print()
print('=' * 70)
print('InspectionResult 落库结果')
print('=' * 70)
rows = InspectionResult.objects.filter(task=task).order_by('id')
if not rows:
    print('❌ 没有巡检结果'); raise SystemExit(1)
for x in rows:
    print(f'  项目={x.check_item:<10} 状态={x.status:<8} severity={x.severity}')
    print(f'     result_value   = {x.result_value!r}')
    print(f'     result_message = {x.result_message}')
    if x.suggestion:
        print(f'     suggestion     = {x.suggestion}')

ts = rows.filter(check_item_code='TIME_SYNC').first()
print()
if ts:
    import re
    first = float(re.findall(r'[-+]?\d+\.?\d*', ts.result_value)[0])
    print(f'✅ 时间同步检查项已产出')
    print(f'   result_value 首个数字 = {first}（应为偏差绝对值，正数）')
    print(f'   severity = {ts.severity}（1=信息 2=警告 3=错误 4=严重）')
else:
    print('❌ 没有 TIME_SYNC 结果')

# 5) 清理
InspectionResult.objects.filter(task=task).delete()
task.delete()
plan.delete()
print()
print('已清理测试计划与任务')
