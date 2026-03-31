<template>
  <div class="work-order-list">
    <div class="page-header">
      <h2>工单管理</h2>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon> 新建工单
      </el-button>
    </div>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.total || 0 }}</div>
          <div class="stat-label">工单总数</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.today || 0 }}</div>
          <div class="stat-label">今日新增</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card">
          <div class="stat-value">{{ stats.pending || 0 }}</div>
          <div class="stat-label">待处理</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="stat-card warning">
          <div class="stat-value">{{ workOrders.filter(w => w.status === 1).length || 0 }}</div>
          <div class="stat-label">处理中</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选表单 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="全部" clearable>
            <el-option label="新建" :value="0" />
            <el-option label="处理中" :value="1" />
            <el-option label="搁置" :value="2" />
            <el-option label="已完成" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="filterForm.type" placeholder="全部" clearable>
            <el-option label="技术" :value="1" />
            <el-option label="销售" :value="2" />
            <el-option label="其他" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filterForm.keyword" placeholder="搜索标题/描述" clearable />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleFilter">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 工单列表 -->
    <el-card class="table-card">
      <el-table :data="workOrders" v-loading="loading" stripe @row-click="handleRowClick">
        <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
        <el-table-column prop="status_name" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status_name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="type_name" label="类型" width="80" />
        <el-table-column prop="priority_name" label="优先级" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.priority === 1" type="danger" size="small">紧急</el-tag>
            <el-tag v-else-if="row.priority === 2" type="warning" size="small">重要</el-tag>
            <span v-else>普通</span>
          </template>
        </el-table-column>
        <el-table-column prop="customer_name" label="客户" width="120" show-overflow-tooltip />
        <el-table-column prop="handler_name" label="处理人" width="100" />
        <el-table-column prop="creator_name" label="创建人" width="100" />
        <el-table-column prop="cttime" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.cttime) }}
          </template>
        </el-table-column>
        <el-table-column prop="step_count" label="跟进" width="80" align="center">
          <template #default="{ row }">
            <el-badge :value="row.step_count" :hidden="!row.step_count" type="info">
              <el-icon><ChatLineSquare /></el-icon>
            </el-badge>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click.stop="handleEdit(row)">编辑</el-button>
            <el-button link type="success" @click.stop="handleChangeStatus(row)">状态</el-button>
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
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="700px">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="标题" prop="title">
          <el-input v-model="form.title" placeholder="请输入工单标题" />
        </el-form-item>
        <el-form-item label="客户">
          <el-select v-model="form.customer" placeholder="选择客户" clearable filterable>
            <el-option
              v-for="c in customers"
              :key="c.id"
              :label="c.customer_name"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="工单类型">
              <el-select v-model="form.order_type" placeholder="选择类型">
                <el-option label="技术" :value="1" />
                <el-option label="销售" :value="2" />
                <el-option label="其他" :value="3" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="优先级">
              <el-select v-model="form.priority" placeholder="选择优先级">
                <el-option label="普通" :value="0" />
                <el-option label="紧急" :value="1" />
                <el-option label="重要" :value="2" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="处理人">
          <el-select v-model="form.handler" placeholder="选择处理人" clearable filterable>
            <el-option
              v-for="u in users"
              :key="u.id"
              :label="u.username"
              :value="u.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="发生时间">
          <el-date-picker v-model="form.occdate" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="4" placeholder="请输入详细描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>

    <!-- 状态变更对话框 -->
    <el-dialog v-model="statusDialogVisible" title="变更状态" width="400px">
      <el-form label-width="80px">
        <el-form-item label="当前状态">
          <el-tag :type="getStatusType(currentOrder?.status)">{{ currentOrder?.status_name }}</el-tag>
        </el-form-item>
        <el-form-item label="新状态">
          <el-select v-model="newStatus" placeholder="选择新状态">
            <el-option label="新建" :value="0" />
            <el-option label="处理中" :value="1" />
            <el-option label="搁置" :value="2" />
            <el-option label="已完成" :value="3" />
          </el-select>
        </el-form-item>
        <el-form-item label="处理描述">
          <el-input v-model="stepDescription" type="textarea" :rows="3" placeholder="请输入处理描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="statusDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleStatusSubmit">确定</el-button>
      </template>
    </el-dialog>

    <!-- 工单详情抽屉 -->
    <el-drawer v-model="detailDrawer" title="工单详情" size="600px">
      <div v-if="currentOrder" class="order-detail">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="标题">{{ currentOrder.title }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentOrder.status)">{{ currentOrder.status_name }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="类型">{{ currentOrder.type_name }}</el-descriptions-item>
          <el-descriptions-item label="优先级">
            <el-tag v-if="currentOrder.priority === 1" type="danger">紧急</el-tag>
            <el-tag v-else-if="currentOrder.priority === 2" type="warning">重要</el-tag>
            <span v-else>普通</span>
          </el-descriptions-item>
          <el-descriptions-item label="客户">{{ currentOrder.customer_name }}</el-descriptions-item>
          <el-descriptions-item label="处理人">{{ currentOrder.handler_name }}</el-descriptions-item>
          <el-descriptions-item label="创建人">{{ currentOrder.creator_name }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDateTime(currentOrder.cttime) }}</el-descriptions-item>
        </el-descriptions>

        <el-divider>问题描述</el-divider>
        <div class="description">{{ currentOrder.description || '无' }}</div>

        <el-divider>跟进记录</el-divider>
        
        <!-- 添加跟进 -->
        <div class="add-step">
          <el-input v-model="newStepDescription" type="textarea" :rows="2" placeholder="添加跟进记录..." />
          <el-button type="primary" size="small" @click="handleAddStep" style="margin-top: 10px;">添加跟进</el-button>
        </div>

        <!-- 跟进列表 -->
        <el-timeline>
          <el-timeline-item
            v-for="step in steps"
            :key="step.id"
            :timestamp="formatDateTime(step.cttime)"
            placement="top"
          >
            <el-card>
              <p>{{ step.description }}</p>
              <p class="step-info">
                <span>处理人: {{ step.handler_name }}</span>
                <el-tag :type="getStatusType(step.status)" size="small">{{ step.status_name }}</el-tag>
              </p>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, ChatLineSquare } from '@element-plus/icons-vue'
import axios from '@/utils/axios'

const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const statusDialogVisible = ref(false)
const detailDrawer = ref(false)
const dialogTitle = ref('新建工单')
const formRef = ref(null)
const customers = ref([])
const users = ref([])
const workOrders = ref([])
const steps = ref([])
const currentOrder = ref(null)

const stats = reactive({
  total: 0,
  today: 0,
  pending: 0
})

const filterForm = reactive({
  status: '',
  type: '',
  keyword: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const form = reactive({
  id: null,
  title: '',
  resume: '',
  order_type: 1,
  priority: 0,
  status: 0,
  customer: null,
  handler: null,
  occdate: '',
  description: ''
})

const newStatus = ref(null)
const stepDescription = ref('')
const newStepDescription = ref('')

const formRules = {
  title: [{ required: true, message: '请输入工单标题', trigger: 'blur' }]
}

function getStatusType(status) {
  const types = { 0: 'info', 1: 'warning', 2: 'warning', 3: 'success' }
  return types[status] || 'info'
}

function formatDateTime(datetime) {
  if (!datetime) return '-'
  return new Date(datetime).toLocaleString('zh-CN')
}

function loadCustomers() {
  axios.get('/api/customers/customers/', { params: { page_size: 100 } })
    .then(res => {
      customers.value = res.results || []
    })
}

function loadUsers() {
  axios.get('/api/auth/users/', { params: { page_size: 100 } })
    .then(res => {
      users.value = res.results || []
    })
}

function loadStatistics() {
  axios.get('/api/workorder/statistics/')
    .then(res => {
      Object.assign(stats, res.data || res)
    })
}

function loadData() {
  loading.value = true
  const params = {
    page: pagination.page,
    page_size: pagination.pageSize,
    ...(filterForm.status !== '' && { status: filterForm.status }),
    ...(filterForm.type && { type: filterForm.type }),
    ...(filterForm.keyword && { keyword: filterForm.keyword })
  }
  
  axios.get('/api/workorder/', { params })
    .then(res => {
      workOrders.value = res.results || []
      pagination.total = res.count || 0
    })
    .catch(() => {
      ElMessage.error('加载数据失败')
    })
    .finally(() => {
      loading.value = false
    })
}

function handleFilter() {
  pagination.page = 1
  loadData()
}

function handleReset() {
  filterForm.status = ''
  filterForm.type = ''
  filterForm.keyword = ''
  handleFilter()
}

function handleCreate() {
  dialogTitle.value = '新建工单'
  Object.assign(form, {
    id: null,
    title: '',
    resume: '',
    order_type: 1,
    priority: 0,
    status: 0,
    customer: null,
    handler: null,
    occdate: '',
    description: ''
  })
  dialogVisible.value = true
}

function handleEdit(row) {
  dialogTitle.value = '编辑工单'
  Object.assign(form, {
    id: row.id,
    title: row.title,
    resume: row.resume || '',
    order_type: row.order_type,
    priority: row.priority,
    status: row.status,
    customer: row.customer,
    handler: row.handler,
    occdate: row.occdate || '',
    description: row.description || ''
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
    submitLoading.value = true
    
    const method = form.id ? 'put' : 'post'
    const url = form.id ? `/api/workorder/${form.id}/` : '/api/workorder/'
    
    await axios[method](url, form)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadData()
    loadStatistics()
  } catch (e) {
    // 验证失败
  } finally {
    submitLoading.value = false
  }
}

function handleRowClick(row) {
  currentOrder.value = row
  loadSteps(row.id)
  detailDrawer.value = true
}

function loadSteps(orderId) {
  axios.get('/api/workorder/steps/', { params: { order: orderId } })
    .then(res => {
      steps.value = res.results || []
    })
}

function handleChangeStatus(row) {
  currentOrder.value = row
  newStatus.value = row.status
  stepDescription.value = ''
  statusDialogVisible.value = true
}

async function handleStatusSubmit() {
  if (newStatus.value === null) {
    ElMessage.warning('请选择新状态')
    return
  }
  
  try {
    await axios.post(`/api/workorder/${currentOrder.value.id}/change_status/`, {
      status: newStatus.value,
      description: stepDescription.value
    })
    
    // 添加跟进记录
    if (stepDescription.value) {
      await axios.post(`/api/workorder/${currentOrder.value.id}/add_step/`, {
        description: stepDescription.value,
        status: newStatus.value
      })
    }
    
    ElMessage.success('状态更新成功')
    statusDialogVisible.value = false
    loadData()
    loadStatistics()
  } catch (e) {
    ElMessage.error('更新失败')
  }
}

async function handleAddStep() {
  if (!newStepDescription.value) {
    ElMessage.warning('请输入跟进内容')
    return
  }
  
  try {
    await axios.post(`/api/workorder/${currentOrder.value.id}/add_step/`, {
      description: newStepDescription.value
    })
    ElMessage.success('跟进已添加')
    newStepDescription.value = ''
    loadSteps(currentOrder.value.id)
    loadData()
  } catch (e) {
    ElMessage.error('添加失败')
  }
}

onMounted(() => {
  loadCustomers()
  loadUsers()
  loadStatistics()
  loadData()
})
</script>

<style scoped>
.work-order-list {
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

.stat-card.warning .stat-value {
  color: #e6a23c;
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

.filter-card {
  margin-bottom: 20px;
}

.table-card {
  background: white;
}

.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.order-detail .description {
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
  min-height: 60px;
}

.step-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.add-step {
  margin-bottom: 20px;
}
</style>
