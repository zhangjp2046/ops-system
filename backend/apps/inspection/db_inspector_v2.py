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
from apps.inspection.db_connectors import get_connector_from_asset, INSPECTION_TEMPLATES, _get_field
from apps.inspection.time_check import offset_from_epoch, time_sync_failure, get_threshold


def _get_ci(d, key):
    """Case-insensitive dict lookup: 先查原样，再查大写，再查小写"""
    if key in d:
        return d[key]
    upper = key.upper()
    if upper in d:
        return d[upper]
    lower = key.lower()
    if lower in d:
        return d[lower]
    return None


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
            # 如果有巡检计划协议，用它确定连接器类型
            plan_protocol = task.plan.protocol.upper() if task.plan and task.plan.protocol else ''
            if plan_protocol in ('MYSQL', 'MSSQL', 'ORACLE', 'POSTGRESQL'):
                # 从资产获取连接参数，但指定协议类型
                from apps.inspection.db_connectors import get_connector, _get_field
                host = asset.ip_address or _get_field(asset, 'db_host') or 'localhost'
                port = asset.port or _get_field(asset, 'db_port') or ''
                username = asset.username or _get_field(asset, 'db_username') or ''
                password = asset.password or _get_field(asset, 'db_password') or ''
                database = asset.database or _get_field(asset, 'db_name') or ''
                db_config_override = {
                    'host': host,
                    'port': port or {'MSSQL': '1433', 'ORACLE': '1521', 'MYSQL': '3306', 'POSTGRESQL': '5432'}.get(plan_protocol, '3306'),
                    'username': username,
                    'password': password,
                    'database': database or {'MSSQL': 'master', 'ORACLE': 'ORCL', 'MYSQL': 'mysql'}.get(plan_protocol, ''),
                    'db_type': plan_protocol,
                }
                connector = get_connector(db_config_override)
            else:
                connector = get_connector_from_asset(asset)
    except Exception as e:
        return _create_record(task, asset, [], start_time, f'无法创建连接器: {e}')

    # 获取巡检模板 — 优先使用巡检计划的协议，其次 database_type 字段，最后资产名猜测
    db_type = ''
    if task.plan and task.plan.protocol:
        proto = task.plan.protocol.upper()
        if proto in ('MSSQL', 'ORACLE', 'MYSQL', 'POSTGRESQL'):
            db_type = proto
    if not db_type:
        db_type = (_get_field(asset, 'database_type') or '').upper()
    if not db_type:
        name_lower = asset.asset_name.lower()
        if 'mssql' in name_lower or 'sql server' in name_lower or 'sql' in name_lower:
            db_type = 'MSSQL'
        elif 'oracle' in name_lower:
            db_type = 'ORACLE'
        elif 'mysql' in name_lower or 'mariadb' in name_lower:
            db_type = 'MYSQL'
        elif 'postgres' in name_lower or 'pgsql' in name_lower:
            db_type = 'POSTGRESQL'
        else:
            db_type = 'MYSQL'

    template = INSPECTION_TEMPLATES.get(db_type, INSPECTION_TEMPLATES['MYSQL'])
    results = []

    # 时间同步阈值取自巡检计划里该检查项所选的 threshold（10/60/180 秒，默认 60）
    time_threshold = get_threshold(task.plan.check_items if task.plan else None)

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
            result = _format_check_result(check['code'], check['name'], data, db_type, time_threshold)
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


def _format_check_result(code, name, data, db_type, time_threshold=60.0):
    """格式化检查结果"""
    if code == 'TIME_SYNC':
        epoch = _get_ci(data, 'epoch') if isinstance(data, dict) else None
        if epoch in (None, ''):
            status, value, message, suggestion = time_sync_failure(
                f'{db_type} 未返回服务器时间（可能不支持该查询）')
        else:
            status, value, message, suggestion = offset_from_epoch(
                epoch, f'{db_type} SELECT', threshold=time_threshold)
        return {
            'name': name, 'status': status, 'value': value,
            'message': message, 'suggestion': suggestion,
        }

    if code == 'DB_VERSION':
        version = _get_ci(data, 'version') if isinstance(data, dict) else '未知'
        if not version:
            version = '未知'
        return {
            'name': name, 'status': 'pass', 'value': str(version)[:80],
            'message': f'{db_type} 版本: {str(version)[:60]}',
        }

    elif code == 'DB_LIST':
        if isinstance(data, list):
            names = [_get_ci(d, 'name') or '?' for d in data[:10]]
            return {
                'name': name, 'status': 'pass',
                'value': f'{len(data)} 个数据库',
                'message': ', '.join(names),
            }
        return {'name': name, 'status': 'warning', 'value': '无数据', 'message': ''}

    elif code == 'DB_SIZE':
        if isinstance(data, list) and data:
            first = data[0]
            # MSSQL 新格式：data_size_mb / log_size_mb（分别聚合后的结果）
            if _get_ci(first, 'data_size_mb') is not None:
                total_data = sum(float(_get_ci(d, 'data_size_mb') or 0) for d in data)
                total_log = sum(float(_get_ci(d, 'log_size_mb') or 0) for d in data)
                details = []
                for d in data:
                    db = _get_ci(d, 'database_name') or '?'
                    data_sz = float(_get_ci(d, 'data_size_mb') or 0)
                    log_sz = float(_get_ci(d, 'log_size_mb') or 0)
                    details.append(f'{db}: 数据={format_size(data_sz)}, 日志={format_size(log_sz)}')
                return {
                    'name': name, 'status': 'pass',
                    'value': f'数据={format_size(total_data)}, 日志={format_size(total_log)}',
                    'message': '\n'.join(details[:10]),
                }
            # MSSQL 旧格式：按文件返回 (file_type / size_mb)
            elif _get_ci(first, 'file_type') is not None or _get_ci(first, 'size_mb') is not None:
                db_totals = {}
                for d in data:
                    db = _get_ci(d, 'database_name') or '?'
                    if db not in db_totals:
                        db_totals[db] = 0
                    db_totals[db] += float(_get_ci(d, 'size_mb') or 0)
                total = sum(db_totals.values())
                details = [f'{db}: {format_size(size)}' for db, size in sorted(db_totals.items())[:10]]
            else:
                # Oracle: total_size_mb 或 total_mb
                total = sum(float(_get_ci(d, 'total_size_mb') or _get_ci(d, 'total_mb') or 0) for d in data)
                details = [f'{_get_ci(d, "database_name") or _get_ci(d, "tablespace_name") or "?"}: {format_size(_get_ci(d, "total_size_mb") or _get_ci(d, "total_mb") or 0)}' for d in data[:10]]
            return {
                'name': name, 'status': 'pass',
                'value': f'总计 {format_size(total)}',
                'message': '\n'.join(details),
            }
        return {'name': name, 'status': 'warning', 'value': '无数据', 'message': ''}

    elif code in ('TABLESPACE',):
        if isinstance(data, list) and data:
            warnings = []
            has_usage_data = False
            for d in data:
                pct_raw = _get_ci(d, 'USED_PCT') or _get_ci(d, 'used_pct') or 'N/A'
                if pct_raw == 'N/A' or not pct_raw:
                    continue
                try:
                    pct = float(pct_raw)
                    has_usage_data = True
                    if pct > 85:
                        warnings.append(f'{_get_ci(d, "TABLESPACE_NAME") or _get_ci(d, "tablespace_name") or "?"}: {pct}%')
                except (ValueError, TypeError):
                    continue
            if has_usage_data:
                status = 'warning' if warnings else 'pass'
                message = f'告警: {", ".join(warnings)}' if warnings else '所有表空间使用正常'
            else:
                status = 'pass'
                message = '仅有总大小（需 DBA 权限获取使用率）'
            return {
                'name': name, 'status': status,
                'value': f'{len(data)} 个表空间',
                'message': message,
                'suggestion': '建议扩容或清理' if warnings else '',
            }
        return {'name': name, 'status': 'pass', 'value': '无数据', 'message': ''}

    elif code == 'SESSIONS':
        if isinstance(data, dict):
            total = _get_ci(data, 'total_sessions') or _get_ci(data, 'threads_connected') or 0
            active = len(_get_ci(data, 'active_sessions') or _get_ci(data, 'active_processes') or [])
            return {
                'name': name, 'status': 'pass' if int(total) < 100 else 'warning',
                'value': f'总数 {total}, 活跃 {active}',
                'message': f'总连接数: {total}',
            }
        return {'name': name, 'status': 'pass', 'value': '无数据', 'message': ''}

    elif code in ('BUFFER_HIT',):
        if isinstance(data, dict):
            ratio = _get_ci(data, 'buffer_pool_hit_ratio') or _get_ci(data, 'buffer_cache_hit_ratio') or _get_ci(data, 'buffer_hit_ratio') or 0
            ratio = float(ratio) if ratio else 0
            status = 'pass' if ratio >= 95 else 'warning'
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
            time_str = _get_ci(latest, 'last_backup_time') or _get_ci(latest, 'START_TIME') or _get_ci(latest, 'start_time') or '?'
            return {'name': name, 'status': 'pass', 'value': f'最近: {time_str}', 'message': str(latest)}
        elif isinstance(data, dict):
            return {'name': name, 'status': 'warning', 'value': _get_ci(data, 'message') or '未知', 'message': str(data)}
        return {'name': name, 'status': 'warning', 'value': '无备份记录', 'message': ''}

    elif code in ('ARCHIVE_LOG',):
        if isinstance(data, dict):
            dest = _get_ci(data, 'recovery_dest') or {}
            pct = float(_get_ci(dest, 'USED_PCT') or 0)
            status = 'pass' if pct < 80 else ('warning' if pct < 95 else 'fail')
            return {
                'name': name, 'status': status,
                'value': f'使用率 {pct}%' if dest else '无数据',
                'message': f'归档目标: {format_size(_get_ci(dest, "USED_MB") or 0)} / {format_size(_get_ci(dest, "LIMIT_MB") or 0)}',
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
