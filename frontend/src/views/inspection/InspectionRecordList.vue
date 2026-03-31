<template>
  <div class="inspection-records">
    <div class="page-header">
      <h2>巡检记录</h2>
      <el-button type="primary" @click="refreshData">
        <el-icon><Refresh /></el-icon> 刷新
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.total_records }}</div>
          <div class="stat-label">巡检总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.today_records }}</div>
          <div class="stat-label">今日巡检</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card success">
          <div class="stat-value">{{ stats.pass_count }}</div>
          <div class="stat-label">合格</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card danger">
          <div class="stat-value">{{ stats.fail_count }}</div>
          <div class="stat-label">不合格</div>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="table-card">
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="created_at" label="巡检时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="asset_name" label="资产" min-width="150" />
        <el-table-column prop="total_checks" label="检查项" width="100" align="center" />
        <el-table-column prop="pass_checks" label="通过" width="80" align="center">
          <template #default="{ row }">
            <span class="text-success">{{ row.pass_checks }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="warning_checks" label="警告" width="80" align="center">
          <template #default="{ row }">
            <span class="text-warning">{{ row.warning_checks }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="fail_checks" label="不合格" width="80" align="center">
          <template #default="{ row }">
            <span class="text-danger">{{ row.fail_checks }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="overall_status" label="结果" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.overall_status)">
              {{ row.overall_status_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="耗时" width="100">
          <template #default="{ row }">
            {{ row.duration ? row.duration + '秒' : '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="executor_name" label="执行人" width="100" />
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="showDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.pageSize"
          :total="pagination.total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog v-model="detailVisible" title="巡检详情" width="900px">
      <div v-if="currentRecord" class="record-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="资产">{{ currentRecord.asset_name }}</el-descriptions-item>
          <el-descriptions-item label="巡检时间">
            {{ formatDateTime(currentRecord.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="总检查项">{{ currentRecord.total_checks }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentRecord.overall_status)">
              {{ currentRecord.overall_status_display }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="耗时">{{ currentRecord.duration }}秒</el-descriptions-item>
          <el-descriptions-item label="执行人">{{ currentRecord.executor_name || '-' }}</el-descriptions-item>
        </el-descriptions>

        <h4>巡检结果</h4>
        <el-table :data="recordResults" stripe size="small">
          <el-table-column prop="check_item" label="检查项" width="150" />
          <el-table-column prop="result_value" label="检查值" width="150" />
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getResultStatusType(row.status)" size="small">
                {{ row.status_display }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="result_message" label="结果说明" />
          <el-table-column prop="suggestion" label="建议" />
        </el-table>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
import axios from '@/utils/axios'

const loading = ref(false)
const detailVisible = ref(false)
const tableData = ref([])
const recordResults = ref([])
const currentRecord = ref(null)

const stats = reactive({
  total_records: 0,
  today_records: 0,
  pass_count: 0,
  fail_count: 0
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

function formatDateTime(datetime) {
  if (!datetime) return '-'
  const d = new Date(datetime)
  return d.toLocaleString('zh-CN')
}

function getStatusType(status) {
  const types = {
    pass: 'success',
    warning: 'warning',
    fail: 'danger',
    skip: 'info'
  }
  return types[status] || 'info'
}

function getResultStatusType(status) {
  return getStatusType(status)
}

function loadStatistics() {
  axios.get('/api/inspection/records/statistics/')
    .then(res => {
      Object.assign(stats, res.data || res)
    })
    .catch(() => {
      // ignore
    })
}

function loadData() {
  loading.value = true
  const params = {
    page: pagination.page,
    page_size: pagination.pageSize
  }
  
  axios.get('/api/inspection/records/', { params })
    .then(res => {
      tableData.value = res.results || []
      pagination.total = res.count || 0
    })
    .catch(() => {
      ElMessage.error('加载数据失败')
    })
    .finally(() => {
      loading.value = false
    })
}

function refreshData() {
  loadStatistics()
  loadData()
}

function handleSizeChange() {
  pagination.page = 1
  loadData()
}

function handlePageChange() {
  loadData()
}

function showDetail(row) {
  currentRecord.value = row
  axios.get(`/api/inspection/records/${row.id}/`)
    .then(res => {
      currentRecord.value = res.data || res
      recordResults.value = res.results || res.data?.results || []
      detailVisible.value = true
    })
    .catch(() => {
      ElMessage.error('加载详情失败')
    })
}

onMounted(() => {
  loadStatistics()
  loadData()
})
</script>

<style scoped>
.inspection-records {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-card.success .stat-value {
  color: #67c23a;
}

.stat-card.danger .stat-value {
  color: #f56c6c;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #409eff;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-top: 8px;
}

.table-card {
  background: white;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.text-success {
  color: #67c23a;
}

.text-warning {
  color: #e6a23c;
}

.text-danger {
  color: #f56c6c;
}

.record-detail h4 {
  margin: 20px 0 10px;
  font-size: 16px;
}
</style>
