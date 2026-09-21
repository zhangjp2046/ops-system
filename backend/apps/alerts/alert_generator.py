#!/usr/bin/env python3
"""
告警生成服务
根据 Ping 检测和巡检结果自动生成告警
支持阈值配置动态判断严重程度
"""
import logging
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)


def extract_numeric_value(value):
    """
    从巡检结果值中提取数字
    支持: '85%' -> 85, '0%' -> 0, '5 条' -> 5, '6个分区' -> 6
    """
    import re
    if not value:
        return None
    # 匹配第一个数字（支持小数）
    match = re.search(r'(\d+\.?\d*)', str(value))
    if match:
        return float(match.group(1))
    return None


def get_threshold_severity(check_item_code, result_value, customer_id=None,
                           asset_type_id=None, protocol=None):
    """
    根据阈值配置判断严重程度

    protocol: 计划/资产的协议类型。传入后只采纳**同协议**的行。
              阈值是按 客户/资产类型 + 协议 配置的，同名检查项在不同协议下
              阈值不同（各库的 SESSIONS 是 100/150/200/300），不区分协议会串。

    返回: (severity, severity_name, threshold_found)
    """
    try:
        from .threshold_models import AlertThreshold
        
        # 提取数值
        numeric_value = extract_numeric_value(result_value)
        if numeric_value is None:
            return None, None, False
        
        # 查找匹配的阈值配置（优先级: 客户+资产类型 > 客户 > 全局）
        queries = []
        
        if customer_id and asset_type_id:
            queries.append({
                'customer_id': customer_id,
                'asset_type_id': asset_type_id,
                'check_item_code': check_item_code,
                'is_active': True
            })
        
        if customer_id:
            queries.append({
                'customer_id': customer_id,
                'asset_type_id__isnull': True,
                'check_item_code': check_item_code,
                'is_active': True
            })
        
        queries.append({
            'customer_id__isnull': True,
            'asset_type_id__isnull': True,
            'check_item_code': check_item_code,
            'is_active': True
        })
        
        # 只采纳同协议的行（阈值是按协议配的，同名检查项跨协议阈值不同）
        if protocol:
            for q in queries:
                q['protocol'] = protocol
        
        for query in queries:
            # ⚠️ 同一层里可能有多行（本查询不区分 protocol），必须逐行挑出
            #    「真的配了阈值」的那一行；只判断 .first() 会在第一行是空阈值行时
            #    把整层放弃，把同层其它行上的阈值一起丢掉。
            #    按 pk 排序保证行为可预期（先建的先匹配，与旧逻辑一致）。
            candidates = AlertThreshold.objects.filter(**query).order_by('pk')
            threshold = next((t for t in candidates if t.has_effective_threshold()), None)
            if threshold:
                severity, severity_name = threshold.get_severity(numeric_value)
                logger.debug(f'阈值匹配: {check_item_code}={result_value}({numeric_value}) -> {severity_name}')
                return severity, severity_name, True
        
        return None, None, False
        
    except Exception as e:
        logger.warning(f'阈值检查异常: {e}')
        return None, None, False


def determine_severity(check_item_code, result_value, status, customer_id=None,
                       asset_type_id=None, protocol=None):
    """
    综合判断严重程度
    
    优先使用阈值配置，如果没有配置则使用默认逻辑
    返回: (severity, severity_name)
    """
    # 尝试使用阈值配置
    severity, severity_name, found = get_threshold_severity(
        check_item_code, result_value, customer_id, asset_type_id, protocol
    )
    
    if found:
        return severity, severity_name
    
    # 默认逻辑（向后兼容）
    if status == 'fail':
        return 3, '错误'
    elif status == 'warning':
        return 2, '警告'
    else:
        return 1, '信息'


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
    """根据 Ping 检测结果生成告警"""
    from apps.assets.models import Asset

    for item in ping_results:
        try:
            asset = Asset.objects.select_related('customer').get(id=item['asset_id'])
        except Asset.DoesNotExist:
            continue

        if not asset.customer:
            continue

        if item['is_online']:
            resolve_alerts_for_asset(asset, alert_type='PING_OFFLINE')
        else:
            ip = item.get('ip', '无IP')
            now_str = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            desc_lines = [
                f'**资产名称**: {asset.asset_name}',
                f'**IP地址**: {ip}',
                f'**资产类型**: {asset.asset_type.type_name if asset.asset_type else "未知"}',
                f'**重要等级**: {asset.importance_level}',
                f'**负责人**: {asset.owner or "未指定"}',
                f'**检测时间**: {now_str}',
                f'',
                f'**检测结果**: Ping不通，资产可能已宕机或网络中断',
                f'',
                f'**处理建议**:',
                f'1. 检查设备电源是否正常',
                f'2. 检查网线/光纤连接',
                f'3. 确认交换机端口状态',
                f'4. 如有带外管理(iDRAC/iLO)，检查BMC是否可达',
            ]
            create_alert(
                title=f'🔴 资产离线: {asset.asset_name} ({ip})',
                description='\n'.join(desc_lines),
                customer=asset.customer,
                asset=asset,
                severity=4,
                alert_type='PING_OFFLINE',
                source='PING',
                metric_name='ping_status',
                metric_value='offline',
                threshold='reachable',
                alert_data={'ip': ip, 'asset_name': asset.asset_name}
            )


# ==================== 巡检结果告警 ====================

def generate_inspection_alerts(task):
    """根据巡检任务结果生成告警（支持阈值配置）"""
    from apps.alerts.models import Alert
    from apps.inspection.models import InspectionResult

    if not task.asset or not task.asset.customer:
        return

    asset = task.asset
    customer = asset.customer
    plan_name = task.plan.name if task.plan else '未知计划'
    protocol = task.plan.protocol if task.plan else ''
    exec_time = (task.executed_time or timezone.now()).strftime('%Y-%m-%d %H:%M:%S')

    results = list(InspectionResult.objects.filter(task=task))
    all_results_summary = []
    for r in results:
        icon = '✅' if r.status == 'pass' else ('⚠️' if r.status == 'warning' else '❌')
        all_results_summary.append(f'{icon} {r.check_item}: {r.result_value} — {(r.result_message or "")[:50]}')

    for r in results:
        alert_type = f'INSPECTION_{r.check_item_code}'
        
        if r.status == 'pass':
            resolve_alerts_for_asset(asset, alert_type=alert_type)
        else:
            # 使用阈值配置判断严重程度
            severity, severity_name = determine_severity(
                check_item_code=r.check_item_code,
                result_value=r.result_value or '',
                status=r.status,
                customer_id=customer.id if customer else None,
                asset_type_id=asset.asset_type_id if asset else None,
                protocol=protocol or None
            )
            
            # 根据严重程度选择图标和文字
            severity_icons = {
                1: ('ℹ️', '信息'),
                2: ('🟡', '警告'),
                3: ('🔴', '错误'),
                4: ('🚨', '严重'),
            }
            icon, status_text = severity_icons.get(severity, ('⚠️', '异常'))

            desc_lines = [
                f'**资产名称**: {asset.asset_name}',
                f'**IP地址**: {asset.ip_address or "未配置"}',
                f'**巡检计划**: {plan_name} ({protocol.upper() if protocol else ""})',
                f'**执行时间**: {exec_time}',
                f'',
                f'---',
                f'',
                f'## 检查项: {r.check_item}',
                f'',
                f'**检查结果**: {r.result_value}',
                f'**严重程度**: {severity_name} ({severity}级)',
                f'',
                f'**详细信息**:',
                f'{r.result_message or "无"}',
            ]

            # 添加阈值信息
            threshold_info = get_threshold_info(r.check_item_code, customer.id if customer else None, asset.asset_type_id if asset else None, protocol or None)
            if threshold_info:
                desc_lines.extend([
                    '',
                    '**阈值配置**:',
                    f'- 警告阈值: {threshold_info.get("warning", "未配置")}',
                    f'- 错误阈值: {threshold_info.get("error", "未配置")}',
                    f'- 严重阈值: {threshold_info.get("critical", "未配置")}',
                    f'- 阈值方向: {threshold_info.get("direction", "")}',
                ])

            if r.suggestion:
                desc_lines.extend(['', f'**处理建议**: {r.suggestion}'])

            desc_lines.extend([
                '',
                '---',
                '',
                '## 本次巡检完整结果',
            ])
            desc_lines.extend(all_results_summary)

            create_alert(
                title=f'{icon} {r.check_item}{status_text}: {asset.asset_name}',
                description='\n'.join(desc_lines),
                customer=customer,
                asset=asset,
                severity=severity,
                alert_type=alert_type,
                source='INSPECTION',
                metric_name=r.check_item,
                metric_value=r.result_value,
                threshold=threshold_info.get('threshold_display', '') if threshold_info else '',
                alert_data={
                    'check_item': r.check_item,
                    'check_item_code': r.check_item_code,
                    'status': r.status,
                    'result_value': r.result_value,
                    'result_message': r.result_message,
                    'suggestion': r.suggestion,
                    'plan_name': plan_name,
                    'protocol': protocol,
                    'severity_from_threshold': threshold_info is not None,
                }
            )

    fail_count = sum(1 for r in results if r.status == 'fail')
    warning_count = sum(1 for r in results if r.status == 'warning')
    info_count = sum(1 for r in results if r.status == 'info')
    logger.info(f'巡检告警生成完成: {asset.asset_name} - {fail_count}失败, {warning_count}警告, {info_count}信息')


def get_threshold_info(check_item_code, customer_id=None, asset_type_id=None, protocol=None):
    """获取阈值配置信息（描述展示用；protocol 同 get_threshold_severity）"""
    try:
        from .threshold_models import AlertThreshold
        
        queries = []
        if customer_id and asset_type_id:
            queries.append({
                'customer_id': customer_id,
                'asset_type_id': asset_type_id,
                'check_item_code': check_item_code,
                'is_active': True
            })
        if customer_id:
            queries.append({
                'customer_id': customer_id,
                'asset_type_id__isnull': True,
                'check_item_code': check_item_code,
                'is_active': True
            })
        queries.append({
            'customer_id__isnull': True,
            'asset_type_id__isnull': True,
            'check_item_code': check_item_code,
            'is_active': True
        })
        
        # 只采纳同协议的行（与 get_threshold_severity 一致，避免描述里显示别的协议的阈值）
        if protocol:
            for q in queries:
                q['protocol'] = protocol

        for query in queries:
            threshold = AlertThreshold.objects.filter(**query).first()
            if threshold:
                return {
                    'warning': f'{threshold.warning_threshold}{threshold.unit}' if threshold.warning_threshold else '未配置',
                    'error': f'{threshold.error_threshold}{threshold.unit}' if threshold.error_threshold else '未配置',
                    'critical': f'{threshold.critical_threshold}{threshold.unit}' if threshold.critical_threshold else '未配置',
                    'direction': threshold.get_threshold_direction_display(),
                    'threshold_display': f'警告>{threshold.warning_threshold}{threshold.unit} 错误>{threshold.error_threshold}{threshold.unit} 严重>{threshold.critical_threshold}{threshold.unit}'
                }
        return None
    except Exception as e:
        logger.warning(f'获取阈值信息异常: {e}')
        return None
