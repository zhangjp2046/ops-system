#!/usr/bin/env python3
"""为「时间同步」检查项补建告警阈值配置行（幂等，可重复执行）

为什么需要：
  「时间同步」的偏差阈值配在**巡检计划**的 check_items[].threshold 里
  （10/60/180 秒，见 apps/inspection/time_check.py），所以告警阈值配置表
  （AlertThreshold）里原本没有它的行 —— 结果是 /monitoring/thresholds
  页面上看不到这一项。

  这些行的作用只有两个：
    1. 让「时间同步」出现在告警阈值配置页面，和其余检查项保持一致
    2. 作为「监控项」开关的载体：勾上 is_monitoring_item 后，
       push_service.record_monitoring_data() 会把每次巡检的偏差值
       记进 MonitoringDataPoint，可在监控中心看趋势

  ⚠️ 这些行**故意不配任何阈值**（warn/error/critical 全空），
     配合 AlertThreshold.has_effective_threshold()，它们不参与严重程度判定，
     严重程度仍由巡检侧按计划阈值算出的 status 决定。
     不要在页面上给它们填阈值，否则会变成第二套阈值并覆盖计划。

用法：
    python manage.py seed_time_sync_thresholds
    python manage.py seed_time_sync_thresholds --dry-run
"""
from django.core.management.base import BaseCommand

from apps.alerts.threshold_models import AlertThreshold

# 「时间同步」检查项出现的协议（与 apps/inspection/check_items.py 一致）
PROTOCOLS = ['snmp', 'mysql', 'mssql', 'oracle', 'postgresql']

CHECK_ITEM_CODE = 'TIME_SYNC'
CHECK_ITEM_NAME = '时间同步'
DESCRIPTION = (
    '偏差阈值在「巡检计划」的检查项里设置（10/60/180 秒）；'
    '本行用于在阈值配置页可见，并作为监控中心趋势记录的开关。'
    '请勿在此填写警告/错误/严重阈值。'
)


class Command(BaseCommand):
    help = '为「时间同步」检查项补建告警阈值配置行（幂等；建全局行，不配阈值）'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true',
                            help='只显示将要创建的行，不写库')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        created, existed = [], []

        for protocol in PROTOCOLS:
            row = AlertThreshold.objects.filter(
                customer__isnull=True,
                asset_type__isnull=True,
                check_item_code=CHECK_ITEM_CODE,
                protocol=protocol,
            ).first()

            if row:
                existed.append(protocol)
                continue

            if not dry_run:
                AlertThreshold.objects.create(
                    customer=None,
                    asset_type=None,
                    check_item_code=CHECK_ITEM_CODE,
                    check_item_name=CHECK_ITEM_NAME,
                    protocol=protocol,
                    # 偏差「越高越严重」，语义正确；
                    # 也避开编辑弹窗只提供 越高/越低 两个选项、会把 exact 显示成 upper 的问题。
                    # 注意：不配阈值时这一列纯展示，不影响判定（has_effective_threshold=False）。
                    threshold_direction='upper',
                    value_type='number',
                    warning_threshold='',
                    error_threshold='',
                    critical_threshold='',
                    # 单位留空：阈值本来就不在这配，留个「秒」会让
                    # 「警告/错误/严重」三列显示成孤零零的「秒」。
                    # 与既有的空阈值行（SNMP可达性 / 数据库版本）保持一致。
                    unit='',
                    description=DESCRIPTION,
                    is_active=True,
                    is_monitoring_item=False,      # 需要趋势图时在页面「编辑」里勾上
                )
            created.append(protocol)

        verb = '将创建' if dry_run else '已创建'
        for protocol in created:
            self.stdout.write(f'  {verb}: {protocol} / {CHECK_ITEM_CODE}（全局行，未配阈值）')
        for protocol in existed:
            self.stdout.write(f'  已存在，跳过: {protocol} / {CHECK_ITEM_CODE}')

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(
            f'完成：{verb} {len(created)} 行，跳过 {len(existed)} 行'
            + ('（--dry-run，未写库）' if dry_run else '')
        ))
        self.stdout.write('提示：要让偏差值进监控中心趋势图，请在'
                          ' /monitoring/thresholds 页面「编辑」对应行并勾选「监控项」。')
