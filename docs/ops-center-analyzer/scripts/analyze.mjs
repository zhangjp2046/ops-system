#!/usr/bin/env node
/**
 * analyze.mjs — 运维告警智能分析体
 * 读取数据 → 构建 prompt → LLM 分析 → 输出报告
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'
import { createRequire } from 'module'

const require = createRequire(import.meta.url)
const __dirname = dirname(fileURLToPath(import.meta.url))
const DATA_DIR = join(__dirname, '..', 'data')
const REPORTS_DIR = join(DATA_DIR, 'reports')
const CUSTOMERS_FILE = join(DATA_DIR, 'customers.json')

// ============ 配置 ============
const OPS_API = process.env.OPS_CENTER_API_URL || 'http://localhost:8002'
const LLM_API_KEY = process.env.LLM_API_KEY || ''
const LLM_API_BASE = process.env.LLM_API_BASE || 'https://api.openai.com/v1'
const LLM_MODEL = process.env.LLM_MODEL || 'gpt-4o-mini'
const DEFAULT_DAYS = 7

// ============ 工具函数 ============
async function api(path) {
  const res = await fetch(`${OPS_API}/api${path}`)
  if (!res.ok) throw new Error(`API 错误: ${res.status} ${path}`)
  const data = await res.json()
  return Array.isArray(data) ? data : (data.results || data)
}

async function fetchAll(path, pageSize = 100) {
  let page = 1, all = [], total = 0
  do {
    const res = await fetch(`${OPS_API}/api${path}?page=${page}&page_size=${pageSize}`)
    if (!res.ok) break
    const d = await res.json()
    const items = d.results || d
    all.push(...items)
    total = d.count || items.length
    if (!d.next && !d.results) break
    page++
    if (page > 10) break
  } while (all.length < total)
  return all
}

function loadCustomers() {
  if (!existsSync(CUSTOMERS_FILE)) return {}
  try { return JSON.parse(readFileSync(CUSTOMERS_FILE, 'utf8')) } catch { return {} }
}

function saveReport(content) {
  if (!existsSync(REPORTS_DIR)) mkdirSync(REPORTS_DIR, { recursive: true })
  const today = new Date().toISOString().split('T')[0]
  const file = join(REPORTS_DIR, `${today}.md`)
  writeFileSync(file, content, 'utf8')
  return file
}

// ============ 数据获取 ============
async function fetchData(days) {
  const [alerts, tenants, inspections] = await Promise.all([
    (async () => {
      const cutoff = new Date(); cutoff.setDate(cutoff.getDate() - days)
      const cutoffStr = cutoff.toISOString().split('T')[0]
      const all = await fetchAll('/alerts/', 50)
      return all.filter(a => (a.occurred_at || a.received_at || '') >= cutoffStr)
    })(),
    fetchAll('/tenants/', 100).catch(() => []),
    (async () => {
      const cutoff = new Date(); cutoff.setDate(cutoff.getDate() - days)
      const cutoffStr = cutoff.toISOString().split('T')[0]
      const all = await fetchAll('/inspections/', 50)
      return all.filter(r => !r.executed_at || r.executed_at >= cutoffStr)
    })()
  ])
  return { alerts, tenants, inspections }
}

// ============ 数据聚合 ============
function groupByTenant(alerts, tenants) {
  const map = {}
  for (const t of tenants) map[t.id] = { ...t, alerts: [], inspections: [] }
  for (const a of alerts) {
    if (map[a.tenant]) map[a.tenant].alerts.push(a)
  }
  return Object.values(map).filter(t => t.alerts.length > 0)
}

function groupByAsset(alerts) {
  const map = {}
  for (const a of alerts) {
    const key = `${a.asset_name}|${a.asset_ip}`
    if (!map[key]) map[key] = { ...a, count: 0, types: [] }
    map[key].count++
    map[key].types.push(a.metric_name || a.alert_type)
  }
  return Object.values(map)
}

function summarize(alerts) {
  const total = alerts.length
  const bySev = { critical: 0, warning: 0, info: 0 }
  const byStatus = {}
  const bySource = {}
  const unhandled = 0

  for (const a of alerts) {
    if (a.severity >= 3) bySev.critical++
    else if (a.severity === 2) bySev.warning++
    else bySev.info++
    byStatus[a.status_display || a.status] = (byStatus[a.status_display || a.status] || 0) + 1
    bySource[a.source_display || a.source] = (bySource[a.source_display || a.source] || 0) + 1
    if (['NEW', 'ACKNOWLEDGED', 'IN_PROGRESS'].includes(a.status)) unhandled++
  }
  return { total, bySev, byStatus, bySource, unhandled }
}

// ============ 构建 Prompt ============
function buildPrompt(tenantGroups, summary, customers) {
  const tenantBlocks = tenantGroups.map(t => {
    const byAsset = groupByAsset(t.alerts)
    const s = summarize(t.alerts)

    const assetBlocks = byAsset.map(a => {
      const customer = customers[t.name]
      const assetInfo = customer?.assets?.[`${a.asset_name}|${a.asset_ip}`]
      return `## ${a.asset_name} (${a.asset_ip})

- 历史告警次数（含本次）：${assetInfo ? assetInfo.alert_count : a.count} 条
- 告警类型：${[...new Set(a.types)].join('、')}
- 最新告警：${a.latest_alert || a.title || '无'}
- 已知标签：${assetInfo?.tags?.join('、') || '暂无'}
- 首次出现：${assetInfo?.first_seen || '本次'}
- 当前告警（${a.count}条）：
${t.alerts.filter(al => al.asset_ip === a.asset_ip).map(al =>
  `  - [${al.severity_display}] ${al.title}`
).join('\n')}`
    }).join('\n\n')

    return `### 租户：${t.name}（${t.id}）

**告警统计：** 合计 ${s.total} 条 | 高危 ${s.bySev.critical} 条 | 警告 ${s.bySev.warning} 条 | 未处理 ${s.unhandled} 条
**来源分布：** ${Object.entries(s.bySource).map(([k,v]) => `${k} ${v}条`).join(' | ')}

${assetBlocks}`
  }).join('\n\n')

  const prompt = `你是资深运维工程师，擅长分析告警日志、定位根因、给出清晰可执行的排错方案。

## 任务
分析以下运维告警数据，输出结构化的分析报告，包含：
1. **总体态势**（一句话总结）
2. **按资产分组的问题分析**（每台设备）
3. **根因分析**
4. **排错步骤**（按优先级 P0→P3）
5. **运维建议**

## 数据

${tenantBlocks}

## 输出要求

输出 Markdown 格式报告，用中文。

**总体态势** 格式：
> 🎯 目前共有 N 条告警（高危 X 条，警告 Y 条），主要问题集中在[一句话概括]，建议优先处理[资产名]。

**每台资产** 格式：
### 🚨 资产名 (IP)
- 严重程度：🔴 高危 / 🟡 警告  
- 告警次数：N 条
- 根因分析：[推测最可能的 1-2 句话]

**排错步骤** 格式（每步要具体，不能泛泛）：
P0 [立即处理] 资产名 - [具体操作，如：在 X 服务器执行 snmpwalk 命令...]
P1 [今日处理] ...

**运维建议**：
- 短期：[1-3 条具体建议]
- 长期：[1-2 条建设性建议，如：建立 SNMP 监控规范]

## 注意
- 如果某资产所有告警都是"SNMP不可达"，根因是网络/配置问题，不是硬件故障
- 如果是接口 DOWN，重点检查物理连接和交换机端口状态
- 优先给出能远程执行的诊断命令

请输出分析报告：`

  return prompt
}

// ============ LLM 调用 ============
async function callLLM(prompt) {
  if (!LLM_API_KEY) {
    throw new Error('未设置 LLM_API_KEY 环境变量')
  }

  const res = await fetch(`${LLM_API_BASE}/chat/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${LLM_API_KEY}`
    },
    body: JSON.stringify({
      model: LLM_MODEL,
      messages: [{ role: 'user', content: prompt }],
      temperature: 0.2
    })
  })

  if (!res.ok) {
    const err = await res.text()
    throw new Error(`LLM API 错误 ${res.status}: ${err}`)
  }

  const data = await res.json()
  return data.choices?.[0]?.message?.content || '（无输出）'
}

// ============ 主函数 ============
async function main() {
  const args = process.argv.slice(2)

  if (args.includes('--help') || args.includes('-h')) {
    console.log(`
用法: node analyze.mjs [选项]

选项:
  --days=N      分析最近 N 天的数据（默认 7）
  --tenant=NAME 只分析指定租户
  --fetch-only  仅读取数据，不调用 LLM
  --no-save     不保存报告文件
  --help        显示帮助

环境变量:
  OPS_CENTER_API_URL  ops-center API 地址（默认 http://localhost:8002）
  LLM_API_KEY          LLM API Key（必填）
  LLM_API_BASE         LLM API Base（默认 https://api.openai.com/v1）
  LLM_MODEL            模型（默认 gpt-4o-mini）
`)
    process.exit(0)
  }

  const days = parseInt(args.find(a => a.startsWith('--days='))?.split('=')[1] || String(DEFAULT_DAYS))
  const tenantFilter = args.find(a => a.startsWith('--tenant='))?.split('=')[1]
  const fetchOnly = args.includes('--fetch-only')
  const noSave = args.includes('--no-save')

  console.log(`\n🏥 ops-center 运维分析体`)
  console.log(`━━━━━━━━━━━━━━━━━━━━━━`)
  console.log(`  数据范围：最近 ${days} 天`)
  console.log(`  API 地址：${OPS_API}`)
  console.log(`  LLM 模型：${LLM_MODEL}`)
  if (fetchOnly) console.log(`  模式：仅读取（不调用 LLM）`)
  console.log()

  // 1. 获取数据
  console.log(`📡 读取告警数据...`)
  const { alerts, tenants, inspections } = await fetchData(days)
  console.log(`  告警：${alerts.length} 条 | 租户：${tenants.length} 个 | 巡检：${inspections.length} 条`)

  if (alerts.length === 0) {
    console.log(`\n✅ 无告警数据，分析结束`)
    return
  }

  // 2. 按租户分组
  let tenantGroups = groupByTenant(alerts, tenants)
  if (tenantFilter) {
    tenantGroups = tenantGroups.filter(t => t.name.includes(tenantFilter))
    console.log(`  筛选租户「${tenantFilter}」：${tenantGroups.length} 个`)
  }

  // 3. 加载客户资料
  const customers = loadCustomers()
  const today = new Date().toISOString().split('T')[0]

  // 4. 构建 prompt
  const overallSummary = summarize(alerts)
  const prompt = buildPrompt(tenantGroups, overallSummary, customers)

  // 5. 保存原始数据摘要
  const dataSummary = {
    generated_at: today,
    days,
    alert_count: alerts.length,
    unhandled: overallSummary.unhandled,
    by_severity: overallSummary.bySev,
    tenants: tenantGroups.map(t => ({ name: t.name, alert_count: t.alerts.length }))
  }

  if (noSave || fetchOnly) {
    console.log(`\n📋 数据摘要（--fetch-only 模式）：`)
    console.log(JSON.stringify(dataSummary, null, 2))
    return
  }

  // 6. 调用 LLM
  console.log(`\n🤖 正在调用 LLM 分析（${tenantGroups.length} 个租户）...`)
  let analysis = ''
  try {
    analysis = await callLLM(prompt)
  } catch (e) {
    console.error(`\n❌ LLM 调用失败：${e.message}`)
    process.exit(1)
  }

  // 7. 输出报告
  const report = `# 运维分析报告 — ${today}

> 🤖 AI 分析 · 数据范围：近 ${days} 天 · 告警 ${alerts.length} 条（未处理 ${overallSummary.unhandled} 条）

${analysis}

---
*本报告由 ops-center-analyzer 自动生成 | 数据来源：${OPS_API}*`

  const reportFile = saveReport(report)
  console.log(`\n✅ 分析完成`)
  console.log(`\n━━━━━━━━━━━━━━━━━━━━━━`)
  console.log(`📊 数据摘要`)
  console.log(`  总告警：${alerts.length} 条（高危 ${overallSummary.bySev.critical} / 警告 ${overallSummary.bySev.warning}）`)
  console.log(`  未处理：${overallSummary.unhandled} 条`)
  console.log(`  受影响租户：${tenantGroups.length} 个`)
  for (const t of tenantGroups) {
    const s = summarize(t.alerts)
    console.log(`  - ${t.name}: ${t.alerts.length} 条（高危 ${s.bySev.critical}）`)
  }
  console.log(`\n📄 报告已保存：${reportFile}`)
  console.log(`\n${'─'.repeat(50)}`)
  console.log(analysis)
}

main().catch(e => { console.error(e); process.exit(1) })
