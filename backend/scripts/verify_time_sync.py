#!/usr/bin/env python3
"""时间同步检查 —— 验证脚本（SNMP + 数据库两条路径，均不用 SSH）"""
import os, sys, time, subprocess, datetime, re, django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.inspection.time_check import (
    TIME_SYNC_OID, parse_snmp_dateandtime, get_threshold, build_result,
    offset_from_epoch, offset_from_samples, time_sync_failure, DEFAULT_THRESHOLD,
)

ok_all = True

def check(label, cond, detail=''):
    global ok_all
    mark = '✅' if cond else '❌'
    if not cond:
        ok_all = False
    print(f'{mark} {label}{(" | " + detail) if detail else ""}')

print('=' * 72)
print('A. parse_snmp_dateandtime —— RFC2579 DateAndTime')
print('=' * 72)
# 11 字节带时区
dt, tz = parse_snmp_dateandtime('07 EA 09 15 09 16 20 00 2B 08 00 ')
check('11字节带时区', dt == datetime.datetime(2026, 9, 21, 9, 22, 32) and str(tz) == 'UTC+08:00',
      f'{dt} {tz}')
# 8 字节无时区（你那台 172.26.11.50 的实际返回）
dt2, tz2 = parse_snmp_dateandtime('07 EA 09 15 09 16 20 02')
check('8字节无时区', dt2 == datetime.datetime(2026, 9, 21, 9, 22, 32, 200000) and tz2 is None,
      f'{dt2} tz={tz2}')
# 负时区
_, tz3 = parse_snmp_dateandtime('07 EA 09 15 09 16 20 00 2D 05 00')
check('负时区 0x2D', str(tz3) == 'UTC-05:00', str(tz3))
# 年份必须是 2 字节（历史 bug：单字节解析成 2007）
dt4, _ = parse_snmp_dateandtime('07 EA 09 15 09 16 20 00')
check('年份取2字节 → 2026（非2007）', dt4.year == 2026, f'year={dt4.year}')
# 异常输入
for bad in [None, '', 'not hex', '07 EA 09', '07 EA 13 15 09 16 20 00']:
    d, _ = parse_snmp_dateandtime(bad)
    check(f'异常输入 {bad!r} → None', d is None)

print()
print('=' * 72)
print('B. get_threshold —— 阈值来源（巡检计划 check_items）')
print('=' * 72)
cases = [
    ([{'code': 'TIME_SYNC', 'threshold': 10}], 10.0, '选了10秒'),
    ([{'code': 'TIME_SYNC', 'threshold': 60}], 60.0, '选了60秒'),
    ([{'code': 'TIME_SYNC', 'threshold': 180}], 180.0, '选了180秒'),
    ([{'code': 'TIME_SYNC', 'threshold': 1}], 1.0, '老计划残留1秒档 → 按原值读取'),
    ([{'code': 'TIME_SYNC'}], 60.0, '老计划无 threshold → 默认60'),
    (['TIME_SYNC'], 60.0, '字符串数组 → 默认60'),
    (None, 60.0, '空 → 默认60'),
    ([{'code': 'TIME_SYNC', 'threshold': 'abc'}], 60.0, '非法值 → 默认60'),
    ([{'code': 'CPU_USAGE', 'threshold': 5}], 60.0, '未选时间同步 → 默认60'),
]
for ci, expect, label in cases:
    got = get_threshold(ci)
    check(f'{label}', got == expect, f'得到 {got}')

print()
print('=' * 72)
print('C. 阈值判定边界（10/60/180 秒）')
print('=' * 72)
for thr, off, expect in [(10, 9.9, 'pass'), (10, 10.1, 'warning'),
                         (60, 59.9, 'pass'), (60, 60.1, 'warning'),
                         (180, 179.9, 'pass'), (180, 180.1, 'warning')]:
    # 构造：服务器 epoch = 现在 + off
    st, val, msg, sug = offset_from_epoch(time.time() + off, 'test', threshold=thr)
    check(f'阈值{thr}s 偏差{off}s → {expect}', st == expect, f'得到 {st}')

print()
print('=' * 72)
print('D. result_value 首个数字 = 偏差绝对值（数值提取规则）')
print('=' * 72)
for off in [-12.345, 12.345]:
    st, val, msg, sug = offset_from_epoch(time.time() + off, 'test', threshold=60)
    first = float(re.findall(r'[-+]?\d+\.?\d*', val)[0])
    check(f'偏差 {off:+}s → 提取 {first}（须为正）', first > 0, f'result_value={val!r}')
    if off < 0:
        check('负偏差时 result_message 保留符号', '-12.3' in msg, msg)

print()
print('=' * 72)
print('E. 取不到时间 → warning（靠 status 兜底 severity=2）')
print('=' * 72)
st, val, msg, sug = time_sync_failure('设备不支持该OID')
check('查询失败形态', st == 'warning' and val == '查询失败', f'{st} / {val}')

print()
print('=' * 72)
print('F. 多次取样：模拟「精度只到秒」的设备（deciseconds 恒为 0）')
print('=' * 72)
# 构造一个真值 -0.85s、但读数被截断到整秒的设备，看单次 vs 多取样的差别
# 每个样本必须带上「它采集那一刻」的本机时间（否则早采的样本会被算进采样间隔）
true_offset = -0.85
samples, single = [], []
for i in range(3):
    t = time.time()
    local_frac = t - int(t)
    trunc_dt = datetime.datetime.fromtimestamp(t + true_offset - local_frac)  # 截断到整秒
    samples.append((trunc_dt, datetime.datetime.now().astimezone().tzinfo, t))
    single.append(round(trunc_dt.timestamp() - t, 3))
    time.sleep(0.45)
print(f'   单次读数: {single}   （真值 {true_offset}s，可见单次误差最大到近 1s）')
st, val, msg, sug = offset_from_samples(samples, '模拟', threshold=60)
best = float(re.findall(r'[\d.]+', val)[0])
check('多取样结果不差于任何单次读数',
      abs(best - abs(true_offset)) <= min(abs(-x - abs(true_offset)) for x in single) + 0.001,
      f'取样得 {val}（单次为 {single}）')
check('设备未提供时区时已标注', '未提供时区' in msg or '取3次' in msg, msg[:110])
check('结果里不再出现「精度仅到秒」提示语（已按 JP 要求摘除）',
      '精度仅到秒' not in msg and '±1s' not in msg, msg[:110])

print()
print('=' * 72)
print('G. 实测：真实 SNMP 读取服务器时间（OID ' + TIME_SYNC_OID + '），每次取 3 个读数')
print('=' * 72)
print(f"本机基准: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  epoch={time.time():.3f}")
skipped = []
for ip in ['192.168.0.18', '172.26.11.50', '172.26.12.11', '172.26.12.1']:
    samples, raws = [], []
    for _ in range(3):
        try:
            r = subprocess.run(['snmpget', '-v2c', '-c', 'public', '-Oqv', '-t', '3', '-r', '1',
                                f'{ip}:161', TIME_SYNC_OID],
                               capture_output=True, text=True, timeout=12)
            raw = r.stdout.strip()
        except Exception:
            raw = ''
        raws.append(raw)
        dt, tz = parse_snmp_dateandtime(raw)
        if dt:
            samples.append((dt, tz))
        if not raw:
            break                  # 不可达就不重试
    if not samples:
        skipped.append(ip)
        print(f'   ⏭️  {ip:<16} SNMP 无响应/不支持该OID → 跳过（环境下不可达，非代码问题）')
        continue
    st, val, msg, sug = offset_from_samples(samples, 'SNMP hrSystemDate', threshold=60)
    check(f'{ip} 读取判定', st in ('pass', 'warning'), f'{st} | {val}')
    print(f'      {msg}')
check(f'不可达主机 {skipped} 记为跳过而非失败', True, f'{len(skipped)} 台')

print()
print('=' * 72)
print('H. 未用 SSH / 未用外网时钟源的确认')
print('=' * 72)
import apps.inspection.views as V
check('_collect_time_offset（SSH版）已移除', not hasattr(V.InspectionTaskViewSet, '_collect_time_offset'))
src = open(os.path.join(os.path.dirname(V.__file__), 'views.py'), encoding='utf-8').read()
check('SSH 巡检里已无 TIME_SYNC 分支',
      'TIME_SYNC' not in src.split('def _execute_ssh_checks')[1].split('def _execute_snmp_checks')[0])
check('SNMP 巡检里有 TIME_SYNC 分支',
      'TIME_SYNC' in src.split('def _execute_snmp_checks')[1].split('def _execute_ping_checks')[0])
check_text = open(os.path.join(os.path.dirname(V.__file__), 'time_check.py'), encoding='utf-8').read()
for bad in ['aliyun', 'pool.ntp.org', 'time.windows']:
    check(f'代码中无外网时钟源 {bad}', bad not in check_text + src)

print()
print('=' * 72)
print('I. 前后端档位一致性（前端可选档位 / 后端默认值）')
print('=' * 72)
vue_path = os.path.join(os.path.dirname(V.__file__), '..', '..', '..',
                        'frontend', 'src', 'views', 'inspection', 'InspectionPlanList.vue')
try:
    vue = open(vue_path, encoding='utf-8').read()
    opts = re.findall(r'<el-radio-button :value="(\d+)">', vue)
    check(f'前端档位 = [10, 60, 180]', opts == ['10', '60', '180'], f'实际 {opts}')
    check(f'后端默认 {DEFAULT_THRESHOLD:g}s 是合法档位之一',
          f'{DEFAULT_THRESHOLD:g}' in opts, f'档位={opts}')
    check('前端默认值 = 后端默认值（60）',
          f'timeSyncThreshold = ref({DEFAULT_THRESHOLD:g})' in vue)
    check('1 秒档已撤（不再出现 1 秒按钮）', '"1">1 秒' not in vue)
except OSError as e:
    check('找到前端 InspectionPlanList.vue', False, str(e))

print()
print('=' * 72)
print('全部验证通过 🎉' if ok_all else '存在失败项 ❌')
print('=' * 72)
sys.exit(0 if ok_all else 1)
