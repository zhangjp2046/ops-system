---
name: ops-center-analyzer
description: "ops-center 告警与客户资产智能分析体。读取告警数据、结合客户资料、用 LLM 分析根因并给出排错建议。持续学习客户资产信息，越用越精准。"
homepage: https://clawhub.ai
metadata: {"openclaw":{"emoji":"🏥","requires":{"bins":["node"],"env":["OPS_CENTER_API_URL","LLM_API_KEY"]}}}
---

# ops-center-analyzer 🏥

> 运维告警智能分析体 — 让 AI 帮你读告警、关联资产、找根因、出方案。

---

## 功能特性

- **告警读取** — 从 ops-center API 获取最新告警，自动按租户分组
- **客户资料积累** — 每次分析自动补充/更新客户资产数据，持久化到 `data/customers.json`
- **LLM 分析** — 结合资产上下文给出根因分析 + 排错步骤 + 优先级建议
- **报告输出** — 每次分析生成报告，写入 `data/reports/YYYY-MM-DD.md`
- **手动触发** — 随时可运行，不依赖定时任务

---

## 环境变量

```bash
# ops-center API 地址（末尾不要斜杠）
export OPS_CENTER_API_URL="http://localhost:8002"

# LLM API Key（支持 OpenAI / 兼容 API）
export LLM_API_KEY="sk-..."

# LLM API Base（可选，兼容第三方代理）
export LLM_API_BASE="https://api.openai.com/v1"

# LLM 模型（默认用 GPT-4o mini，省成本）
export LLM_MODEL="gpt-4o-mini"
```

---

## 手动运行

```bash
# 完整分析（读取告警 + 更新客户资料 + LLM分析）
node {baseDir}/scripts/analyze.mjs

# 仅读取数据（不调用 LLM，快速预览）
node {baseDir}/scripts/analyze.mjs --fetch-only

# 指定租户分析
node {baseDir}/scripts/analyze.mjs --tenant "博越信息"

# 指定时间范围（天）
node {baseDir}/scripts/analyze.mjs --days 3

# 查看帮助
node {baseDir}/scripts/analyze.mjs --help
```

---

## 数据说明

### 客户资料持久化

`data/customers.json` — 随分析次数增加，内容不断丰富：

```json
{
  "博越信息": {
    "id": 2,
    "assets": [
      {
        "name": "物资管理服务器",
        "ip": "192.168.0.15",
        "type": "SERVER",
        "alert_count": 8,
        "last_seen": "2026-04-08",
        "last_alert": "SNMP不可达",
        "tags": ["snmp-unreachable", "needs-attention"]
      }
    ],
    "alert_summary": { "total": 20, "critical": 16, "warning": 4 },
    "last_analyzed": "2026-04-11"
  }
}
```

> `tags` 字段会随分析自动生成和更新，用于标识该资产的特征和状态。

---

## 分析报告示例

每次分析生成 `data/reports/YYYY-MM-DD.md`：

```
## 运维分析报告 — 2026-04-11

### 总体态势
- 总告警：20 条（未处理）
- 高危：16 条 / 警告：4 条
- 受影响租户：1 个（博越信息）

### 🚨 紧急问题

#### 物资管理服务器 (192.168.0.15) — SNMP 不可达
**严重程度：** 🔴 高危  
**告警数量：** 8 条

**根因分析：**
SNMP Agent 无响应，最可能是网络层面的问题...

**排错步骤：**
1. 在监控服务器执行：snmpwalk -v 2c -c public 192.168.0.15
2. 检查目标防火墙：确认 UDP 161 端口放行
3. 检查 SNMP Service 状态
...

**建议操作：** P0 — 立即处理
```

---

## 权限说明

技能脚本只读 ops-center 数据，不做任何写操作。

| 读取 | 说明 |
|------|------|
| GET /api/alerts/ | 告警列表 |
| GET /api/tenants/ | 租户列表 |
| GET /api/inspections/ | 巡检记录 |
| GET /api/asset-status/ | 资产状态 |

---

## OpenClaw Cron 配置（可选）

每天早上 9 点自动分析：

```json
{
  "name": "ops-center-daily-analysis",
  "schedule": { "kind": "cron", "expr": "0 9 * * *", "tz": "Asia/Shanghai" },
  "sessionTarget": "isolated",
  "payload": {
    "kind": "agentTurn",
    "message": "运行技能 ops-center-analyzer：node {baseDir}/scripts/analyze.mjs"
  }
}
```

---

## 工作流程

```
analyze.mjs
  ├── fetch-data.mjs
  │     ├── GET /api/alerts/         → 最新告警
  │     ├── GET /api/tenants/        → 租户列表
  │     ├── GET /api/inspections/    → 巡检记录
  │     └── 更新 customers.json      → 持久化
  │
  ├── 构建 prompt
  │     ├── 告警上下文（按资产分组）
  │     ├── 客户资料（从 customers.json）
  │     └── 分析要求（根因+方案+优先级）
  │
  ├── 调用 LLM API
  │
  ├── 保存报告 → data/reports/YYYY-MM-DD.md
  │
  └── 输出摘要 → 控制台/会话
```
