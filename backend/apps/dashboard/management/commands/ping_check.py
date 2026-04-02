from django.core.management.base import BaseCommand
from apps.dashboard.ping_service import check_all_assets


class Command(BaseCommand):
    help = 'Ping检测所有资产的在线状态'

    def add_arguments(self, parser):
        parser.add_argument(
            '--workers',
            type=int,
            default=20,
            help='并发检测的最大线程数'
        )

    def handle(self, *args, **options):
        workers = options['workers']
        
        self.stdout.write(f'开始Ping检测，并发数: {workers}')
        
        result = check_all_assets(max_workers=workers)
        
        self.stdout.write(self.style.SUCCESS(
            f'检测完成:\n'
            f'  总计: {result["total"]} 台\n'
            f'  在线: {result["online"]} 台\n'
            f'  离线: {result["offline"]} 台\n'
            f'  跳过: {result["skipped"]} 台 (无IP)\n'
            f'  更新: {result["updated"]} 台\n'
            f'  耗时: {result["elapsed_seconds"]} 秒'
        ))
