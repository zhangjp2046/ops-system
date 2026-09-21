<template>
  <div class="repair-list">
    <div class="header">
      <h2>资产维修管理</h2>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建维修
      </el-button>
    </div>

    <!-- 搜索和筛选 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="维修单号">
          <el-input v-model="filterForm.repair_no" placeholder="维修单号" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="选择状态" clearable style="width: 120px">
            <el-option label="已申请" value="APPLIED" />
            <el-option label="已派工" value="ASSIGNED" />
            <el-option label="已接单" value="ACCEPTED" />
            <el-option label="维修中" value="PROCESSING" />
            <el-option label="已完成" value="COMPLETED" />
            <el-option label="已验收" value="QUALIFIED" />
          </el-select>
        </el-form-item>
        <el-form-item label="优先级">
          <el-select v-model="filterForm.priority" placeholder="选择优先级" clearable style="width: 100px">
            <el-option label="低" value="LOW" />
            <el-option label="中" value="MEDIUM" />
            <el-option label="高" value="HIGH" />
            <el-option label="紧急" value="URGENT" />
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
      <el-table v-loading="loading" :data="repairs" stripe>
        <el-table-column prop="repair_no" label="维修单号" width="180" />
        <el-table-column prop="asset_name" label="资产名称" width="150" />
        <el-table-column prop="asset_code" label="资产编号" width="120" />
        <el-table-column prop="priority_text" label="优先级" width="80">
          <template #default="{ row }">
            <el-tag :type="getPriorityType(row.priority)">{{ row.priority_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status_text" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="fault_description" label="故障描述" show-overflow-tooltip />
        <el-table-column prop="assignee" label="维修人员" width="100" />
        <el-table-column prop="created_at" label="申请时间" width="160" />
        <el-table-column label="操作" fixed="right" width="280">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">详情</el-button>
            <el-button link type="primary" @click="handleEdit(row)" v-if="row.status === 'APPLIED'">编辑</el-button>
            <el-button link type="warning" @click="handleAssign(row)" v-if="row.status === 'APPLIED'">派工</el-button>
            <el-button link type="success" @click="handleAccept(row)" v-if="row.status === 'ASSIGNED'">接单</el-button>
            <el-button link type="info" @click="handleProcess(row)" v-if="row.status === 'ACCEPTED'">开始维修</el-button>
            <el-button link type="success" @click="handleComplete(row)" v-if="row.status === 'PROCESSING'">完成</el-button>
            <el-button link type="success" @click="handleAcceptInspect(row)" v-if="row.status === 'COMPLETED'">验收</el-button>
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
    <el-dialog v-model="showCreateDialog" :title="isEdit ? '编辑维修' : '新建维修'" width="600px">
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
        <el-form-item label="故障描述" prop="fault_description">
          <el-input v-model="form.fault_description" type="textarea" rows="3" placeholder="请描述故障情况" />
        </el-form-item>
        <el-form-item label="故障时间">
          <el-date-picker v-model="form.fault_time" type="datetime" placeholder="选择故障时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="维修类型">
          <el-input v-model="form.repair_type" placeholder="维修类型" />
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-select v-model="form.priority" placeholder="选择优先级" style="width: 100%">
            <el-option label="低" value="LOW" />
            <el-option label="中" value="MEDIUM" />
            <el-option label="高" value="HIGH" />
            <el-option label="紧急" value="URGENT" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 派工对话框 -->
    <el-dialog v-model="showAssignDialog" title="派工" width="400px">
      <el-form label-width="80px">
        <el-form-item label="维修人员">
          <el-input v-model="assignForm.assignee" placeholder="维修人员姓名" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="assignForm.assignee_phone" placeholder="联系电话" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAssignDialog = false">取消</el-button>
        <el-button type="primary" @click="doAssign">确定派工</el-button>
      </template>
    </el-dialog>

    <!-- 完成维修对话框 -->
    <el-dialog v-model="showCompleteDialog" title="完成维修" width="500px">
      <el-form label-width="100px">
        <el-form-item label="维修结果">
          <el-input v-model="completeForm.repair_result" type="textarea" rows="3" placeholder="维修结果描述" />
        </el-form-item>
        <el-form-item label="维修费用">
          <el-input-number v-model="completeForm.repair_cost" :min="0" :precision="2" />
        </el-form-item>
        <el-form-item label="配件费用">
          <el-input-number v-model="completeForm.parts_cost" :min="0" :precision="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCompleteDialog = false">取消</el-button>
        <el-button type="primary" @click="doComplete">确定完成</el-button>
      </template>
    </el-dialog>

    <!-- 验收对话框 -->
    <el-dialog v-model="showAcceptDialog" title="验收" width="400px">
      <el-form label-width="80px">
        <el-form-item label="验收结果">
          <el-input v-model="acceptForm.accept_result" placeholder="验收结果" />
        </el-form-item>
        <el-form-item label="验收意见">
          <el-input v-model="acceptForm.accept_comment" type="textarea" rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAcceptDialog = false">取消</el-button>
        <el-button type="primary" @click="doAcceptInspect">确定验收</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="维修详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="维修单号">{{ currentRow?.repair_no }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentRow?.status)">{{ currentRow?.status_text }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="资产名称">{{ currentRow?.asset_name }}</el-descriptions-item>
        <el-descriptions-item label="资产编号">{{ currentRow?.asset_code }}</el-descriptions-item>
        <el-descriptions-item label="优先级">
          <el-tag :type="getPriorityType(currentRow?.priority)">{{ currentRow?.priority_text }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="维修类型">{{ currentRow?.repair_type }}</el-descriptions-item>
        <el-descriptions-item label="故障描述" :span="2">{{ currentRow?.fault_description }}</el-descriptions-item>
        <el-descriptions-item label="维修人员">{{ currentRow?.assignee }}</el-descriptions-item>
        <el-descriptions-item label="联系电话">{{ currentRow?.assignee_phone }}</el-descriptions-item>
        <el-descriptions-item label="维修费用">{{ currentRow?.repair_cost }}</el-descriptions-item>
        <el-descriptions-item label="配件费用">{{ currentRow?.parts_cost }}</el-descriptions-item>
        <el-descriptions-item label="总费用">{{ currentRow?.total_cost }}</el-descriptions-item>
        <el-descriptions-item label="维修结果" :span="2">{{ currentRow?.repair_result }}</el-descriptions-item>
        <el-descriptions-item label="验收结果" :span="2">{{ currentRow?.accept_result }}</el-descriptions-item>
        <el-descriptions-item label="验收意见" :span="2">{{ currentRow?.accept_comment }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { getRepairList, createRepair, updateRepair, getAssetList, assignRepair, acceptRepair, processRepair, completeRepair, acceptRepairInspect } from '@/api/asset'
import { getCustomerList } from '@/api/customer'

const loading = ref(false)
const repairs = ref([])
const customers = ref([])
const assetList = ref([])
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const showAssignDialog = ref(false)
const showCompleteDialog = ref(false)
const showAcceptDialog = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const currentRow = ref(null)

const filterForm = reactive({
  repair_no: '',
  status: '',
  priority: ''
})

const pagination = reactive({
  page: 1,
  pageSize: 20,
  total: 0
})

const form = reactive({
  customer: null,
  asset: null,
  fault_description: '',
  fault_time: null,
  repair_type: '',
  priority: 'MEDIUM'
})

const assignForm = reactive({
  assignee: '',
  assignee_phone: ''
})

const completeForm = reactive({
  repair_result: '',
  repair_cost: 0,
  parts_cost: 0
})

const acceptForm = reactive({
  accept_result: '合格',
  accept_comment: ''
})

const formRules = {
  customer: [{ required: true, message: '请选择客户', trigger: 'change' }],
  asset: [{ required: true, message: '请选择资产', trigger: 'change' }],
  fault_description: [{ required: true, message: '请输入故障描述', trigger: 'blur' }]
}

function getStatusType(status) {
  const types = {
    APPLIED: 'info',
    ASSIGNED: 'warning',
    ACCEPTED: 'warning',
    PROCESSING: 'primary',
    COMPLETED: 'success',
    QUALIFIED: 'success',
    REJECTED: 'danger'
  }
  return types[status] || ''
}

function getPriorityType(priority) {
  const types = {
    LOW: 'info',
    MEDIUM: 'warning',
    HIGH: 'danger',
    URGENT: 'danger'
  }
  return types[priority] || ''
}

async function fetchData() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.pageSize,
      ...filterForm
    }
    const res = await getRepairList(params)
    repairs.value = res.results || res
    pagination.total = res.count || res.length
  } catch (e) {
    ElMessage.error('获取维修列表失败')
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
  filterForm.repair_no = ''
  filterForm.status = ''
  filterForm.priority = ''
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
    fault_description: '',
    fault_time: null,
    repair_type: '',
    priority: 'MEDIUM'
  })
  showCreateDialog.value = true
}

function handleEdit(row) {
  isEdit.value = true
  Object.assign(form, {
    customer: row.customer,
    asset: row.asset,
    fault_description: row.fault_description,
    fault_time: row.fault_time,
    repair_type: row.repair_type,
    priority: row.priority
  })
  showCreateDialog.value = true
}

function handleAssign(row) {
  currentRow.value = row
  assignForm.assignee = ''
  assignForm.assignee_phone = ''
  showAssignDialog.value = true
}

async function doAssign() {
  try {
    await assignRepair(currentRow.value.id, assignForm.assignee, assignForm.assignee_phone)
    ElMessage.success('派工成功')
    showAssignDialog.value = false
    fetchData()
  } catch (e) {
    ElMessage.error('派工失败')
  }
}

async function handleAccept(row) {
  try {
    await acceptRepair(row.id)
    ElMessage.success('已接单')
    fetchData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function handleProcess(row) {
  try {
    await processRepair(row.id)
    ElMessage.success('维修开始')
    fetchData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

function handleComplete(row) {
  currentRow.value = row
  completeForm.repair_result = ''
  completeForm.repair_cost = 0
  completeForm.parts_cost = 0
  showCompleteDialog.value = true
}

async function doComplete() {
  try {
    await completeRepair(currentRow.value.id, completeForm.repair_result, completeForm.repair_cost, completeForm.parts_cost)
    ElMessage.success('维修完成')
    showCompleteDialog.value = false
    fetchData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

function handleAcceptInspect(row) {
  currentRow.value = row
  acceptForm.accept_result = '合格'
  acceptForm.accept_comment = ''
  showAcceptDialog.value = true
}

async function doAcceptInspect() {
  try {
    await acceptRepairInspect(currentRow.value.id, acceptForm.accept_result, acceptForm.accept_comment)
    ElMessage.success('验收通过')
    showAcceptDialog.value = false
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
      if (isEdit.value) {
        await updateRepair(currentRow.value.id, form)
        ElMessage.success('更新成功')
      } else {
        await createRepair(form)
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
.repair-list {
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
