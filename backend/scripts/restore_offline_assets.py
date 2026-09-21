#!/usr/bin/env python3
"""
从 cleanup_offline_assets.py 生成的备份中恢复资产及关联数据。

用法:
  python restore_offline_assets.py                      # 列出备份文件 + 干跑校验
  python restore_offline_assets.py <备份文件> --restore  # 实际恢复

注意: 恢复用 serializers.deserialize，会按主键写回。
若主键已被新数据占用会报 IntegrityError，需先处理冲突。
"""
import os, sys, json, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.core import serializers

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_DIR = os.path.join(BASE, 'backups')

args = [a for a in sys.argv[1:] if not a.startswith('--')]
DO_RESTORE = '--restore' in sys.argv

if args:
    path = args[0]
else:
    files = sorted(f for f in os.listdir(BACKUP_DIR) if f.startswith('offline_assets_'))
    if not files:
        print('没有找到备份文件'); sys.exit(1)
    path = os.path.join(BACKUP_DIR, files[-1])
    print(f'使用最新备份: {path}\n')

with open(path, encoding='utf-8') as f:
    payload = json.load(f)

print(f'备份时间: {payload.get("generated_at")}')
print(f'包含资产 ID: {payload.get("asset_ids")}\n')

# 按依赖顺序恢复（主表在前）
ORDER = ['assets.Asset', 'assets.AssetData', 'assets.AssetStatusHistory',
         'assets.AssetTransfer', 'assets.AssetRepair', 'assets.AssetScrap',
         'assets.AssetLend', 'inspection.Inspection', 'inspection.InspectionTask',
         'inspection.InspectionResult', 'inspection.InspectionRecord',
         'monitoring.MonitoringTask', 'monitoring.MonitoringResult',
         'monitoring.MonitoringDataPoint', 'alerts.Alert']

tables = {t['model']: t for t in payload['tables']}
total = sum(t['count'] for t in payload['tables'])
print(f'共 {len(payload["tables"])} 张表 / {total} 条记录待恢复:')
for model in ORDER:
    t = tables.get(model)
    if t:
        print(f'   {model:34s} {t["count"]}')

# 干跑校验：验证 fixture 可反序列化
print('\n--- 校验 fixture 可解析 ---')
ok = True
for model in ORDER:
    t = tables.get(model)
    if not t:
        continue
    try:
        objs = list(serializers.deserialize('json', json.dumps(t['data'])))
        if len(objs) != t['count']:
            print(f'   ⚠️ {model}: 解析出 {len(objs)} 条, 备份声明 {t["count"]} 条')
            ok = False
    except Exception as e:
        print(f'   ❌ {model}: {e}')
        ok = False
print('校验通过 ✅' if ok else '校验存在问题 ⚠️')

if not DO_RESTORE:
    print('\n（干跑模式，未写入数据库。加 --restore 执行）')
    sys.exit(0 if ok else 2)

print('\n--- 开始恢复 ---')
with django.db.transaction.atomic():
    for model in ORDER:
        t = tables.get(model)
        if not t:
            continue
        for obj in serializers.deserialize('json', json.dumps(t['data'])):
            obj.save()
        print(f'   ✓ {model}: {t["count"]}')

from apps.assets.models import Asset
print(f'\n恢复完成，资产总数: {Asset.objects.count()}')
