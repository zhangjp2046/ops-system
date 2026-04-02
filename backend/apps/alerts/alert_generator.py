#!/usr/bin/env python3
"""
告警生成服务
根据 Ping 检测和巡检结果自动生成告警
"""
import logging
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


def create_alert(title, description, customer, asset=None, severity=2,
                 alert_type='', source='LOCAL', metric_name='', metric_value='',
                 threshold='', alert_data=None):
    """
    创建告警（带去重：同一资产同类型未关闭告警不重复创建）
    """
    from apps.alerts.models import Alert
    
    # 去重：检查同一资产是否有未关闭的同类告警
    if asset:
        existing = Alert.objects.filter(
            asset=asset,
            alert_type=alert_type,
            status__in=['NEW', 'ACKNOWLEDGED', 'IN_PROGRESS'],
            title=title
        ).first()
        if existing:
            logger.debug(f'告警已存在，跳过: {title} ({asset.asset_name})')
            return existing
    
    alert = Alert.objects.create(
        title=title,
        description=description,
        customer=customer,
        asset=asset,
        severity=severity,
        alert_type=alert_type,
        source=source,
        metric_name=metric_name,
        metric_value=metric_value,
        threshold=threshold,
        occurred_at=timezone.now(),
        alert_data=alert_data or {},
    )
    logger.info(f'创建告警: {title} severity={severity} source={source}')
    return alert


def resolve_alerts_for_asset(asset, alert_type=None):
    """
    自动解决资产的相关告警（资产恢复时）
    """
    from apps.alerts.models import Alert
    
    qs = Alert.objects.filter(
        asset=asset,
        status__in=['NEW', 'ACKNOWLEDGED', 'IN_PROGRESS']
    )
    if alert_type:
        qs = qs.filter(alert_type=alert_type)
    
    resolved = qs.update(status='RESOLVED', resolved_at=timezone.now())
    if resolved:
        logger.info(f'自动解决 {resolved} 条告警: {asset.asset_name}')
    return resolved


# ==================== Ping 检测告警 ====================

def generate_ping_alerts(ping_results):
    """
    根据 Ping 检测结果生成告警
    
    ping_results: [{
        'asset_id': int,
        'asset_name': str,
        'ip': str,
        'is_online': bool,
        'response_time': float or None,
    }, ...]
    """
    from apps.assets.models import Asset
    
    for item in ping_results:
        try:
            asset = Asset.objects.select_related('customer').get(id=item['asset_id'])
        except Asset.DoesNotExist:
            continue
        
        if not asset.customer:
            continue
        
        if item['is_online']:
            # 在线：解决之前的离线告警
            resolve_alerts_for_asset(asset, alert_type='PING_OFFLINE')
        else:
            # 离线：创建告警
            create_alert(
                title=f'资产离线: {asset.asset_name}',
                description=f'资产 {asset.asset_name} ({item.get("ip", "无IP")}) 无法Ping通，可能已离线。',
                customer=asset.customer,
                asset=asset,
                severity=4,  # 严重
                alert_type='PING_OFFLINE',
                source='PING',
                metric_name='ping_status',
                metric_value='offline',
                threshold='reachable',
                alert_data={
                    'ip': item.get('ip'),
                    'asset_name': asset.asset_name,
                }
            )


# ==================== 巡检结果告警 ====================

def generate_inspection_alerts(task):
    """
    根据巡检任务结果生成告警
    
    task: InspectionTask 实例（已完成）
    """
    from apps.alerts.models import Alert
    from apps.inspection.models import InspectionResult
    
    if not task.asset or not task.asset.customer:
        return
    
    asset = task.asset
    customer = asset.customer
    plan_name = task.plan.name if task.plan else '未知计划'
    
    # 获取巡检结果
    results = InspectionResult.objects.filter(task=task)
    
    for r in results:
        if r.status == 'pass':
            # 通过：解决之前的同类告警
            resolve_alerts_for_asset(
                asset,
                alert_type=f'INSPECTION_{r.check_item_code}'
            )
        elif r.status in ('warning', 'fail'):
            # 警告/失败：创建告警
            severity = 3 if r.status == 'fail' else 2  # fail=错误, warning=警告
            description_parts = [
                f'巡检计划: {plan_name}',
                f'检查项: {r.check_item}',
                f'结果: {r.result_value}',
                f'说明: {r.result_message}',
            ]
            if r.suggestion:
                description_parts.append(f'建议: {r.suggestion}')
            
            create_alert(
                title=f'{r.check_item} {"异常" if r.status == "fail" else "警告"}: {asset.asset_name}',
                description='\n'.join(description_parts),
                customer=customer,
                asset=asset,
                severity=severity,
                alert_type=f'INSPECTION_{r.check_item_code}',
                source='INSPECTION',
                metric_name=r.check_item,
                metric_value=r.result_value,
                alert_data={
                    'check_item': r.check_item,
                    'check_item_code': r.check_item_code,
                    'status': r.status,
                    'result_value': r.result_value,
                    'result_message': r.result_message,
                    'suggestion': r.suggestion,
                    'plan_name': plan_name,
                    'task_id': task.id,
                }
            )
    
    # 统计
    fail_count = results.filter(status='fail').count()
    warning_count = results.filter(status='warning').count()
    logger.info(f'巡检告警生成完成: {asset.asset_name} - {fail_count}失败, {warning_count}警告')
