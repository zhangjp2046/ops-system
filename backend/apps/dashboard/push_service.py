#!/usr/bin/env python3
"""
推送服务 - 将巡检结果、告警、资产状态推送到 ops-center
"""
import json
import logging
import requests
from django.utils import timezone

logger = logging.getLogger(__name__)

# ops-center 配置（可通过管理界面或环境变量配置）
OPS_CENTER_URL = ''  # 如 http://center.example.com:9000
OPS_CENTER_API_KEY = ''  # 租户 API Key


def get_config():
    """获取推送配置（从环境变量或数据库）"""
    import os
    url = os.environ.get('OPS_CENTER_URL', OPS_CENTER_URL)
    api_key = os.environ.get('OPS_CENTER_API_KEY', OPS_CENTER_API_KEY)
    return url, api_key


def _post(endpoint, data):
    """发送 POST 请求到 ops-center"""
    url, api_key = get_config()
    if not url or not api_key:
        logger.debug('ops-center 未配置，跳过推送')
        return None
    
    full_url = f'{url.rstrip("/")}/api/receive/{endpoint.lstrip("/")}'
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': api_key,
    }
    
    try:
        resp = requests.post(full_url, json=data, headers=headers, timeout=10)
        if resp.status_code == 200:
            result = resp.json()
            logger.info(f'推送成功 [{endpoint}]: {result.get("message", "")}')
            return result
        else:
            logger.warning(f'推送失败 [{endpoint}]: {resp.status_code} {resp.text[:200]}')
            return None
    except Exception as e:
        logger.error(f'推送异常 [{endpoint}]: {e}')
        return None


def push_ping_results(ping_results):
    """
    推送 Ping 检测结果
    
    ping_results: [{
        'asset_id': int,
        'asset_name': str,
        'ip': str,
        'is_online': bool,
        'response_time': float or None,
    }]
    """
    from apps.assets.models import Asset
    
    statuses = []
    alerts = []
    now = timezone.now().isoformat()
    
    for item in ping_results:
        statuses.append({
            'asset_name': item.get('asset_name', ''),
            'asset_ip': item.get('ip', ''),
            'is_online': item.get('is_online', False),
            'response_time': item.get('response_time'),
            'checked_at': now,
        })
        
        # 离线资产生成告警
        if not item.get('is_online'):
            try:
                asset = Asset.objects.get(id=item['asset_id'])
                alerts.append({
                    'remote_id': f'ping-{asset.id}-{now[:19]}',
                    'title': f'资产离线: {asset.asset_name}',
                    'description': f'资产 {asset.asset_name} ({item.get("ip", "无IP")}) 无法Ping通',
                    'severity': 4,
                    'source': 'PING',
                    'alert_type': 'PING_OFFLINE',
                    'asset_name': asset.asset_name,
                    'asset_ip': item.get('ip', ''),
                    'metric_name': 'ping_status',
                    'metric_value': 'offline',
                    'threshold': 'reachable',
                    'occurred_at': now,
                })
            except Asset.DoesNotExist:
                pass
    
    # 推送资产状态
    if statuses:
        _post('asset-status/', {'statuses': statuses})
    
    # 推送告警
    if alerts:
        _post('alerts/', {'alerts': alerts})


def push_inspection_result(task):
    """
    推送巡检结果
    
    task: InspectionTask 实例（已完成）
    """
    from apps.inspection.models import InspectionResult
    
    asset = task.asset
    results = []
    
    for r in InspectionResult.objects.filter(task=task):
        results.append({
            'check_item': r.check_item,
            'check_item_code': r.check_item_code,
            'status': r.status,
            'result_value': r.result_value,
            'result_message': r.result_message,
            'suggestion': r.suggestion,
        })
    
    # 推送巡检记录
    _post('inspections/', {
        'inspections': [{
            'remote_task_id': str(task.id),
            'asset_name': asset.asset_name,
            'asset_ip': asset.ip_address or '',
            'plan_name': task.plan.name if task.plan else '',
            'protocol': task.plan.protocol if task.plan else '',
            'total_checks': len(results),
            'pass_checks': sum(1 for r in results if r['status'] == 'pass'),
            'warning_checks': sum(1 for r in results if r['status'] == 'warning'),
            'fail_checks': sum(1 for r in results if r['status'] == 'fail'),
            'overall_status': 'fail' if any(r['status'] == 'fail' for r in results) else ('warning' if any(r['status'] == 'warning' for r in results) else 'pass'),
            'summary': f'{len(results)}项检查',
            'executed_at': (task.executed_time or timezone.now()).isoformat(),
            'results': results,
        }]
    })
    
    # 推送告警（fail/warning 的检查项）
    alerts = []
    for r in results:
        if r['status'] in ('warning', 'fail'):
            alerts.append({
                'remote_id': f'inspect-{task.id}-{r["check_item_code"]}',
                'title': f'{r["check_item"]} {"异常" if r["status"] == "fail" else "警告"}: {asset.asset_name}',
                'description': f'巡检计划: {task.plan.name if task.plan else ""}\n检查项: {r["check_item"]}\n结果: {r["result_value"]}\n说明: {r["result_message"]}',
                'severity': 3 if r['status'] == 'fail' else 2,
                'source': 'INSPECTION',
                'alert_type': f'INSPECTION_{r["check_item_code"]}',
                'asset_name': asset.asset_name,
                'asset_ip': asset.ip_address or '',
                'metric_name': r['check_item'],
                'metric_value': r['result_value'],
                'occurred_at': (task.executed_time or timezone.now()).isoformat(),
                'alert_data': r,
            })
    
    if alerts:
        _post('alerts/', {'alerts': alerts})
