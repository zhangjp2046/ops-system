"""
巡检服务报告生成器（博越版式）
================================
按「客户(租户) + 时间范围」生成数据中心巡检报告 HTML。
客户名/地址/联系人来自该实例 Customer（异地租户部署时即该医院），
数据全部来自巡检记录 Inspection/InspectionResult + 资产 Asset，
不写死任何客户名称。物理环境(机房温湿度/UPS等)无自动数据时给出占位说明。

用法（views.generate_report 内调用）:
    html = build_report_html(inspections, date_from, date_to, now_str)
"""
from django.utils.html import escape

# 巡检记录状态中文映射
INS_STATUS_CN = {'COMPLETED': '已完成', 'FAILED': '失败', 'RUNNING': '运行中', 'PENDING': '等待中'}
# 检查项结果（InspectionItem.result: PASS/WARNING/FAIL）
RESULT_CN = {'pass': '通过', 'warning': '警告', 'fail': '失败', 'skip': '跳过', 'unknown': '未知'}
RESULT_ICON = {'pass': '✅', 'warning': '⚠️', 'fail': '❌', 'skip': '⏭️', 'unknown': '❓'}
RESULT_CLASS = {'pass': 'res-pass', 'warning': 'res-warn', 'fail': 'res-fail', 'skip': 'res-skip', 'unknown': 'res-unk'}


def res_key(result):
    """归一化检查项结果键（兼容大小写）"""
    return (result or 'unknown').strip().lower()


def h(text):
    return escape('' if text is None else str(text))


import re
_HEX_DUMP_RE = re.compile(r'(?:[0-9A-Fa-f]{2} ){6,}(?:[0-9A-Fa-f]{2})?')


def humanize(value):
    """将 SNMP 等协议返回中的 hex dump 还原为可读文本；无法还原则截断。
    典型场景：接口名以 UTF-16LE hex 形式编码（如 "53 6F 66 74..." → "Soft..."）。"""
    s = '' if value is None else str(value)
    if not s:
        return s

    def repl(m):
        hx = m.group(0).replace(' ', '')
        try:
            raw = bytes.fromhex(hx)
        except ValueError:
            return m.group(0)
        for enc in ('utf-16-le', 'utf-8'):
            try:
                txt = raw.decode(enc).strip('\x00').strip()
                if txt and all(c in ' \n\t' or 0x20 <= ord(c) < 0x7f or ord(c) > 0xa0 for c in txt):
                    return txt
            except Exception:
                continue
        return m.group(0)

    s = _HEX_DUMP_RE.sub(repl, s)
    return s


def classify_subsystem(asset_type, asset_name=''):
    """将资产归入模板的子系统章节（第4/5/6章）。关键词按中文巡检类型+资产名匹配。"""
    t = (asset_type or '') + ' ' + (asset_name or '')
    t_low = t.lower()
    net_kw = ['交换', '路由', '防火墙', 'ips', '入侵防御', '防毒', '审计', '行为管理', '负载', '安全', '网御', 'sanforg', '网关']
    vir_kw = ['虚拟', 'vmware', 'esxi', 'vcenter', '超融合', 'hci', 'kvm', 'hyper-v']
    sto_kw = ['存储', '磁盘阵列', 'san', '宏杉', 'nas', '备份', '容灾', '爱数']
    if any(k in t_low for k in net_kw):
        return 'network'
    if any(k in t_low for k in vir_kw):
        return 'virtual'
    if any(k in t_low for k in sto_kw):
        return 'storage'
    return 'server'   # 默认服务器/计算类


SUBSYSTEM_TITLE = {
    'server': '服务器与计算系统',
    'storage': '存储与备份系统',
    'virtual': '虚拟化平台',
    'network': '网络与安全系统',
}
SUBSYSTEM_NO = {'server': 4, 'storage': 5, 'virtual': 6, 'network': 7}


def _fmt_dt(dt, fmt='%Y-%m-%d %H:%M'):
    if not dt:
        return '-'
    try:
        from django.utils import timezone
        return timezone.localtime(dt).strftime(fmt)
    except Exception:
        return str(dt)[:16]


def _fmt_date(dt):
    return _fmt_dt(dt, '%Y-%m-%d')


def build_report_html(inspections, date_from, date_to, now_str):
    """inspections: QuerySet/列表，需 select_related('asset','customer') + prefetch_related('items')"""
    inspections = list(inspections)
    css = _CSS

    # ---------- 按客户分组 ----------
    cust_groups = {}   # customer_id -> {customer, ins_list}
    for ins in inspections:
        c = ins.customer
        cid = c.id if c else 0
        g = cust_groups.setdefault(cid, {'customer': c, 'ins_list': []})
        g['ins_list'].append(ins)

    parts = []
    parts.append(f'<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">'
                 f'<meta name="viewport" content="width=device-width, initial-scale=1.0">'
                 f'<title>数据中心巡检报告</title><style>{css}</style></head><body>')

    multi = len(cust_groups) > 1
    overall_no = 1
    for cid, g in cust_groups.items():
        customer = g['customer']
        cl = sorted(g['ins_list'], key=lambda x: (x.asset_id or 0, x.started_at or x.created_at))
        cust_name = customer.customer_name if customer else '未关联客户'
        parts.append(_cover(cust_name, date_from, date_to, now_str, multi, overall_no))
        parts.append(_doc_history(date_from, date_to, now_str))
        parts.append(_toc())
        parts.append(_ch1_overview(customer, cl, date_from, date_to))
        parts.append(_ch2_env_placeholder())
        parts.append(_ch3_asset_list(cl))
        # 第4~7章：按子系统分组展示每台设备最近一次巡检明细
        parts.append(_subsystem_chapters(cl))
        parts.append(_footer(now_str, cust_name))
        parts.append('<div class="page-break"></div>')
        overall_no += 1

    parts.append('</body></html>')
    return '\n'.join(parts)


# ============================================================
# 封面
# ============================================================
def _cover(cust_name, date_from, date_to, now_str, multi, no):
    period = f'{str(date_from)[:10]} 至 {str(date_to)[:10]}'
    return f'''
<div class="cover">
  <div class="cover-company">博越信息技术有限公司</div>
  <div class="cover-title">{h(cust_name)}</div>
  <div class="cover-sub">数据中心巡检报告</div>
  <div class="cover-line"></div>
  <table class="cover-meta">
    <tr><td class="k">报告周期</td><td>{h(period)}</td></tr>
    <tr><td class="k">生成时间</td><td>{h(now_str)}</td></tr>
    <tr><td class="k">报告编号</td><td>INSP-{no:03d}-{str(date_to)[:10].replace("-", "")}</td></tr>
  </table>
  <div class="cover-copy">版权所有 © 2018 - 2026 博越信息技术有限公司 · 本报告由运维管理系统自动生成</div>
</div>
<div class="page-break"></div>'''


def _doc_history(date_from, date_to, now_str):
    return f'''
<h1 class="ch">文档历史</h1>
<table class="grid narrow">
  <thead><tr><th style="width:15%">版本</th><th style="width:25%">时间</th><th style="width:30%">作者</th><th>状态</th></tr></thead>
  <tbody>
    <tr><td>001</td><td>{h(now_str[:10])}</td><td>运维管理系统</td><td>已发布</td></tr>
  </tbody>
</table>
<div class="page-break"></div>'''


def _toc():
    return '''
<h1 class="ch" id="toc">目录</h1>
<div class="toc">
  <div class="toc-l1">第1章 巡检概览</div>
  <div class="toc-l2"><a href="#s1-1">1.1 客户信息</a></div>
  <div class="toc-l2"><a href="#s1-2">1.2 服务记录</a></div>
  <div class="toc-l2"><a href="#s1-3">1.3 评估方式</a></div>
  <div class="toc-l2"><a href="#s1-4">1.4 评估结果</a></div>
  <div class="toc-l2"><a href="#s1-5">1.5 相关建议</a></div>
  <div class="toc-l1">第2章 机房环境</div>
  <div class="toc-l1">第3章 设备清单和网络架构</div>
  <div class="toc-l2"><a href="#s3-1">3.1 资产清单表</a></div>
  <div class="toc-l2">3.2 网络拓扑（待补充）</div>
  <div class="toc-l1">第4章 服务器与计算系统</div>
  <div class="toc-l1">第5章 存储与备份系统</div>
  <div class="toc-l1">第6章 虚拟化平台</div>
  <div class="toc-l1">第7章 网络与安全系统</div>
</div>
<div class="page-break"></div>'''


# ============================================================
# 第1章 巡检概览
# ============================================================
def _ch1_overview(customer, cl, date_from, date_to):
    parts = ['<h1 class="ch">第1章 巡检概览</h1>']
    parts.append(_s1_1_customer(customer))
    parts.append(_s1_2_service(cl, date_from, date_to))
    parts.append(_s1_3_method())
    parts.append(_s1_4_result(cl))
    parts.append(_s1_5_suggest(cl))
    parts.append('<div class="page-break"></div>')
    return '\n'.join(parts)


def _s1_1_customer(customer):
    name = customer.customer_name if customer else '-'
    addr = getattr(customer, 'address', '') or '-'
    p1 = getattr(customer, 'contact_person', '') or ''
    ph1 = getattr(customer, 'contact_phone', '') or ''
    em1 = getattr(customer, 'contact_email', '') or ''
    rows = f'<tr><td class="k">客户名称</td><td colspan="3">{h(name)}</td></tr>'
    rows += f'<tr><td class="k">客户地址</td><td colspan="3">{h(addr)}</td></tr>'
    rows += (f'<tr><td class="k">第一联系人</td><td>{h(p1)}</td><td class="k">电子邮箱</td><td>{h(em1)}</td></tr>'
             f'<tr><td class="k">联系电话</td><td>{h(ph1)}</td><td></td><td></td></tr>')
    return f'<h2 class="sec" id="s1-1">1.1 客户信息</h2><table class="grid kv">{rows}</table>'


def _s1_2_service(cl, date_from, date_to):
    total = len(cl)
    assets = {}
    protocols = set()
    for ins in cl:
        key = ins.asset_id or ('n', ins.name)
        assets[key] = ins
        if ins.asset_type:
            pass
        if getattr(ins, 'asset', None) and ins.asset.protocol:
            protocols.add(ins.asset.protocol)
        elif ins.name:
            pass
    asset_count = len(assets)
    proto = '、'.join(sorted(protocols)) or 'SNMP'
    plan_names = sorted({ins.name for ins in cl if ins.name})
    service = '例行设备巡检'
    if plan_names and all('手工' in n for n in plan_names):
        service = '手工巡检'
    return f'''
<h2 class="sec" id="s1-2">1.2 服务记录</h2>
<table class="grid">
  <thead><tr><th style="width:22%">服务时间</th><th style="width:48%">服务内容</th><th>服务人员</th></tr></thead>
  <tbody>
    <tr>
      <td>{h(str(date_from)[:10])} 至 {h(str(date_to)[:10])}</td>
      <td>{h(service)}：共执行巡检 {total} 次，覆盖 {asset_count} 台设备（{h(proto)} 协议自动巡检）</td>
      <td>运维管理系统（自动）</td>
    </tr>
  </tbody>
</table>'''


def _s1_3_method():
    return '''
<h2 class="sec" id="s1-3">1.3 评估方式</h2>
<table class="grid">
  <thead><tr><th style="width:50%">选项</th><th>交付类型</th></tr></thead>
  <tbody>
    <tr><td>☐ 现场服务</td><td>☑ 远程服务（设备协议自动巡检 + 定期现场人工巡检）</td></tr>
  </tbody>
</table>'''


def _s1_4_result(cl):
    """按子系统归类每台设备最近一次巡检状态 → 结论行"""
    # 每台资产最近一次
    latest = {}
    for ins in cl:
        key = ins.asset_id or ins.id
        cur = latest.get(key)
        if cur is None or (ins.started_at or ins.created_at) > (cur.started_at or cur.created_at):
            latest[key] = ins
    groups = {'server': [], 'storage': [], 'virtual': [], 'network': []}
    for ins in latest.values():
        at = getattr(ins.asset, 'asset_type', '') if ins.asset else ''
        g = classify_subsystem(ins.asset_type or at, ins.asset.asset_name if ins.asset else '')
        groups.setdefault(g, []).append(ins)

    rows = []
    order = ['server', 'storage', 'virtual', 'network']
    any_fail = any_fail_all = False
    for g in order:
        lst = groups.get(g) or []
        if not lst:
            continue
        fail_n = sum(1 for i in lst if i.failed_items and i.failed_items > 0 or i.status == 'FAILED')
        warn_n = sum(1 for i in lst if i.warning_items and i.warning_items > 0)
        ok_n = len(lst) - fail_n
        total_n = len(lst)
        if fail_n:
            status_cn = f'异常（{fail_n} 台存在失败检查项）'
            cls = 'bad'
            any_fail_all = True
        elif warn_n:
            status_cn = f'存在警告（{warn_n} 台需关注）'
            cls = 'warn'
        else:
            status_cn = '正常'
            cls = 'ok'
        rows.append(f'<tr><td class="subsys">{h(SUBSYSTEM_TITLE[g])}</td>'
                    f'<td>{total_n} 台</td>'
                    f'<td><span class="pill {cls}">{status_cn}</span></td></tr>')
    if not rows:
        rows.append('<tr><td colspan="3">所选时间段内无巡检数据</td></tr>')
    overall = '设备整体运行正常' if not any_fail_all else '部分设备存在异常，详见相关章节及建议'
    return f'''
<h2 class="sec" id="s1-4">1.4 评估结果</h2>
<p class="lead">巡检人员于 {h(str(cl[0].started_at or cl[0].created_at))[:10] if cl else "-"} 前完成对客户设备的运行状态评估。评估结果如下：</p>
<table class="grid">
  <thead><tr><th style="width:30%">系统</th><th style="width:15%">设备数量</th><th>状态</th></tr></thead>
  <tbody>{''.join(rows)}</tbody>
</table>
<p class="summary-line">总体结论：{overall}。</p>'''


def _s1_5_suggest(cl):
    """聚合 warning/fail 检查项的建议/说明，去重取前10"""
    seen = set()
    items = []
    for ins in cl:
        for it in ins.items.all():
            if res_key(it.result) not in ('warning', 'fail'):
                continue
            msg = humanize(it.message).strip()
            line = msg
            if not line:
                continue
            # 超长输出（如接口名 hex dump）截断，避免撑破排版
            if len(line) > 120:
                line = line[:120] + ' …'
            key = (it.item_code or it.item_name, msg)
            if key in seen:
                continue
            seen.add(key)
            dev = ins.asset.asset_name if ins.asset else '未知设备'
            items.append((dev, it.item_name, line, res_key(it.result)))
    parts = [f'<h2 class="sec" id="s1-5">1.5 相关建议</h2>']
    if not items:
        parts.append('<p class="summary-line">本期巡检未发现需要特别关注的问题，建议保持现有巡检频率。</p>')
    else:
        parts.append('<ol class="suggest">')
        for idx, (dev, chk, line, st) in enumerate(items[:10], 1):
            cls = 'warn' if st == 'warning' else 'bad'
            parts.append(f'<li><b>{h(dev)}</b>（{h(chk)}）：{h(line)}'
                         f' <span class="pill {cls}">{"警告" if st=="warning" else "异常"}</span></li>')
        parts.append('</ol>')
    return '\n'.join(parts)


# ============================================================
# 第2章 机房环境（占位）
# ============================================================
def _ch2_env_placeholder():
    return '''
<h1 class="ch">第2章 机房环境</h1>
<div class="note">本章（机房温湿度、水患、UPS/电池、门禁等物理环境检查项）需现场人工巡检后补充填写。
当前系统通过设备协议（SNMP 等）自动巡检，暂不包含物理环境项。</div>
<div class="page-break"></div>'''


# ============================================================
# 第3章 资产清单
# ============================================================
def _ch3_asset_list(cl):
    # 每台资产聚合：巡检次数/最近一次状态
    by_asset = {}
    for ins in cl:
        key = ins.asset_id or 0
        a = by_asset.setdefault(key, {'ins': ins, 'count': 0, 'latest': None})
        a['count'] += 1
        if a['latest'] is None or (ins.started_at or ins.created_at) > (a['latest'].started_at or a['latest'].created_at):
            a['latest'] = ins
    rows = []
    idx = 1
    for key in sorted(by_asset.keys(), key=lambda k: (by_asset[k]['ins'].asset.asset_name if by_asset[k]['ins'].asset else '') or ''):
        a = by_asset[key]
        ins = a['latest']
        asset = ins.asset
        name = asset.asset_name if asset else (ins.asset_type and ins.name or '未知')
        ip = asset.ip_address if asset else ''
        atype = ins.asset_type or (getattr(asset, 'asset_type', '') if asset else '') or '-'
        # 最新状态
        if ins.status == 'FAILED':
            st = '<span class="pill bad">异常</span>'
        elif ins.failed_items and ins.failed_items > 0:
            st = '<span class="pill bad">异常</span>'
        elif ins.warning_items and ins.warning_items > 0:
            st = '<span class="pill warn">警告</span>'
        else:
            st = '<span class="pill ok">正常</span>'
        latest_t = _fmt_date(ins.started_at or ins.completed_at or ins.created_at)
        rows.append(f'<tr><td>{idx}</td><td>{h(name)}</td><td>{h(atype)}</td><td>{h(ip)}</td>'
                    f'<td>{a["count"]}</td><td>{latest_t}</td><td>{st}</td></tr>')
        idx += 1
    head = ('<tr><th style="width:5%">序号</th><th>设备名称</th><th style="width:16%">类别</th>'
            '<th style="width:18%">IP 地址</th><th style="width:9%">巡检次数</th>'
            '<th style="width:12%">最近巡检</th><th style="width:10%">状态</th></tr>')
    return f'''
<h1 class="ch" id="ch3">第3章 设备清单和网络架构</h1>
<h2 class="sec" id="s3-1">3.1 资产清单表</h2>
<table class="grid"><thead>{head}</thead><tbody>{''.join(rows)}</tbody></table>
<div class="note">3.2 网络拓扑图、3.3 机柜位置：由现场人工巡检后补充。</div>
<div class="page-break"></div>'''


# ============================================================
# 第4~7章 子系统设备检查明细（每台设备最近一次巡检的检查项）
# ============================================================
def _subsystem_chapters(cl):
    # 每台资产最新一次巡检
    latest = {}
    for ins in cl:
        key = ins.asset_id or ins.id
        cur = latest.get(key)
        if cur is None or (ins.started_at or ins.created_at) > (cur.started_at or cur.created_at):
            latest[key] = ins
    # 归组
    groups = {'server': [], 'storage': [], 'virtual': [], 'network': []}
    for ins in latest.values():
        asset = ins.asset
        at = getattr(asset, 'asset_type', '') if asset else ''
        g = classify_subsystem(ins.asset_type or at, asset.asset_name if asset else '')
        groups.setdefault(g, []).append(ins)

    parts = []
    # 组内排序：按资产名
    for g, title in SUBSYSTEM_TITLE.items():
        lst = sorted(groups.get(g) or [], key=lambda i: (i.asset.asset_name if i.asset else '') or '')
        if not lst:
            continue
        ch_no = SUBSYSTEM_NO[g]
        parts.append(f'<h1 class="ch">第{ch_no}章 {h(title)}</h1>')
        for sub_idx, ins in enumerate(lst, 1):
            parts.append(_device_block(ins, f'{ch_no}.{sub_idx}'))
        parts.append('<div class="page-break"></div>')
    return '\n'.join(parts)


def _device_block(ins, no):
    asset = ins.asset
    name = asset.asset_name if asset else (ins.name or '未知设备')
    ip = asset.ip_address if asset else ''
    atype = ins.asset_type or (getattr(asset, 'asset_type', '') if asset else '') or '-'
    vendor = getattr(asset, 'vendor', '') if asset else ''
    latest_t = _fmt_dt(ins.started_at or ins.completed_at or ins.created_at)
    items = list(ins.items.all())
    ok_n = sum(1 for i in items if res_key(i.result) == 'pass')
    warn_n = sum(1 for i in items if res_key(i.result) == 'warning')
    fail_n = sum(1 for i in items if res_key(i.result) == 'fail')
    total_n = len(items) or (ins.total_items or 0)
    pct = (ok_n / total_n * 100) if total_n else 0
    if fail_n:
        badge = '<span class="pill bad">异常</span>'
    elif warn_n:
        badge = '<span class="pill warn">警告</span>'
    else:
        badge = '<span class="pill ok">正常</span>'

    info = (f'<table class="kv-inline">'
            f'<tr><td class="k">设备名称</td><td>{h(name)}</td>'
            f'<td class="k">管理地址</td><td>{h(ip)}</td></tr>'
            f'<tr><td class="k">设备类别</td><td>{h(atype)}</td>'
            f'<td class="k">厂商</td><td>{h(vendor or "-")}</td></tr>'
            f'<tr><td class="k">最近巡检</td><td>{latest_t}</td>'
            f'<td class="k">检查通过率</td><td>{pct:.0f}% （通过 {ok_n} / 警告 {warn_n} / 失败 {fail_n}）{badge}</td></tr>'
            f'</table>')

    if not items:
        body = '<div class="note">该设备本期无检查项明细。</div>'
    else:
        trs = []
        for i, it in enumerate(items, 1):
            st = res_key(it.result)
            res_cls = RESULT_CLASS.get(st, 'res-unk')
            res_icon = RESULT_ICON.get(st, '')
            res_cn = RESULT_CN.get(st, st)
            expect = (it.expected_value or '').strip() or '-'
            remark = humanize(it.message).strip() or '-'
            if len(remark) > 200:
                remark = remark[:200] + ' …'
            actual = humanize(it.actual_value).strip() or '-'
            if len(actual) > 200:
                actual = actual[:200] + ' …'
            trs.append(f'<tr><td>{i}</td><td>{h(it.item_name)}</td>'
                       f'<td class="mono">{h(expect)}</td>'
                       f'<td class="mono">{h(actual)}</td>'
                       f'<td><span class="tag {res_cls}">{res_icon} {res_cn}</span></td>'
                       f'<td>{h(remark)}</td></tr>')
        body = ('<table class="grid"><thead><tr><th style="width:4%">#</th><th style="width:18%">检查项</th>'
                '<th style="width:16%">期望值/阈值</th><th style="width:18%">实际值</th>'
                '<th style="width:10%">结果</th><th>备注 / 建议</th></tr></thead>'
                f'<tbody>{"" .join(trs)}</tbody></table>')

    return f'''
<h2 class="sec">{h(no)} {h(name)}</h2>
{info}
{body}'''


# ============================================================
# 页脚
# ============================================================
def _footer(now_str, cust_name):
    return f'<div class="footer">—— 本报告由运维管理系统自动生成 · {h(cust_name)} · {h(now_str)} ——</div>'


_CSS = '''
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: "Microsoft YaHei", "PingFang SC", "Helvetica Neue", Arial, sans-serif; color: #1a1a2e; background: #eef1f5; line-height: 1.7; }
.page-break { page-break-after: always; }
/* ---------- 封面 ---------- */
.cover { background: #fff; max-width: 900px; margin: 0 auto; min-height: 900px; padding: 90px 70px 40px; text-align: center; border: 1px solid #e5e9f0; }
.cover-company { color: #8a93a5; letter-spacing: 6px; font-size: 14px; margin-bottom: 120px; }
.cover-title { font-size: 36px; font-weight: 700; color: #1f3a5f; letter-spacing: 4px; }
.cover-sub { font-size: 28px; font-weight: 600; color: #1f3a5f; margin: 16px 0 40px; }
.cover-line { width: 90px; height: 4px; background: #1f4e79; margin: 0 auto 56px; }
.cover-meta { margin: 0 auto 100px; border-collapse: collapse; }
.cover-meta td { padding: 8px 18px; font-size: 15px; }
.cover-meta td.k { color: #8a93a5; text-align: right; }
.cover-copy { color: #aab2c0; font-size: 12px; margin-top: 60px; }
/* ---------- 正文容器 ---------- */
h1.ch { font-size: 20px; color: #1f4e79; border-left: 6px solid #1f4e79; padding: 6px 0 6px 14px; margin: 34px 0 16px; background: #f2f6fb; }
h2.sec { font-size: 16px; color: #2b5c8a; margin: 20px 0 10px; }
#toc-page h1.ch { margin-top: 20px; }
.toc { font-size: 15px; }
.toc-l1 { font-weight: 700; color: #1f4e79; margin: 10px 0 4px; }
.toc-l2 { padding-left: 26px; color: #455; }
.toc a { color: #2b5c8a; text-decoration: none; }
/* ---------- 表格 ---------- */
table.grid { width: 100%; border-collapse: collapse; font-size: 13px; background: #fff; margin: 6px 0 12px; }
table.grid th { background: #1f4e79; color: #fff; font-weight: 600; padding: 7px 10px; text-align: left; border: 1px solid #1a4270; white-space: nowrap; }
table.grid td { padding: 6px 10px; border: 1px solid #d5dbe5; vertical-align: top; word-break: break-all; }
table.grid tr:nth-child(even) td { background: #f7f9fc; }
table.kv td.k { background: #eef3f9; color: #1f4e79; font-weight: 600; width: 120px; white-space: nowrap; }
table.kv tr td { padding: 8px 12px; }
table.narrow { max-width: 640px; }
table.kv-inline { width: 100%; border-collapse: collapse; font-size: 13px; background: #fbfcfe; margin: 4px 0 10px; }
table.kv-inline td { padding: 4px 10px; border: none; }
table.kv-inline td.k { color: #8a93a5; width: 90px; white-space: nowrap; }
.mono { font-family: Consolas, Monaco, monospace; font-size: 12px; }
/* ---------- 状态 ---------- */
.pill { display: inline-block; padding: 1px 10px; border-radius: 10px; font-size: 12px; font-weight: 600; }
.pill.ok { background: #e6f6ec; color: #1e9e4a; }
.pill.warn { background: #fdf3e1; color: #d98a06; }
.pill.bad { background: #fde8e8; color: #d64545; }
.tag { display: inline-block; padding: 1px 8px; border-radius: 4px; font-size: 12px; white-space: nowrap; }
.res-pass { background: #e6f6ec; color: #1e9e4a; }
.res-warn { background: #fdf3e1; color: #d98a06; }
.res-fail { background: #fde8e8; color: #d64545; }
.res-skip, .res-unk { background: #eef1f5; color: #8a93a5; }
p.lead { margin: 6px 0; font-size: 13.5px; }
p.summary-line { margin: 12px 0 6px; font-size: 13.5px; font-weight: 600; color: #2b5c8a; }
ol.suggest { padding-left: 26px; font-size: 13.5px; }
ol.suggest li { margin: 4px 0; }
.note { background: #fdf6ec; border: 1px solid #f0d9a8; color: #8a6d1a; padding: 10px 14px; font-size: 13px; border-radius: 4px; margin: 8px 0 14px; }
.footer { text-align: center; color: #aab2c0; font-size: 12px; padding: 24px; }
/* ---------- 打印 ---------- */
@media print {
  body { background: #fff; }
  .cover { border: none; }
  .page-break { page-break-after: always; }
}
'''
