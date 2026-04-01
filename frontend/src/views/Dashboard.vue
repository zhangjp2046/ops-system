<template>
  <div class="dashboard">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2>运维驾驶舱</h2>
      <div class="header-actions">
        <el-button type="primary" @click="refreshAll">
          <el-icon><Refresh /></el-icon>
          刷新数据
        </el-button>
      </div>
    </div>
    
    <!-- 概览统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <div class="stat-card customers" @click="goToAssets">
          <div class="stat-icon">
            <el-icon :size="36"><OfficeBuilding /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.overview.total_customers }}</div>
            <div class="stat-label">客户总数</div>
          </div>
        </div>
      </el-col>
      
      <el-col :span="6">
        <div class="stat-card assets" @click="goToAssets">
          <div class="stat-icon">
            <el-icon :size="36"><Box /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.overview.total_assets }}</div>
            <div class="stat-label">资产总数</div>
          </div>
        </div>
      </el-col>
      
      <el-col :span="6">
        <div class="stat-card online" @click="goToAssets">
          <div class="stat-icon">
            <el-icon :size="36"><CircleCheck /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.overview.online_assets }}</div>
            <div class="stat-label">在线资产</div>
          </div>
        </div>
      </el-col>
      
      <el-col :span="6">
        <div class="stat-card offline" @click="goToAssets">
          <div class="stat-icon">
            <el-icon :size="36"><CircleClose /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.overview.offline_assets }}</div>
            <div class="stat-label">离线资产</div>
          </div>
        </div>
      </el-col>
    </el-row>
    
    <!-- 第二行统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <div class="stat-card alerts" @click="goToAlerts">
          <div class="stat-icon">
            <el-icon :size="36"><Warning /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ alertStats.unhandled_count || 0 }}</div>
            <div class="stat-label">待处理告警</div>
          </div>
        </div>
      </el-col>
      
      <el-col :span="6">
        <div class="stat-card monitoring" @click="goToMonitoring">
          <div class="stat-icon">
            <el-icon :size="36"><Monitor /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ monitoringStats.availability_rate || 0 }}%</div>
            <div class="stat-label">监控可用率</div>
          </div>
        </div>
      </el-col>
      
      <el-col :span="6">
        <div class="stat-card inspection" @click="goToInspection">
          <div class="stat-icon">
            <el-icon :size="36"><DocumentChecked /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ inspectionStats.today_passed || 0 }}</div>
            <div class="stat-label">今日巡检通过</div>
          </div>
        </div>
      </el-col>
      
      <el-col :span="6">
        <div class="stat-card tasks" @click="goToTasks">
          <div class="stat-icon">
            <el-icon :size="36"><Timer /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ taskStats.task_enabled || 0 }}</div>
            <div class="stat-label">启用的任务</div>
          </div>
        </div>
      </el-col>
    </el-row>
    
    <!-- 图表区域 -->
    <el-row :gutter="20" class="charts-row">
      <!-- 资产分布饼图 -->
      <el-col :span="8">
        <el-card class="chart-card">
          <template #header>
            <span>资产分布</span>
          </template>
          <div ref="typeChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      
      <!-- 资产状态分布 -->
      <el-col :span="8">
        <el-card class="chart-card">
          <template #header>
            <span>资产状态</span>
          </template>
          <div ref="statusChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      
      <!-- 客户资产统计 -->
      <el-col :span="8">
        <el-card class="chart-card">
          <template #header>
            <span>客户资产统计</span>
          </template>
          <div ref="customerChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 详细信息区域 -->
    <el-row :gutter="20" class="details-row">
      <!-- 告警信息 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>待处理告警</span>
              <el-button type="primary" link @click="goToAlerts">查看全部</el-button>
            </div>
          </template>
          <el-table :data="alertStats.unhandled_alerts || []" stripe>
            <el-table-column prop="title" label="告警标题" />
            <el-table-column prop="severity" label="严重程度" width="100">
              <template #default="{ row }">
                <el-tag :type="getSeverityType(row.severity)">{{ row.severity }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="asset_name" label="资产" width="150" />
            <el-table-column prop="occurred_at" label="时间" width="150">
              <template #default="{ row }">
                {{ formatTime(row.occurred_at) }}
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!alertStats.unhandled_alerts?.length" description="暂无待处理告警" />
        </el-card>
      </el-col>
      
      <!-- 巡检记录 -->
      <el-col :span="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近巡检</span>
              <el-button type="primary" link @click="goToInspection">查看全部</el-button>
            </div>
          </template>
          <el-table :data="inspectionStats.recent_inspections || []" stripe>
            <el-table-column prop="asset_name" label="资产" />
            <el-table-column prop="overall_status" label="结果" width="80">
              <template #default="{ row }">
                <el-tag :type="getInspectionStatusType(row.overall_status)">{{ row.overall_status_display || row.overall_status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="检查项" width="120">
              <template #default="{ row }">
                <span class="inspection-result">
                  <span class="passed">{{ row.pass_checks }}</span> /
                  <span class="warning">{{ row.warning_checks }}</span> /
                  <span class="failed">{{ row.fail_checks }}</span>
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="时间" width="160">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
          </el-table>
          <el-empty v-if="!inspectionStats.recent_inspections?.length" description="暂无巡检记录" />
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 任务执行情况 -->
    <el-row :gutter="20" class="details-row">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近任务执行</span>
              <el-button type="primary" link @click="goToTasks">查看全部</el-button>
            </div>
          </template>
          <el-table :data="taskStats.recent_executions || []" stripe>
            <el-table-column prop="task_name" label="任务名称" />
            <el-table-column prop="task_type" label="任务类型" width="120">
              <template #default="{ row }">
                <el-tag>{{ getTaskTypeName(row.task_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getExecutionStatusType(row.status)">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="start_time" label="开始时间" width="180">
              <template #default="{ row }">
                {{ formatTime(row.start_time) }}
              </template>
            </el-table-column>
            <el-table-column prop="duration" label="耗时" width="100">
              <template #default="{ row }">
                {{ row.duration ? row.duration + 'ms' : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="error_message" label="错误信息" show-overflow-tooltip />
          </el-table>
          <el-empty v-if="!taskStats.recent_executions?.length" description="暂无执行记录" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { 
  OfficeBuilding, Box, CircleCheck, CircleClose, 
  Warning, Monitor, DocumentChecked, Timer, Refresh 
} from '@element-plus/icons-vue'
import { 
  getDashboardStats, getMonitoringStats, getAlertStats, 
  getInspectionStats, getTaskStats 
} from '@/api/dashboard'
import api from '@/api/index'
import * as echarts from 'echarts'

const router = useRouter()

// 统计数据
const stats = reactive({
  overview: {
    total_customers: 0,
    total_assets: 0,
    active_assets: 0,
    online_assets: 0,
    offline_assets: 0,
  }
})

const alertStats = reactive({
  unhandled_count: 0,
  unhandled_alerts: [],
})

const monitoringStats = reactive({
  availability_rate: 0,
})

const inspectionStats = reactive({
  today_passed: 0,
  recent_inspections: [],
})

const taskStats = reactive({
  task_enabled: 0,
  recent_executions: [],
})

// 图表引用
const typeChartRef = ref(null)
const statusChartRef = ref(null)
const customerChartRef = ref(null)

let typeChart = null
let statusChart = null
let customerChart = null

// 加载所有数据
async function loadAllData() {
  await Promise.all([
    loadDashboardStats(),
    loadMonitoringStats(),
    loadAlertStats(),
    loadInspectionStats(),
    loadTaskStats(),
  ])
  await nextTick()
  initCharts()
}

// 加载驾驶舱统计
async function loadDashboardStats() {
  try {
    const res = await getDashboardStats()
    if (res.success) {
      Object.assign(stats, res.data)
    }
  } catch (error) {
    console.error('加载驾驶舱统计失败:', error)
  }
}

// 加载监控统计
async function loadMonitoringStats() {
  try {
    const res = await getMonitoringStats()
    if (res.success) {
      monitoringStats.availability_rate = res.data.recent_24h_stats?.availability_rate || 0
    }
  } catch (error) {
    console.error('加载监控统计失败:', error)
  }
}

// 加载告警统计
async function loadAlertStats() {
  try {
    const res = await getAlertStats()
    if (res.success) {
      alertStats.unhandled_count = (res.data.by_status?.open || 0) + (res.data.by_status?.acknowledged || 0)
      alertStats.unhandled_alerts = res.data.unhandled_alerts || []
    }
  } catch (error) {
    console.error('加载告警统计失败:', error)
  }
}

// 加载巡检统计
async function loadInspectionStats() {
  try {
    const res = await getInspectionStats()
    if (res.success) {
      inspectionStats.today_passed = res.data.today_stats?.passed || 0
      inspectionStats.recent_inspections = res.data.recent_inspections || []
    }
  } catch (error) {
    console.error('加载巡检统计失败:', error)
  }
}

// 加载任务统计
async function loadTaskStats() {
  try {
    const res = await getTaskStats()
    if (res.success) {
      taskStats.task_enabled = res.data.task_stats?.enabled || 0
      taskStats.recent_executions = res.data.recent_executions || []
    }
  } catch (error) {
    console.error('加载任务统计失败:', error)
  }
}

// 刷新所有数据
async function refreshAll() {
  // 先ping检测所有资产，刷新在线状态
  try {
    await api.post('/dashboard/health/')
  } catch (e) {
    console.error('刷新资产状态失败:', e)
  }
  await loadAllData()
}

// 初始化图表
function initCharts() {
  // 资产类型分布图
  if (typeChartRef.value && stats.type_distribution?.length) {
    if (!typeChart) {
      typeChart = echarts.init(typeChartRef.value)
    }
    const typeData = stats.type_distribution.map(item => ({
      name: item.asset_type__type_name,
      value: item.count
    }))
    typeChart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, formatter: '{b}: {c}' },
        data: typeData,
        color: ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399']
      }]
    })
  }
  
  // 资产状态分布图
  if (statusChartRef.value && stats.status_distribution?.length) {
    if (!statusChart) {
      statusChart = echarts.init(statusChartRef.value)
    }
    const statusData = stats.status_distribution.map(item => ({
      name: getStatusText(item.status),
      value: item.count
    }))
    statusChart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, formatter: '{b}: {c}' },
        data: statusData,
        color: ['#67c23a', '#909399', '#e6a23c', '#f56c6c']
      }]
    })
  }
  
  // 客户资产分布图
  if (customerChartRef.value && stats.customer_distribution?.length) {
    if (!customerChart) {
      customerChart = echarts.init(customerChartRef.value)
    }
    const customerData = stats.customer_distribution.map(item => ({
      name: item.customer__customer_name,
      value: item.count
    }))
    customerChart.setOption({
      tooltip: { trigger: 'item' },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: { borderRadius: 10, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, formatter: '{b}: {c}' },
        data: customerData,
        color: ['#409eff', '#67c23a']
      }]
    })
  }
}

// 页面跳转
function goToAssets() {
  router.push('/assets')
}

function goToAlerts() {
  router.push('/monitoring/alerts')
}

function goToMonitoring() {
  router.push('/monitoring')
}

function goToInspection() {
  router.push('/inspection')
}

function goToTasks() {
  router.push('/scheduler')
}

// 工具函数
function getSeverityType(severity) {
  const s = (severity || '').toUpperCase()
  const types = { 'CRITICAL': 'danger', 'HIGH': 'danger', 'MEDIUM': 'warning', 'LOW': 'info', 'WARNING': 'warning' }
  return types[s] || 'info'
}

function getStatusType(status) {
  const types = { 'COMPLETED': 'success', 'RUNNING': 'primary', 'FAILED': 'danger', 'PENDING': 'info' }
  return types[status] || 'info'
}

function getInspectionStatusType(status) {
  const types = { 'pass': 'success', 'warning': 'warning', 'fail': 'danger', 'error': 'danger' }
  return types[status] || 'info'
}

function getStatusText(status) {
  const texts = { 'ACTIVE': '活跃', 'INACTIVE': '停用', 'MAINTENANCE': '维护中', 'DECOMMISSIONED': '已退役' }
  return texts[status] || status
}

function getTaskTypeName(type) {
  const names = {
    'monitoring': '监控',
    'inspection': '巡检',
    'status_refresh': '状态刷新',
    'cleanup': '清理',
    'report': '报表'
  }
  return names[type] || type
}

function getExecutionStatusType(status) {
  const types = { 'success': 'success', 'failed': 'danger', 'running': 'primary' }
  return types[status] || 'info'
}

function formatTime(time) {
  if (!time) return '-'
  const date = new Date(time)
  return date.toLocaleString('zh-CN')
}

// 监听窗口变化
function handleResize() {
  typeChart?.resize()
  statusChart?.resize()
  customerChart?.resize()
}

let refreshInterval = null

onMounted(() => {
  loadAllData()
  // 每30秒自动刷新数据
  refreshInterval = setInterval(loadAllData, 30000)
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
  window.removeEventListener('resize', handleResize)
  typeChart?.dispose()
  statusChart?.dispose()
  customerChart?.dispose()
})
</script>

<style scoped>
.dashboard {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 60px);
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  padding: 20px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  cursor: pointer;
  transition: all 0.3s;
}

.stat-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 16px;
  color: white;
}

.stat-card.customers .stat-icon { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
.stat-card.assets .stat-icon { background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%); }
.stat-card.online .stat-icon { background: linear-gradient(135deg, #67c23a 0%, #85ce61 100%); }
.stat-card.offline .stat-icon { background: linear-gradient(135deg, #f56c6c 0%, #f78989 100%); }
.stat-card.alerts .stat-icon { background: linear-gradient(135deg, #e6a23c 0%, #ebb563 100%); }
.stat-card.monitoring .stat-icon { background: linear-gradient(135deg, #909399 0%, #a6a9ad 100%); }
.stat-card.inspection .stat-icon { background: linear-gradient(135deg, #36cfc9 0%, #5bc0de 100%); }
.stat-card.tasks .stat-icon { background: linear-gradient(135deg, #ba55d3 0%, #d27cd8 100%); }

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 4px;
}

.charts-row {
  margin-bottom: 20px;
}

.chart-card {
  height: 100%;
}

.chart-container {
  height: 260px;
  width: 100%;
}

.details-row {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.inspection-result .passed { color: #67c23a; font-weight: bold; }
.inspection-result .warning { color: #e6a23c; font-weight: bold; }
.inspection-result .failed { color: #f56c6c; font-weight: bold; }
</style>
