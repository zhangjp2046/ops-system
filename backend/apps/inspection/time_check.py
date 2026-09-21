#!/usr/bin/env python3
"""
时间同步检查 —— 公共逻辑

两条数据来源（都不用 SSH，权限都很低）：
  服务器   → SNMP hrSystemDate (1.3.6.1.2.1.25.1.2.0)，只需只读 community
  数据库   → SQL 取服务器 UTC epoch，只需 SELECT 权限

统一以 ops-system 本机时间为基准（本机时间由部署方保证准确），
算出偏差后按「巡检计划里该检查项所选阈值」判定。

⚠️ result_value 的第一个数字必须是偏差绝对值 —— get_threshold_severity 和
   record_monitoring_data 都用 re.findall 取首个数字，顺序错了会把别的数字
   当成偏差（磁盘那次把「磁盘个数」当使用率的同类坑）。

⚠️ 租户内网无外网：本模块不得引入任何外网时钟源。
"""
import time
import datetime

TIME_SYNC_OID = '1.3.6.1.2.1.25.1.2.0'   # hrSystemDate (HOST-RESOURCES-MIB)
DEFAULT_THRESHOLD = 60.0                  # 计划未指定阈值时的默认值（秒）


def get_threshold(check_items, default=DEFAULT_THRESHOLD):
    """从巡检计划的 check_items 里读 TIME_SYNC 的阈值（秒）。

    兼容三种形态：对象数组带 threshold、对象数组无 threshold、纯字符串数组。
    ⚠️ 前端当前可选档位为 10/60/180 秒（默认 60）。老计划里可能残留 1 秒档，
       这里按原值读取（不做归一），判定逻辑不受档位集合限制。
    """
    item = next((i for i in (check_items or [])
                 if isinstance(i, dict) and i.get('code') == 'TIME_SYNC'), None)
    try:
        return float((item or {}).get('threshold', default))
    except (TypeError, ValueError):
        return float(default)


def parse_snmp_dateandtime(raw):
    """解析 RFC 2579 DateAndTime 八位组字符串 → (naive datetime, tzinfo 或 None)

    各实现的字节数不一致，两种都要支持：
        07 EA 09 15 09 16 20 00 2B 08 00  → 2026-09-21 09:22:32.0 +08:00   (11 字节)
        07 EA 09 15 09 16 20 02           → 2026-09-21 09:22:32.2 无时区    (8 字节)

    ⚠️ 年份占 2 字节：0x07EA = 2026，不是「2000 + 0x07」。
    """
    if not raw:
        return None, None
    try:
        b = [int(x, 16) for x in str(raw).strip().strip('"').split()]
    except (ValueError, AttributeError):
        return None, None
    if len(b) < 8:
        return None, None

    year = b[0] * 256 + b[1]
    try:
        dt = datetime.datetime(year, b[2], b[3], b[4], b[5], b[6], b[7] * 100000)
    except ValueError:
        return None, None

    tz = None
    if len(b) >= 11:
        minutes = b[9] * 60 + b[10]
        if b[8] != 0x2B:          # 0x2B = '+', 0x2D = '-'
            minutes = -minutes
        tz = datetime.timezone(datetime.timedelta(minutes=minutes))
    return dt, tz


def build_result(offset, threshold, source, extra=''):
    """把偏差（秒）转成巡检结果。

    offset: 服务器时间 − 本机时间（带符号；正=服务器快，负=服务器慢）
    超过阈值 → warning（警告）；否则 pass
    返回 (status, result_value, result_message, suggestion)
    """
    off_abs = abs(offset)
    exceeded = off_abs > threshold
    direction = '服务器快' if offset > 0 else '服务器慢'
    msg = (f"偏差 {offset:+}s（{direction}）"
           f" | 采集 {source}"
           + (f" | {extra}" if extra else '')
           + f" | 本机基准 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if exceeded:
        msg += f" | 超过阈值 {threshold:g}s"
    return (
        'warning' if exceeded else 'pass',
        f'偏差 {off_abs}s',           # ← 绝对值必须放最前面
        msg,
        '该服务器时间偏差超过阈值，请检查其 NTP 同步配置' if exceeded else '',
    )


def offset_from_epoch(server_epoch, source, extra='', threshold=DEFAULT_THRESHOLD):
    """数据库路径：服务器返回 UTC epoch（与时区无关，最省事）"""
    try:
        offset = round(float(server_epoch) - time.time(), 3)
    except (TypeError, ValueError):
        return time_sync_failure(f'时间值无法解析: {server_epoch!r}')
    return build_result(offset, threshold, source, extra)


def compute_offset(server_dt, tz, local_ts=None):
    """把「服务器本地时间 + 时区」换算成相对本机的偏差（秒）

    local_ts: 该次读数对应的本机 epoch。**必须传该次读数当时的本机时间**，
              不能统一用调用时刻 —— 否则多次取样时，早先采的样本会被算进
              采样间隔，偏差凭空变大。
    """
    zone = tz or datetime.datetime.now().astimezone().tzinfo
    ref = local_ts if local_ts is not None else time.time()
    return round(server_dt.replace(tzinfo=zone).timestamp() - ref, 3)


def offset_from_samples(samples, source, extra='', threshold=DEFAULT_THRESHOLD):
    """SNMP 路径：多次读数取 |偏差| 最小的那一次。

    samples: [(naive datetime, tzinfo 或 None, 该次读数的本机 epoch), ...]
             （也兼容 [(datetime, tz), ...]，此时用调用时刻做参考）

    ⚠️ 为什么要多次取样：部分设备的 hrSystemDate 精度只到秒（deciseconds 恒为 0），
       单次读数的偏差会随「本机当时秒的小数部分」在 0~1s 之间跳（实测
       192.168.0.18 一次 -0.255s、一次 -0.903s），会误报。截断型设备的读数分布
       落在 (真值-1s, 真值] 区间内，取其中最接近 0 的一次即可逼近真值；
       对高精度设备所有读数本来就一致，取最小值也不会失真。
    """
    if not samples:
        return time_sync_failure('未取到任何读数')

    best_offset = None
    tz_missing = False
    for sample in samples:
        dt, tz = sample[0], sample[1]
        local_ts = sample[2] if len(sample) > 2 else None
        if tz is None:
            tz_missing = True
        off = compute_offset(dt, tz, local_ts)
        if best_offset is None or abs(off) < abs(best_offset):
            best_offset = off

    if tz_missing:
        extra = (extra + ' | 设备未提供时区，按本机时区推定').strip(' |')
    if len(samples) > 1:
        extra = (extra + f' | 取{len(samples)}次读数中最接近0的一次').strip(' |')
    # 注：设备精度只到秒（deciseconds 恒为 0）时不再往结果里追加提示语。
    # 多做样已吸收该误差，最小档位 10s 远大于 ±1s 量化残留，提示纯属噪音。
    return build_result(best_offset, threshold, source, extra)


def time_sync_failure(reason):
    """取不到时间时的结果（不参与阈值判定，靠 status 兜底 severity=2）"""
    return (
        'warning',
        '查询失败',
        f'无法获取时间: {reason}',
        '请确认该设备/数据库的时间信息可被读取',
    )
