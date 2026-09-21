<template>
  <div class="inspection-records">
    <div class="page-header">
      <h2>巡检记录</h2>
      <div>
        <el-button type="warning" @click="showGenerateReport" style="margin-right:8px">
          <el-icon><Document /></el-icon> 生成巡检报告
        </el-button>
        <el-button type="danger" @click="handleBatchDelete" :disabled="!selectedRows.length">
          <el-icon><Delete /></el-icon> 批量删除{{ selectedRows.length ? `(${selectedRows.length})` : '' }}
        </el-button>
        <el-button type="primary" @click="refreshData" :loading="loading">
          <el-icon><Refresh /></el-icon> 刷新
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="16" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value text-primary">{{ stats.total_records }}</div>
          <div class="stat-label">巡检总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value text-info">{{ stats.today_records }}</div>
          <div class="stat-label">今日巡检</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value text-success">{{ stats.qualified_count }}</div>
          <div class="stat-label">合格</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value text-danger">{{ stats.fail_count }}</div>
          <div class="stat-label">不合格</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选栏 -->
    <el-card class="filter-card">
      <el-form :inline="true" class="filter-form">
        <el-form-item label="资产">
          <el-select v-model="filters.asset" placeholder="全部资产" clearable @change="handleFilter" style="width: 200px">
            <el-option v-for="a in assets" :key="a.id" :label="a.asset_name" :value="a.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filters.status" placeholder="全部状态" clearable @change="handleFilter" style="width: 130px">
            <el-option label="通过" value="pass" />
            <el-option label="警告" value="warning" />
            <el-option label="不合格" value="fail" />
          </el-select>
        </el-form-item>
        <el-form-item label="时间">
          <el-date-picker v-model="filters.dateRange" type="daterange" range-separator="至"
            start-placeholder="开始日期" end-placeholder="结束日期"
            @change="handleFilter" style="width: 260px" />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 记录列表 -->
    <el-card class="table-card">
      <el-table :data="tableData" v-loading="loading" stripe @row-click="showDetail" style="cursor: pointer" @selection-change="onSelectionChange">
        <el-table-column type="selection" width="40" />
        <el-table-column prop="created_at" label="巡检时间" width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="name" label="巡检名称" min-width="160" show-overflow-tooltip />
        <el-table-column prop="inspection_type" label="类型" width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.inspection_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="检查结果" min-width="200">
          <template #default="{ row }">
            <div class="progress-bar-container">
              <div class="progress-bar">
                <div class="bar-pass" :style="{ width: getPercent(row.passed_items, row.total_items) + '%' }"></div>
                <div class="bar-warn" :style="{ width: getPercent(row.warning_items, row.total_items) + '%' }"></div>
                <div class="bar-fail" :style="{ width: getPercent(row.failed_items, row.total_items) + '%' }"></div>
              </div>
              <div class="progress-labels">
                <span class="pass">✅{{ row.passed_items || 0 }}</span>
                <span class="warn" v-if="row.warning_items">⚠️{{ row.warning_items }}</span>
                <span class="fail" v-if="row.failed_items">❌{{ row.failed_items }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'COMPLETED' ? 'success' : row.status === 'FAILED' ? 'danger' : 'info'" effect="dark" round>
              {{ row.status === 'COMPLETED' ? '完成' : row.status === 'FAILED' ? '失败' : row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration_ms" label="耗时" width="80" align="center">
          <template #default="{ row }">
            {{ row.duration_ms ? (row.duration_ms / 1000).toFixed(1) + 's' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="总结" min-width="180" show-overflow-tooltip />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="showDetail(row)">
              <el-icon><View /></el-icon> 详情
            </el-button>
            <el-button link type="danger" @click.stop="handleDelete(row)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination v-model:current-page="pagination.page" v-model:page-size="pagination.pageSize"
          :total="pagination.total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next"
          @size-change="loadData" @current-change="loadData" />
      </div>
    </el-card>

    <!-- 详情弹窗 -->
    <el-dialog v-model="detailVisible" title="巡检报告详情" width="950px" top="5vh" destroy-on-close>
      <div v-if="currentRecord" class="record-detail">
        <!-- 概览 -->
        <div class="detail-header">
          <div class="detail-overview">
            <div class="overview-item">
              <span class="label">巡检名称</span>
              <span class="value">{{ currentRecord.name }}</span>
            </div>
            <div class="overview-item">
              <span class="label">时间</span>
              <span class="value">{{ formatDateTime(currentRecord.created_at) }}</span>
            </div>
            <div class="overview-item">
              <span class="label">耗时</span>
              <span class="value">{{ currentRecord.duration_ms ? (currentRecord.duration_ms / 1000).toFixed(1) + '秒' : '-' }}</span>
            </div>
            <div class="overview-item">
              <span class="label">状态</span>
              <el-tag :type="currentRecord.status === 'COMPLETED' ? 'success' : currentRecord.status === 'FAILED' ? 'danger' : 'info'" effect="dark">
                {{ currentRecord.status === 'COMPLETED' ? '完成' : currentRecord.status === 'FAILED' ? '失败' : currentRecord.status }}
              </el-tag>
            </div>
          </div>
          <!-- 结果统计条 -->
          <div class="result-bar">
            <div class="bar-item pass" :style="{ flex: currentRecord.passed_items || 0 }">
              <span v-if="currentRecord.passed_items">{{ currentRecord.passed_items }} 通过</span>
            </div>
            <div class="bar-item warn" :style="{ flex: currentRecord.warning_items || 0 }">
              <span v-if="currentRecord.warning_items">{{ currentRecord.warning_items }} 警告</span>
            </div>
            <div class="bar-item fail" :style="{ flex: currentRecord.failed_items || 0 }">
              <span v-if="currentRecord.failed_items">{{ currentRecord.failed_items }} 异常</span>
            </div>
          </div>
        </div>

        <el-divider />

        <!-- 检查项列表 -->
        <h4 class="section-title">检查项明细</h4>
        <div class="result-list">
          <div v-for="(r, idx) in (currentRecord.items || [])" :key="idx" class="result-item" :class="r.result.toLowerCase()">
            <div class="result-header">
              <span class="result-icon">
                {{ r.result === 'PASS' ? '✅' : r.result === 'WARNING' ? '⚠️' : '❌' }}
              </span>
              <span class="result-name">{{ r.item_name }}</span>
              <el-tag :type="getResultTagType(r.result === 'PASS' ? 'pass' : r.result === 'WARNING' ? 'warning' : 'fail')" size="small" round>
                {{ r.result === 'PASS' ? '通过' : r.result === 'WARNING' ? '警告' : '失败' }}
              </el-tag>
            </div>
            <div class="result-body">
              <div class="result-value">
                <span class="label">实际值：</span>
                <span class="value">{{ r.actual_value }}</span>
              </div>
              <div class="result-message" v-if="r.message">
                <span class="label">详情：</span>
                <pre class="message-text">{{ r.message }}</pre>
              </div>
              <div class="result-expected" v-if="r.expected_value">
                <span class="label">期望值：</span>
                <span>{{ r.expected_value }}</span>
              </div>
            </div>
          </div>
          <div v-if="!currentRecord.items || currentRecord.items.length === 0" style="color: #999; text-align: center; padding: 20px">
            暂无检查项数据
          </div>
        </div>
      </div>
    </el-dialog>

    <!-- 生成巡检报告弹窗 -->
    <el-dialog v-model="reportDialogVisible" title="生成巡检报告" width="500px">
      <el-form label-width="100px">
        <el-form-item label="时间范围" required>
          <el-date-picker v-model="reportDateRange" type="daterange" range-separator="至"
            start-placeholder="开始日期" end-placeholder="结束日期" style="width:100%" />
        </el-form-item>
        <el-alert type="info" :closable="false" show-icon>
          <template #title>
            将汇总该时间段内所有巡检记录及其检查项详情，生成一个 Markdown 格式的巡检报告文件
          </template>
        </el-alert>
      </el-form>
      <template #footer>
        <el-button @click="reportDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="downloadReport" :loading="reportLoading">
          <el-icon><Download /></el-icon> 下载报告
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, View, Warning } from '@element-plus/icons-vue'
import axios from '@/utils/axios'

const loading = ref(false)
const detailVisible = ref(false)
const tableData = ref([])
const currentRecord = ref(null)
const assets = ref([])
const selectedRows = ref([])

const stats = reactive({ total_records: 0, today_records: 0, pass_count: 0, fail_count: 0, warning_count: 0, qualified_count: 0 })
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const filters = reactive({ asset: null, status: null, dateRange: null })

// 生成巡检报告
const reportDialogVisible = ref(false)
const reportDateRange = ref(null)
const reportLoading = ref(false)

function formatDate(d) {
  if (!d) return ''
  const dt = new Date(d)
  return dt.getFullYear() + '-' +
    String(dt.getMonth() + 1).padStart(2, '0') + '-' +
    String(dt.getDate()).padStart(2, '0')
}

function formatDateTime(dt) {
  if (!dt) return '-'
  return new Date(dt).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function getPercent(part, total) {
  if (!total) return 0
  return Math.round((part / total) * 100)
}

function getStatusType(status) {
  return { pass: 'success', warning: 'warning', fail: 'danger', skip: 'info' }[status] || 'info'
}

function getResultTagType(status) {
  return { pass: 'success', warning: 'warning', fail: 'danger' }[status] || 'info'
}

async function loadAssets() {
  try {
    const res = await axios.get('/api/assets/assets/', { params: { page_size: 100 } })
    if (Array.isArray(res)) {
      assets.value = res
    } else if (Array.isArray(res.data)) {
      assets.value = res.data
    } else {
      assets.value = res.results || res.data?.results || []
    }
  } catch { /* ignore */ }
}

function showGenerateReport() {
  // 如果筛选器已有日期范围，自动带入
  if (filters.dateRange && filters.dateRange.length === 2) {
    reportDateRange.value = [filters.dateRange[0], filters.dateRange[1]]
  } else {
    reportDateRange.value = null
  }
  reportDialogVisible.value = true
}

async function downloadReport() {
  if (!reportDateRange.value || reportDateRange.value.length !== 2) {
    ElMessage.warning('请选择时间范围')
    return
  }
  reportLoading.value = true
  try {
    const dateFrom = formatDate(reportDateRange.value[0])
    const dateTo = formatDate(reportDateRange.value[1]) + ' 23:59:59'

    // 直接通过浏览器下载
    const link = document.createElement('a')
    link.href = `/api/inspection/inspections/generate-report/?date_from=${encodeURIComponent(dateFrom)}&date_to=${encodeURIComponent(dateTo)}`
    link.download = `巡检报告_${dateFrom}_${formatDate(reportDateRange.value[1])}.html`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)

    ElMessage.success('巡检报告下载中')
    reportDialogVisible.value = false
  } catch (e) {
    ElMessage.error(`生成报告失败: ${e.message || ''}`)
  } finally { reportLoading.value = false }
}

async function loadStatistics() {
  // 从已加载的数据中统计
  try {
    const res = await axios.get('/api/inspection/inspections/', { params: { page_size: 1 } })
    const totalCount = res.count || res.data?.count || 0
    // 获取所有记录（用于今日/通过/失败统计）
    const allRes = await axios.get('/api/inspection/inspections/', { params: { page_size: totalCount > 1000 ? 1000 : totalCount } })
    const all = allRes.results || allRes.data?.results || []
    const today = new Date().toISOString().slice(0, 10)
    stats.total_records = totalCount
    stats.today_records = all.filter(r => r.created_at && r.created_at.slice(0, 10) === today).length
    stats.pass_count = all.filter(r => r.status === 'COMPLETED' && r.failed_items === 0).length
    stats.fail_count = all.filter(r => r.status === 'FAILED' || r.failed_items > 0).length
    stats.qualified_count = stats.pass_count
  } catch { /* ignore */ }
}

async function loadData() {
  loading.value = true
  const params = { page: pagination.page, page_size: pagination.pageSize }
  if (filters.asset) params.asset_id = filters.asset
  if (filters.status) params.status = filters.status
  if (filters.dateRange && filters.dateRange.length === 2) {
    params.date_from = formatDate(filters.dateRange[0])
    params.date_to = formatDate(filters.dateRange[1]) + ' 23:59:59'
  }

  try {
    const res = await axios.get('/api/inspection/inspections/', { params })
    tableData.value = res.results || res.data?.results || []
    pagination.total = res.count || res.data?.count || 0
  } catch {
    ElMessage.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

function handleFilter() {
  pagination.page = 1
  loadData()
}

function refreshData() {
  loadStatistics()
  loadData()
}

function onSelectionChange(selection) {
  selectedRows.value = selection
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除巡检记录「${row.asset_name}」(${formatDateTime(row.created_at)})吗？此操作不可恢复。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await axios.delete(`/api/inspection/inspections/${row.id}/`)
    ElMessage.success('删除成功')
    loadData()
    loadStatistics()
  } catch (error) {
    if (error !== 'cancel') ElMessage.error('删除失败')
  }
}

async function handleBatchDelete() {
  if (!selectedRows.value.length) return
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedRows.value.length} 条巡检记录吗？此操作不可恢复。`,
      '确认批量删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    const ids = selectedRows.value.map(r => r.id)
    const res = await axios.post('/api/inspection/inspections/batch-delete/', { ids })
    ElMessage.success(`已删除 ${res.data.deleted || ids.length} 条`)
    selectedRows.value = []
    loadData()
    loadStatistics()
  } catch (error) {
    if (error !== 'cancel') {
      const msg = error?.response?.data?.error || error.message || '批量删除失败'
      ElMessage.error(msg)
    }
  }
}

async function showDetail(row) {
  currentRecord.value = { ...row }
  detailVisible.value = true
}

onMounted(() => {
  loadAssets()
  loadStatistics()
  loadData()
})
</script>

<style scoped>
.inspection-records { padding: 20px; }

.page-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
}
.page-header h2 { margin: 0; font-size: 18px; font-weight: 500; }

.stats-row { margin-bottom: 16px; }
.stat-card { text-align: center; }
.stat-value { font-size: 28px; font-weight: bold; }
.stat-label { font-size: 13px; color: #909399; margin-top: 6px; }
.text-primary { color: #409eff; }
.text-info { color: #909399; }
.text-success { color: #67c23a; }
.text-danger { color: #f56c6c; }

.filter-card { margin-bottom: 16px; }
.filter-card :deep(.el-card__body) { padding: 12px 16px; }

.table-card { background: white; }

/* 进度条 */
.progress-bar-container { display: flex; align-items: center; gap: 8px; }
.progress-bar {
  flex: 1; height: 10px; border-radius: 5px; background: #f0f0f0;
  display: flex; overflow: hidden;
}
.bar-pass { background: #67c23a; transition: width 0.3s; }
.bar-warn { background: #e6a23c; transition: width 0.3s; }
.bar-fail { background: #f56c6c; transition: width 0.3s; }
.progress-labels { display: flex; gap: 6px; font-size: 12px; white-space: nowrap; }
.progress-labels .pass { color: #67c23a; }
.progress-labels .warn { color: #e6a23c; }
.progress-labels .fail { color: #f56c6c; }

.pagination { margin-top: 16px; display: flex; justify-content: flex-end; }

/* 详情弹窗 */
.record-detail { max-height: 70vh; overflow-y: auto; }

.detail-header { margin-bottom: 16px; }
.detail-overview { display: flex; gap: 24px; margin-bottom: 12px; flex-wrap: wrap; }
.overview-item { display: flex; align-items: center; gap: 8px; }
.overview-item .label { color: #909399; font-size: 13px; }
.overview-item .value { font-weight: 500; }

.result-bar {
  display: flex; height: 28px; border-radius: 4px; overflow: hidden; font-size: 12px;
}
.bar-item {
  display: flex; align-items: center; justify-content: center; color: white; min-width: 0;
}
.bar-item.pass { background: #67c23a; }
.bar-item.warn { background: #e6a23c; }
.bar-item.fail { background: #f56c6c; }
.bar-item span { padding: 0 8px; white-space: nowrap; }

.section-title { font-size: 15px; font-weight: 500; margin: 16px 0 12px; }

/* 检查项列表 */
.result-list { display: flex; flex-direction: column; gap: 8px; }
.result-item {
  border: 1px solid #ebeef5; border-radius: 6px; padding: 12px 16px;
  transition: box-shadow 0.2s;
}
.result-item:hover { box-shadow: 0 2px 8px rgba(0,0,0,0.08); }
.result-item.fail { border-left: 3px solid #f56c6c; }
.result-item.warning { border-left: 3px solid #e6a23c; }
.result-item.pass { border-left: 3px solid #67c23a; }

.result-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.result-icon { font-size: 16px; }
.result-name { font-weight: 500; flex: 1; }

.result-body { padding-left: 28px; font-size: 13px; color: #606266; }
.result-body .label { color: #909399; }
.result-value { margin-bottom: 4px; }
.result-value .value { font-weight: 500; color: #303133; }

.result-message { margin-bottom: 4px; }
.message-text {
  margin: 4px 0 0; padding: 6px 10px; background: #f5f7fa; border-radius: 4px;
  font-size: 12px; white-space: pre-wrap; word-break: break-all; font-family: inherit;
  max-height: 120px; overflow-y: auto;
}

.result-suggestion {
  display: flex; align-items: flex-start; gap: 4px; margin-top: 6px;
  color: #e6a23c; font-size: 12px;
}

.tr { text-align: right; }
</style>
