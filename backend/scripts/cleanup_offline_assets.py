#!/usr/bin/env python3
"""
删除本地 ops-system 中离线的测试资产。
- 先备份（dumpdata JSON fixture，可恢复）
- 明确测试数据（SNMP-* 批量灌注 + test22）直接删除
- 疑似真实资产（物资管理服务器 / 物资系统数据库）仅报告，不删除
用法: python cleanup_offline_assets.py [--delete]
"""
import os, sys, json, django
from datetime import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core import serializers
from django.db import transaction
from apps.assets.models import (
    Asset, AssetData, AssetStatusHistory, AssetTransfer,
    AssetRepair, AssetScrap, AssetLend,
)
from apps.inspection.models import InspectionTask, InspectionResult, InspectionRecord, Inspection
from apps.monitoring.models import MonitoringTask, MonitoringResult, MonitoringDataPoint

DO_DELETE = '--delete' in sys.argv

# 全部离线资产都删除（批次灌注的 SNMP 测试设备 + test22 + 物资管理服务器/数据库）
TEST_IDS = [8] + list(range(17, 36)) + [5, 6]
# 保持为空：全部离线资产都在删除范围内
HOLD_IDS = []

offline = Asset.objects.filter(online=False).order_by('id')
print(f'在线状态为离线的资产共 {offline.count()} 个\n')

# ---------- 备份 ----------
backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'backups')
os.makedirs(backup_dir, exist_ok=True)
stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_path = os.path.abspath(os.path.join(backup_dir, f'offline_assets_{stamp}.json'))

all_ids = list(offline.values_list('id', flat=True))
models_to_dump = [
    ('assets.Asset', Asset.objects.filter(id__in=all_ids)),
    ('assets.AssetData', AssetData.objects.filter(asset_id__in=all_ids)),
    ('assets.AssetStatusHistory', AssetStatusHistory.objects.filter(asset_id__in=all_ids)),
    ('assets.AssetTransfer', AssetTransfer.objects.filter(asset_id__in=all_ids)),
    ('assets.AssetRepair', AssetRepair.objects.filter(asset_id__in=all_ids)),
    ('assets.AssetScrap', AssetScrap.objects.filter(asset_id__in=all_ids)),
    ('assets.AssetLend', AssetLend.objects.filter(asset_id__in=all_ids)),
    ('inspection.Inspection', Inspection.objects.filter(asset_id__in=all_ids)),
    ('inspection.InspectionTask', InspectionTask.objects.filter(asset_id__in=all_ids)),
    ('inspection.InspectionResult', InspectionResult.objects.filter(asset_id__in=all_ids)),
    ('inspection.InspectionRecord', InspectionRecord.objects.filter(asset_id__in=all_ids)),
    ('monitoring.MonitoringTask', MonitoringTask.objects.filter(asset_id__in=all_ids)),
    ('monitoring.MonitoringResult', MonitoringResult.objects.filter(asset_id__in=all_ids)),
    ('monitoring.MonitoringDataPoint', MonitoringDataPoint.objects.filter(asset_id__in=all_ids)),
]
from apps.alerts.models import Alert as AlertsAlert
models_to_dump.append(('alerts.Alert', AlertsAlert.objects.filter(asset_id__in=all_ids)))

payload = []
for label, qs in models_to_dump:
    objs = list(qs)
    if objs:
        payload.append({'model': label, 'count': len(objs),
                        'data': json.loads(serializers.serialize('json', objs))})

with open(backup_path, 'w', encoding='utf-8') as f:
    json.dump({'generated_at': stamp, 'asset_ids': all_ids, 'tables': payload}, f,
              ensure_ascii=False, indent=2)
print(f'✅ 备份已写入: {backup_path}')
for t in payload:
    print(f'   {t["model"]:34s} {t["count"]}')
print()

# ---------- 待删除清单 ----------
targets = Asset.objects.filter(id__in=TEST_IDS).order_by('id')
print(f'=== 将删除 {targets.count()} 个测试资产 ===')
for a in targets:
    print(f'   id={a.id:<3} {a.asset_code:<14} {a.ip_address:<14} {a.asset_name}')
print()
held = Asset.objects.filter(id__in=HOLD_IDS)
print(f'=== 暂不删除（疑似真实）{held.count()} 个 ===')
for a in held:
    print(f'   id={a.id:<3} {a.asset_code:<14} {a.ip_address:<14} {a.asset_name}')
print()

if not DO_DELETE:
    print('（干跑模式，未删除任何数据。加 --delete 执行）')
    sys.exit(0)

# ---------- 执行删除 ----------
with transaction.atomic():
    # 先删除 alerts.Alert（SET_NULL，不删会变成无主告警）
    alert_cnt = AlertsAlert.objects.filter(asset_id__in=TEST_IDS).delete()[0]
    # Asset 级联会带走 AssetData/历史/巡检/监控等
    cascaded = {}
    for a in targets:
        cascaded[a.id] = a.asset_name
    cnt, detail = Asset.objects.filter(id__in=TEST_IDS).delete()

print(f'🗑️  alerts.Alert 删除: {alert_cnt}')
print(f'🗑️  级联删除总记录数: {cnt}')
by_model = {}
for label, n in detail.items():
    by_model[label] = by_model.get(label, 0) + n
for label in sorted(by_model):
    print(f'   {label:34s} {by_model[label]}')
print()
print(f'剩余资产总数: {Asset.objects.count()}')
print(f'其中离线: {Asset.objects.filter(online=False).count()}')
