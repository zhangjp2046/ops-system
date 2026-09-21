<template>
  <div class="transfer-list">
    <div class="header">
      <h2>资产调拨管理</h2>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        新建调拨
      </el-button>
    </div>

    <!-- 搜索和筛选 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="调拨单号">
          <el-input v-model="filterForm.transfer_no" placeholder="调拨单号" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="选择状态" clearable style="width: 120px">
            <el-option label="待调拨" value="PENDING" />
            <el-option label="已审批" value="APPROVED" />
            <el-option label="已拒绝" value="REJECTED" />
            <el-option label="已完成" value="COMPLETED" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleFilter">
            <el-icon><Search /></el-icon> 搜索
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon> 重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 数据表格 -->
    <el-card class="table-card">
      <el-table v-loading="loading" :data="transfers" stripe>
        <el-table-column prop="transfer_no" label="调拨单号" width="180" />
        <el-table-column prop="asset_name" label="资产名称" width="150" />
        <el-table-column prop="asset_code" label="资产编号" width="120" />
        <el-table-column prop="from_department" label="调出部门" width="120" />
        <el-table-column prop="to_department" label="调入部门" width="120" />
        <el-table-column prop="status_text" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="applicant" label="申请人" width="100" />
        <el-table-column prop="created_at" label="申请时间" width="160" />
        <el-table-column label="操作" fixed="right" width="200">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">详情</el-button>
            <el-button link type="primary" @click="handleEdit(row)" v-if="row.status === 'PENDING'">编辑</el-button>
            <el-button link type="success" @click="handleApprove(row)" v-if="row.status === 'PENDING'">审批</el-button>
            <el-button link type="warning" @click="handleExecute(row)" v-if="row.status === 'APPROVED'">执行</el-button>
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

    <!-- 新建/编辑对话框 -->
    <el-dialog v-model="showCreateDialog" :title="isEdit ? '编辑调拨' : '新建调拨'" width="600px">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="客户" prop="customer">
          <el-select v-model="form.customer" placeholder="选择客户" style="width: 100%">
            <el-option v-for="c in customers" :key="c.id" :label="c.customer_name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="资产" prop="asset">
          <el-select v-model="form.asset" placeholder="选择资产" filterable style="width: 100%">
            <el-option
              v-for="a in assetList"
              :key="a.id"
              :label="`${a.asset_name} (${a.asset_code})`"
              :value="a.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="调出部门" prop="from_department">
          <el-input v-model="form.from_department" placeholder="调出部门" />
        </el-form-item>
        <el-form-item label="调入部门" prop="to_department">
          <el-input v-model="form.to_department" placeholder="调入部门" />
        </el-form-item>
        <el-form-item label="调出位置">
          <el-input v-model="form.from_location" placeholder="调出位置" />
        </el-form-item>
        <el-form-item label="调入位置">
          <el-input v-model="form.to_location" placeholder="调入位置" />
        </el-form-item>
        <el-form-item label="调拨原因">
          <el-input v-model="form.reason" type="textarea" rows="3" placeholder="调拨原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="调拨详情" width="600px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="调拨单号">{{ currentRow?.transfer_no }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentRow?.status)">{{ currentRow?.status_text }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="资产名称">{{ currentRow?.asset_name }}</el-descriptions-item>
        <el-descriptions-item label="资产编号">{{ currentRow?.asset_code }}</el-descriptions-item>
        <el-descriptions-item label="调出部门">{{ currentRow?.from_department }}</el-descriptions-item>
        <el-descriptions-item label="调入部门">{{ currentRow?.to_department }}</el-descriptions-item>
        <el-descriptions-item label="调出位置">{{ currentRow?.from_location }}</el-descriptions-item>
        <el-descriptions-item label="调入位置">{{ currentRow?.to_location }}</el-descriptions-item>
        <el-descriptions-item label="申请人">{{ currentRow?.applicant }}</el-descriptions-item>
        <el-descriptions-item label="审批人">{{ currentRow?.approver }}</el-descriptions-item>
        <el-descriptions-item label="调拨原因" :span="2">{{ currentRow?.reason }}</el-descriptions-item>
        <el-descriptions-item label="审批意见" :span="2">{{ currentRow?.approve_comment }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>

    <!-- 审批对话框 -->
    <el-dialog v-model="showApproveDialog" title="审批调拨" width="400px">
      <el-form label-width="80px">
        <el-form-item label="审批意见">
          <el-input v-model="approveComment" type="textarea" rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showApproveDialog = false">取消</el-button>
        <el-button type="success" @click="doApprove">通过</el-button>
        <el-button type="danger" @click="doReject">拒绝</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { getTransferList, createTransfer, updateTransfer, getAssetList, approveTransfer, rejectTransfer } from '@/api/asset'
import api from '@/api/index'
import { getCustomerList } from '@/api/customer'

const loading = ref(false)
const transfers = ref([])
const customers = ref([])
const assetList = ref([])
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const showApproveDialog = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const currentRow = ref(null)
const approveComment = ref('')
const approveAction = ref('')

const filterForm = reactive({
  transfer_no: '',
  status: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const form = reactive({
  customer: null,
  asset: null,
  from_department: '',
  to_department: '',
  from_location: '',
  to_location: '',
  reason: ''
})

const formRules = {
  customer: [{ required: true, message: '请选择客户', trigger: 'change' }],
  asset: [{ required: true, message: '请选择资产', trigger: 'change' }],
  from_department: [{ required: true, message: '请输入调出部门', trigger: 'blur' }],
  to_department: [{ required: true, message: '请输入调入部门', trigger: 'blur' }]
}

function getStatusType(status) {
  const types = {
    PENDING: 'warning',
    APPROVED: 'success',
    REJECTED: 'danger',
    COMPLETED: 'info',
    CANCELLED: 'info'
  }
  return types[status] || ''
}

async function fetchData() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      ...filterForm
    }
    const res = await getTransferList(params)
    transfers.value = res.results || res
    pagination.total = res.count || res.length
  } catch (e) {
    ElMessage.error('获取调拨列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchCustomers() {
  try {
    const res = await getCustomerList()
    customers.value = res.results || res
  } catch (e) {
    console.error(e)
  }
}

async function fetchAssets() {
  try {
    const res = await getAssetList({ page_size: 1000 })
    assetList.value = res.results || res
  } catch (e) {
    console.error(e)
  }
}

function handleFilter() {
  pagination.page = 1
  fetchData()
}

function handleReset() {
  filterForm.transfer_no = ''
  filterForm.status = ''
  pagination.page = 1
  fetchData()
}

function handleSizeChange() {
  pagination.page = 1
  fetchData()
}

function handlePageChange() {
  fetchData()
}

function handleView(row) {
  currentRow.value = row
  showDetailDialog.value = true
}

function handleEdit(row) {
  isEdit.value = true
  Object.assign(form, {
    customer: row.customer,
    asset: row.asset,
    from_department: row.from_department,
    to_department: row.to_department,
    from_location: row.from_location,
    to_location: row.to_location,
    reason: row.reason
  })
  showCreateDialog.value = true
}

function handleApprove(row) {
  currentRow.value = row
  approveComment.value = ''
  approveAction.value = ''
  showApproveDialog.value = true
}

async function doApprove() {
  try {
    await ElMessageBox.confirm('确认通过此调拨申请?', '审批确认', { type: 'success' })
    await approveTransfer(currentRow.value.id, approveComment.value)
    ElMessage.success('审批通过')
    showApproveDialog.value = false
    fetchData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('操作失败')
  }
}

async function doReject() {
  try {
    await ElMessageBox.confirm('确认拒绝此调拨申请?', '审批确认', { type: 'warning' })
    await rejectTransfer(currentRow.value.id, approveComment.value)
    ElMessage.success('已拒绝')
    showApproveDialog.value = false
    fetchData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('操作失败')
  }
}

async function handleExecute(row) {
  try {
    await ElMessageBox.confirm('确认执行此调拨?', '执行确认', { type: 'warning' })
    await api.post(`/assets/transfers/${row.id}/execute/`)
    ElMessage.success('调拨执行完成')
    fetchData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('操作失败')
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      if (isEdit.value) {
        await updateTransfer(currentRow.value.id, form)
        ElMessage.success('更新成功')
      } else {
        await createTransfer(form)
        ElMessage.success('创建成功')
      }
      showCreateDialog.value = false
      fetchData()
    } catch (e) {
      ElMessage.error('操作失败')
    } finally {
      submitting.value = false
    }
  })
}

onMounted(() => {
  fetchData()
  fetchCustomers()
  fetchAssets()
})
</script>

<style scoped>
.transfer-list {
  padding: 20px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.header h2 {
  margin: 0;
}
.filter-card {
  margin-bottom: 20px;
}
.table-card {
  margin-bottom: 20px;
}
.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
