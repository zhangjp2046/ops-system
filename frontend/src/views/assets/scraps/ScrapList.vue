<template>
  <div class="scrap-list">
    <div class="header">
      <h2>资产报废管理</h2>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        新建报废
      </el-button>
    </div>

    <!-- 搜索和筛选 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="报废单号">
          <el-input v-model="filterForm.scrap_no" placeholder="报废单号" clearable />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="选择状态" clearable style="width: 120px">
            <el-option label="已申请" value="APPLIED" />
            <el-option label="已审批" value="APPROVED" />
            <el-option label="已拒绝" value="REJECTED" />
            <el-option label="已报废" value="SCRAPPED" />
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
      <el-table v-loading="loading" :data="scraps" stripe>
        <el-table-column prop="scrap_no" label="报废单号" width="180" />
        <el-table-column prop="asset_name" label="资产名称" width="150" />
        <el-table-column prop="asset_code" label="资产编号" width="120" />
        <el-table-column prop="status_text" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status_text }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="scrap_reason" label="报废原因" show-overflow-tooltip />
        <el-table-column prop="original_value" label="原值" width="100" />
        <el-table-column prop="net_value" label="净值" width="100" />
        <el-table-column prop="handler" label="处理人" width="100" />
        <el-table-column prop="created_at" label="申请时间" width="160" />
        <el-table-column label="操作" fixed="right" width="200">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleView(row)">详情</el-button>
            <el-button link type="primary" @click="handleEdit(row)" v-if="row.status === 'APPLIED'">编辑</el-button>
            <el-button link type="success" @click="handleApprove(row)" v-if="row.status === 'APPLIED'">审批</el-button>
            <el-button link type="warning" @click="handleExecute(row)" v-if="row.status === 'APPROVED'">执行报废</el-button>
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
    <el-dialog v-model="showCreateDialog" :title="isEdit ? '编辑报废' : '新建报废'" width="600px">
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
        <el-form-item label="报废原因" prop="scrap_reason">
          <el-input v-model="form.scrap_reason" type="textarea" rows="3" placeholder="请输入报废原因" />
        </el-form-item>
        <el-form-item label="报废类型">
          <el-input v-model="form.scrap_type" placeholder="报废类型" />
        </el-form-item>
        <el-form-item label="原值">
          <el-input-number v-model="form.original_value" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="净值">
          <el-input-number v-model="form.net_value" :min="0" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="折旧率(%)">
          <el-input-number v-model="form.depreciation_rate" :min="0" :max="100" :precision="2" style="width: 100%" />
        </el-form-item>
        <el-form-item label="处理人">
          <el-input v-model="form.handler" placeholder="处理人" />
        </el-form-item>
        <el-form-item label="处理人电话">
          <el-input v-model="form.handler_phone" placeholder="处理人电话" />
        </el-form-item>
        <el-form-item label="处理方式">
          <el-input v-model="form.disposal_method" placeholder="处理方式" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">确定</el-button>
      </template>
    </el-dialog>

    <!-- 审批对话框 -->
    <el-dialog v-model="showApproveDialog" title="审批报废" width="400px">
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

    <!-- 执行报废对话框 -->
    <el-dialog v-model="showExecuteDialog" title="执行报废" width="400px">
      <el-form label-width="100px">
        <el-form-item label="处理结果">
          <el-input v-model="executeForm.disposal_result" type="textarea" rows="3" placeholder="处理结果描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showExecuteDialog = false">取消</el-button>
        <el-button type="primary" @click="doExecute">确定报废</el-button>
      </template>
    </el-dialog>

    <!-- 详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="报废详情" width="700px">
      <el-descriptions :column="2" border>
        <el-descriptions-item label="报废单号">{{ currentRow?.scrap_no }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentRow?.status)">{{ currentRow?.status_text }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="资产名称">{{ currentRow?.asset_name }}</el-descriptions-item>
        <el-descriptions-item label="资产编号">{{ currentRow?.asset_code }}</el-descriptions-item>
        <el-descriptions-item label="报废类型">{{ currentRow?.scrap_type }}</el-descriptions-item>
        <el-descriptions-item label="原值">{{ currentRow?.original_value }}</el-descriptions-item>
        <el-descriptions-item label="净值">{{ currentRow?.net_value }}</el-descriptions-item>
        <el-descriptions-item label="折旧率">{{ currentRow?.depreciation_rate }}%</el-descriptions-item>
        <el-descriptions-item label="报废原因" :span="2">{{ currentRow?.scrap_reason }}</el-descriptions-item>
        <el-descriptions-item label="处理人">{{ currentRow?.handler }}</el-descriptions-item>
        <el-descriptions-item label="处理人电话">{{ currentRow?.handler_phone }}</el-descriptions-item>
        <el-descriptions-item label="处理方式">{{ currentRow?.disposal_method }}</el-descriptions-item>
        <el-descriptions-item label="审批人">{{ currentRow?.approver }}</el-descriptions-item>
        <el-descriptions-item label="审批意见" :span="2">{{ currentRow?.approve_comment }}</el-descriptions-item>
        <el-descriptions-item label="处理结果" :span="2">{{ currentRow?.disposal_result }}</el-descriptions-item>
      </el-descriptions>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, Refresh } from '@element-plus/icons-vue'
import { getScrapList, createScrap, updateScrap, getAssetList, approveScrap, executeScrap } from '@/api/asset'
import { getCustomerList } from '@/api/customer'

const loading = ref(false)
const scraps = ref([])
const customers = ref([])
const assetList = ref([])
const showCreateDialog = ref(false)
const showDetailDialog = ref(false)
const showApproveDialog = ref(false)
const showExecuteDialog = ref(false)
const isEdit = ref(false)
const submitting = ref(false)
const formRef = ref(null)
const currentRow = ref(null)

const filterForm = reactive({
  scrap_no: '',
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
  scrap_reason: '',
  scrap_type: '',
  original_value: 0,
  net_value: 0,
  depreciation_rate: 0,
  handler: '',
  handler_phone: '',
  disposal_method: ''
})

const approveComment = ref('')
const executeForm = reactive({
  disposal_result: ''
})

const formRules = {
  customer: [{ required: true, message: '请选择客户', trigger: 'change' }],
  asset: [{ required: true, message: '请选择资产', trigger: 'change' }],
  scrap_reason: [{ required: true, message: '请输入报废原因', trigger: 'blur' }]
}

function getStatusType(status) {
  const types = {
    APPLIED: 'info',
    APPROVED: 'success',
    REJECTED: 'danger',
    SCRAPPED: 'warning'
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
    const res = await getScrapList(params)
    scraps.value = res.results || res
    pagination.total = res.count || res.length
  } catch (e) {
    ElMessage.error('获取报废列表失败')
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
  filterForm.scrap_no = ''
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
    scrap_reason: '',
    scrap_type: '',
    original_value: 0,
    net_value: 0,
    depreciation_rate: 0,
    handler: '',
    handler_phone: '',
    disposal_method: ''
  })
  showCreateDialog.value = true
}

function handleEdit(row) {
  isEdit.value = true
  Object.assign(form, {
    customer: row.customer,
    asset: row.asset,
    scrap_reason: row.scrap_reason,
    scrap_type: row.scrap_type,
    original_value: row.original_value,
    net_value: row.net_value,
    depreciation_rate: row.depreciation_rate,
    handler: row.handler,
    handler_phone: row.handler_phone,
    disposal_method: row.disposal_method
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
    await approveScrap(currentRow.value.id, 'approve', approveComment.value)
    ElMessage.success('审批通过')
    showApproveDialog.value = false
    fetchData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

async function doReject() {
  try {
    await approveScrap(currentRow.value.id, 'reject', approveComment.value)
    ElMessage.success('已拒绝')
    showApproveDialog.value = false
    fetchData()
  } catch (e) {
    ElMessage.error('操作失败')
  }
}

function handleExecute(row) {
  currentRow.value = row
  executeForm.disposal_result = ''
  showExecuteDialog.value = true
}

async function doExecute() {
  try {
    await executeScrap(currentRow.value.id, executeForm.disposal_result)
    ElMessage.success('报废执行完成')
    showExecuteDialog.value = false
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
        await updateScrap(currentRow.value.id, form)
        ElMessage.success('更新成功')
      } else {
        await createScrap(form)
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
.scrap-list {
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
