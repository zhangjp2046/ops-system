#!/usr/bin/env python3
"""
定时重试失败的推送
用法: python manage.py retry_failed_push
建议配合 cron 每5分钟执行一次
"""
import sys
import time
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from datetime import timedelta


class Command(BaseCommand):
    help = '重试所有失败的推送（指数退避）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='只查询，不实际重试',
        )
        parser.add_argument(
            '--type',
            type=str,
            help='只重试指定类型: alert, inspection, asset_status',
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='最多重试多少条，默认20',
        )

    def handle(self, *args, **options):
        from apps.dashboard.models import PushLog
        from apps.dashboard.push_service import retry_failed

        dry_run = options.get('dry_run', False)
        push_type = options.get('type')
        limit = options['limit']

        now = timezone.now()
        queryset = PushLog.objects.filter(
            status='failed',
            retry_count__lt=5,
        ).filter(
            models.Q(next_retry_at__isnull=True) | models.Q(next_retry_at__lte=now)
        )

        if push_type:
            queryset = queryset.filter(push_type=push_type)

        logs = list(queryset.order_by('created_at')[:limit])

        if dry_run:
            self.stdout.write(f'[Dry Run] 将重试 {len(logs)} 条失败的推送:')
            for log in logs:
                self.stdout.write(
                    f"  - [{log.push_type}] {log.endpoint} "
                    f"(第{log.retry_count}次, 错误: {log.error_message[:50]})"
                )
            return

        if not logs:
            self.stdout.write(self.style.WARNING('没有需要重试的推送'))
            return

        self.stdout.write(f'开始重试 {len(logs)} 条推送...')

        for log in logs:
            self.stdout.write(
                f"  重试 [{log.push_type}] {log.endpoint} "
                f"(第{log.retry_count + 1}次)..."
            )

        success, failed = retry_failed(log_id=None, push_type=push_type, limit=limit)

        self.stdout.write(
            self.style.SUCCESS(f'重试完成: {success} 成功, {failed} 失败')
        )
