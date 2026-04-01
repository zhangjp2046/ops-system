<template>
  <div class="inspection-plans">
    <div class="page-header">
      <h2>巡检计划管理</h2>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon> 新建计划
      </el-button>
    </div>

    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="客户">
          <el-select v-model="filterForm.customer" placeholder="全部客户" clearable filterable style="width: 180px">
            <el-option
              v-for="c in customers"
              :key="c.id"
              :label="c.customer_name"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="全部" clearable>
            <el-option label="草稿" value="draft" />
            <el-option label="启用" value="active" />
            <el-option label="暂停" value="paused" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleFilter">查询</el-button>
          <el-button @click="handleReset">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card class="table-card">
      <el-table :data="tableData" v-loading="loading" stripe>
        <el-table-column prop="name" label="计划名称" min-width="150" />
        <el-table-column prop="customer_name" label="客户" width="150">
          <template #default="{ row }">
            {{ row.customer_name || '-' }}
          </template>
        </el-table-column>
        <el-table-column prop="code" label="计划编码" width="150" />
        <el-table-column prop="cycle" label="执行周期" width="100">
          <template #default="{ row }">
            {{ row.cycle_display }}
          </template>
        </el-table-column>
        <el-table-column prop="scheduled_time" label="计划时间" width="100">
          <template #default="{ row }">
            {{ row.scheduled_time }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ row.status_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="task_count" label="关联任务" width="100" align="center">
          <template #default="{ row }">
            <el-link type="primary" @click="showTasks(row)">
              {{ row.task_count }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="success" @click="handleExecute(row)" v-if="row.status === 'active'">
              执行
            </el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
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

    <!-- 创建/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
    >
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="所属客户" prop="customer">
          <el-select v-model="form.customer" placeholder="请选择客户" filterable clearable style="width: 100%">
            <el-option
              v-for="c in customers"
              :key="c.id"
              :label="c.customer_name"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="计划名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入计划名称" />
        </el-form-item>
        <el-form-item label="计划编码" prop="code">
          <el-input v-model="form.code" placeholder="请输入计划编码" />
        </el-form-item>
        <el-form-item label="执行周期" prop="cycle">
          <el-select v-model="form.cycle">
            <el-option label="每天" value="daily" />
            <el-option label="每周" value="weekly" />
            <el-option label="每月" value="monthly" />
          </el-select>
        </el-form-item>
        <el-form-item label="计划时间" prop="scheduled_time">
          <el-time-picker v-model="form.scheduled_time" format="HH:mm" value-format="HH:mm" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">
          确定
        </el-button>
      </template>
    </el-dialog>

    <!-- 巡检任务对话框 -->
    <el-dialog v-model="taskDialogVisible" title="巡检任务" width="900px">
      <el-table :data="taskTableData" stripe>
        <el-table-column prop="asset_name" label="资产" width="150" />
        <el-table-column prop="scheduled_time" label="计划时间" width="160" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getTaskStatusType(row.status)">
              {{ row.status_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80">
          <template #default="{ row }">
            {{ row.priority_display }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="executeTask(row)">执行</el-button>
            <el-button link type="info" @click="showRecords(row)">记录</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import axios from '@/utils/axios'

const loading = ref(false)
const submitLoading = ref(false)
const dialogVisible = ref(false)
const taskDialogVisible = ref(false)
const dialogTitle = ref('新建计划')
const formRef = ref(null)

const customers = ref([])
const filterForm = reactive({
  customer: null,
  status: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 10,
  total: 0
})

const form = reactive({
  id: null,
  customer: null,
  name: '',
  code: '',
  cycle: 'daily',
  scheduled_time: '09:00',
  description: ''
})

const formRules = {
  name: [{ required: true, message: '请输入计划名称', trigger: 'blur' }],
  code: [{ required: true, message: '请输入计划编码', trigger: 'blur' }],
  cycle: [{ required: true, message: '请选择执行周期', trigger: 'change' }],
  scheduled_time: [{ required: true, message: '请选择计划时间', trigger: 'change' }]
}

const tableData = ref([])
const taskTableData = ref([])
const currentPlan = ref(null)

function getStatusType(status) {
  const types = {
    draft: 'info',
    active: 'success',
    paused: 'warning',
    archived: 'info'
  }
  return types[status] || 'info'
}

function getTaskStatusType(status) {
  const types = {
    pending: 'info',
    in_progress: 'warning',
    completed: 'success',
    failed: 'danger',
    cancelled: 'info'
  }
  return types[status] || 'info'
}

function loadData() {
  loading.value = true
  const params = {
    page: pagination.page,
    page_size: pagination.pageSize,
    ...(filterForm.status && { status: filterForm.status }),
    ...(filterForm.customer && { customer: filterForm.customer })
  }
  
  axios.get('/api/inspection/plans/', { params })
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

function handleFilter() {
  pagination.page = 1
  loadData()
}

function handleReset() {
  filterForm.customer = null
  filterForm.status = ''
  handleFilter()
}

function handleSizeChange() {
  pagination.page = 1
  loadData()
}

function handlePageChange() {
  loadData()
}

function handleCreate() {
  dialogTitle.value = '新建计划'
  Object.assign(form, {
    id: null,
    customer: customers.value.length > 0 ? customers.value[0].id : null,
    name: '',
    code: '',
    cycle: 'daily',
    scheduled_time: '09:00',
    description: ''
  })
  dialogVisible.value = true
}

function handleEdit(row) {
  dialogTitle.value = '编辑计划'
  Object.assign(form, row)
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
    submitLoading.value = true
    
    const method = form.id ? 'put' : 'post'
    const url = form.id ? `/api/inspection/plans/${form.id}/` : '/api/inspection/plans/'
    
    await axios[method](url, form)
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadData()
  } catch (e) {
    // 验证失败或请求失败
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定要删除该巡检计划吗？', '提示', { type: 'warning' })
    await axios.delete(`/api/inspection/plans/${row.id}/`)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

function showTasks(row) {
  currentPlan.value = row
  axios.get('/api/inspection/tasks/', { params: { plan: row.id } })
    .then(res => {
      taskTableData.value = res.results || []
      taskDialogVisible.value = true
    })
    .catch(() => {
      ElMessage.error('加载任务失败')
    })
}

async function handleExecute(row) {
  try {
    await ElMessageBox.confirm('确定要执行该巡检计划吗？', '提示', { type: 'info' })
    await axios.post(`/api/inspection/plans/${row.id}/execute/`)
    ElMessage.success('执行成功')
    loadData()
  } catch (e) {
    if (e !== 'cancel') {
      ElMessage.error('执行失败')
    }
  }
}

function executeTask(row) {
  axios.post(`/api/inspection/tasks/${row.id}/execute/`)
    .then(res => {
      ElMessage.success(`执行完成，发现${res.results?.length || 0}个检查项`)
      showRecords(row)
    })
    .catch(() => {
      ElMessage.error('执行失败')
    })
}

function showRecords(row) {
  // TODO: 跳转到巡检记录页面
  ElMessage.info('功能开发中')
}

function loadCustomers() {
  axios.get('/api/customers/customers/', { params: { page_size: 200 } })
    .then(res => {
      customers.value = res.results || []
    })
    .catch(() => {
      console.error('加载客户失败')
    })
}

onMounted(() => {
  loadData()
  loadCustomers()
})
</script>

<style scoped>
.inspection-plans {
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
</style>
