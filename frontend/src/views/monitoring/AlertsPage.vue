<template>
  <div class="alerts-page">
    <div class="page-header">
      <h2>告警中心</h2>
      <div class="header-actions">
        <el-button type="primary" @click="loadAlerts" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="4">
        <div class="stat-card" :class="{ active: filterStatus === '' }" @click="filterByStatus('')">
          <div class="stat-value">{{ stats.total }}</div>
          <div class="stat-label">全部告警</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card new" :class="{ active: filterStatus === 'NEW' }" @click="filterByStatus('NEW')">
          <div class="stat-value">{{ stats.NEW || 0 }}</div>
          <div class="stat-label">新告警</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card acked" :class="{ active: filterStatus === 'ACKNOWLEDGED' }" @click="filterByStatus('ACKNOWLEDGED')">
          <div class="stat-value">{{ stats.ACKNOWLEDGED || 0 }}</div>
          <div class="stat-label">已确认</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card progress" :class="{ active: filterStatus === 'IN_PROGRESS' }" @click="filterByStatus('IN_PROGRESS')">
          <div class="stat-value">{{ stats.IN_PROGRESS || 0 }}</div>
          <div class="stat-label">处理中</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card resolved" :class="{ active: filterStatus === 'RESOLVED' }" @click="filterByStatus('RESOLVED')">
          <div class="stat-value">{{ stats.RESOLVED || 0 }}</div>
          <div class="stat-label">已解决</div>
        </div>
      </el-col>
      <el-col :span="4">
        <div class="stat-card critical">
          <div class="stat-value">{{ stats.critical || 0 }}</div>
          <div class="stat-label">高危未处理</div>
        </div>
      </el-col>
    </el-row>

    <!-- 筛选栏 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filters">
        <el-form-item label="来源">
          <el-select v-model="filters.source" clearable placeholder="全部来源" style="width:140px" @change="loadAlerts">
            <el-option label="连通性检测" value="PING" />
            <el-option label="巡检结果" value="INSPECTION" />
            <el-option label="本地监控" value="LOCAL" />
            <el-option label="手动" value="MANUAL" />
          </el-select>
        </el-form-item>
        <el-form-item label="严重程度">
          <el-select v-model="filters.severity" clearable placeholder="全部" style="width:120px" @change="loadAlerts">
            <el-option label="信息" :value="1" />
            <el-option label="警告" :value="2" />
            <el-option label="错误" :value="3" />
            <el-option label="严重" :value="4" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filters.search" placeholder="搜索标题/资产" clearable @keyup.enter="loadAlerts" style="width:200px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadAlerts">搜索</el-button>
          <el-button @click="resetFilters">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 告警列表 -->
    <el-card class="table-card">
      <el-table :data="alerts" v-loading="loading" stripe @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="45" />
        <el-table-column label="严重程度" width="80">
          <template #default="{ row }">
            <el-tag :type="getSeverityType(row.severity)" size="small" effect="dark">
              {{ row.severity_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="来源" width="90">
          <template #default="{ row }">
            <el-tag :type="getSourceType(row.source)" size="small">{{ row.source_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="告警标题" min-width="250" show-overflow-tooltip />
        <el-table-column prop="asset_name" label="资产" width="150" show-overflow-tooltip />
        <el-table-column prop="customer_name" label="客户" width="120" show-overflow-tooltip />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="发生时间" width="160">
          <template #default="{ row }">{{ formatTime(row.occurred_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status === 'NEW'" link type="primary" size="small" @click="ackAlert(row)">
              确认
            </el-button>
            <el-button v-if="row.status !== 'RESOLVED' && row.status !== 'CLOSED'" link type="success" size="small" @click="resolveAlert(row)">
              解决
            </el-button>
            <el-button link type="info" size="small" @click="showDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && alerts.length === 0" description="暂无告警数据" />

      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next"
          @size-change="loadAlerts"
          @current-change="loadAlerts"
        />
      </div>
    </el-card>

    <!-- 告警详情弹窗 -->
    <el-dialog v-model="detailVisible" title="告警详情" width="650px" destroy-on-close>
      <template v-if="currentAlert">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="告警标题" :span="2">{{ currentAlert.title }}</el-descriptions-item>
          <el-descriptions-item label="严重程度">
            <el-tag :type="getSeverityType(currentAlert.severity)" effect="dark">{{ currentAlert.severity_display }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="来源">
            <el-tag :type="getSourceType(currentAlert.source)">{{ currentAlert.source_display }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentAlert.status)">{{ currentAlert.status_display }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="告警类型">{{ currentAlert.alert_type || '-' }}</el-descriptions-item>
          <el-descriptions-item label="资产">{{ currentAlert.asset_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="客户">{{ currentAlert.customer_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="指标名称">{{ currentAlert.metric_name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="指标值">{{ currentAlert.metric_value || '-' }}</el-descriptions-item>
          <el-descriptions-item label="阈值">{{ currentAlert.threshold || '-' }}</el-descriptions-item>
          <el-descriptions-item label="发生时间">{{ formatTime(currentAlert.occurred_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="currentAlert.acknowledged_at" label="确认时间">{{ formatTime(currentAlert.acknowledged_at) }}</el-descriptions-item>
          <el-descriptions-item v-if="currentAlert.resolved_at" label="解决时间">{{ formatTime(currentAlert.resolved_at) }}</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">
            <div class="desc-text">{{ currentAlert.description || '-' }}</div>
          </el-descriptions-item>
        </el-descriptions>

        <!-- 告警详情 JSON -->
        <div v-if="currentAlert.alert_data && Object.keys(currentAlert.alert_data).length" class="alert-data-section">
          <div class="section-title">详细数据</div>
          <div class="alert-data-grid">
            <div v-for="(val, key) in currentAlert.alert_data" :key="key" class="data-item">
              <span class="data-key">{{ key }}:</span>
              <span class="data-val">{{ val }}</span>
            </div>
          </div>
        </div>
      </template>

      <template #footer>
        <el-button v-if="currentAlert?.status === 'NEW'" type="primary" @click="ackAlert(currentAlert); detailVisible = false">确认</el-button>
        <el-button v-if="currentAlert && !['RESOLVED','CLOSED'].includes(currentAlert.status)" type="success" @click="resolveAlert(currentAlert); detailVisible = false">解决</el-button>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import axios from '@/utils/axios'

const loading = ref(false)
const alerts = ref([])
const selectedAlerts = ref([])
const detailVisible = ref(false)
const currentAlert = ref(null)
const filterStatus = ref('')

const stats = reactive({
  total: 0, NEW: 0, ACKNOWLEDGED: 0, IN_PROGRESS: 0, RESOLVED: 0, CLOSED: 0, critical: 0
})

const filters = reactive({
  source: '',
  severity: null,
  search: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

// ========== 数据加载 ==========

function extractArray(res) {
  const body = res.data ?? res
  if (Array.isArray(body)) return body
  if (Array.isArray(body.data)) return body.data
  if (Array.isArray(body.results)) return body.results
  return []
}

async function loadStats() {
  try {
    const res = await axios.get('/api/dashboard/alerts/')
    const body = res.data ?? res
    const data = body.data || body
    stats.total = data.total || 0
    stats.critical = data.critical_count || 0
    // by_status
    const bs = data.by_status || {}
    for (const k of ['NEW', 'ACKNOWLEDGED', 'IN_PROGRESS', 'RESOLVED', 'CLOSED']) {
      stats[k] = bs[k] || 0
    }
  } catch (e) {
    console.error('加载告警统计失败:', e)
  }
}

async function loadAlerts() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size,
    }
    if (filterStatus.value) params.status = filterStatus.value
    if (filters.source) params.source = filters.source
    if (filters.severity) params.severity = filters.severity

    const res = await axios.get('/api/alerts/alerts/', { params })
    const body = res.data ?? res
    alerts.value = body.results || body.data?.results || extractArray(res)
    pagination.total = body.count || body.data?.count || 0
  } catch (e) {
    console.error('加载告警失败:', e)
    ElMessage.error('加载告警列表失败')
  } finally {
    loading.value = false
  }
}

function filterByStatus(status) {
  filterStatus.value = status
  pagination.page = 1
  loadAlerts()
}

function resetFilters() {
  filters.source = ''
  filters.severity = null
  filters.search = ''
  filterStatus.value = ''
  pagination.page = 1
  loadAlerts()
}

function handleSelectionChange(selection) {
  selectedAlerts.value = selection
}

// ========== 操作 ==========

async function ackAlert(row) {
  try {
    await axios.post(`/api/alerts/alerts/${row.id}/acknowledge/`)
    ElMessage.success('已确认')
    loadAlerts()
    loadStats()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function resolveAlert(row) {
  try {
    await axios.post(`/api/alerts/alerts/${row.id}/resolve/`)
    ElMessage.success('已解决')
    loadAlerts()
    loadStats()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

function showDetail(row) {
  currentAlert.value = row
  detailVisible.value = true
}

// ========== 工具函数 ==========

function getSeverityType(severity) {
  const s = String(severity || '')
  if (s === '严重' || s === '4') return 'danger'
  if (s === '错误' || s === '3') return 'danger'
  if (s === '警告' || s === '2') return 'warning'
  return 'info'
}

function getSourceType(source) {
  return { 'PING': 'danger', 'INSPECTION': 'warning', 'LOCAL': 'info', 'MANUAL': '' }[source] || 'info'
}

function getStatusType(status) {
  return {
    'NEW': 'danger', 'ACKNOWLEDGED': 'warning', 'IN_PROGRESS': '',
    'RESOLVED': 'success', 'CLOSED': 'info'
  }[status] || 'info'
}

function formatTime(time) {
  if (!time) return '-'
  return new Date(time).toLocaleString('zh-CN')
}

// ========== 生命周期 ==========

onMounted(() => {
  loadStats()
  loadAlerts()
})
</script>

<style scoped>
.alerts-page { padding: 20px; }
.page-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px;
}
.page-header h2 { margin: 0; font-size: 18px; font-weight: 500; }

.stats-row { margin-bottom: 16px; }
.stat-card {
  padding: 16px; text-align: center; border-radius: 10px;
  background: #fff; cursor: pointer; transition: all 0.2s;
  border: 2px solid transparent;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
.stat-card.active { border-color: #409eff; background: #ecf5ff; }
.stat-value { font-size: 28px; font-weight: 700; line-height: 1.2; }
.stat-label { font-size: 13px; color: #909399; margin-top: 4px; }
.stat-card.new .stat-value { color: #f56c6c; }
.stat-card.acked .stat-value { color: #e6a23c; }
.stat-card.progress .stat-value { color: #409eff; }
.stat-card.resolved .stat-value { color: #67c23a; }
.stat-card.critical .stat-value { color: #f56c6c; }

.filter-card { margin-bottom: 16px; }
.table-card { background: white; }

.pagination {
  margin-top: 16px; display: flex; justify-content: flex-end;
}

.desc-text {
  white-space: pre-wrap; word-break: break-all;
  max-height: 200px; overflow-y: auto; line-height: 1.6;
}

.alert-data-section { margin-top: 16px; }
.section-title {
  font-size: 14px; font-weight: 600; color: #303133;
  margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid #ebeef5;
}
.alert-data-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 6px;
  background: #fafafa; padding: 12px; border-radius: 8px;
}
.data-item { font-size: 13px; }
.data-key { color: #909399; margin-right: 4px; }
.data-val { color: #303133; word-break: break-all; }
</style>
