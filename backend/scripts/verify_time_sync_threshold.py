#!/usr/bin/env python3
"""验证「时间同步」在告警阈值配置里的落地（方案 A）

覆盖：
  A. 5 个协议各有一行 TIME_SYNC 全局行，且**故意不配阈值**
  B. 回归：这些行不能吃掉巡检侧的 status（曾经会把 9000s 偏差压成「信息」）
  C. 链路仍支持真正的阈值：客户级带阈值的行照常生效；
     客户级「空行」也不会遮蔽全局带阈值行（会继续往下找）
  D. 监控项开关：不勾 → 无趋势数据；勾上 → 偏差值记进 MonitoringDataPoint
  E. 同类空阈值行（DB_VERSION 等）的 status 不再被吃掉

所有测试数据用完即删，对环境无残留。
"""
import os
import re
import json
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.utils import timezone

from apps.assets.models import Asset
from apps.alerts.alert_generator import determine_severity, get_threshold_severity
from apps.alerts.threshold_models import AlertThreshold
from apps.inspection.models import InspectionPlan, InspectionTask, InspectionResult
from apps.monitoring.models import MonitoringDataPoint
from apps.users.models import User

PROTOCOLS = ['snmp', 'mysql', 'mssql', 'oracle', 'postgresql']
ASSET_IP = '192.168.0.18'
PLAN_CODE = 'zz-verify-ts-threshold'
THRESHOLD = 60
CUSTOMER_ID = 1

ok_all = True


def check(label, cond, extra=''):
    global ok_all
    mark = '✅' if cond else '❌'
    if not cond:
        ok_all = False
    print(f'{mark} {label}' + (f' | {extra}' if extra else ''))


def global_row(protocol):
    return AlertThreshold.objects.filter(
        customer__isnull=True, asset_type__isnull=True,
        check_item_code='TIME_SYNC', protocol=protocol).first()


print('=' * 74)
print('A. 阈值配置行存在性（5 个协议，全局行，不配阈值）')
print('=' * 74)
for p in PROTOCOLS:
    row = global_row(p)
    if not row:
        check(f'{p} / TIME_SYNC 行存在', False, '缺失 —— 请先跑 manage.py seed_time_sync_thresholds')
        continue
    empty = not (row.warning_threshold or row.error_threshold or row.critical_threshold)
    check(f'{p} / TIME_SYNC 行存在且三阈值留空', empty,
          f'dir={row.threshold_direction} warn={row.warning_threshold!r}')
    check(f'{p} / TIME_SYNC 行不参与判定（has_effective_threshold=False）',
          row.has_effective_threshold() is False)

print()
print('=' * 74)
print('B. 回归：行存在也不能吃掉巡检侧的 status')
print('=' * 74)
for status, value, expect in [('pass', '偏差 0.2s', (1, '信息')),
                              ('warning', '偏差 500s', (2, '警告')),
                              ('fail', '偏差 9000s', (3, '错误'))]:
    got = determine_severity('TIME_SYNC', value, status,
                             customer_id=CUSTOMER_ID, asset_type_id=None)
    check(f'{value:<12} status={status:<8} → {expect[1]}', got == expect, f'得到 {got}')
    found = get_threshold_severity('TIME_SYNC', value, CUSTOMER_ID, None)[2]
    check(f'   未被阈值行接管（threshold_found=False）', found is False, f'found={found}')

print()
print('=' * 74)
print('C. 链路仍支持真正的阈值（客户级行 / 往下寻找的优先级）')
print('=' * 74)
cust_row = AlertThreshold.objects.create(
    customer_id=CUSTOMER_ID, asset_type=None,
    check_item_code='TIME_SYNC', check_item_name='时间同步', protocol='snmp',
    threshold_direction='upper', unit='秒', is_active=True,
    warning_threshold='60', critical_threshold='300',
)
try:
    for value, expect in [('偏差 5s', (1, '信息')), ('偏差 100s', (2, '警告')),
                          ('偏差 500s', (4, '严重'))]:
        got = determine_severity('TIME_SYNC', value, 'warning',
                                 customer_id=CUSTOMER_ID, asset_type_id=None)
        check(f'客户级阈值(warn=60/crit=300) {value:<12} → {expect[1]}',
              got == expect, f'得到 {got}')
finally:
    cust_row.delete()

# 客户级「空行」不该遮蔽全局带阈值的行
cust_empty = AlertThreshold.objects.create(
    customer_id=CUSTOMER_ID, asset_type=None,
    check_item_code='TIME_SYNC', check_item_name='时间同步', protocol='snmp',
    threshold_direction='exact', unit='秒', is_active=True,
)
grow = global_row('snmp')
saved = (grow.warning_threshold, grow.threshold_direction)
try:
    grow.warning_threshold, grow.threshold_direction = '60', 'upper'
    grow.save(update_fields=['warning_threshold', 'threshold_direction'])
    got = determine_severity('TIME_SYNC', '偏差 100s', 'warning',
                             customer_id=CUSTOMER_ID, asset_type_id=None)
    check('客户级空行不遮蔽全局带阈值行 → 仍取到警告', got == (2, '警告'), f'得到 {got}')
    got_none = get_threshold_severity('TIME_SYNC', '偏差 100s', CUSTOMER_ID, None)
    check('   实际命中的是全局行（found=True）', got_none[2] is True, f'{got_none}')
finally:
    cust_empty.delete()
    grow.warning_threshold, grow.threshold_direction = saved
    grow.save(update_fields=['warning_threshold', 'threshold_direction'])

print()
print('=' * 74)
print('E. 同类空阈值行（DB_VERSION）也不该吃掉 status —— 顺带修掉的既有问题')
print('=' * 74)
got = determine_severity('DB_VERSION', '8.0.32', 'fail',
                         customer_id=CUSTOMER_ID, asset_type_id=None)
check('DB_VERSION fail → 错误(3)（修复前会被压成信息(1)）', got == (3, '错误'), f'得到 {got}')
got = determine_severity('SNMP_REACHABLE', '可达', 'fail', customer_id=CUSTOMER_ID)
check('SNMP_REACHABLE fail → 错误(3)', got == (3, '错误'), f'得到 {got}')

print()
print('=' * 74)
print('F. 阈值查表按 protocol 隔离（既有 bug：MSSQL/Oracle 曾被 PostgreSQL 的阈值判定）')
print('=' * 74)
sess = {t.protocol: t for t in AlertThreshold.objects.filter(check_item_code='SESSIONS')}
print('   各协议 SESSIONS 行:', {p: r.warning_threshold for p, r in sess.items()})
if len(sess) < 2:
    check('SESSIONS 各协议行齐备（用于对照）', False, f'只有 {list(sess)}')
else:
    # 每个协议用自己的行判定
    for proto, value, expect in [('mssql', '120 个', (1, '信息')),      # warn=150
                                 ('oracle', '150 个', (1, '信息')),     # warn=200
                                 ('postgresql', '120 个', (2, '警告'))]:  # warn=100
        got = determine_severity('SESSIONS', value, 'warning',
                                 customer_id=CUSTOMER_ID, asset_type_id=None, protocol=proto)
        check(f'{proto:<11} 会话数 {value:<8} 用自己那行 → {expect[1]}', got == expect, f'得到 {got}')

    # 同协议没有行时，不跨协议借用，回落到 status
    has_mysql_row = 'mysql' in sess
    if not has_mysql_row:
        got = determine_severity('SESSIONS', '120 个', 'fail',
                                 customer_id=CUSTOMER_ID, asset_type_id=None, protocol='mysql')
        check('mysql 无该行 → 不借用别的协议，按 status 兜底 → 错误(3)',
              got == (3, '错误'), f'得到 {got}')
        found = get_threshold_severity('SESSIONS', '120 个', CUSTOMER_ID, None, 'mysql')[2]
        check('   threshold_found=False（未串到其它协议）', found is False, f'found={found}')
    else:
        print('   （mysql 已有 SESSIONS 行，跳过「无行兜底」用例）')

    # 协议感知不影响正确命中：传对协议时 found=True
    found = get_threshold_severity('SESSIONS', '120 个', CUSTOMER_ID, None, 'mssql')[2]
    check('传对协议时正常命中该协议的行（found=True）', found is True, f'found={found}')

print()
print('=' * 74)
print('D. 监控项开关 → 偏差值进监控中心趋势（正/反向对照，跑真实巡检）')
print('=' * 74)
asset = Asset.objects.filter(ip_address=ASSET_IP).first()
row = global_row('snmp')
if not asset or not row:
    check('前置条件（资产 + snmp TIME_SYNC 行）', False)
else:
    c = Client()
    c.force_login(User.objects.filter(username='admin').first())
    InspectionPlan.objects.filter(code=PLAN_CODE).delete()
    payload = {
        'name': '验证时间同步阈值配置', 'code': PLAN_CODE, 'protocol': 'snmp',
        'cycle': 'daily', 'scheduled_time': '03:00', 'status': 'active',
        'check_items': [{'code': 'TIME_SYNC', 'name': '时间同步', 'threshold': THRESHOLD}],
    }
    r = c.post('/api/inspection/plans/', data=json.dumps(payload),
               content_type='application/json')
    plan = InspectionPlan.objects.filter(code=PLAN_CODE).first()
    if not plan:
        check('建计划', False, r.content[:200])
    else:
        original_flag = row.is_monitoring_item
        created_tasks = []
        try:
            for flag, label in [(False, '不勾监控项'), (True, '勾上监控项')]:
                row.is_monitoring_item = flag
                row.save(update_fields=['is_monitoring_item'])

                task = InspectionTask.objects.create(
                    plan=plan, asset=asset, scheduled_time=timezone.now(), status='pending')
                created_tasks.append(task)
                c.post(f'/api/inspection/tasks/{task.id}/execute/',
                       data=json.dumps({}), content_type='application/json')

                res = InspectionResult.objects.filter(
                    task=task, check_item_code='TIME_SYNC').first()
                dps = MonitoringDataPoint.objects.filter(
                    inspection_task=task, check_item_code='TIME_SYNC')

                if flag:
                    dp = dps.first()
                    if not dp:
                        check(f'{label} → 生成趋势数据点', False, '未生成')
                    else:
                        nums = re.findall(r'[\d.]+', res.result_value) if res else []
                        expect_num = float(nums[0]) if nums else None
                        check(f'{label} → 生成趋势数据点', True,
                              f'numeric_value={dp.numeric_value} display={dp.display_value!r}')
                        check('   数值 = 巡检结果里的偏差值',
                              expect_num is not None
                              and abs((dp.numeric_value or 0) - expect_num) < 0.001,
                              f'数据点 {dp.numeric_value} vs 结果 {expect_num}')
                        check('   协议/资产归属正确', dp.protocol == 'snmp' and dp.asset_id == asset.id,
                              f'protocol={dp.protocol} asset={dp.asset_id}')
                else:
                    check(f'{label} → 不生成趋势数据点（对照）', dps.count() == 0,
                          f'实际 {dps.count()} 条')
        finally:
            row.is_monitoring_item = original_flag
            row.save(update_fields=['is_monitoring_item'])
            MonitoringDataPoint.objects.filter(inspection_task__in=created_tasks).delete()
            InspectionResult.objects.filter(task__in=created_tasks).delete()
            for t in created_tasks:
                t.delete()
            plan.delete()
            print('   （测试计划/任务/数据点已清理，监控项开关已还原）')

print()
print('=' * 74)
print('全部验证通过 🎉' if ok_all else '存在失败项 ❌')
print('=' * 74)
raise SystemExit(0 if ok_all else 1)
