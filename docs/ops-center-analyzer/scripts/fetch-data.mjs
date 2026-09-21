#!/usr/bin/env node
/**
 * fetch-data.mjs — 读取 ops-center 数据
 * 用法: node fetch-data.mjs [--days N] [--tenant NAME]
 */

import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs'
import { join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const DATA_DIR = join(__dirname, '..', 'data')
const CUSTOMERS_FILE = join(DATA_DIR, 'customers.json')

// ============ 配置 ============
const API_BASE = process.env.OPS_CENTER_API_URL || 'http://localhost:8002'
const DEFAULT_DAYS = 7

// ============ 工具函数 ============
async function api(path) {
  const url = `${API_BASE}/api${path}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`API 错误: ${res.status} ${url}`)
  const data = await res.json()
  return Array.isArray(data) ? data : (data.results || data)
}

async function fetchAll(path, pageSize = 100) {
  let page = 1, all = [], total = 0
  do {
    const res = await fetch(`${API_BASE}/api${path}?page=${page}&page_size=${pageSize}`)
    if (!res.ok) break
    const d = await res.json()
    const items = d.results || d
    all.push(...items)
    total = d.count || items.length
    if (!d.next && !d.results) break
    page++
    if (page > 10) break // 安全限制
  } while (all.length < total)
  return all
}

// ============ 读取数据 ============
async function fetchAlerts(days = DEFAULT_DAYS) {
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - days)
  const cutoffStr = cutoff.toISOString().split('T')[0]

  const all = await fetchAll('/alerts/', 50)
  // 按时间过滤
  return all.filter(a => {
    const d = a.occurred_at || a.received_at || ''
    return d >= cutoffStr
  })
}

async function fetchTenants() {
  return fetchAll('/tenants/', 100)
}

async function fetchInspections(days = DEFAULT_DAYS) {
  const cutoff = new Date()
  cutoff.setDate(cutoff.getDate() - days)
  const cutoffStr = cutoff.toISOString().split('T')[0]

  const all = await fetchAll('/inspections/', 50)
  return all.filter(r => {
    const d = r.executed_at || ''
    return !d || d >= cutoffStr
  })
}

async function fetchAssetStatuses() {
  return fetchAll('/asset-status/', 100)
}

// ============ 客户资料持久化 ============
function loadCustomers() {
  if (!existsSync(CUSTOMERS_FILE)) return {}
  try { return JSON.parse(readFileSync(CUSTOMERS_FILE, 'utf8')) } catch { return {} }
}

function saveCustomers(data) {
  if (!existsSync(DATA_DIR)) mkdirSync(DATA_DIR, { recursive: true })
  writeFileSync(CUSTOMERS_FILE, JSON.stringify(data, null, 2), 'utf8')
}

/**
 * 根据告警和巡检数据，更新客户资料
 * 只更新/添加字段，保留已有信息
 */
function updateCustomerProfiles(customers, tenants, alerts, inspections) {
  const now = new Date().toISOString().split('T')[0]

  // 按租户聚合
  for (const tenant of tenants) {
    if (!customers[tenant.name]) {
      customers[tenant.name] = {
        id: tenant.id,
        name: tenant.name,
        assets: {},
        alert_summary: { total: 0, critical: 0, warning: 0, by_status: {} },
        inspection_summary: { total: 0, pass: 0, fail: 0 },
        last_analyzed: null,
        total_alerts_all_time: 0
      }
    }
    const profile = customers[tenant.name]

    // 筛选该租户的告警和巡检
    const tenantAlerts = alerts.filter(a => a.tenant === tenant.id || a.tenant_name === tenant.name)
    const tenantInspections = inspections.filter(r => r.tenant === tenant.id || r.tenant_name === tenant.name)

    // 按资产聚合告警
    const assetAlertMap = {}
    for (const a of tenantAlerts) {
      const key = `${a.asset_name}|${a.asset_ip}`
      if (!assetAlertMap[key]) {
        assetAlertMap[key] = {
          name: a.asset_name,
          ip: a.asset_ip,
          alert_count: 0,
          latest_alert: null,
          latest_alert_time: null,
          severity_max: 0,
          alert_types: new Set(),
          tags: new Set()
        }
      }
      const ent = assetAlertMap[key]
      ent.alert_count++
      ent.severity_max = Math.max(ent.severity_max, a.severity || 0)
      ent.alert_types.add(a.metric_name || a.alert_type)
      if (!ent.latest_alert_time || a.occurred_at > ent.latest_alert_time) {
        ent.latest_alert_time = a.occurred_at
        ent.latest_alert = a.title
      }
    }

    // 更新资产列表（只增不减，保留历史）
    for (const [key, info] of Object.entries(assetAlertMap)) {
      const existing = profile.assets[key]
      if (existing) {
        // 更新已有字段
        existing.alert_count = info.alert_count
        existing.latest_alert = info.latest_alert
        existing.latest_alert_time = info.latest_alert_time
        existing.severity_max = info.severity_max
        existing.alert_types = [...new Set([...(existing.alert_types || []), ...info.alert_types])]
        // 自动生成 tags
        existing.tags = generateTags(existing, info)
      } else {
        profile.assets[key] = {
          ...info,
          tags: generateTags(null, info),
          first_seen: now,
          last_seen: now
        }
      }
      profile.assets[key].last_seen = now
    }

    // 更新汇总
    profile.alert_summary = {
      total: tenantAlerts.length,
      critical: tenantAlerts.filter(a => a.severity >= 3).length,
      warning: tenantAlerts.filter(a => a.severity === 2).length,
      by_status: Object.fromEntries(
        [...new Set(tenantAlerts.map(a => a.status))].map(s => [
          s, tenantAlerts.filter(a => a.status === s).length
        ])
      ),
      by_source: Object.fromEntries(
        [...new Set(tenantAlerts.map(a => a.source))].map(s => [
          s, tenantAlerts.filter(a => a.source === s).length
        ])
      )
    }

    profile.inspection_summary = {
      total: tenantInspections.length,
      pass: tenantInspections.filter(r => r.overall_status === 'pass').length,
      warning: tenantInspections.filter(r => r.overall_status === 'warning').length,
      fail: tenantInspections.filter(r => r.overall_status === 'fail').length
    }

    profile.total_alerts_all_time = (profile.total_alerts_all_time || 0) + tenantAlerts.length
    profile.last_analyzed = now
  }

  return customers
}

function generateTags(existing, info) {
  const tags = new Set(existing?.tags || [])
  if (info.alert_count >= 5) tags.add('high-alert-volume')
  if (info.severity_max >= 3) tags.add('has-critical-alerts')
  if (info.alert_types.has('SNMP可达性')) tags.add('snmp-issue')
  if (info.alert_types.has('CPU使用率')) tags.add('cpu-issue')
  if (info.alert_types.has('接口状态')) tags.add('interface-down')
  if (info.alert_types.has('磁盘使用率')) tags.add('disk-issue')
  return [...tags]
}

// ============ 主函数 ============
async function main() {
  const args = process.argv.slice(2)
  const days = parseInt(args.find(a => a.startsWith('--days='))?.split('=')[1] || String(DEFAULT_DAYS))
  const tenantFilter = args.find(a => a.startsWith('--tenant='))?.split('=')[1]
  const fetchOnly = args.includes('--fetch-only')

  console.log(`\n📡 读取 ops-center 数据（最近 ${days} 天）...\n`)

  const [alerts, tenants, inspections, assetStatuses] = await Promise.all([
    fetchAlerts(days).catch(() => []),
    fetchTenants().catch(() => []),
    fetchInspections(days).catch(() => []),
    fetchAssetStatuses().catch(() => [])
  ])

  console.log(`  告警：${alerts.length} 条`)
  console.log(`  租户：${tenants.length} 个`)
  console.log(`  巡检记录：${inspections.length} 条`)
  console.log(`  资产状态：${assetStatuses.length} 条`)

  // 更新客户资料
  const customers = loadCustomers()
  updateCustomerProfiles(customers, tenants, alerts, inspections)

  if (!fetchOnly) {
    saveCustomers(customers)
    console.log(`\n💾 客户资料已更新（${Object.keys(customers).length} 个租户）`)
  }

  // 按租户分组输出摘要
  for (const tenant of tenants) {
    const ta = alerts.filter(a => a.tenant === tenant.id)
    if (ta.length === 0 && tenantFilter) continue
    console.log(`\n  ${tenant.name}: ${ta.length} 条告警`)
  }

  return { alerts, tenants, inspections, assetStatuses, customers }
}

export { main, fetchAlerts, fetchTenants, fetchInspections, fetchAssetStatuses, loadCustomers, updateCustomerProfiles }

const isMain = process.argv[1]?.endsWith('fetch-data.mjs')
if (isMain) main().catch(console.error)
