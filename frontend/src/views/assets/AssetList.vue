<template>
  <div class="asset-list">
    <div class="header">
      <h2>资产管理</h2>
      <el-button type="primary" @click="goToCreate">
        <el-icon><Plus /></el-icon>
        新建资产
      </el-button>
      <el-button @click="handleRefresh">
        <el-icon><Refresh /></el-icon>
        刷新并检测在线状态
      </el-button>
    </div>
    
    <!-- 搜索和筛选 -->
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm">
        <el-form-item label="客户">
          <el-select
            v-model="filterForm.customer"
            placeholder="选择客户"
            clearable
            style="width: 200px"
            @change="handleFilterChange"
          >
            <el-option
              v-for="customer in customers"
              :key="customer.id"
              :label="customer.customer_name"
              :value="customer.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="资产类型">
          <el-select
            v-model="filterForm.asset_type"
            placeholder="选择类型"
            clearable
            style="width: 150px"
            @change="handleFilterChange"
          >
            <el-option
              v-for="type in assetTypes"
              :key="type.id"
              :label="type.type_name"
              :value="type.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="状态">
          <el-select
            v-model="filterForm.status"
            placeholder="选择状态"
            clearable
            style="width: 120px"
            @change="handleFilterChange"
          >
            <el-option label="活跃" value="ACTIVE" />
            <el-option label="停用" value="INACTIVE" />
            <el-option label="维护中" value="MAINTENANCE" />
            <el-option label="已退役" value="DECOMMISSIONED" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="关键词">
          <el-input
            v-model="filterForm.search"
            placeholder="搜索资产编号/名称"
            clearable
            @keyup.enter="handleFilterChange"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="handleFilterChange">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="handleReset">
            <el-icon><Refresh /></el-icon>
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>
    
    <!-- 数据表格 -->
    <el-card class="table-card">
      <el-table
        v-loading="loading"
        :data="assets"
        stripe
        style="width: 100%"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        
        <el-table-column prop="asset_code" label="资产编号" width="150">
          <template #default="{ row }">
            <el-link type="primary" @click="goToDetail(row.id)">
              {{ row.asset_code }}
            </el-link>
          </template>
        </el-table-column>
        
        <el-table-column prop="asset_name" label="资产名称" min-width="180" />
        
        <el-table-column prop="asset_type_name" label="资产类型" width="120" />
        
        <el-table-column prop="customer_name" label="所属客户" width="150" />

        <el-table-column prop="online" label="在线状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getOnlineType(row.online)" size="small">
              {{ getOnlineText(row.online) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="资产状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="importance_level" label="重要等级" width="100">
          <template #default="{ row }">
            <el-tag :type="getImportanceType(row.importance_level)">
              {{ getImportanceText(row.importance_level) }}
            </el-tag>
          </template>
        </el-table-column>
        
        <el-table-column prop="owner" label="负责人" width="100" />
        
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="goToDetail(row.id)">
              <el-icon><View /></el-icon>
              详情
            </el-button>
            <el-button type="primary" link @click="goToEdit(row.id)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button type="danger" link @click="handleDelete(row)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <!-- 分页 -->
      <div class="pagination">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.page_size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="loadAssets"
          @current-change="loadAssets"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAssetList, deleteAsset, getAssetTypeList } from '@/api/asset'
import { getCustomerList } from '@/api/customer'
import api from '@/api/index'
import { formatDate, getStatusType, getStatusText, getImportanceType, getImportanceText, getOnlineType, getOnlineText } from '@/utils/format'
import { Plus, Search, Refresh, View, Edit, Delete } from '@element-plus/icons-vue'

const router = useRouter()

const loading = ref(false)
const assets = ref([])
const customers = ref([])
const assetTypes = ref([])

const filterForm = reactive({
  customer: null,
  asset_type: null,
  status: '',
  search: ''
})

const pagination = reactive({
  page: 1,
  page_size: 20,
  total: 0
})

let refreshInterval = null

async function handleRefresh() {
  // 先ping检测所有资产，刷新在线状态
  try {
    await api.post('/dashboard/health/')
  } catch (e) {
    console.error('刷新资产在线状态失败:', e)
  }
  await loadAssets()
}

onMounted(() => {
  loadCustomers()
  loadAssetTypes()
  handleRefresh()
  // 每60秒自动刷新一次（ping检测在线状态）
  refreshInterval = setInterval(handleRefresh, 60000)
})

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})

async function loadCustomers() {
  try {
    const res = await getCustomerList({ page_size: 100 })
    customers.value = res.results || []
  } catch (error) {
    console.error('加载客户失败:', error)
  }
}

async function loadAssetTypes() {
  try {
    const res = await getAssetTypeList({ page_size: 100 })
    assetTypes.value = res.results || []
  } catch (error) {
    console.error('加载资产类型失败:', error)
  }
}

async function loadAssets() {
  loading.value = true
  try {
    const params = {
      page: pagination.page,
      page_size: pagination.page_size
    }
    
    if (filterForm.customer) {
      params.customer = filterForm.customer
    }
    if (filterForm.asset_type) {
      params.asset_type = filterForm.asset_type
    }
    if (filterForm.status) {
      params.status = filterForm.status
    }
    if (filterForm.search) {
      params.search = filterForm.search
    }
    
    const res = await getAssetList(params)
    assets.value = res.results || []
    pagination.total = res.count || 0
  } catch (error) {
    console.error('加载资产失败:', error)
    ElMessage.error('加载资产列表失败')
  } finally {
    loading.value = false
  }
}

function handleFilterChange() {
  pagination.page = 1
  loadAssets()
}

function handleReset() {
  filterForm.customer = null
  filterForm.asset_type = null
  filterForm.status = ''
  filterForm.search = ''
  pagination.page = 1
  loadAssets()
}

function handleSelectionChange(selection) {
  console.log('selection:', selection)
}

function goToCreate() {
  router.push('/assets/create')
}

function goToDetail(id) {
  router.push(`/assets/${id}`)
}

function goToEdit(id) {
  router.push(`/assets/${id}/edit`)
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(
      `确定要删除资产 "${row.asset_name}" 吗？删除后无法恢复。`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await deleteAsset(row.id)
    ElMessage.success('删除成功')
    loadAssets()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}
</script>

<style scoped>
.asset-list {
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
  font-size: 24px;
  font-weight: 600;
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