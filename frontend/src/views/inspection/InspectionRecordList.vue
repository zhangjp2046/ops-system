<template>
  <div class="inspection-records">
    <div class="page-header">
      <h2>巡检记录</h2>
      <el-button type="primary" @click="refreshData" :loading="loading">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
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
          <div class="stat-value text-success">{{ stats.pass_count }}</div>
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
      <el-table :data="tableData" v-loading="loading" stripe @row-click="showDetail" style="cursor: pointer">
        <el-table-column prop="created_at" label="巡检时间" width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="asset_name" label="资产" min-width="140" />
        <el-table-column label="检查结果" min-width="200">
          <template #default="{ row }">
            <div class="progress-bar-container">
              <div class="progress-bar">
                <div class="bar-pass" :style="{ width: getPercent(row.pass_checks, row.total_checks) + '%' }"></div>
                <div class="bar-warn" :style="{ width: getPercent(row.warning_checks, row.total_checks) + '%' }"></div>
                <div class="bar-fail" :style="{ width: getPercent(row.fail_checks, row.total_checks) + '%' }"></div>
              </div>
              <div class="progress-labels">
                <span class="pass">✅{{ row.pass_checks }}</span>
                <span class="warn" v-if="row.warning_checks">⚠️{{ row.warning_checks }}</span>
                <span class="fail" v-if="row.fail_checks">❌{{ row.fail_checks }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="结果" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.overall_status)" effect="dark" round>
              {{ row.overall_status_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时" width="80" align="center">
          <template #default="{ row }">
            {{ row.duration ? row.duration + 's' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="summary" label="总结" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="80" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="showDetail(row)">
              <el-icon><View /></el-icon> 详情
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
              <span class="label">资产</span>
              <span class="value">{{ currentRecord.asset_name }}</span>
            </div>
            <div class="overview-item">
              <span class="label">时间</span>
              <span class="value">{{ formatDateTime(currentRecord.created_at) }}</span>
            </div>
            <div class="overview-item">
              <span class="label">耗时</span>
              <span class="value">{{ currentRecord.duration || 0 }}秒</span>
            </div>
            <div class="overview-item">
              <span class="label">结果</span>
              <el-tag :type="getStatusType(currentRecord.overall_status)" effect="dark">
                {{ currentRecord.overall_status_display }}
              </el-tag>
            </div>
          </div>
          <!-- 结果统计条 -->
          <div class="result-bar">
            <div class="bar-item pass" :style="{ flex: currentRecord.pass_checks }">
              <span v-if="currentRecord.pass_checks">{{ currentRecord.pass_checks }} 通过</span>
            </div>
            <div class="bar-item warn" :style="{ flex: currentRecord.warning_checks }">
              <span v-if="currentRecord.warning_checks">{{ currentRecord.warning_checks }} 警告</span>
            </div>
            <div class="bar-item fail" :style="{ flex: currentRecord.fail_checks }">
              <span v-if="currentRecord.fail_checks">{{ currentRecord.fail_checks }} 异常</span>
            </div>
          </div>
        </div>

        <el-divider />

        <!-- 检查项列表 -->
        <h4 class="section-title">检查项明细</h4>
        <div class="result-list">
          <div v-for="r in recordResults" :key="r.id" class="result-item" :class="r.status">
            <div class="result-header">
              <span class="result-icon">
                {{ r.status === 'pass' ? '✅' : r.status === 'warning' ? '⚠️' : '❌' }}
              </span>
              <span class="result-name">{{ r.check_item }}</span>
              <el-tag :type="getResultTagType(r.status)" size="small" round>
                {{ r.status_display }}
              </el-tag>
            </div>
            <div class="result-body">
              <div class="result-value">
                <span class="label">检查值：</span>
                <span class="value">{{ r.result_value }}</span>
              </div>
              <div class="result-message" v-if="r.result_message">
                <span class="label">详情：</span>
                <pre class="message-text">{{ r.result_message }}</pre>
              </div>
              <div class="result-expected" v-if="r.expected_value">
                <span class="label">期望值：</span>
                <span>{{ r.expected_value }}</span>
              </div>
              <div class="result-suggestion" v-if="r.suggestion">
                <el-icon><Warning /></el-icon>
                <span>{{ r.suggestion }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
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
const recordResults = ref([])
const currentRecord = ref(null)
const assets = ref([])

const stats = reactive({ total_records: 0, today_records: 0, pass_count: 0, fail_count: 0, warning_count: 0 })
const pagination = reactive({ page: 1, pageSize: 10, total: 0 })
const filters = reactive({ asset: null, status: null, dateRange: null })

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
    assets.value = res.results || res.data?.results || []
  } catch { /* ignore */ }
}

async function loadStatistics() {
  try {
    const res = await axios.get('/api/inspection/records/statistics/')
    Object.assign(stats, res.data || res)
  } catch { /* ignore */ }
}

async function loadData() {
  loading.value = true
  const params = { page: pagination.page, page_size: pagination.pageSize }
  if (filters.asset) params.asset = filters.asset
  if (filters.status) params.overall_status = filters.status

  try {
    const res = await axios.get('/api/inspection/records/', { params })
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

async function showDetail(row) {
  try {
    const res = await axios.get(`/api/inspection/records/${row.id}/`)
    const data = res.data || res
    currentRecord.value = data
    recordResults.value = data.results || []
    detailVisible.value = true
  } catch {
    ElMessage.error('加载详情失败')
  }
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
