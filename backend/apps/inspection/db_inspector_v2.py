#!/usr/bin/env python3
"""
数据库巡检执行器 v2
支持 MySQL / MSSQL / Oracle 差异化巡检
支持自定义 SQL 执行
"""
import os
import sys
from datetime import datetime
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.inspection.models import InspectionTask, InspectionResult, InspectionRecord
from apps.inspection.db_connectors import get_connector_from_asset, INSPECTION_TEMPLATES


def format_size(mb_val):
    """格式化大小"""
    try:
        mb = float(mb_val)
        if mb >= 1024:
            return f'{mb / 1024:.2f} GB'
        return f'{mb:.2f} MB'
    except:
        return str(mb_val)


def run_inspection(task_id, custom_sql=None, db_config=None):
    """
    执行数据库巡检
    :param task_id: 巡检任务 ID
    :param custom_sql: 可选的自定义 SQL 列表 [{'name': 'xxx', 'sql': 'SELECT ...'}]
    :param db_config: 可选的数据库连接配置（覆盖资产字段）
    :return: InspectionRecord
    """
    task = InspectionTask.objects.select_related('asset', 'asset__asset_type').get(id=task_id)
    asset = task.asset

    # 清除旧结果
    InspectionResult.objects.filter(task=task).delete()
    InspectionRecord.objects.filter(task=task).delete()

    start_time = datetime.now()

    # 获取连接器
    try:
        if db_config:
            from apps.inspection.db_connectors import get_connector
            connector = get_connector(db_config)
        else:
            connector = get_connector_from_asset(asset)
    except Exception as e:
        return _create_record(task, asset, [], start_time, f'无法创建连接器: {e}')

    # 获取巡检模板
    name_lower = asset.asset_name.lower()
    if 'mssql' in name_lower or 'sql server' in name_lower:
        db_type = 'MSSQL'
    elif 'oracle' in name_lower:
        db_type = 'ORACLE'
    else:
        db_type = 'MYSQL'

    template = INSPECTION_TEMPLATES.get(db_type, INSPECTION_TEMPLATES['MYSQL'])
    results = []

    # 连接测试
    conn_result = connector.check_connection()
    connected = conn_result['status'] == 'success'

    results.append(InspectionResult(
        task=task, asset=asset,
        check_item='数据库连接', check_item_code='DB_CONNECTION',
        status='pass' if connected else 'fail',
        result_value='连接成功' if connected else f'连接失败: {conn_result["message"][:200]}',
        result_message=f'{db_type} 连接{"正常" if connected else "失败"}',
        expected_value='连接成功',
        suggestion='' if connected else '请检查网络、端口、用户名密码配置',
    ))

    if not connected:
        return _create_record(task, asset, results, start_time, '数据库连接失败，部分检查使用模拟数据')

    # 执行各项检查
    for check in template['checks']:
        if check['code'] == 'DB_CONNECTION':
            continue  # 已处理

        method = getattr(connector, check['method'], None)
        if not method:
            continue

        try:
            data = method()
            result = _format_check_result(check['code'], check['name'], data, db_type)
            results.append(InspectionResult(
                task=task, asset=asset,
                check_item=result['name'],
                check_item_code=check['code'],
                status=result['status'],
                result_value=result['value'],
                result_message=result['message'],
                expected_value=result.get('expected', ''),
                suggestion=result.get('suggestion', ''),
            ))
        except Exception as e:
            results.append(InspectionResult(
                task=task, asset=asset,
                check_item=check['name'],
                check_item_code=check['code'],
                status='warning',
                result_value='异常',
                result_message=f'获取数据异常: {str(e)[:200]}',
            ))

    # 执行自定义 SQL
    if custom_sql:
        for sql_item in custom_sql:
            try:
                sql_result = connector.execute_custom_sql(sql_item['sql'])
                if sql_result['status'] == 'success':
                    value = f'{sql_result["row_count"]} 行结果'
                    message = f'列: {", ".join(sql_result["columns"][:5])}'
                    if sql_result['rows']:
                        first_row = sql_result['rows'][0]
                        message += f'\n首行: {str(first_row[:3])}'
                else:
                    value = f'执行失败'
                    message = sql_result.get('message', '')

                results.append(InspectionResult(
                    task=task, asset=asset,
                    check_item=f'自定义SQL: {sql_item.get("name", "未命名")}',
                    check_item_code=f'CUSTOM_SQL_{sql_item.get("name", "")}',
                    status='pass' if sql_result['status'] == 'success' else 'fail',
                    result_value=value,
                    result_message=message,
                    suggestion='自定义SQL执行结果',
                ))
            except Exception as e:
                results.append(InspectionResult(
                    task=task, asset=asset,
                    check_item=f'自定义SQL: {sql_item.get("name", "未命名")}',
                    check_item_code='CUSTOM_SQL',
                    status='fail',
                    result_value='异常',
                    result_message=str(e)[:500],
                ))

    # 保存结果
    return _create_record(task, asset, results, start_time, '')


def _format_check_result(code, name, data, db_type):
    """格式化检查结果"""
    if code == 'DB_VERSION':
        version = data.get('version', '未知') if isinstance(data, dict) else '未知'
        return {
            'name': name, 'status': 'pass', 'value': version[:80],
            'message': f'{db_type} 版本: {version[:60]}',
        }

    elif code == 'DB_LIST':
        if isinstance(data, list):
            names = [d.get('name', '?') for d in data[:10]]
            return {
                'name': name, 'status': 'pass',
                'value': f'{len(data)} 个数据库',
                'message': ', '.join(names),
            }
        return {'name': name, 'status': 'warning', 'value': '无数据', 'message': ''}

    elif code == 'DB_SIZE':
        if isinstance(data, list) and data:
            total = sum(float(d.get('total_size_mb', 0) or 0) for d in data)
            details = []
            for d in data[:10]:
                db_name = d.get('database_name', d.get('tablespace_name', '?'))
                size = format_size(d.get('total_size_mb', 0))
                details.append(f'{db_name}: {size}')
            return {
                'name': name, 'status': 'pass',
                'value': f'总计 {format_size(total)}',
                'message': '\n'.join(details),
            }
        return {'name': name, 'status': 'warning', 'value': '无数据', 'message': ''}

    elif code in ('TABLESPACE',):
        if isinstance(data, list) and data:
            warnings = []
            for d in data:
                pct = float(d.get('USED_PCT', d.get('used_pct', 0) or 0))
                if pct > 85:
                    warnings.append(f'{d.get("TABLESPACE_NAME", d.get("tablespace_name", "?"))}: {pct}%')
            status = 'warning' if warnings else 'pass'
            return {
                'name': name, 'status': status,
                'value': f'{len(data)} 个表空间',
                'message': f'告警: {", ".join(warnings)}' if warnings else '所有表空间使用正常',
                'suggestion': '建议扩容或清理' if warnings else '',
            }
        return {'name': name, 'status': 'pass', 'value': '无数据', 'message': ''}

    elif code == 'SESSIONS':
        if isinstance(data, dict):
            total = data.get('total_sessions', data.get('threads_connected', 0))
            active = len(data.get('active_sessions', data.get('active_processes', [])))
            return {
                'name': name, 'status': 'pass' if int(total) < 100 else 'warning',
                'value': f'总数 {total}, 活跃 {active}',
                'message': f'总连接数: {total}',
            }
        return {'name': name, 'status': 'pass', 'value': '无数据', 'message': ''}

    elif code in ('BUFFER_HIT',):
        if isinstance(data, dict):
            ratio = data.get('buffer_pool_hit_ratio', data.get('buffer_cache_hit_ratio', data.get('buffer_hit_ratio', 0)))
            ratio = float(ratio) if ratio else 0
            status = 'pass' if ratio >= 95 else ('warning' if ratio >= 85 else 'fail')
            return {
                'name': name, 'status': status,
                'value': f'{ratio}%',
                'message': f'命中率 {ratio}%',
                'expected': '> 95%',
                'suggestion': '' if ratio >= 95 else '缓冲区偏小，考虑增加内存',
            }
        return {'name': name, 'status': 'warning', 'value': '无数据', 'message': ''}

    elif code == 'BACKUP':
        if isinstance(data, list) and data:
            latest = data[0]
            time_str = latest.get('last_backup_time', latest.get('START_TIME', latest.get('start_time', '?')))
            return {'name': name, 'status': 'pass', 'value': f'最近: {time_str}', 'message': str(latest)}
        elif isinstance(data, dict):
            return {'name': name, 'status': 'warning', 'value': data.get('message', '未知'), 'message': str(data)}
        return {'name': name, 'status': 'warning', 'value': '无备份记录', 'message': ''}

    elif code in ('ARCHIVE_LOG',):
        if isinstance(data, dict):
            dest = data.get('recovery_dest', {})
            pct = float(dest.get('USED_PCT', 0) or 0)
            status = 'pass' if pct < 80 else ('warning' if pct < 95 else 'fail')
            return {
                'name': name, 'status': status,
                'value': f'使用率 {pct}%' if dest else '无数据',
                'message': f'归档目标: {format_size(dest.get("USED_MB", 0))} / {format_size(dest.get("LIMIT_MB", 0))}',
                'expected': '< 80%',
                'suggestion': '' if pct < 80 else '归档空间不足，建议清理或扩容',
            }
        return {'name': name, 'status': 'warning', 'value': '无数据', 'message': ''}

    elif code in ('ERROR_LOG', 'SLOW_QUERIES', 'SLOW_SQL', 'LOCK_INFO'):
        count = len(data) if isinstance(data, list) else 0
        status = 'pass' if count == 0 else ('warning' if count < 10 else 'fail')
        preview = str(data[:3])[:300] if data else ''
        return {
            'name': name, 'status': status,
            'value': f'{count} 条',
            'message': preview,
            'suggestion': '' if count == 0 else '请查看详情',
        }

    return {'name': name, 'status': 'pass', 'value': str(data)[:200], 'message': ''}


def _create_record(task, asset, results, start_time, summary_prefix):
    """保存巡检结果并创建记录"""
    # 保存结果
    for r in results:
        r.save()

    pass_n = sum(1 for r in results if r.status == 'pass')
    warn_n = sum(1 for r in results if r.status == 'warning')
    fail_n = sum(1 for r in results if r.status == 'fail')
    overall = 'fail' if fail_n else ('warning' if warn_n else 'pass')

    from django.utils import timezone
    summary = summary_prefix or f'{len(results)}项检查: {pass_n}通过, {warn_n}警告, {fail_n}异常'

    record = InspectionRecord.objects.create(
        task=task, asset=asset,
        total_checks=len(results),
        pass_checks=pass_n,
        warning_checks=warn_n,
        fail_checks=fail_n,
        status='completed',
        overall_status=overall,
        summary=summary,
        started_at=start_time,
        completed_at=timezone.now(),
        duration=int((timezone.now() - timezone.make_aware(start_time)).total_seconds()),
    )

    task.status = 'completed'
    task.executed_time = timezone.now()
    task.save()

    return record


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--task-id', type=int, required=True)
    args = parser.parse_args()

    record = run_inspection(args.task_id)
    print(f'巡检完成: {record.summary}')
    print(f'通过: {record.pass_checks}, 警告: {record.warning_checks}, 异常: {record.fail_checks}')
