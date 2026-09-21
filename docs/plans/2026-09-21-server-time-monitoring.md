# 服务器时间检查 实施方案（v4 · 已实现）

> **状态：已实现并验证（2026-09-21）。** 早期版本（SSH 取时间 / 内网基准配置）已作废。
> 本文件记录最终落地形态，供后续维护参考。

**目标：** 在巡检计划里勾选「时间同步」检查项，对**服务器**和**数据库系统**两类目标取时间与 ops-system 本机比对，偏差超过所选阈值（10/60/180 秒）则报警告，并进入巡检报告。

**已确认的约束（JP 2026-09-21）：**
- 只针对**服务器**和**数据库系统**，其他设备类型不出现在选择列表
- **不用 SSH**（登录权限太高）
- 数据库沿用现有凭据（DBA），只做 SELECT，不需要任何写权限
- 需要检查时间的服务器**都开了 SNMP**
- 租户内网无外网 → 代码里不得出现任何外网时钟源
- 本机时间由部署方保证准确 → 代码不做本机同步/校验

---

## 一、两条采集路径

| 目标 | 检查项所在协议 | 取时间方式 | 权限 | 精度 |
|---|---|---|---|---|
| 服务器 | `snmp` | `hrSystemDate` `1.3.6.1.2.1.25.1.2.0` | SNMP 只读 community | 0.1s（部分设备仅到秒） |
| 数据库系统 | `mysql` / `mssql` / `oracle` / `postgresql` | SQL 取服务器 UTC epoch | SELECT | ms |

`check_items.py` 里 `TIME_SYNC` 只加在上述 5 个协议下 —— `ssh` / `ping` / `port` 不加，所以其他设备自然不会出现在选择列表。

### SNMP：hrSystemDate 解析要点（RFC 2579 DateAndTime）

| 字节 | 含义 |
|---|---|
| 0-1 | 年（**2 字节大端**，`07 EA` = 2026） |
| 2-7 | 月/日/时/分/秒 |
| 7 | deciseconds（0.1 秒） |
| 8 | UTC 方向：`0x2B` = `+`，`0x2D` = `-` |
| 9-10 | UTC 偏移 时/分 |

⚠️ 踩过的坑：
1. **年份是 2 字节**：按单字节解析会得到 2007（`0x07EA` 当 `0x07`）
2. **字节数不一致**：实测 `192.168.0.18` 返回 11 字节（带 `2B 08 00` = +08:00），`172.26.11.50` 只返回 8 字节（无时区）→ 无时区时按本机时区推定并在结果里标注
3. **部分设备精度只到秒**：deciseconds 恒为 0，单次读数会随本机秒的小数部分在 0~1s 间跳（实测同一台一次 -0.255s、一次 -0.903s）→ **取 3 次读数、用 |偏差| 最小的那次**。（原先把「测量误差约±1s」写进结果里，后按需求摘除：多做样已吸收该误差，最小档位 10s 远大于量化残留，提示纯属噪音。）
4. **每次读数必须配当次的本机时间**（SNMP 往返中点）——不能 3 次采完再统一和本机比，否则早采的样本会被算进采样间隔，偏差凭空变大

### 数据库：取 UTC epoch

- MySQL: `SELECT UNIX_TIMESTAMP(NOW(6)) AS EPOCH`
- MSSQL: `SELECT DATEDIFF_BIG(MILLISECOND,'19700101',SYSUTCDATETIME())/1000.0 AS EPOCH`（2016+ 不支持则回退秒级 `DATEDIFF`）
- Oracle: `SELECT (CAST(SYS_EXTRACT_UTC(SYSTIMESTAMP) AS DATE)-TO_DATE('19700101','YYYYMMDD'))*86400 AS EPOCH FROM DUAL`

用 UTC epoch 最省事：与时区无关，直接 `epoch - time.time()`。
取结果时用「首行首值」`_first_epoch(rows)` —— 各引擎结果形态不一（MySQL DictCursor / MSSQL tsql 文本解析 / Oracle sqlplus COLSEP），列名大小写不保证。

---

## 二、阈值与判定

**阈值的唯一来源是巡检计划的 `check_items`**：

```json
{"code": "TIME_SYNC", "name": "时间同步", "threshold": 60}
```

前端在「巡检项目」勾选「时间同步」后出现 `10秒 / 60秒 / 180秒` 单选，**默认 60 秒**。

> 档位放宽的原因：多数服务器的 `hrSystemDate` 精度只到秒，测量误差本身可达 ±1s，
> 1 秒档会 100% 误报。老计划里残留的 `threshold: 1` 在前端会被归一到 10 秒
> （`normalizeTimeSyncThreshold`），后端判定则按存的原值走，不做归一。

| 条件 | status | severity |
|---|---|---|
| `|偏差| ≤ threshold` | `pass` | 1 |
| `|偏差| > threshold` | `warning` | 2（靠 status 兜底映射） |
| 取不到时间 | `warning`，`result_value='查询失败'` | 2 |

> 🔴 **`result_value` 的第一个数字必须是偏差绝对值** —— `get_threshold_severity` / `record_monitoring_data` 都取首个数字。带符号的偏差只能放 `result_message`。（同类坑：磁盘那次把「磁盘个数」当成了使用率）

### 告警阈值配置页（`/monitoring/thresholds`）里的行

那一页列的是 `AlertThreshold` 表，所以要让「时间同步」出现在页面上、并支持勾选「监控项」，
就必须有行 —— 但行的**作用是展示 + 监控项开关，不参与判定**：

```bash
python manage.py seed_time_sync_thresholds          # 幂等，可重复执行
```

建 5 条全局行（`snmp` + `mysql` / `mssql` / `oracle` / `postgresql`），
**三个阈值字段全空**、`threshold_direction='exact'`、`is_monitoring_item=False`（需要趋势图时在页面里勾）。

> 🔴 **踩过的坑：行存在但没配阈值，会把 status 吃掉。**
> `get_threshold_severity()` 原先是「行存在就 return」，而 `get_severity()` 在没阈值可比时
> 会一路 fallthrough 到 `return 1, '信息'`。实测（真实链路，带 `customer_id`）：
>
> ```
> 无行:        status=fail  偏差 9000s -> (3, '错误')   ✅
> 有行(空阈值): status=fail  偏差 9000s -> (1, '信息')   ❌ 差 2.5 小时只报「信息」
> ```
>
> 修法：`AlertThreshold.has_effective_threshold()`（三个基础阈值 + 启用中的复杂规则全空 → 不参与判定），
> 查表层逐行挑选真正有效的那一行。顺带修掉了 `DB_VERSION` / `DB_CONNECTION` 这类
> 空阈值行吃 status 的既有问题。

> 🔴 **同一层要多行逐个挑，不能只看 `.first()`。** 查表**不区分 protocol**，
> 全局层里 `TIME_SYNC` 会命中 5 行；若只判断 `.first()`，一旦取到空阈值行就会把整层放弃，
> 把同层其它行真实存在的阈值一起丢掉。（这是上面那个修法第一版踩的坑，已在
> `verify_time_sync_threshold.py` C 组固化为断言。）

> 🔴 **阈值查表必须带 protocol**（同文件 F 组断言）。阈值是按
> `客户/资产类型 + 协议` 配的，同名检查项跨协议阈值不同——各库 `SESSIONS` 是
> 100/150/200/300。原先 `generate_inspection_alerts` 不传 protocol，实测：
>
> ```
> MSSQL 资产 会话数 120 个（自己那行 warn=150，应判「信息」）
>   实际: (2,'警告')  ← 命中的是 postgresql 那行(warn=100)
> ```
>
> `get_threshold_severity()` / `get_threshold_info()` / `_find_threshold()` 均加了
> `protocol` 参数；同协议没有行时不跨协议借用，回落到 status 判定。

---

## 三、落地文件

| 文件 | 改动 |
|---|---|
| `apps/inspection/time_check.py` | **新增** — 公共逻辑：DateAndTime 解析、阈值读取、偏差计算、结果组装 |
| `apps/inspection/check_items.py` | `TIME_SYNC` 加到 snmp + 4 个数据库协议 |
| `apps/inspection/views.py` | `_execute_snmp_checks` 加 TIME_SYNC 分支（3 次取样 + 往返中点） |
| `apps/inspection/db_connectors.py` | 3 个连接器各加 `get_server_time()`；`_first_epoch()` 辅助；`INSPECTION_TEMPLATES` 加 TIME_SYNC |
| `apps/inspection/db_inspector_v2.py` | `_format_check_result` 加 TIME_SYNC 分支；阈值从 `task.plan.check_items` 传入 |
| `frontend/src/views/inspection/InspectionPlanList.vue` | 勾选「时间同步」时显示阈值单选；提交带 `threshold`；编辑回显；新增时重置 |

**无数据库迁移**（`check_items` 是 JSONField，`choices` 是 Django 层校验）。
**无新增模型、无新增 AlertThreshold、无 root 依赖、无外网依赖。**

---

## 四、验证

```bash
# 逻辑验证（37 项）
python scripts/verify_time_sync.py

# 端到端（建计划→建任务→执行→查结果→自动清理）
python scripts/e2e_time_sync.py
```

覆盖：DateAndTime 解析（11/8 字节、正负时区、2 字节年份、5 种异常输入）、阈值读取
（9 种形态）、阈值边界（10/60/180 × 各两侧）、偏差绝对值提取、多次取样、
外网时钟源禁用检查、SSH 路径已移除、前后端档位一致性。

实测（2026-09-21）：
```
192.168.0.18   偏差 -0.022s   （设备时间 2026-09-21 09:53:55 +08:00）
172.26.11.50   偏差 -0.076s   （设备未提供时区，按本机时区推定）
172.26.12.11   SNMP 无响应 → 跳过
```

end-to-end 落库结果：
```
项目=时间同步  状态=pass  severity=1
  result_value   = '偏差 0.235s'
  result_message = 偏差 -0.235s（服务器慢） | 采集 SNMP hrSystemDate | 设备时间 2026-09-21 09:58:23 UTC+08:00 | 取3次读数中最接近0的一次 | 本机基准 2026-09-21 09:58:23
```

---

## 五、维护提醒

1. **巡检报告**：`report_builder.classify_subsystem()` 默认归 `server` 章节（第4章），新增检查项自动出现在检查明细里，无需改报告代码
2. **老计划兼容**：`check_items` 是对象数组但无 `threshold`，或更老的字符串数组 → 一律取默认 60 秒；前端回显时会把残留的 1 秒档归一到 10 秒
3. **默认阈值**：`time_check.DEFAULT_THRESHOLD = 60.0`，要改只改这一处（同时改前端 `timeSyncThreshold` 初值与档位数组，`verify_time_sync.py` 的 I 组会校验两者一致）
4. **PostgreSQL**：`db_connectors` 里目前没有 PG 连接器（`get_connector` 落到 MySQL 连接器），PG 资产的时间检查会失败——属既有缺口，未在本次范围内
5. **前端改了要重新 build**，发布补丁时 `frontend/dist` 必须一起带上
