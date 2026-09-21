#!/usr/bin/env python3
"""
推送服务 - 将巡检结果、告警、资产状态推送到 ops-center
配置从 system_settings 表读取
"""
import json
import os
import logging
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from django.utils import timezone
from django.db import models
from django.db.models import Count

logger = logging.getLogger(__name__)

# 全局 HTTP Session（连接池复用）
_http_session = None

# 配置缓存（5秒过期）
_config_cache = {'data': None, 'expires_at': 0}



def get_http_session():
    """获取带连接池的全局 HTTP Session"""
    global _http_session
    if _http_session is None:
        session = requests.Session()
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=Retry(total=0)
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        _http_session = session
    return _http_session


def record_monitoring_data(task):
    """
    将巡检结果中的监控项记录到 MonitoringDataPoint 表
    只有 AlertThreshold.is_monitoring_item=True 的检查项才会被记录
    """
    from apps.monitoring.models import MonitoringDataPoint
    from apps.alerts.threshold_models import AlertThreshold
    from apps.inspection.models import InspectionResult

    asset = task.asset
    protocol = task.plan.protocol if task.plan else 'snmp'
    recorded_at = task.executed_time or timezone.now()

    # 获取所有已启用监控的阈值（按 protocol + check_item_code 去重）
    monitoring_thresholds = {
        t.check_item_code: t for t in
        AlertThreshold.objects.filter(
            is_monitoring_item=True,
            is_active=True,
            protocol=protocol,
        )
    }

    if not monitoring_thresholds:
        return 0

    # 获取该任务的巡检结果
    results = InspectionResult.objects.filter(task=task)
    created = 0
    abnormal_points = []

    for r in results:
        if r.check_item_code not in monitoring_thresholds:
            continue

        threshold = monitoring_thresholds[r.check_item_code]

        # 尝试解析数值
        numeric_value = None
        display_value = r.result_value or ''
        try:
            # 从 result_value 中提取数字（如 "85%", "1523MB", "23.5"）
            import re
            numbers = re.findall(r'[-+]?\d+\.?\d*', display_value)
            if numbers:
                numeric_value = float(numbers[0])
        except Exception:
            pass

        # 判断 severity
        severity_map = {'pass': 1, 'warning': 2, 'fail': 3}
        severity = severity_map.get(r.status, 1)

        # 提取警告/错误阈值字符串
        warning_th = str(threshold.warning_threshold) if threshold.warning_threshold else ''
        error_th = str(threshold.error_threshold) if threshold.error_threshold else ''

        try:
            dp = MonitoringDataPoint.objects.create(
                customer=asset.customer,
                asset=asset,
                inspection_task=task,
                check_item_code=r.check_item_code,
                check_item_name=r.check_item,
                protocol=protocol,
                numeric_value=numeric_value,
                display_value=display_value,
                severity=severity,
                warning_threshold=warning_th,
                error_threshold=error_th,
                result_message=r.result_message or '',
                suggestion=r.suggestion or '',
                recorded_at=recorded_at,
            )
            created += 1

            # 收集非正常数据点（severity >= 2），稍后推送到 center
            if severity >= 2:
                remote_data_id = f'{task.id}_{r.check_item_code}'
                abnormal_points.append({
                    'remote_data_id': remote_data_id,
                    'asset_name': asset.asset_name or '',
                    'asset_ip': asset.ip_address or '',
                    'asset_type': str(asset.asset_type.type_name) if asset.asset_type else '',
                    'check_item_code': r.check_item_code,
                    'check_item_name': r.check_item or '',
                    'protocol': protocol,
                    'numeric_value': numeric_value,
                    'display_value': display_value,
                    'severity': severity,
                    'result_message': r.result_message or '',
                    'suggestion': r.suggestion or '',
                    'warning_threshold': warning_th,
                    'error_threshold': error_th,
                    'recorded_at': recorded_at.isoformat() if recorded_at else '',
                })
        except Exception as e:
            logger.warning(f'记录监控数据失败 [{asset.asset_name}/{r.check_item_code}]: {e}')

    if created > 0:
        logger.info(f'记录了 {created} 条监控数据点 [{asset.asset_name}]')

    # 异步推送非正常数据到 ops-center
    if abnormal_points:
        import threading
        points_copy = list(abnormal_points)
        threading.Thread(
            target=lambda: _async_push_monitoring_data(points_copy),
            daemon=True
        ).start()

    return created


def _async_push_monitoring_data(abnormal_points):
    """后台线程：推送非正常监控数据到 ops-center"""
    try:
        result = push_monitoring_data(abnormal_points)
        if result is not None:
            logger.info(f'推送 {len(abnormal_points)} 条监控异常数据到 center 成功')
        else:
            logger.warning(f'推送 {len(abnormal_points)} 条监控异常数据到 center 失败')
    except Exception as e:
        logger.error(f'推送监控异常数据异常: {e}')



def get_config():
    """从数据库读取推送配置，带5秒缓存"""
    global _config_cache
    from django.utils import timezone
    now = timezone.now().timestamp()

    if _config_cache['data'] and _config_cache['expires_at'] > now:
        return _config_cache['data']

    from apps.system.models import SystemSetting
    enabled = SystemSetting.get_bool('push.enabled', False)
    url = SystemSetting.get('push.center_url', '')
    api_key = SystemSetting.get('push.api_key', '')
    timeout = int(SystemSetting.get('push.timeout', '10') or '10')
    result = (enabled, url, api_key, timeout)
    _config_cache = {'data': result, 'expires_at': now + 5}
    return result


def _schedule_retry(log, max_retries=5):
    """为失败的推送安排重试（指数退避）"""
    from datetime import timedelta

    if log.retry_count >= max_retries:
        log.next_retry_at = None
        log.error_message = (log.error_message or '') + f' | 已达最大重试次数({max_retries})'
        log.save()
        return

    # 指数退避: 1min, 5min, 15min, 1h, 4h
    delays = [1, 5, 15, 60, 240]
    delay_minutes = delays[min(log.retry_count, len(delays) - 1)]
    from django.utils import timezone
    log.next_retry_at = timezone.now() + timedelta(minutes=delay_minutes)
    log.save()
    logger.info(f'推送日志 {log.id} 计划 {delay_minutes} 分钟后重试 (第{log.retry_count + 1}次)')


def retry_failed(log_id=None, push_type=None, limit=50):
    """
    重试失败的推送

    Args:
        log_id: 指定日志ID重试（单条）
        push_type: 指定类型重试（批量）
        limit: 最多重试多少条

    Returns: (success_count, failed_count)
    """
    from apps.dashboard.models import PushLog
    from django.utils import timezone
    from datetime import timedelta

    now = timezone.now()

    if log_id:
        qs = PushLog.objects.filter(id=log_id, status='failed')
    elif push_type:
        qs = PushLog.objects.filter(
            push_type=push_type,
            status='failed',
            retry_count__lt=5
        ).filter(
            models.Q(next_retry_at__isnull=True) | models.Q(next_retry_at__lte=now)
        )
    else:
        # 超过重试时间的所有失败记录
        qs = PushLog.objects.filter(
            status='failed',
            retry_count__lt=5
        ).filter(
            models.Q(next_retry_at__isnull=True) | models.Q(next_retry_at__lte=now)
        )

    logs = list(qs.order_by('created_at')[:limit])
    success = 0
    failed = 0

    for log in logs:
        if not log.request_payload:
            log.status = 'failed'
            log.error_message = (log.error_message or '') + ' | 无原始数据无法重试'
            log.save()
            failed += 1
            continue

        log.status = 'retrying'
        log.retry_count += 1
        log.save()

        # 重新发送
        enabled, url, api_key, timeout = get_config()
        if not enabled or not url or not api_key:
            log.status = 'failed'
            log.error_message = '推送配置已禁用'
            log.save()
            failed += 1
            continue

        full_url = f'{url.rstrip("/")}/api/receive/{log.endpoint.lstrip("/")}'
        headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_key,
        }

        try:
            session = get_http_session()
            resp = session.post(full_url, json=log.request_payload, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                result = resp.json()
                log.status = 'success'
                log.next_retry_at = None
                log.error_message = ''
                log.save()
                logger.info(f'重试成功 [log {log.id}]: {result.get("message", "")}')
                success += 1
            else:
                log.status = 'failed'
                log.error_message = f'HTTP {resp.status_code}: {resp.text[:200]}'
                log.save()
                _schedule_retry(log)
                logger.warning(f'重试失败 [log {log.id}]: HTTP {resp.status_code}')
                failed += 1
        except requests.Timeout:
            log.status = 'failed'
            log.error_message = f'请求超时({timeout}s)'
            log.save()
            _schedule_retry(log)
            logger.error(f'重试超时 [log {log.id}]: {timeout}s')
            failed += 1
        except Exception as e:
            log.status = 'failed'
            log.error_message = str(e)[:500]
            log.save()
            _schedule_retry(log)
            logger.error(f'重试异常 [log {log.id}]: {e}')
            failed += 1

    logger.info(f'重试完成: {success} 成功, {failed} 失败')
    return success, failed


def _post(endpoint, data, push_type='alert', timeout=None):
    """发送 POST 请求到 ops-center"""
    from apps.dashboard.models import PushLog

    enabled, url, api_key, default_timeout = get_config()

    if not enabled:
        return None
    if not url or not api_key:
        return None

    _timeout = timeout if timeout is not None else default_timeout

    full_url = f'{url.rstrip("/")}/api/receive/{endpoint.lstrip("/")}'
    headers = {
        'Content-Type': 'application/json',
        'X-API-Key': api_key,
    }

    # 保存推送日志（含原始数据用于重试）
    log = PushLog.objects.create(
        push_type=push_type,
        endpoint=endpoint,
        request_data_size=len(json.dumps(data).encode('utf-8')),
        request_payload=data,
    )

    try:
        session = get_http_session()
        resp = session.post(full_url, json=data, headers=headers, timeout=_timeout)
        if resp.status_code == 200:
            result = resp.json()
            log.status = 'success'
            log.records_count = len(data.get('alerts', []) or data.get('statuses', []) or data.get('inspections', []) or data.get('results', []))
            log.save()
            logger.info(f'推送成功 [{push_type}/{endpoint}]: {result.get("message", "")}')

            # 推送成功后，异步检查知识包版本和补丁版本
            _deferred_knowledge_check()
            _deferred_patch_check()

            return result
        else:
            log.status = 'failed'
            log.error_message = f'HTTP {resp.status_code}: {resp.text[:200]}'
            log.save()
            _schedule_retry(log)
            logger.warning(f'推送失败 [{push_type}/{endpoint}]: {resp.status_code}')
            return None
    except requests.Timeout:
        log.status = 'failed'
        log.error_message = f'请求超时({_timeout}s)'
        log.save()
        _schedule_retry(log)
        logger.error(f'推送超时 [{push_type}/{endpoint}]: {_timeout}s')
        return None
    except Exception as e:
        log.status = 'failed'
        log.error_message = str(e)[:500]
        log.save()
        _schedule_retry(log)
        logger.error(f'推送异常 [{push_type}/{endpoint}]: {e}')
        return None


def get_push_stats():
    """
    获取今日推送统计，供仪表盘使用
    """
    from apps.dashboard.models import PushLog
    from django.utils import timezone
    from datetime import timedelta

    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    stats = PushLog.objects.filter(created_at__gte=today).aggregate(
        total=Count('id'),
        success=Count('id', filter=models.Q(status='success')),
        failed=Count('id', filter=models.Q(status='failed')),
    )

    last_success = PushLog.objects.filter(status='success').order_by('-created_at').first()
    last_fail = PushLog.objects.filter(status='failed').order_by('-created_at').first()

    return {
        'today_total': stats['total'] or 0,
        'today_success': stats['success'] or 0,
        'today_failed': stats['failed'] or 0,
        'last_push_at': last_success.created_at.isoformat() if last_success else None,
        'last_fail_at': last_fail.created_at.isoformat() if last_fail else None,
        'last_fail_error': last_fail.error_message[:100] if last_fail else None,
    }


def test_push():
    """测试推送连接"""
    from apps.dashboard.models import PushLog
    enabled, url, api_key, timeout = get_config()
    if not enabled:
        return {'success': False, 'message': '推送未启用'}
    if not url:
        return {'success': False, 'message': '未配置中心平台地址'}
    if not api_key:
        return {'success': False, 'message': '未配置API Key'}

    try:
        full_url = f'{url.rstrip("/")}/api/receive/health/'
        session = get_http_session()
        resp = session.get(full_url, headers={"X-API-Key": api_key}, timeout=timeout)
        if resp.status_code == 200:
            data = resp.json()
            # 测试成功也记录一条心跳
            PushLog.objects.create(
                push_type='heartbeat',
                status='success',
                endpoint='receive/health/',
                records_count=0,
            )
            return {'success': True, 'message': f'连接成功: {data.get("tenant", "未知租户")}', 'data': data}
        elif resp.status_code == 401:
            return {'success': False, 'message': 'API Key无效'}
        else:
            return {'success': False, 'message': f'连接失败: {resp.status_code}'}
    except Exception as e:
        return {'success': False, 'message': f'连接异常: {e}'}


def push_monitor_test_result(result_id):
    """推送单条采集测试结果到 ops-center"""
    from apps.monitoring.test_config import MonitorTestResult, MonitorTestConfig

    try:
        result = MonitorTestResult.objects.select_related('config').get(id=result_id)
    except MonitorTestResult.DoesNotExist:
        return None

    config = result.config
    from apps.assets.models import Asset
    asset_qs = Asset.objects.filter(id=config.asset_id) if config.asset_id else None

    payload = {
        'results': [{
            'remote_id': str(result.id),
            'asset_name': asset_qs.first().asset_name if asset_qs and asset_qs.exists() else '',
            'asset_ip': config.host or '',
            'config_name': config.name,
            'protocol': config.protocol or '',
            'host': config.host or '',
            'port': config.port or 0,
            'status': result.status,
            'error_message': result.error_message or '',
            'response_time': result.response_time or 0,
            'test_duration': result.test_duration or 0,
            'test_data': result.data or {},
            'version': result.data.get('version', ''),
            'driver': result.data.get('driver', ''),
            'executed_at': result.created_at.isoformat() if result.created_at else '',
        }]
    }
    return _post('monitor-tests/', payload, push_type='monitor_test')


def push_monitoring_data(data_points):
    """
    推送监控中心异常数据（severity >= 2）到 ops-center

    Args:
        data_points: list of dict，每个元素包含:
            - remote_data_id: str (唯一标识，用于center去重)
            - asset_name: str
            - asset_ip: str
            - asset_type: str
            - check_item_code: str
            - check_item_name: str
            - protocol: str
            - numeric_value: float or None
            - display_value: str
            - severity: int (2/3/4)
            - result_message: str
            - suggestion: str
            - warning_threshold: str
            - error_threshold: str
            - recorded_at: str (ISO format)

    Returns: dict or None
    """
    if not data_points:
        return None

    # 只推送非正常数据（severity >= 2）
    abnormal = [dp for dp in data_points if dp.get('severity', 1) >= 2]
    if not abnormal:
        return None

    payload = {'data_points': abnormal}
    return _post('monitoring-data/', payload, push_type='monitoring_data')


def push_ping_results(ping_results):
    """推送 Ping 检测结果"""
    from apps.system.models import SystemSetting
    from apps.assets.models import Asset

    push_status = SystemSetting.get_bool('push.push_asset_status', True)
    push_alert = SystemSetting.get_bool('push.push_alerts', True)

    if not push_status and not push_alert:
        return

    statuses = []
    alerts = []
    now = timezone.now()

    for item in ping_results:
        asset_name = item.get('asset_name', '')
        ip = item.get('ip', '')
        is_online = item.get('is_online', False)

        statuses.append({
            'asset_name': asset_name,
            'asset_ip': ip,
            'is_online': is_online,
            'response_time': item.get('response_time'),
            'checked_at': now.isoformat(),
        })

        # 离线才发告警
        if not is_online:
            alert_time = now.strftime('%Y-%m-%d %H:%M:%S')
            desc_lines = [
                f'## 资产离线告警',
                f'',
                f'**资产名称**: {asset_name}',
                f'**IP地址**: {ip or "未配置"}',
                f'**检测时间**: {alert_time}',
                f'**检测结果**: 无法Ping通，资产可能已宕机或网络中断',
                f'',
                f'## 处理建议',
                f'1. 检查设备电源和网线连接',
                f'2. 确认IP地址配置是否正确',
                f'3. 检查网络交换机/路由器状态',
                f'4. 如有带外管理(iDRAC/iLO)，检查BMC状态',
            ]

            try:
                asset = Asset.objects.get(id=item['asset_id'])
                desc_lines.insert(4, f'**资产类型**: {asset.asset_type.type_name if asset.asset_type else "未知"}')
                desc_lines.insert(5, f'**重要等级**: {asset.get_importance_level_display() if hasattr(asset, "get_importance_level_display") else asset.importance_level}')
                desc_lines.insert(6, f'**负责人**: {asset.owner or "未指定"}')
                alerts.append({
                    'remote_id': f'ping-{asset.id}-{now.strftime("%Y%m%d%H%M")}',
                    'title': f'🔴 资产离线: {asset_name} ({ip})',
                    'description': '\n'.join(desc_lines),
                    'severity': 4,  # 严重
                    'source': 'PING',
                    'alert_type': 'PING_OFFLINE',
                    'asset_name': asset_name,
                    'asset_ip': ip,
                    'metric_name': 'ping_status',
                    'metric_value': 'offline',
                    'threshold': 'reachable',
                    'occurred_at': now.isoformat(),
                })
            except Asset.DoesNotExist:
                pass

    if push_status and statuses:
        _post('asset-status/', {'statuses': statuses}, push_type='asset_status')

    if push_alert and alerts:
        _post('alerts/', {'alerts': alerts}, push_type='alert')


def push_inspection_result(task):
    """推送巡检结果和告警"""
    from apps.system.models import SystemSetting
    from apps.inspection.models import InspectionResult

    asset = task.asset
    plan = task.plan
    plan_name = plan.name if plan else '未知计划'
    protocol = plan.protocol if plan else ''
    exec_time = (task.executed_time or timezone.now())
    exec_time_str = exec_time.strftime('%Y-%m-%d %H:%M:%S')

    results = []
    for r in InspectionResult.objects.filter(task=task):
        results.append({
            'check_item': r.check_item,
            'check_item_code': r.check_item_code,
            'status': r.status,
            'result_value': r.result_value,
            'result_message': r.result_message,
            'suggestion': r.suggestion,
            'severity': r.severity,
            'threshold': {
                'expected': r.expected_value or '',
                'min': r.threshold_min or '',
                'max': r.threshold_max or '',
            },
        })

    pass_count = sum(1 for r in results if r['status'] == 'pass')
    warning_count = sum(1 for r in results if r['status'] == 'warning')
    fail_count = sum(1 for r in results if r['status'] == 'fail')

    if fail_count > 0:
        overall = 'fail'
        status_icon = '🔴'
    elif warning_count > 0:
        overall = 'warning'
        status_icon = '🟡'
    else:
        overall = 'pass'
        status_icon = '🟢'

    # 结构化摘要（替代 Markdown 表格，便于机器解析）
    summary_struct = {
        'plan_name': plan_name,
        'protocol': protocol,
        'pass': pass_count,
        'warning': warning_count,
        'fail': fail_count,
        'total': len(results),
        'overall': overall,
        'executed_at': exec_time_str,
        'items': [
            {
                'check_item': rr['check_item'],
                'status': rr['status'],
                'result_value': rr['result_value'],
                'result_message': rr['result_message'],
            }
            for rr in results
        ],
    }


    # 推送巡检记录
    inspection_data = {
        'inspections': [{
            'remote_task_id': str(task.id),
            'asset_name': asset.asset_name,
            'asset_ip': asset.ip_address or '',
            'plan_name': plan_name,
            'protocol': protocol,
            'total_checks': len(results),
            'pass_checks': pass_count,
            'warning_checks': warning_count,
            'fail_checks': fail_count,
            'overall_status': overall,
            'summary': summary_struct,
            'executed_at': exec_time.isoformat(),
            'results': results,
        }]
    }
    
    if SystemSetting.get_bool('push.push_inspections', True):
        _post('inspections/', inspection_data, push_type='inspection')

    # 推送告警（仅 WARNING 和 FAIL，severity >= 2，过滤 INFO）
    if SystemSetting.get_bool('push.push_alerts', True):
        alerts = []
        for r in results:
            if r['status'] not in ('warning', 'fail'):
                continue

            is_fail = r['status'] == 'fail'
            # WARNING -> severity 2, FAIL -> severity 3
            severity = 3 if is_fail else 2
            icon = '🔴' if is_fail else '🟡'
            status_text = '异常' if is_fail else '警告'

            desc_lines = [
                f'## 巡检{status_text}详情',
                f'',
                f'**资产名称**: {asset.asset_name}',
                f'**IP地址**: {asset.ip_address or "未配置"}',
                f'**巡检计划**: {plan_name} ({protocol.upper() if protocol else ""})',
                f'**执行时间**: {exec_time_str}',
                f'',
                f'---',
                f'',
                f'## 检查项: {r["check_item"]}',
                f'',
                f'**检查结果**: {r["result_value"]}',
                f'**状态**: {"❌ 异常" if is_fail else "⚠️ 警告"}',
                f'',
                f'**详细信息**:',
                f'```',
                f'{r["result_message"] or "无"}',
                f'```',
            ]

            if r.get('suggestion'):
                desc_lines.extend([f'', f'**处理建议**: {r["suggestion"]}'])

            desc_lines.extend([f'', f'---', f'', f'## 完整巡检结果'])
            for rr in results:
                r_icon = '✅' if rr['status'] == 'pass' else ('⚠️' if rr['status'] == 'warning' else '❌')
                desc_lines.append(f'{r_icon} {rr["check_item"]}: {rr["result_value"]} — {rr["result_message"][:50]}')

            alerts.append({
                'remote_id': f'inspect-{task.id}-{r["check_item_code"]}',
                'title': f'{icon} {r["check_item"]}{status_text}: {asset.asset_name}',
                'description': '\n'.join(desc_lines),
                'severity': severity,  # 2=WARNING, 3=ERROR
                'source': 'INSPECTION',
                'alert_type': f'INSPECTION_{r["check_item_code"]}',
                'asset_name': asset.asset_name,
                'asset_ip': asset.ip_address or '',
                'metric_name': r['check_item'],
                'metric_value': r['result_value'],
                'occurred_at': exec_time.isoformat(),
                'alert_data': {
                    'check_item': r['check_item'],
                    'check_item_code': r['check_item_code'],
                    'status': r['status'],
                    'result_value': r['result_value'],
                    'result_message': r['result_message'],
                    'suggestion': r.get('suggestion', ''),
                    'plan_name': plan_name,
                    'protocol': protocol,
                    'all_results': [{
                        'item': rr['check_item'],
                        'status': rr['status'],
                        'value': rr['result_value'],
                    } for rr in results],
                },
            })

        if alerts:
            _post('alerts/', {'alerts': alerts}, push_type='alert')

    return {'inspection': inspection_data, 'alerts': alerts}


def push_alerts(customer_id=None, alert_ids=None):
    """
    推送告警到 ops-center
    
    Args:
        customer_id: 客户ID（可选，不指定则推送所有）
        alert_ids: 指定告警ID列表（可选）
    
    Returns:
        {'success': True/False, 'sent_count': N, 'errors': [...]}
    """
    from apps.alerts.models import Alert
    
    # 构建查询 - 只取未关闭的告警
    queryset = Alert.objects.filter(status__in=['NEW', 'ACKNOWLEDGED', 'IN_PROGRESS'])
    
    if customer_id:
        queryset = queryset.filter(customer_id=customer_id)
    
    if alert_ids:
        queryset = queryset.filter(id__in=alert_ids)
    
    alerts_qs = queryset.order_by('-created_at')[:100]
    
    if not alerts_qs.exists():
        logger.info('没有待推送的告警')
        return {'success': True, 'sent_count': 0, 'errors': []}
    
    # 转换为字典
    alert_list = []
    for a in alerts_qs:
        # 获取资产信息
        asset_name = ''
        asset_ip = ''
        if a.asset:
            asset_name = getattr(a.asset, 'asset_name', '') or ''
            asset_ip = getattr(a.asset, 'ip_address', '') or ''
        
        alert_list.append({
            'id': a.id,
            'title': a.title,
            'description': a.description or '',
            'alert_type': a.alert_type,
            'severity': a.severity,
            'source': a.source,
            'asset_name': asset_name,
            'asset_ip': asset_ip,
            'status': a.status,
            'occurred_at': a.occurred_at.isoformat() if a.occurred_at else None,
            'acknowledged_at': a.acknowledged_at.isoformat() if a.acknowledged_at else None,
            'resolved_at': a.resolved_at.isoformat() if a.resolved_at else None,
            'customer_id': a.customer_id.id if hasattr(a.customer_id, 'id') else a.customer_id,
            'metadata': a.alert_data or {},
        })
    
    logger.info(f'推送 {len(alert_list)} 条告警到 ops-center')
    
    result = _post('alerts/', {'alerts': alert_list}, push_type='alert')
    
    if result is not None:
        return {'success': True, 'sent_count': len(alert_list), 'errors': []}
    else:
        return {'success': False, 'sent_count': 0, 'errors': ['推送失败']}


# ==================== 心跳发送 ====================

import threading
_heartbeat_thread_started = False


def send_heartbeat():
    """向 ops-center 发送一次心跳"""
    try:
        enabled, url, api_key, timeout = get_config()
        if not enabled or not url or not api_key:
            logger.warning('心跳发送跳过: 推送未启用或未配置中心地址/API Key')
            return False

        import requests
        resp = requests.post(
            f'{url.rstrip("/")}/api/receive/heartbeat/',
            json={'status': 'online', 'message': 'normal'},
            headers={'X-API-Key': api_key, 'Content-Type': 'application/json'},
            timeout=timeout,
        )
        if resp.status_code == 200:
            logger.info('心跳发送成功')
            return True
        else:
            logger.warning(f'心跳发送失败: HTTP {resp.status_code} - {resp.text[:200]}')
            return False
    except Exception as e:
        logger.error(f'心跳发送异常: {e}')
        return False


def _heartbeat_loop():
    """后台心跳循环（每 5 分钟）"""
    import time
    while True:
        try:
            send_heartbeat()
        except Exception as e:
            logger.error(f'心跳循环异常: {e}')
        time.sleep(300)  # 5 分钟


def start_heartbeat():
    """启动心跳后台线程（全局唯一）"""
    global _heartbeat_thread_started
    if _heartbeat_thread_started:
        return
    _heartbeat_thread_started = True
    t = threading.Thread(target=_heartbeat_loop, daemon=True)
    t.start()
    logger.info('心跳后台线程已启动')


# ==================== 知识包异步检查 ====================

_ktime = 0  # 上次检查时间


def _deferred_knowledge_check():
    """
    推送成功后异步检查知识包版本（每 60 秒最多一次）。
    如果发现新版本，自动触发同步。
    """
    global _ktime
    now = time.time()
    if now - _ktime < 60:
        return  # 限流：每分钟最多一次
    _ktime = now

    import threading

    def _check():
        try:
            from apps.dashboard.knowledge_updater import check_and_update
            result = check_and_update()
            if result.get('updated'):
                logger.info(f'知识包自动更新成功: {result.get("version")}')
            elif result.get('success'):
                logger.debug(f'知识包无需更新: {result.get("message", "")}')
        except Exception as e:
            logger.debug(f'知识包检查跳过: {e}')

    t = threading.Thread(target=_check, daemon=True)
    t.start()


# ==================== 补丁异步检查 ====================

_ptime = 0  # 上次检查时间


def _deferred_patch_check():
    """
    推送成功后异步检查补丁版本（每 5 分钟最多一次）。
    如果发现新版本，打印日志提醒管理员。
    """
    global _ptime
    now = time.time()
    if now - _ptime < 300:
        return
    _ptime = now

    import threading

    def _check():
        try:
            from apps.system.models import SystemSetting
            url = SystemSetting.get('push.center_url', '')
            if not url:
                return
            import requests

            # 必须先读本地版本并随请求带给中心端：中心端按
            # needs_update = (not client_version) or client_version != latest 判定，
            # 不带版本号会因 client_version 为空而恒为 True（永远提示"有新版本"）
            ver_file = os.path.expanduser('~/.openclaw/patches/patch_version.txt')
            local_ver = ''
            if os.path.exists(ver_file):
                try:
                    local_ver = open(ver_file).read().strip()
                except Exception:
                    local_ver = ''

            center = f'{url.rstrip("/")}/api/collector/patches/'
            params = {'version': local_ver} if local_ver else None
            resp = requests.get(center, params=params, timeout=5)
            if resp.status_code == 200:
                meta = resp.json()
                if meta.get('needs_update'):
                    logger.warning(
                        f'发现新补丁: {local_ver or "(未安装)"} → {meta["latest_version"]}'
                    )
                    logger.warning(f'更新内容: {meta.get("changelog", [])}')
                    logger.warning(f'请运行: bash apply-patch.sh')
                # 缓存检查结果供 dashboard 使用
                try:
                    cache_path = os.path.expanduser('~/.openclaw/patches/patch_check_cache.json')
                    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                    with open(cache_path, 'w') as f:
                        json.dump({
                            'local_version': local_ver,
                            'needs_update': meta.get('needs_update', False),
                            'latest_version': meta['latest_version'],
                            'changelog': meta.get('changelog', []),
                            'checked_at': time.time(),
                        }, f)
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f'补丁检查跳过: {e}')

    t = threading.Thread(target=_check, daemon=True)
    t.start()
