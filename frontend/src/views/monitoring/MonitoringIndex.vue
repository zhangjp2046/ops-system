<template>
  <div class="monitoring-center">
    <div class="page-header">
      <h2>监控中心</h2>
      <div class="header-actions">
        <el-select v-model="filterProtocol" placeholder="全部协议" clearable size="default" style="width: 140px; margin-right: 8px;" @change="loadOverview">
          <el-option label="SNMP" value="snmp" />
          <el-option label="MySQL" value="mysql" />
          <el-option label="MSSQL" value="mssql" />
          <el-option label="Oracle" value="oracle" />
          <el-option label="PostgreSQL" value="postgresql" />
          <el-option label="SSH" value="ssh" />
          <el-option label="Ping" value="ping" />
          <el-option label="端口检测" value="port" />
        </el-select>
        <el-select v-model="filterAssetType" placeholder="资产类型" clearable size="default" style="width: 140px; margin-right: 8px;" @change="loadOverview">
          <el-option v-for="t in assetTypes" :key="t.id" :label="t.type_name" :value="t.id" />
        </el-select>
        <el-button @click="loadOverview">刷新</el-button>
      </div>
    </div>

    <!-- 概览统计 -->
    <el-row :gutter="16" class="overview-row">
      <el-col :span="6">
        <div class="overview-card">
          <div class="overview-icon blue"><el-icon :size="28"><Box /></el-icon></div>
          <div class="overview-info">
            <div class="overview-value">{{ overview.length }}</div>
            <div class="overview-label">监控指标数</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="overview-card">
          <div class="overview-icon green"><el-icon :size="28"><CircleCheck /></el-icon></div>
          <div class="overview-info">
            <div class="overview-value">{{ healthyCount }}</div>
            <div class="overview-label">正常</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="overview-card">
          <div class="overview-icon yellow"><el-icon :size="28"><Warning /></el-icon></div>
          <div class="overview-info">
            <div class="overview-value">{{ warningCount }}</div>
            <div class="overview-label">警告</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="overview-card">
          <div class="overview-icon red"><el-icon :size="28"><CircleClose /></el-icon></div>
          <div class="overview-info">
            <div class="overview-value">{{ errorCount }}</div>
            <div class="overview-label">异常</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <!-- 指标表格 -->
    <el-card class="table-card">
      <!-- 多选操作栏 -->
      <div v-if="selectedRows.length > 0" class="selection-bar">
        <span>已选择 <strong>{{ selectedRows.length }}</strong> 项</span>
        <el-button type="primary" size="small" @click="openCompareChart">对比趋势图</el-button>
        <el-button type="danger" size="small" @click="handleBatchDelete">批量删除</el-button>
        <el-button size="small" @click="selectedRows = []">取消选择</el-button>
      </div>

      <el-table :data="overview" stripe @selection-change="onSelectionChange" @row-click="toggleRowSelect">
        <el-table-column type="selection" width="40" />
        <el-table-column prop="asset_name" label="资产" min-width="140" />
        <el-table-column prop="asset_ip" label="IP地址" width="130" />
        <el-table-column prop="check_item_name" label="监控指标" min-width="150" />
        <el-table-column prop="protocol" label="协议" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ protocolLabel(row.protocol) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="display_value" label="最新值" width="150">
          <template #default="{ row }">
            <span class="metric-value" :class="severityClass(row.severity)">
              {{ row.display_value || '-' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="recorded_at" label="采集时间" width="160">
          <template #default="{ row }">
            {{ row.recorded_at ? formatDate(row.recorded_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="severity" label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="severityTagType(row.severity)" size="small">
              {{ severityLabel(row.severity) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click.stop="openTimeline(row)">趋势图</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 单指标趋势图弹窗 -->
    <el-dialog v-model="timelineVisible" :title="`${timelineTitle} - 趋势图`" width="900px" destroy-on-close>
      <div class="timeline-filters">
        <el-select v-model="timelineDays" size="default" style="width: 130px; margin-right: 12px;" @change="loadTimeline">
          <el-option label="近24小时" :value="1" />
          <el-option label="近3天" :value="3" />
          <el-option label="近7天" :value="7" />
          <el-option label="近30天" :value="30" />
        </el-select>
        <span style="color: #888; font-size: 13px;">
          共 {{ timelineData.length }} 条记录
        </span>
      </div>
      <div ref="chartRef" class="echarts-container"></div>
      <el-empty v-if="timelineData.length === 0 && !chartLoading" description="暂无数据" />
      <template #footer>
        <el-button @click="timelineVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 多指标对比趋势图弹窗 -->
    <el-dialog v-model="compareVisible" title="多指标对比趋势图" width="960px" destroy-on-close>
      <div class="timeline-filters">
        <el-select v-model="compareDays" size="default" style="width: 130px; margin-right: 12px;" @change="loadCompareChart">
          <el-option label="近24小时" :value="1" />
          <el-option label="近3天" :value="3" />
          <el-option label="近7天" :value="7" />
          <el-option label="近30天" :value="30" />
        </el-select>
        <span style="color: #888; font-size: 13px;">
          {{ compareSeries.length }} 个指标 · {{ compareTotalPoints }} 条记录
        </span>
      </div>
      <div ref="compareChartRef" class="echarts-container"></div>
      <el-empty v-if="compareSeries.length === 0 && !chartLoading" description="暂无对比数据" />
      <template #footer>
        <el-button @click="compareVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onUnmounted } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'
import { Box, CircleCheck, CircleClose, Warning } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'

const API = '/api'

// 数据
const overview = ref([])
const timelineData = ref([])
const assetTypes = ref([])
const selectedRows = ref([])

// 筛选
const filterProtocol = ref('')
const filterAssetType = ref('')

// 多指标对比
const compareVisible = ref(false)
const compareDays = ref(7)
const compareSeries = ref([])
const compareTotalPoints = ref(0)
const compareChartRef = ref(null)
let compareChart = null

// 时间线
const timelineVisible = ref(false)
const timelineTitle = ref('')
const timelineAssetId = ref(null)
const timelineCheckItemCode = ref('')
const timelineDays = ref(7)
const chartRef = ref(null)
const chartLoading = ref(false)
let timelineChart = null

// 统计
const healthyCount = computed(() => overview.value.filter(r => r.severity === 1 || !r.severity).length)
const warningCount = computed(() => overview.value.filter(r => r.severity === 2).length)
const errorCount = computed(() => overview.value.filter(r => r.severity >= 3).length)

// 工具函数
function protocolLabel(p) {
  const map = { snmp: 'SNMP', mysql: 'MySQL', mssql: 'MSSQL', oracle: 'Oracle', postgresql: 'PostgreSQL', ping: 'Ping', ssh: 'SSH', port: '端口' }
  return map[p] || p || ''
}
function severityLabel(s) {
  return ['', '正常', '警告', '错误', '严重'][s] || '正常'
}
function severityTagType(s) {
  return ['', 'success', 'warning', 'danger', 'danger'][s] || 'info'
}
function severityClass(s) {
  return ['', 'text-success', 'text-warning', 'text-danger', 'text-danger'][s] || ''
}
function formatDate(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  return `${d.getMonth()+1}/${d.getDate()} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
}

// 加载概览
async function loadOverview() {
  try {
    const params = {}
    if (filterProtocol.value) params.protocol = filterProtocol.value
    if (filterAssetType.value) params.asset_type = filterAssetType.value
    const res = await axios.get(`${API}/monitoring/data/overview/`, { params })
    overview.value = res.data || []
  } catch (e) {
    console.error('加载监控概览失败:', e)
  }
}

// 表格行选中切换
function toggleRowSelect(row) {
  const idx = selectedRows.value.findIndex(r => r.asset === row.asset && r.check_item_code === row.check_item_code)
  if (idx >= 0) {
    selectedRows.value.splice(idx, 1)
  } else {
    selectedRows.value.push(row)
  }
}
function onSelectionChange(selection) {
  selectedRows.value = selection
}

// 批量删除
async function handleBatchDelete() {
  if (selectedRows.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedRows.value.length} 项监控数据吗？删除后不可恢复。`,
      '确认删除',
      { confirmButtonText: '确定', cancelButtonText: '取消', type: 'warning' }
    )
    const ids = selectedRows.value.map(r => r.id)
    await axios.post(`${API}/monitoring/data/batch_delete/`, { ids })
    ElMessage.success(`已删除 ${ids.length} 条记录`)
    selectedRows.value = []
    loadOverview()
  } catch (e) {
    if (e !== 'cancel') {
      console.error('批量删除失败:', e)
      ElMessage.error('删除失败')
    }
  }
}

// 渲染单指标折线图
function renderTimelineChart() {
  if (!chartRef.value || timelineData.value.length === 0) return
  if (timelineChart) {
    timelineChart.dispose()
    timelineChart = null
  }
  timelineChart = echarts.init(chartRef.value)

  const times = timelineData.value.map(d => formatDate(d.recorded_at))
  const values = timelineData.value.map(d => d.numeric_value)
  const severities = timelineData.value.map(d => d.severity)

  // 颜色根据严重程度变化
  const color = severities.every(s => s === 1 || !s) ? '#67c23a'
    : severities.some(s => s >= 3) ? '#f56c6c'
    : '#e6a23c'

  timelineChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const p = params[0]
        const raw = timelineData.value[p.dataIndex]
        return `<b>${p.name}</b><br/>值: <b>${raw.display_value}</b><br/>状态: <b>${severityLabel(raw.severity)}</b>`
      }
    },
    grid: { top: 16, right: 24, bottom: 40, left: 60 },
    xAxis: {
      type: 'category', data: times,
      axisLabel: { fontSize: 11, color: '#666', rotate: timelineDays.value > 1 ? 30 : 0 },
      axisLine: { lineStyle: { color: '#ddd' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 11, color: '#666' },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
    },
    series: [{
      type: 'line',
      data: values,
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      lineStyle: { color, width: 2 },
      itemStyle: { color },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: color + '44' },
          { offset: 1, color: color + '00' },
        ])
      },
    }],
    dataZoom: [{
      type: 'inside',
      start: 0,
      end: times.length > 100 ? 30 : 100,
    }],
  }, true)
}

// 加载单指标时间线
async function loadTimeline() {
  if (!timelineAssetId.value || !timelineCheckItemCode.value) return
  chartLoading.value = true
  try {
    const res = await axios.get(`${API}/monitoring/data/timeline/`, {
      params: {
        asset: timelineAssetId.value,
        check_item_code: timelineCheckItemCode.value,
        days: timelineDays.value,
      }
    })
    timelineData.value = res.data.data || []
    await nextTick()
    renderTimelineChart()
  } catch (e) {
    console.error('加载时间线失败:', e)
    timelineData.value = []
  } finally {
    chartLoading.value = false
  }
}

// 打开单指标时间线
function openTimeline(row) {
  timelineTitle.value = `${row.asset_name} - ${row.check_item_name}`
  timelineAssetId.value = row.asset
  timelineCheckItemCode.value = row.check_item_code
  timelineDays.value = 7
  timelineData.value = []
  timelineVisible.value = true
  nextTick(() => renderTimelineChart())
  loadTimeline()
}

// 渲染多指标对比图
function renderCompareChart() {
  if (!compareChartRef.value || compareSeries.value.length === 0) return
  if (compareChart) {
    compareChart.dispose()
    compareChart = null
  }
  compareChart = echarts.init(compareChartRef.value)

  const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#8e71d8', '#e29b4b', '#56a3da']

  const allTimes = [...new Set(compareSeries.value.flatMap(s => s.times))].sort()

  const series = compareSeries.value.map((s, i) => ({
    name: s.name,
    type: 'line',
    data: allTimes.map(t => {
      const idx = s.times.indexOf(t)
      return idx >= 0 ? s.values[idx] : null
    }),
    smooth: true,
    symbol: 'circle',
    symbolSize: 4,
    lineStyle: { color: colors[i % colors.length], width: 2 },
    itemStyle: { color: colors[i % colors.length] },
  }))

  compareChart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        let html = `<b>${params[0].name}</b><br/>`
        params.forEach(p => {
          if (p.value !== null) {
            html += `${p.marker} ${p.seriesName}: <b>${p.value}</b><br/>`
          }
        })
        return html
      }
    },
    legend: {
      data: compareSeries.value.map(s => s.name),
      bottom: 0,
      textStyle: { fontSize: 12 },
    },
    grid: { top: 16, right: 24, bottom: 48, left: 60 },
    xAxis: {
      type: 'category', data: allTimes,
      axisLabel: { fontSize: 11, color: '#666', rotate: compareDays.value > 1 ? 30 : 0 },
      axisLine: { lineStyle: { color: '#ddd' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { fontSize: 11, color: '#666' },
      splitLine: { lineStyle: { color: '#f0f0f0' } },
    },
    series,
    dataZoom: [{
      type: 'inside',
      start: 0,
      end: allTimes.length > 100 ? 20 : 100,
    }],
  }, true)
}

// 加载多指标对比数据
async function loadCompareChart() {
  if (selectedRows.value.length === 0) return
  chartLoading.value = true
  compareSeries.value = []
  compareTotalPoints.value = 0

  try {
    const promises = selectedRows.value.map(row =>
      axios.get(`${API}/monitoring/data/timeline/`, {
        params: { asset: row.asset, check_item_code: row.check_item_code, days: compareDays.value }
      }).then(res => ({
        name: `${row.asset_name} - ${row.check_item_name}`,
        times: (res.data.data || []).map(d => formatDate(d.recorded_at)),
        values: (res.data.data || []).map(d => d.numeric_value),
        raw: res.data.data || [],
      }))
    )
    const results = await Promise.all(promises)
    compareSeries.value = results
    compareTotalPoints.value = results.reduce((s, r) => s + r.raw.length, 0)
    await nextTick()
    renderCompareChart()
  } catch (e) {
    console.error('加载对比数据失败:', e)
  } finally {
    chartLoading.value = false
  }
}

// 打开多指标对比图
async function openCompareChart() {
  compareVisible.value = true
  await nextTick()
  loadCompareChart()
}

// 加载资产类型列表
async function loadAssetTypes() {
  try {
    const res = await axios.get(`${API}/assets/types/`, { params: { page_size: 100 } })
    assetTypes.value = res.data.results || []
  } catch (e) { console.error('加载资产类型失败:', e) }
}

// 窗口大小变化时重绘图表
function onResize() {
  if (timelineChart) timelineChart.resize()
  if (compareChart) compareChart.resize()
}

onMounted(() => {
  loadOverview()
  loadAssetTypes()
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  if (timelineChart) { timelineChart.dispose(); timelineChart = null }
  if (compareChart) { compareChart.dispose(); compareChart = null }
})
</script>

<style scoped>
.monitoring-center { padding: 20px; }
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}
.page-header h2 { margin: 0; font-size: 18px; font-weight: 500; }
.header-actions { display: flex; align-items: center; }

.overview-row { margin-bottom: 16px; }
.overview-card {
  display: flex; align-items: center; gap: 14px;
  background: #fff; border-radius: 8px; padding: 16px 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
}
.overview-icon {
  width: 48px; height: 48px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  color: #fff; flex-shrink: 0;
}
.overview-icon.blue { background: linear-gradient(135deg, #409eff, #66b1ff); }
.overview-icon.green { background: linear-gradient(135deg, #67c23a, #85ce61); }
.overview-icon.yellow { background: linear-gradient(135deg, #e6a23c, #ebb563); }
.overview-icon.red { background: linear-gradient(135deg, #f56c6c, #f78989); }
.overview-value { font-size: 26px; font-weight: 700; line-height: 1; }
.overview-label { font-size: 13px; color: #888; margin-top: 4px; }

.table-card { margin-top: 0; }

.selection-bar {
  display: flex; align-items: center; gap: 12px;
  padding: 8px 12px; margin-bottom: 10px;
  background: #f0f9eb; border-radius: 6px;
  font-size: 13px; color: #67c23a;
}

.metric-value { font-weight: 600; }
.text-success { color: #67c23a; }
.text-warning { color: #e6a23c; }
.text-danger { color: #f56c6c; }

.timeline-filters { display: flex; align-items: center; margin-bottom: 16px; }

.echarts-container {
  width: 100%; height: 420px;
  border: 1px solid #f0f0f0; border-radius: 8px;
}
</style>
