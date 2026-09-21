"""
从 ops-center 同步最新知识包（设备识别规则、厂商MIB、阈值配置）

用法:
  python manage.py sync_knowledge              # 检查并更新（如有新版本）
  python manage.py sync_knowledge --force       # 强制重新下载并应用
  python manage.py sync_knowledge --check-only  # 仅检查版本，不下载
"""
import logging
from django.core.management.base import BaseCommand
from apps.dashboard.knowledge_updater import check_and_update, check_version

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '从 ops-center 同步知识包'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='强制重新下载并应用')
        parser.add_argument('--check-only', action='store_true', help='仅检查版本，不下载')

    def handle(self, *args, **options):
        force = options.get('force', False)
        check_only = options.get('check_only', False)

        if check_only:
            self.stdout.write('正在检查知识包版本...')
            result = check_version()
            if result.get('success'):
                current = result.get('current_version', '无')
                latest = result.get('latest_version', '?')
                needs = result.get('needs_update', False)
                if needs:
                    self.stdout.write(self.style.WARNING(
                        f'当前版本: {current} → 最新版本: {latest} (需要更新)'
                    ))
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f'当前版本: {current} (已是最新)'
                    ))
            else:
                self.stdout.write(self.style.ERROR(
                    f'版本检查失败: {result.get("error", "未知错误")}'
                ))
            return

        self.stdout.write('正在同步知识包...')
        result = check_and_update(force=force)

        if result.get('success'):
            if result.get('updated'):
                self.stdout.write(self.style.SUCCESS(
                    f'✅ 更新成功! 版本: {result.get("version", "?")}'
                ))
                for item in result.get('applied', []):
                    stats = result.get('stats', {}).get(item, 0)
                    self.stdout.write(f'   ✓ {item}: {stats} 项')
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'✓ 已是最新版本 ({result.get("version", "?")})'
                ))
        else:
            self.stdout.write(self.style.ERROR(
                f'❌ 同步失败: {result.get("error", "未知错误")}'
            ))
