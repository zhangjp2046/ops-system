<template>
  <div class="lend-list">
    <div class="header">
      <h2>资产出借管理</h2>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建出借
      </el-button>
    </div>

    <!-- 搜索和筛选 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="出借单号">
          <el-input v-model="filterForm.lend_no" placeholder="出借单号" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="选择状态" clearable style="width: 120px">
            <el-option label="待审批" value="PENDING" />
            <el-option label="已审批" value="APPROVED" />
            <el-option label="已拒绝" value="REJECTED" />
            <el-option label="已借出" value="OUT" />
            <el-option label="已归还" value="RETURNED" />
            <el-option label="已逾期" value="OVERDUE" />
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
      <el-table v-loading="loading" :data="lends" stripe>
        <el-table-column prop="lend_no" label="出借单号" width="180" />
        <el-table-column prop="asset_name" label="资产名称" width="150" />
        <el-table-column prop="asset_code" label="资产编号" width="120" />
        <el-table-column prop="lendee" label="借用人" width="100" />
        <el-table-column prop="to_department" label="借往部门" width="120" />
        <el-table-column prop="status_text" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" :disable-transitions="true">
              {{ row.status_text }}
              <el-icon v-if="row.is_overdue" color="red"><WarningFilled /></el-icon>
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="expected_return_date" label="预计归还" width="110" />
        <el-table-column prop="lend_date" label="借出日期" width="110" />
        <el-table-column prop="actual_return_date" label="实际归还" width="110" />
        <el-table-column label="操作" fixed="right" width="220">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">详情</el-button>
            <el-button link type="primary" @click="handleEdit(row)" v-if="row.status === 'PENDING'">编辑</el-button>
            <el-button link type="success" @click="handleApprove(row)" v-if="row.status === 'PENDING'">审批</el-button>
            <el-button link type="warning" @click="handleLendOut(row)" v-if="row.status === 'APPROVED'">借出</el-button>
            <el-button link type="success" @click="handleReturn(row)" v-if="row.status === 'OUT' || row.status === 'OVERDUE'">归还</el-button>
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
    <el-dialog v-model="showCreateDialog" :title="isEdit ? '编辑出借' : '新建出借'" width="600px">
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
              :label="`${a.asset_name} (${a.asset_code}) - ${a.department || '未分配'}`"
              :value="a.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="借出部门" prop="from_department">
          <el-input v-model="form.from_department" placeholder="借出部门" />
        </el-form-item>
        <el-form-item label="借往部门" prop="to_department">
          <el-input v-model="form.to_department" placeholder="借往部门" />
        </el-form-item>
        <el-form-item label="借往地点">
          <el-input v-model="form.to_location" placeholder="借往地点" />
        </el-form-item>
        <el-form-item label="借用人" prop="lendee">
          <el-input v-model="form.lendee" placeholder="借用人姓名" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.lendee_phone" placeholder="联系电话" />
        </el-form-item>
        <el-form-item label="预计归还" prop="expected_return_date">
          <el-date-picker
            v-model="form.expected_return_date"
            type="date"
            placeholder="选择预计归还日期"
            style="width: 100%"
            :disabled-date="disabledDate"
          />
        </el-form-item>
        <el-form-item label="出借原因">
          <el-input v-model="form.reason" type="textarea" rows="3" placeholder="出借原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 审批对话框 -->
    <el-dialog v-model="showApproveDialog" title="审批出借" width="400px">
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

    <!-- 归还对话框 -->
    <el-dialog v-model="showReturnDialog" title="资产归还" width="400px">
      <el-form label-width="100px">
        <el-form-item label="归还验收">
          <el-input v-model="returnForm.return_acceptance" type="textarea" rows="3" placeholder="归还验收情况" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showReturnDialog = false">取消</el-button>
        <el-button type="primary" @click="doReturn">确定归还</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="出借详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="出借单号">{{ currentRow?.lend_no }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentRow?.status)">{{ currentRow?.status_text }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="资产名称">{{ currentRow?.asset_name }}</el-descriptions-item>
        <el-descriptions-item label="资产编号">{{ currentRow?.asset_code }}</el-descriptions-item>
        <el-descriptions-item label="借出部门">{{ currentRow?.from_department }}</el-descriptions-item>
        <el-descriptions-item label="借往部门">{{ currentRow?.to_department }}</el-descriptions-item>
        <el-descriptions-item label="借往地点">{{ currentRow?.to_location }}</el-descriptions-item>
        <el-descriptions-item label="借用人">{{ currentRow?.lendee }}</el-descriptions-item>
        <el-descriptions-item label="联系电话">{{ currentRow?.lendee_phone }}</el-descriptions-item>
        <el-descriptions-item label="预计归还">{{ currentRow?.expected_return_date }}</el-descriptions-item>
        <el-descriptions-item label="借出日期">{{ currentRow?.lend_date }}</el-descriptions-item>
        <el-descriptions-item label="实际归还">{{ currentRow?.actual_return_date }}</el-descriptions-item>
        <el-descriptions-item label="出借原因" :span="2">{{ currentRow?.reason }}</el-descriptions-item>
        <el-descriptions-item label="审批意见" :span="2">{{ currentRow?.approve_comment }}</el-descriptions-item>
        <el-descriptions-item label="归还验收" :span="2">{{ currentRow?.return_acceptance }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh, WarningFilled } from '@element-plus/icons-vue'
import { getLendList, createLend, updateLend, getAssetList, approveLend, lendOut, returnLend } from '@/api/asset'
import { getCustomerList } from '@/api/customer'

const loading = ref(false)
const lends = ref([])
const customers = ref([])
const assetList = ref([])
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const showApproveDialog = ref(false)
const showReturnDialog = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const currentRow = ref(null)

const filterForm = reactive({
  lend_no: '',
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
  to_location: '',
  lendee: '',
  lendee_phone: '',
  expected_return_date: null,
  reason: ''
})

const approveComment = ref('')
const returnForm = reactive({
  return_acceptance: ''
})

const formRules = {
  customer: [{ required: true, message: '请选择客户', trigger: 'change' }],
  asset: [{ required: true, message: '请选择资产', trigger: 'change' }],
  from_department: [{ required: true, message: '请输入借出部门', trigger: 'blur' }],
  to_department: [{ required: true, message: '请输入借往部门', trigger: 'blur' }],
  lendee: [{ required: true, message: '请输入借用人', trigger: 'blur' }],
  expected_return_date: [{ required: true, message: '请选择预计归还日期', trigger: 'change' }]
}

function disabledDate(date) {
  return date < new Date()
}

function getStatusType(status) {
  const types = {
    PENDING: 'info',
    APPROVED: 'success',
    REJECTED: 'danger',
    OUT: 'warning',
    RETURNED: 'success',
    OVERDUE: 'danger',
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
    const res = await getLendList(params)
    lends.value = res.results || res
    pagination.total = res.count || res.length
  } catch (e) {
    ElMessage.error('获取出借列表失败')
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
  filterForm.lend_no = ''
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

function openCreate() {
  isEdit.value = false
  Object.assign(form, {
    customer: null,
    asset: null,
    from_department: '',
    to_department: '',
    to_location: '',
    lendee: '',
    lendee_phone: '',
    expected_return_date: null,
    reason: ''
  })
  showCreateDialog.value = true
}

function handleEdit(row) {
  isEdit.value = true
  Object.assign(form, {
    customer: row.customer,
    asset: row.asset,
    from_department: row.from_department,
    to_department: row.to_department,
    to_location: row.to_location,
    lendee: row.lendee,
    lendee_phone: row.lendee_phone,
    expected_return_date: row.expected_return_date,
    reason: row.reason
  })
  showCreateDialog.value = true
}

function handleApprove(row) {
  currentRow.value = row
  approveComment.value = ''
  showApproveDialog.value = true
}

async function doApprove() {
  try {
    await approveLend(currentRow.value.id, 'approve', approveComment.value)
    ElMessage.success('审批通过')
    showApproveDialog.value = false
    fetchData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function doReject() {
  try {
    await approveLend(currentRow.value.id, 'reject', approveComment.value)
    ElMessage.success('已拒绝')
    showApproveDialog.value = false
    fetchData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function handleLendOut(row) {
  try {
    await ElMessageBox.confirm('确认执行借出操作?', '借出确认', { type: 'warning' })
    await lendOut(row.id)
    ElMessage.success('已借出')
    fetchData()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('操作失败')
  }
}

function handleReturn(row) {
  currentRow.value = row
  returnForm.return_acceptance = ''
  showReturnDialog.value = true
}

async function doReturn() {
  try {
    await returnLend(currentRow.value.id, returnForm.return_acceptance)
    ElMessage.success('已归还')
    showReturnDialog.value = false
    fetchData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      const submitData = { ...form }
      if (form.expected_return_date) {
        submitData.expected_return_date = form.expected_return_date.toISOString().split('T')[0]
      }
      if (isEdit.value) {
        await updateLend(currentRow.value.id, submitData)
        ElMessage.success('更新成功')
      } else {
        await createLend(submitData)
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
.lend-list {
  padding: 20px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.header h2 { margin: 0; }
.filter-card { margin-bottom: 20px; }
.table-card { margin-bottom: 20px; }
.pagination {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
