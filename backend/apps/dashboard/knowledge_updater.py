"""
知识包更新器
==================
从 ops-center 拉取最新知识包（Knowledge Pack），
更新本地的设备识别规则、厂商 MIB 映射、默认阈值配置。

工作流程:
  1. 推送数据到 ops-center 后，检查知识包版本
  2. 如果有更新，下载完整知识包
  3. 写入本地缓存文件（JSON），后续程序启动时加载
  4. 支持定期同步（通过 cron/scheduler）

使用方式:
  # 手动同步
  python manage.py sync_knowledge

  # 在代码中调用
  from apps.dashboard.knowledge_updater import check_and_update
  result = check_and_update()

本地缓存路径: ~/.openclaw/knowledge/ 或 项目 data/ 目录
"""

import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

# 知识包缓存路径
DEFAULT_CACHE_DIR = os.path.expanduser('~/.openclaw/knowledge')
CACHE_FILE = 'knowledge_pack.json'
VERSION_FILE = 'knowledge_version.txt'

# 推送配置缓存
_config_cache = {'data': None, 'expires_at': 0}


def _get_config():
    """获取 ops-center 推送配置"""
    global _config_cache
    now = time.time()

    if _config_cache['data'] and _config_cache['expires_at'] > now:
        return _config_cache['data']

    try:
        from apps.system.models import SystemSetting
        url = SystemSetting.get('push.center_url', '')
        api_key = SystemSetting.get('push.api_key', '')
        timeout = int(SystemSetting.get('push.timeout', '10') or '10')
        enabled = SystemSetting.get_bool('push.enabled', False)
        result = (enabled, url, api_key, timeout)
        _config_cache = {'data': result, 'expires_at': now + 5}
        return result
    except Exception:
        return (False, '', '', 10)


def _get_cache_dir() -> str:
    """获取知识包缓存目录"""
    cache_dir = DEFAULT_CACHE_DIR
    try:
        from django.conf import settings
        # 优先使用项目 data 目录
        project_dir = getattr(settings, 'BASE_DIR', None)
        if project_dir:
            cache_dir = os.path.join(str(project_dir), 'data', 'knowledge')
    except Exception:
        pass
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _get_cached_version() -> str:
    """读取本地缓存的知识包版本号"""
    cache_dir = _get_cache_dir()
    version_file = os.path.join(cache_dir, VERSION_FILE)
    try:
        with open(version_file, 'r') as f:
            return f.read().strip()
    except (FileNotFoundError, IOError):
        return ''


def _save_cached_version(version: str):
    """保存知识包版本号到本地"""
    cache_dir = _get_cache_dir()
    version_file = os.path.join(cache_dir, VERSION_FILE)
    with open(version_file, 'w') as f:
        f.write(version)


def _get_cached_pack() -> Optional[Dict]:
    """读取本地缓存的知识包完整内容"""
    cache_dir = _get_cache_dir()
    pack_file = os.path.join(cache_dir, CACHE_FILE)
    try:
        with open(pack_file, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return None


def _save_cached_pack(pack: Dict):
    """保存知识包完整内容到本地缓存"""
    cache_dir = _get_cache_dir()
    pack_file = os.path.join(cache_dir, CACHE_FILE)
    with open(pack_file, 'w', encoding='utf-8') as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)


def check_version() -> Dict:
    """
    检查 ops-center 是否有新版本知识包。
    仅查版本号，不下载完整包（节省带宽）。

    返回:
      {
        'success': True/False,
        'latest_version': '1.0.0',
        'current_version': '0.9.0',
        'needs_update': True,
        'error': None
      }
    """
    enabled, center_url, api_key, timeout = _get_config()
    if not enabled or not center_url:
        return {
            'success': False,
            'error': '推送未启用或未配置中心地址',
            'needs_update': False,
        }

    current = _get_cached_version()
    url = f'{center_url.rstrip("/")}/api/collector/knowledge-pack/?version={current}'

    try:
        import requests
        headers = {'X-API-Key': api_key}
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            needs = data.get('needs_update', data.get('up_to_date') is False)
            return {
                'success': True,
                'latest_version': data.get('latest_version', data.get('version', '')),
                'current_version': current,
                'needs_update': needs,
            }
        else:
            return {
                'success': False,
                'error': f'HTTP {resp.status_code}: {resp.text[:200]}',
                'needs_update': False,
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'needs_update': False,
        }


def download_pack() -> Dict:
    """
    从 ops-center 下载完整知识包。

    返回:
      {
        'success': True/False,
        'version': '1.0.0',
        'checksum': 'sha256...',
        'data_size': 12345,
        'data': {...},     # 完整知识包内容
        'error': None
      }
    """
    enabled, center_url, api_key, timeout = _get_config()
    if not enabled or not center_url:
        return {'success': False, 'error': '推送未启用或未配置中心地址'}

    current = _get_cached_version()
    url = f'{center_url.rstrip("/")}/api/collector/knowledge-pack/?full=true'

    try:
        import requests
        headers = {'X-API-Key': api_key}
        resp = requests.get(url, headers=headers, timeout=timeout)
        if resp.status_code == 200:
            pack = resp.json()
            version = pack.get('version', '')
            checksum = pack.get('checksum', '')

            # 保存到本地缓存
            _save_cached_pack(pack)
            _save_cached_version(version)

            data = pack.get('data', {})
            return {
                'success': True,
                'version': version,
                'checksum': checksum,
                'data_size': len(json.dumps(data)),
                'data': data,
            }
        else:
            return {
                'success': False,
                'error': f'HTTP {resp.status_code}: {resp.text[:200]}',
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
        }


def apply_vendor_mibs(data: Dict):
    """
    应用厂商 MIB 映射到本地。
    写入 ~/.openclaw/knowledge/vendor_mibs.json，
    供 SNMP 采集器读取。
    """
    vendor_mibs = data.get('vendor_mibs', {})
    if not vendor_mibs:
        return 0

    cache_dir = _get_cache_dir()
    path = os.path.join(cache_dir, 'vendor_mibs.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(vendor_mibs, f, ensure_ascii=False, indent=2)

    logger.info(f'已更新厂商MIB映射: {len(vendor_mibs)} 家厂商')
    return len(vendor_mibs)


def apply_device_detection(data: Dict):
    """
    应用设备类型识别规则。
    写入 ~/.openclaw/knowledge/device_detection.json
    """
    rules = data.get('device_detection', {})
    if not rules:
        return 0

    cache_dir = _get_cache_dir()
    path = os.path.join(cache_dir, 'device_detection.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)

    logger.info(f'已更新设备识别规则: {len(rules)} 种设备类型')
    return len(rules)


def apply_oid_mappings(data: Dict):
    """
    应用 SNMP OID 映射。
    写入 ~/.openclaw/knowledge/oid_mappings.json
    """
    mappings = data.get('oid_mappings', {})
    if not mappings:
        return 0

    cache_dir = _get_cache_dir()
    path = os.path.join(cache_dir, 'oid_mappings.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)

    logger.info(f'已更新OID映射: {len(mappings)} 个OID别名')
    return len(mappings)


def apply_inspection_checks(data: Dict):
    """
    应用巡检检查项定义。
    写入 ~/.openclaw/knowledge/inspection_checks.json
    """
    checks = data.get('inspection_checks', {})
    if not checks:
        return 0

    cache_dir = _get_cache_dir()
    path = os.path.join(cache_dir, 'inspection_checks.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(checks, f, ensure_ascii=False, indent=2)

    logger.info(f'已更新巡检检查项: {len(checks)} 种协议')
    return len(checks)


def apply_default_thresholds(data: Dict):
    """
    应用默认阈值配置。
    写入 ~/.openclaw/knowledge/default_thresholds.json
    """
    thresholds = data.get('default_thresholds', {})
    if not thresholds:
        return 0

    cache_dir = _get_cache_dir()
    path = os.path.join(cache_dir, 'default_thresholds.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(thresholds, f, ensure_ascii=False, indent=2)

    protocols = len(thresholds)
    items = sum(len(v) for v in thresholds.values())
    logger.info(f'已更新默认阈值: {protocols} 种协议, {items} 个检查项')
    return items


def apply_pack(data: Dict) -> Dict:
    """
    应用知识包到本地系统。
    依次更新: 厂商MIB → 设备识别 → OID映射 → 巡检检查项 → 默认阈值

    返回:
      {
        'success': True,
        'applied': ['vendor_mibs', 'device_detection', ...],
        'stats': {...}
      }
    """
    applied = []
    stats = {}

    n = apply_vendor_mibs(data)
    if n:
        applied.append('vendor_mibs')
        stats['vendor_mibs'] = n

    n = apply_device_detection(data)
    if n:
        applied.append('device_detection')
        stats['device_detection'] = n

    n = apply_oid_mappings(data)
    if n:
        applied.append('oid_mappings')
        stats['oid_mappings'] = n

    n = apply_inspection_checks(data)
    if n:
        applied.append('inspection_checks')
        stats['inspection_checks'] = n

    n = apply_default_thresholds(data)
    if n:
        applied.append('default_thresholds')
        stats['default_thresholds'] = n

    return {
        'success': True,
        'applied': applied,
        'stats': stats,
    }


def check_and_update(force: bool = False) -> Dict:
    """
    一键检查 + 下载 + 应用。

    参数:
      force: 强制更新（即使版本相同）

    返回:
      {
        'success': True/False,
        'version_checked': True,
        'updated': True/False,
        'version': '1.0.0',
        'applied': ['vendor_mibs', ...],
        'error': None
      }
    """
    # 1. 检查版本
    version_info = check_version()
    if not version_info.get('success'):
        return {
            'success': False,
            'version_checked': True,
            'updated': False,
            'error': version_info.get('error', '版本检查失败'),
        }

    needs_update = version_info.get('needs_update', False)

    if not needs_update and not force:
        # 首次同步：无本地缓存时也执行下载
        if _get_cached_version() or force:
            return {
                'success': True,
                'version_checked': True,
                'updated': False,
                'version': _get_cached_version(),
                'message': '已是最新版本',
            }

    # 2. 下载完整包
    pack = download_pack()
    if not pack.get('success'):
        return {
            'success': False,
            'version_checked': True,
            'updated': False,
            'error': pack.get('error', '下载失败'),
        }

    # 3. 应用
    data = pack.get('data', {})
    result = apply_pack(data)

    return {
        'success': True,
        'version_checked': True,
        'updated': True,
        'version': pack.get('version', ''),
        'checksum': pack.get('checksum', ''),
        'applied': result.get('applied', []),
        'stats': result.get('stats', {}),
    }


def get_cached_oid_mappings() -> Dict:
    """读取本地缓存的 OID 映射（供采集器使用）"""
    cache_dir = _get_cache_dir()
    path = os.path.join(cache_dir, 'oid_mappings.json')
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return {}


def get_cached_vendor_mibs() -> Dict:
    """读取本地缓存的厂商 MIB（供采集器使用）"""
    cache_dir = _get_cache_dir()
    path = os.path.join(cache_dir, 'vendor_mibs.json')
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, IOError):
        return {}
