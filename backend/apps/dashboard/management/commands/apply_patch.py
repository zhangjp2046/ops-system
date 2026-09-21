"""
ops-system 补丁管理命令

用法:
  python manage.py apply_patch                     # 检查并应用更新
  python manage.py apply_patch --check              # 仅检查版本
  python manage.py apply_patch --url=http://...     # 指定补丁源地址
  python manage.py apply_patch --force              # 强制重新下载并应用

补丁源 URL 通过系统设置 'patch.center_url' 配置，默认从推送设置中的 center_url 推断。
"""
import os
import sys
import json
import tarfile
import tempfile
import shutil
from pathlib import Path
from urllib.request import urlopen, Request

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings


BASE_DIR = settings.BASE_DIR  # backend/
CACHE_DIR = os.path.expanduser('~/.openclaw/patches')


class Command(BaseCommand):
    help = '检查并应用 ops-system 补丁包'

    def add_arguments(self, parser):
        parser.add_argument('--check', action='store_true', help='仅检查版本，不下载')
        parser.add_argument('--force', action='store_true', help='强制重新下载并应用')
        parser.add_argument('--url', type=str, default='', help='补丁源地址')

    def handle(self, *args, **options):
        check_only = options['check']
        force = options['force']
        patch_url = options['url']

        if not patch_url:
            patch_url = self._detect_center_url()

        if not patch_url:
            self.stderr.write(self.style.ERROR(
                '未配置补丁源地址。请通过 --url 指定，或在系统设置中配置 push.center_url'
            ))
            sys.exit(1)

            patch_url = patch_url.rstrip('/')

        # 检查版本
        local_ver = self._get_local_version()
        remote_meta = self._check_remote(patch_url, local_ver)

        if not remote_meta:
            self.stdout.write(self.style.SUCCESS('没有可用的补丁包'))
            return

        if not remote_meta.get('needs_update'):
            self.stdout.write(self.style.SUCCESS(f'已是最新版本 ({local_ver})'))
            return

        self.stdout.write(self.style.WARNING(
            f'发现新补丁: {remote_meta["latest_version"]} (当前: {local_ver})'
        ))
        self.stdout.write('更新内容:')
        for item in remote_meta.get('changelog', []):
            self.stdout.write(f'  - {item}')

        if check_only:
            return

        # 确认
        self.stdout.write('')
        confirm = input('是否下载并应用此更新? [y/N]: ')
        if confirm.lower() not in ('y', 'yes'):
            self.stdout.write('已取消')
            return

        # 下载
        self.stdout.write('正在下载补丁包...')
        tar_path = self._download_patch(
            patch_url, remote_meta['latest_version']
        )

        # 备份
        backup_dir = os.path.join(CACHE_DIR, f'backup_{local_ver}')
        self._backup_current(backup_dir)

        # 应用
        self._apply_patch(tar_path)

        # 保存版本
        self._save_version(remote_meta['latest_version'])

        self.stdout.write(self.style.SUCCESS(
            f'\n✅ 更新完成! 版本: {local_ver} → {remote_meta["latest_version"]}'
        ))
        self.stdout.write(self.style.WARNING(
            '请重启 Django 服务以使更改生效: supervisorctl restart ops-system'
        ))

    def _detect_center_url(self):
        """从推送设置推断补丁源地址"""
        try:
            from apps.system.models import SystemSetting
            center = SystemSetting.get('push.center_url', '')
            if center:
                # 例如 http://center:9000 推断为 http://center:9000/api/collector/patches/
                return f'{center.rstrip("/")}/api/collector/patches/'
        except Exception:
            pass
        return ''

    def _get_version_file(self):
        os.makedirs(CACHE_DIR, exist_ok=True)
        return os.path.join(CACHE_DIR, 'patch_version.txt')

    def _get_local_version(self):
        vf = self._get_version_file()
        if os.path.exists(vf):
            with open(vf) as f:
                return f.read().strip()
        return ''

    def _save_version(self, version):
        with open(self._get_version_file(), 'w') as f:
            f.write(version)

    def _check_remote(self, base_url, local_ver):
        url = f'{base_url}?version={local_ver}'
        try:
            req = Request(url)
            with urlopen(req, timeout=10) as resp:
                return json.loads(resp.read())
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'检查更新失败: {e}'))
            return None

    def _download_patch(self, base_url, version):
        url = f'{base_url}?version={version}&download=true'
        os.makedirs(CACHE_DIR, exist_ok=True)
        tar_path = os.path.join(CACHE_DIR, f'patch_{version}.tar.gz')

        try:
            req = Request(url)
            with urlopen(req, timeout=120) as resp:
                with open(tar_path, 'wb') as f:
                    shutil.copyfileobj(resp, f)
            return tar_path
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'下载补丁失败: {e}'))
            sys.exit(1)

    def _backup_current(self, backup_dir):
        """备份当前被补丁会覆盖的文件"""
        import subprocess

        self.stdout.write(f'正在备份当前文件到 {backup_dir}...')
        os.makedirs(backup_dir, exist_ok=True)

        # 备份 inspection/views.py 和 monitoring/protocols.py
        files_to_backup = [
            'apps/inspection/views.py',
            'apps/monitoring/protocols.py',
        ]
        for rel_path in files_to_backup:
            src = os.path.join(BASE_DIR, rel_path)
            if os.path.exists(src):
                dst = os.path.join(backup_dir, os.path.basename(rel_path))
                shutil.copy2(src, dst)
                self.stdout.write(f'  备份: {rel_path}')

    def _get_frontend_dir(self):
        """获取前端编译产物目录（frontend/dist/）"""
        # 从 BASE_DIR (backend/) 向上取父目录，再找 frontend/dist/
        project_root = os.path.normpath(os.path.join(BASE_DIR, '..'))
        frontend_dist = os.path.join(project_root, 'frontend', 'dist')
        if os.path.isdir(frontend_dist):
            return frontend_dist
        # 回退: 直接检查项目根
        return os.path.join(project_root, 'frontend', 'dist')

    def _apply_patch(self, tar_path):
        """解压补丁包并覆盖文件"""
        self.stdout.write('正在应用补丁...')

        frontend_dist = self._get_frontend_dir()

        with tarfile.open(tar_path, 'r:gz') as tar:
            # 检查补丁包结构
            members = tar.getmembers()
            for m in members:
                # 补丁包结构: files/backend/... 或 files/frontend/...
                if m.name.startswith('files/') and m.isfile():
                    # 去掉 files/ 前缀
                    target_rel = m.name[len('files/'):]

                    if target_rel.startswith('frontend/'):
                        # 前端文件 → frontend/dist/ 目录
                        # tar里是 frontend/dist/assets/xxx.js
                        # 去掉 frontend/dist/ 前缀
                        prefix = 'frontend/dist/'
                        if target_rel.startswith(prefix):
                            inner_rel = target_rel[len(prefix):]
                        else:
                            inner_rel = target_rel[len('frontend/'):]
                        target = os.path.join(frontend_dist, inner_rel)
                        self.stdout.write(f'  前端: {inner_rel}')
                    else:
                        # 后端文件 → BASE_DIR 下，去掉 backend/ 前缀
                        if target_rel.startswith('backend/'):
                            inner_rel = target_rel[len('backend/'):]
                        else:
                            inner_rel = target_rel
                        target = os.path.join(BASE_DIR, inner_rel)
                        self.stdout.write(f'  后端: {inner_rel}')

                    # 创建目录
                    os.makedirs(os.path.dirname(target), exist_ok=True)

                    # 提取文件
                    with tar.extractfile(m) as src:
                        with open(target, 'wb') as dst:
                            shutil.copyfileobj(src, dst)

        self.stdout.write(self.style.SUCCESS('补丁应用完成'))
