#!/usr/bin/env python3
"""
数据库巡检执行器 v3
- 结构化保存巡检结果
- 格式化检查项输出
- 报警阈值判断
"""
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

import django
django.setup()

from apps.inspection.models import InspectionTask, InspectionResult, InspectionRecord
from apps.inspection.db_connectors import get_connector_from_asset, INSPECTION_TEMPLATES


# ========== 报警阈值配置 ==========
THRESHOLDS = {
    'MYSQL': {
        'buffer_pool_hit_ratio': {'min': 90, 'warn': 95, 'unit': '%', 'name': '缓冲池命中率'},
        'threads_connected': {'max': 100, 'warn': 50, 'unit': '', 'name': '连接数'},
        'slow_queries': {'max': 10, 'warn': 5, 'unit': '条/小时', 'name': '慢查询'},
        'aborted_connects': {'max': 10, 'warn': 5, 'unit': '', 'name': '异常连接'},
        'db_size_mb': {'max': 50000, 'warn': 30000, 'unit': 'MB', 'name': '数据库大小'},
    },
    'MSSQL': {
        'buffer_cache_hit_ratio': {'min': 90, 'warn': 95, 'unit': '%', 'name': '缓冲命中率'},
        'page_life_expectancy': {'min': 300, 'warn': 500, 'unit': '秒', 'name': '页面预期寿命'},
        'batch_requests_per_sec': {'max': 5000, 'warn': 2000, 'unit': '次/秒', 'name': '每秒请求数'},
        'active_sessions': {'max': 100, 'warn': 50, 'unit': '', 'name': '活跃会话'},
        'file_used_pct': {'max': 90, 'warn': 80, 'unit': '%', 'name': '文件使用率'},
        'backup_days_ago': {'max': 7, 'warn': 3, 'unit': '天', 'name': '备份天数'},
        'slow_query_count': {'max': 20, 'warn': 10, 'unit': '条', 'name': '慢查询数'},
        'lock_count': {'max': 5, 'warn': 1, 'unit': '个', 'name': '锁数量'},
    },
    'ORACLE': {
        'buffer_hit_ratio': {'min': 95, 'warn': 98, 'unit': '%', 'name': '缓冲命中率'},
        'tablespace_used_pct': {'max': 90, 'warn': 80, 'unit': '%', 'name': '表空间使用率'},
        'archive_log_used_pct': {'max': 90, 'warn': 80, 'unit': '%', 'name': '归档日志使用率'},
        'active_sessions': {'max': 100, 'warn': 50, 'unit': '', 'name': '活跃会话'},
        'hard_parse_ratio': {'max': 20, 'warn': 10, 'unit': '%', 'name': '硬解析率'},
    }
}


def check_threshold(db_type, key, value):
    """检查阈值，返回 (status, message)"""
    threshold = THRESHOLDS.get(db_type, {}).get(key)
    if not threshold or value is None:
        return 'pass', ''

    try:
        val = float(value)
    except (ValueError, TypeError):
        return 'warning', f'值无法解析: {value}'

    name = threshold['name']
    unit = threshold['unit']

    if 'min' in threshold:
        # 值越小越危险（如命中率）
        if val < threshold['min']:
            return 'fail', f'{name} {val}{unit} 低于危险阈值 {threshold["min"]}{unit}'
        elif val < threshold['warn']:
            return 'warning', f'{name} {val}{unit} 低于警告阈值 {threshold["warn"]}{unit}'
    if 'max' in threshold:
        # 值越大越危险（如使用率）
        if val > threshold['max']:
            return 'fail', f'{name} {val}{unit} 超过危险阈值 {threshold["max"]}{unit}'
        elif val > threshold['warn']:
            return 'warning', f'{name} {val}{unit} 超过警告阈值 {threshold["warn"]}{unit}'

    return 'pass', f'{name} {val}{unit} 正常'


def format_size(mb_val):
    """格式化大小"""
    try:
        mb = float(mb_val)
        if mb >= 1024:
            return f'{mb / 1024:.1f} GB'
        return f'{mb:.1f} MB'
    except:
        return str(mb_val)


def format_pct(val):
    """格式化百分比"""
    try:
        return f'{float(val):.1f}%'
    except:
        return str(val)


def format_countdown_days(date_str):
    """计算距今天数"""
    try:
        from datetime import datetime as dt
        if isinstance(date_str, str):
            # 处理中文日期格式
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%m月 %d %Y']:
                try:
                    d = dt.strptime(date_str.strip(), fmt)
                    break
                except:
                    continue
            else:
                return None, date_str
        else:
            d = date_str
        days = (datetime.now() - d.replace(tzinfo=None)).days if hasattr(d, 'replace') else (datetime.now() - d).days
        return days, f'{days}天前'
    except:
        return None, str(date_str)


# ========== 巡检执行器 ==========
def run_inspection_v3(task_id, custom_sql=None, db_config=None):
    """执行数据库巡检 v3"""
    task = InspectionTask.objects.select_related('asset', 'asset__asset_type').get(id=task_id)
    asset = task.asset

    InspectionResult.objects.filter(task=task).delete()
    InspectionRecord.objects.filter(task=task).delete()

    start_time = datetime.now()

    # 获取连接器
    if db_config:
        from apps.inspection.db_connectors import get_connector
        connector = get_connector(db_config)
    else:
        connector = get_connector_from_asset(asset)

    # 判断数据库类型
    name_lower = asset.asset_name.lower()
    if 'mssql' in name_lower or 'sql server' in name_lower or (db_config and db_config.get('db_type') == 'MSSQL'):
        db_type = 'MSSQL'
    elif 'oracle' in name_lower or (db_config and db_config.get('db_type') == 'ORACLE'):
        db_type = 'ORACLE'
    else:
        db_type = 'MYSQL'

    results = []

    # 1. 连接测试
    conn = connector.check_connection()
    connected = conn['status'] == 'success'
    results.append(_make_result(task, asset, '数据库连接', 'DB_CONNECTION',
        'pass' if connected else 'fail',
        '连接成功' if connected else f'连接失败: {conn["message"][:150]}',
        f'{db_type} 连接{"正常" if connected else "失败"}',
        '' if connected else '请检查网络、端口、用户名密码'))

    if not connected:
        return _save_record(task, asset, results, start_time, '数据库连接失败')

    # 根据类型执行检查
    if db_type == 'MSSQL':
        results.extend(_check_mssql(connector, task, asset))
    elif db_type == 'ORACLE':
        results.extend(_check_oracle(connector, task, asset))
    else:
        results.extend(_check_mysql(connector, task, asset))

    # 自定义SQL
    if custom_sql:
        for sql_item in custom_sql:
            try:
                r = connector.execute_custom_sql(sql_item['sql'])
                if r['status'] == 'success':
                    value = f'{r["row_count"]} 行'
                    msg = f'列: {", ".join(r["columns"][:5])}'
                    if r['rows']:
                        msg += f'\n首行: {json.dumps(r["rows"][0], ensure_ascii=False)[:200]}'
                    status = 'pass'
                else:
                    value = '执行失败'
                    msg = r.get('message', '')
                    status = 'fail'
                results.append(_make_result(task, asset, f'SQL: {sql_item.get("name","")}', 'CUSTOM_SQL', status, value, msg))
            except Exception as e:
                results.append(_make_result(task, asset, f'SQL: {sql_item.get("name","")}', 'CUSTOM_SQL', 'fail', '异常', str(e)[:300]))

    return _save_record(task, asset, results, start_time)


def _check_mssql(connector, task, asset):
    """MSSQL 专项检查"""
    results = []
    db_type = 'MSSQL'

    # 版本
    info = connector.get_server_info()
    version = info.get('version', '未知') if info else '未知'
    results.append(_make_result(task, asset, '数据库版本', 'DB_VERSION', 'pass', version[:80], f'SQL Server 版本: {version[:60]}'))

    # 数据库列表
    dbs = connector.get_databases()
    db_names = [d.get('name', '?') for d in dbs]
    results.append(_make_result(task, asset, '数据库列表', 'DB_LIST', 'pass', f'{len(dbs)} 个数据库', ', '.join(db_names)))

    # 数据库文件大小
    sizes = connector.get_database_sizes()
    total_mb = 0
    file_details = []
    for s in sizes:
        size_mb = float(s.get('size_mb', 0) or 0)
        used_val = s.get('used_mb', 0)
        try:
            used_mb = float(used_val) if used_val and str(used_val).upper() != 'NULL' else 0
        except (ValueError, TypeError):
            used_mb = 0
        total_mb += size_mb
        pct = round(used_mb / size_mb * 100, 1) if size_mb > 0 else 0
        fname = s.get('file_name', '?')
        ftype = s.get('file_type', '?')
        file_details.append(f'{fname}({ftype}): {format_size(size_mb)}, 已用 {format_pct(pct)}')

        # 检查文件使用率
        if ftype in ('ROWS', 'LOG'):
            st, msg = check_threshold(db_type, 'file_used_pct', pct)
            if st != 'pass':
                results.append(_make_result(task, asset, f'{fname} 使用率', 'FILE_USAGE', st, format_pct(pct), msg, suggestion='考虑扩容或收缩日志' if st == 'fail' else ''))

    results.append(_make_result(task, asset, '数据库文件', 'DB_FILES', 'pass',
        f'{len(sizes)} 个文件, 总计 {format_size(total_mb)}', '\n'.join(file_details[:15])))

    # 会话
    sessions = connector.get_session_info()
    total_sess = sessions.get('total_sessions', 0)
    active_sess = len(sessions.get('active_sessions', []))
    st, msg = check_threshold(db_type, 'active_sessions', total_sess)
    results.append(_make_result(task, asset, '会话信息', 'SESSIONS', st,
        f'总数 {total_sess}, 活跃 {active_sess}', msg or f'当前 {total_sess} 个用户会话'))

    # 性能
    perf = connector.get_performance_info()
    if perf:
        hit = float(perf.get('buffer_cache_hit_ratio', 0) or 0)
        st, msg = check_threshold(db_type, 'buffer_cache_hit_ratio', hit)
        results.append(_make_result(task, asset, '缓冲命中率', 'BUFFER_HIT', st,
            format_pct(hit), msg or f'命中率 {hit}%',
            suggestion='考虑增加内存' if st == 'fail' else ''))

        ple = int(perf.get('page_life_expectancy', 0) or 0)
        st, msg = check_threshold(db_type, 'page_life_expectancy', ple)
        results.append(_make_result(task, asset, '页面预期寿命', 'PAGE_LIFE', st,
            f'{ple} 秒', msg or f'PLE {ple} 秒'))

        batch = int(perf.get('batch_requests_per_sec', 0) or 0)
        st, msg = check_threshold(db_type, 'batch_requests_per_sec', batch)
        results.append(_make_result(task, asset, '每秒请求数', 'BATCH_REQ', st,
            f'{batch} 次/秒', msg or f'Batch Requests {batch}/s'))

    # 备份
    backup = connector.get_backup_info()
    if backup:
        latest = backup[0]
        bk_time = latest.get('last_backup_time', latest.get('backup_start_date', '?'))
        bk_db = latest.get('database_name', '?')
        bk_size = latest.get('backup_size_mb', latest.get('size_mb', '?'))
        days, days_str = format_countdown_days(bk_time)
        st = 'pass'
        msg = f'最近备份: {bk_db} ({bk_time}, {bk_size} MB)'
        if days is not None:
            st, _ = check_threshold(db_type, 'backup_days_ago', days)
            msg += f' ({days_str})'
            if st != 'pass':
                msg += ' ⚠️ 超过建议备份周期'
        results.append(_make_result(task, asset, '备份状态', 'BACKUP', st,
            f'{bk_db}: {bk_time}', msg,
            suggestion='建议立即安排备份' if st != 'pass' else ''))
    else:
        results.append(_make_result(task, asset, '备份状态', 'BACKUP', 'warning', '无备份记录', '无备份记录，请配置备份策略'))

    # 慢查询
    slow = connector.get_slow_queries()
    st, msg = check_threshold(db_type, 'slow_query_count', len(slow))
    preview = json.dumps(slow[:3], ensure_ascii=False)[:300] if slow else '无'
    results.append(_make_result(task, asset, '慢查询', 'SLOW_QUERIES', st,
        f'{len(slow)} 条', msg or preview,
        suggestion='建议优化慢查询' if st != 'pass' else ''))

    # 锁信息
    locks = connector.get_lock_info()
    st, msg = check_threshold(db_type, 'lock_count', len(locks))
    results.append(_make_result(task, asset, '锁信息', 'LOCK_INFO', st,
        f'{len(locks)} 个', msg or '无阻塞锁'))

    return results


def _check_oracle(connector, task, asset):
    """Oracle 专项检查"""
    results = []
    db_type = 'ORACLE'

    info = connector.get_server_info()
    version = info.get('version', '未知') if info else '未知'
    results.append(_make_result(task, asset, '数据库版本', 'DB_VERSION', 'pass', version[:80], f'Oracle 版本: {version[:60]}'))

    # 表空间
    ts = connector.get_tablespace_info()
    for t in ts:
        name = t.get('TABLESPACE_NAME', t.get('tablespace_name', '?'))
        pct = float(t.get('USED_PCT', t.get('used_pct', 0)) or 0)
        st, msg = check_threshold(db_type, 'tablespace_used_pct', pct)
        if st != 'pass':
            results.append(_make_result(task, asset, f'表空间 {name}', 'TABLESPACE_USAGE', st,
                format_pct(pct), msg, suggestion='建议扩容或清理' if st == 'fail' else ''))
    results.append(_make_result(task, asset, '表空间概览', 'TABLESPACE', 'pass',
        f'{len(ts)} 个表空间', json.dumps(ts[:5], ensure_ascii=False)[:300]))

    # 归档日志
    archive = connector.get_archive_logs()
    if archive:
        dest = archive.get('recovery_dest', {})
        pct = float(dest.get('USED_PCT', 0) or 0)
        st, msg = check_threshold(db_type, 'archive_log_used_pct', pct)
        results.append(_make_result(task, asset, '归档日志', 'ARCHIVE_LOG', st,
            f'使用率 {format_pct(pct)}', msg or f'归档空间正常 ({format_pct(pct)})',
            suggestion='建议清理归档日志' if st != 'pass' else ''))

    # RMAN 备份
    backup = connector.get_backup_info()
    if backup:
        latest = backup[0]
        results.append(_make_result(task, asset, 'RMAN备份', 'BACKUP', 'pass',
            f'{latest.get("status", "?")} ({latest.get("start_time", "?")})',
            json.dumps(latest, ensure_ascii=False)[:200]))
    else:
        results.append(_make_result(task, asset, 'RMAN备份', 'BACKUP', 'warning', '无备份记录', ''))

    # 错误日志
    errors = connector.get_error_logs()
    results.append(_make_result(task, asset, 'ORA-错误日志', 'ERROR_LOG',
        'pass' if len(errors) == 0 else 'warning',
        f'{len(errors)} 条', '无 ORA- 错误' if len(errors) == 0 else json.dumps(errors[:3], ensure_ascii=False)[:200]))

    # 慢SQL
    slow = connector.get_slow_queries()
    results.append(_make_result(task, asset, '资源消耗SQL', 'SLOW_SQL',
        'pass' if len(slow) == 0 else 'warning',
        f'{len(slow)} 条', json.dumps(slow[:3], ensure_ascii=False)[:300] if slow else '无'))

    # 锁
    locks = connector.get_lock_info()
    results.append(_make_result(task, asset, '锁信息', 'LOCK_INFO',
        'pass' if len(locks) == 0 else 'warning',
        f'{len(locks)} 个', '无阻塞锁' if len(locks) == 0 else str(locks[:3])[:200]))

    return results


def _check_mysql(connector, task, asset):
    """MySQL 专项检查"""
    results = []
    db_type = 'MYSQL'

    info = connector.get_server_info()
    version = info.get('version', '未知') if info else '未知'
    results.append(_make_result(task, asset, '数据库版本', 'DB_VERSION', 'pass', version[:80], f'MySQL {version[:60]}'))

    # 数据库大小
    sizes = connector.get_database_sizes()
    total_mb = sum(float(s.get('total_size_mb', 0) or 0) for s in sizes)
    st, _ = check_threshold(db_type, 'db_size_mb', total_mb)
    details = [f'{s.get("database_name")}: {format_size(s.get("total_size_mb",0))}' for s in sizes[:10]]
    results.append(_make_result(task, asset, '数据库大小', 'DB_SIZE', st,
        f'总计 {format_size(total_mb)}', '\n'.join(details)))

    # 性能
    perf = connector.get_performance_info()
    if perf:
        hit = float(perf.get('buffer_pool_hit_ratio', 0) or 0)
        st, msg = check_threshold(db_type, 'buffer_pool_hit_ratio', hit)
        results.append(_make_result(task, asset, '缓冲池命中率', 'BUFFER_HIT', st,
            format_pct(hit), msg or f'命中率 {hit}%'))

        slow = int(perf.get('slow_queries', 0) or 0)
        st, msg = check_threshold(db_type, 'slow_queries', slow)
        results.append(_make_result(task, asset, '慢查询', 'SLOW_QUERIES', st,
            f'{slow} 条', msg or f'慢查询 {slow} 条'))

    # 会话
    sessions = connector.get_session_info()
    threads = sessions.get('threads_connected', 0)
    st, msg = check_threshold(db_type, 'threads_connected', threads)
    results.append(_make_result(task, asset, '会话信息', 'SESSIONS', st,
        f'连接数 {threads}', msg or f'当前 {threads} 个连接'))

    return results


def _make_result(task, asset, name, code, status, value, message='', suggestion=''):
    """创建巡检结果对象"""
    return InspectionResult(
        task=task, asset=asset,
        check_item=name, check_item_code=code,
        status=status, result_value=str(value)[:500],
        result_message=str(message)[:1000],
        suggestion=str(suggestion)[:500] if suggestion else '',
    )


def _save_record(task, asset, results, start_time, prefix=''):
    """保存巡检结果"""
    from django.utils import timezone

    for r in results:
        r.save()

    pass_n = sum(1 for r in results if r.status == 'pass')
    warn_n = sum(1 for r in results if r.status == 'warning')
    fail_n = sum(1 for r in results if r.status == 'fail')
    overall = 'fail' if fail_n else ('warning' if warn_n else 'pass')

    summary = prefix or f'{len(results)}项检查: {pass_n}通过, {warn_n}警告, {fail_n}异常'

    record = InspectionRecord.objects.create(
        task=task, asset=asset,
        total_checks=len(results), pass_checks=pass_n,
        warning_checks=warn_n, fail_checks=fail_n,
        status='completed', overall_status=overall,
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

    record = run_inspection_v3(args.task_id)
    print(f'巡检完成: {record.summary}')
    print(f'通过: {record.pass_checks}, 警告: {record.warning_checks}, 异常: {record.fail_checks}')
