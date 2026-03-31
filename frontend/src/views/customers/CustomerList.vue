<template>
  <div class="customer-list">
    <div class="header">
      <h2>客户管理</h2>
    </div>
    
    <el-card>
      <el-table
        v-loading="loading"
        :data="customers"
        stripe
        style="width: 100%"
      >
        <el-table-column prop="customer_code" label="客户编码" width="150" />
        <el-table-column prop="customer_name" label="客户名称" min-width="180" />
        <el-table-column prop="customer_type" label="客户类型" width="120" />
        <el-table-column prop="industry" label="行业" width="100" />
        <el-table-column prop="contact_person" label="联系人" width="120" />
        <el-table-column prop="contact_phone" label="联系电话" width="150" />
        <el-table-column label="资产统计" width="180">
          <template #default="{ row }">
            <span>总数: {{ row.asset_count || 0 }}</span>
            <el-divider direction="vertical" />
            <span>活跃: {{ row.active_asset_count || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'">
              {{ row.status === 'ACTIVE' ? '活跃' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getCustomerList } from '@/api/customer'
import { formatDate } from '@/utils/format'

const loading = ref(false)
const customers = ref([])

onMounted(() => {
  loadCustomers()
})

async function loadCustomers() {
  loading.value = true
  try {
    const res = await getCustomerList({ page_size: 100 })
    customers.value = res.results || []
  } catch (error) {
    console.error('加载客户失败:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.customer-list {
  padding: 20px;
}

.header {
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}
</style>