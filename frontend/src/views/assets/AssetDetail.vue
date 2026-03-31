<template>
  <div class="asset-detail">
    <div class="header">
      <el-button @click="goBack">
        <el-icon><Back /></el-icon>
        返回
      </el-button>
      <div class="actions">
        <el-button type="primary" @click="goToEdit">
          <el-icon><Edit /></el-icon>
          编辑
        </el-button>
        <el-button
          v-if="asset.status === 'ACTIVE'"
          type="warning"
          @click="handleMaintenance"
        >
          设置维护
        </el-button>
        <el-button
          v-if="asset.status !== 'ACTIVE'"
          type="success"
          @click="handleActivate"
        >
          激活
        </el-button>
        <el-button type="danger" @click="handleDelete">
          <el-icon><Delete /></el-icon>
          删除
        </el-button>
      </div>
    </div>
    
    <el-row :gutter="20">
      <!-- 基本信息 -->
      <el-col :span="16">
        <el-card class="info-card">
          <template #header>
            <span>基本信息</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="资产编号">
              {{ asset.asset_code }}
            </el-descriptions-item>
            <el-descriptions-item label="资产名称">
              {{ asset.asset_name }}
            </el-descriptions-item>
            <el-descriptions-item label="资产类型">
              {{ asset.asset_type_name }}
            </el-descriptions-item>
            <el-descriptions-item label="所属客户">
              {{ asset.customer_name }}
            </el-descriptions-item>
            <el-descriptions-item label="状态">
              <el-tag :type="getStatusType(asset.status)">
                {{ getStatusText(asset.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="重要等级">
              <el-tag :type="getImportanceType(asset.importance_level)">
                {{ getImportanceText(asset.importance_level) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="位置">
              {{ asset.location || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="机房">
              {{ asset.room || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="机柜">
              {{ asset.rack || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="负责人">
              {{ asset.owner || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="部门">
              {{ asset.department || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="供应商">
              {{ asset.vendor || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="购买日期">
              {{ formatDate(asset.purchase_date) }}
            </el-descriptions-item>
            <el-descriptions-item label="保修到期">
              {{ formatDate(asset.warranty_end) }}
            </el-descriptions-item>
            <el-descriptions-item label="描述" :span="2">
              {{ asset.description || '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
        
        <!-- 字段数据 -->
        <el-card v-if="Object.keys(asset.field_data || {}).length > 0" class="info-card">
          <template #header>
            <span>配置信息</span>
          </template>
          <el-descriptions :column="2" border>
            <el-descriptions-item
              v-for="(data, key) in asset.field_data"
              :key="key"
              :label="data.label || key"
            >
              {{ data.value || '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
      
      <!-- 侧边信息 -->
      <el-col :span="8">
        <el-card class="info-card">
          <template #header>
            <span>操作记录</span>
          </template>
          <el-timeline>
            <el-timeline-item
              v-for="(item, index) in timeline"
              :key="index"
              :timestamp="item.timestamp"
              placement="top"
            >
              {{ item.content }}
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getAsset, deleteAsset, activateAsset, updateAsset } from '@/api/asset'
import { formatDate, getStatusType, getStatusText, getImportanceType, getImportanceText } from '@/utils/format'
import { Back, Edit, Delete } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const asset = ref({})
const timeline = ref([
  { timestamp: formatDate(new Date()), content: '资产创建' }
])

const assetId = route.params.id

onMounted(() => {
  loadAsset()
})

async function loadAsset() {
  try {
    const res = await getAsset(assetId)
    asset.value = res
  } catch (error) {
    console.error('加载资产详情失败:', error)
    ElMessage.error('加载资产详情失败')
  }
}

function goBack() {
  router.push('/assets')
}

function goToEdit() {
  router.push(`/assets/${assetId}/edit`)
}

async function handleActivate() {
  try {
    await activateAsset(assetId)
    ElMessage.success('资产已激活')
    loadAsset()
  } catch (error) {
    console.error('激活失败:', error)
  }
}

async function handleMaintenance() {
  try {
    await updateAsset(assetId, { status: 'MAINTENANCE' })
    ElMessage.success('资产已设置为维护状态')
    loadAsset()
  } catch (error) {
    console.error('设置维护失败:', error)
  }
}

async function handleDelete() {
  try {
    await ElMessageBox.confirm(
      `确定要删除资产 "${asset.value.asset_name}" 吗？删除后无法恢复。`,
      '警告',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await deleteAsset(assetId)
    ElMessage.success('删除成功')
    router.push('/assets')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除失败:', error)
    }
  }
}
</script>

<style scoped>
.asset-detail {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.actions {
  display: flex;
  gap: 10px;
}

.info-card {
  margin-bottom: 20px;
}
</style>