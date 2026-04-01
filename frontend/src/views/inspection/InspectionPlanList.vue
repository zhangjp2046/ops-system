<template>
  <div class="inspection-plan">
    <div class="page-header">
      <h2>巡检计划</h2>
      <el-button type="primary" @click="showCreate">
        <el-icon><Plus /></el-icon> 新建计划
      </el-button>
    </div>

    <!-- 按协议分组的卡片 -->
    <el-row :gutter="16" class="protocol-cards">
      <el-col :span="4" v-for="g in protocolGroups" :key="g.code">
        <el-card class="protocol-card" :class="{ active: selectedProtocol === g.code }" @click="filterByProtocol(g.code)">
          <div class="protocol-icon">{{ g.icon }}</div>
          <div class="protocol-name">{{ g.name }}</div>
          <div class="protocol-count">{{ g.count }} 个计划</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 计划列表 -->
    <el-card class="table-card">
      <el-table :data="filteredPlans" v-loading="loading" stripe>
        <el-table-column prop="name" label="计划名称" min-width="180" />
        <el-table-column prop="code" label="编码" width="140" />
        <el-table-column label="协议/类型" width="120">
          <template #default="{ row }">
            <el-tag :type="getProtocolType(row)" size="small">{{ getProtocolLabel(row) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="周期" width="80">
          <template #default="{ row }">{{ row.cycle_display }}</template>
        </el-table-column>
        <el-table-column label="执行时间" width="80">
          <template #default="{ row }">{{ row.scheduled_time }}</template>
        </el-table-column>
        <el-table-column label="自动执行" width="80" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_auto_execute ? 'success' : 'info'" size="small">
              {{ row.is_auto_execute ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="executePlan(row)" :loading="row._executing">
              <el-icon><VideoPlay /></el-icon> 执行
            </el-button>
            <el-button link type="info" size="small" @click="viewResults(row)">
              <el-icon><View /></el-icon> 记录
            </el-button>
            <el-button link type="danger" size="small" @click="deletePlan(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建计划弹窗 -->
    <el-dialog v-model="createVisible" title="新建巡检计划" width="650px">
      <el-form :model="form" label-width="110px">
        <el-form-item label="计划名称" required>
          <el-input v-model="form.name" placeholder="如：MSSQL日常巡检" />
        </el-form-item>
        <el-form-item label="计划编码" required>
          <el-input v-model="form.code" placeholder="如：db-mssql-daily" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="协议/类型">
              <el-select v-model="form.protocol" style="width:100%">
                <el-option-group label="数据库">
                  <el-option label="MySQL" value="mysql" />
                  <el-option label="MSSQL" value="mssql" />
                  <el-option label="Oracle" value="oracle" />
                  <el-option label="PostgreSQL" value="postgresql" />
                </el-option-group>
                <el-option-group label="设备">
                  <el-option label="SNMP设备" value="snmp" />
                  <el-option label="SSH服务器" value="ssh" />
                </el-option-group>
                <el-option-group label="通用">
                  <el-option label="Ping检测" value="ping" />
                  <el-option label="端口检测" value="port" />
                </el-option-group>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="执行周期">
              <el-select v-model="form.cycle" style="width:100%">
                <el-option label="每天" value="daily" />
                <el-option label="每周" value="weekly" />
                <el-option label="每月" value="monthly" />
                <el-option label="每季度" value="quarterly" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="执行时间">
              <el-time-picker v-model="form.scheduled_time" format="HH:mm" value-format="HH:mm:ss" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="自动执行">
              <el-switch v-model="form.is_auto_execute" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="关联资产">
          <el-select v-model="form.asset_ids" multiple placeholder="选择资产" style="width:100%">
            <el-option v-for="a in assets" :key="a.id" :label="`${a.asset_name} (${a.protocol || '无协议'})`" :value="a.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="createPlan" :loading="creating">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, VideoPlay, View } from '@element-plus/icons-vue'
import axios from '@/utils/axios'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(false)
const creating = ref(false)
const createVisible = ref(false)
const plans = ref([])
const assets = ref([])
const selectedProtocol = ref(null)

const form = reactive({
  name: '', code: '', description: '', protocol: 'mssql',
  cycle: 'daily', scheduled_time: '09:00:00', is_auto_execute: true, asset_ids: []
})

const protocolGroups = computed(() => {
  const groups = [
    { code: 'mssql', name: 'MSSQL', icon: '🗄️' },
    { code: 'mysql', name: 'MySQL', icon: '🐬' },
    { code: 'oracle', name: 'Oracle', icon: '🔴' },
    { code: 'snmp', name: 'SNMP', icon: '📡' },
    { code: 'ssh', name: 'SSH', icon: '🖥️' },
    { code: 'ping', name: 'Ping', icon: '🌐' },
  ]
  return groups.map(g => ({
    ...g,
    count: plans.value.filter(p => {
      const desc = (p.description || '').toLowerCase()
      const name = (p.name || '').toLowerCase()
      return desc.includes(g.code) || name.includes(g.code.toLowerCase()) || name.includes(g.name.toLowerCase())
    }).length
  }))
})

const filteredPlans = computed(() => {
  if (!selectedProtocol.value) return plans.value
  const p = selectedProtocol.value
  return plans.value.filter(plan => {
    const desc = (plan.description || '').toLowerCase()
    const name = (plan.name || '').toLowerCase()
    return desc.includes(p) || name.includes(p) || name.includes(p.toLowerCase())
  })
})

function filterByProtocol(code) {
  selectedProtocol.value = selectedProtocol.value === code ? null : code
}

function getProtocolLabel(row) {
  const name = (row.name || '').toLowerCase()
  if (name.includes('mssql') || name.includes('sql server')) return 'MSSQL'
  if (name.includes('mysql') || name.includes('maria')) return 'MySQL'
  if (name.includes('oracle')) return 'Oracle'
  if (name.includes('snmp')) return 'SNMP'
  if (name.includes('ssh')) return 'SSH'
  if (name.includes('ping')) return 'Ping'
  return '通用'
}

function getProtocolType(row) {
  const label = getProtocolLabel(row)
  const map = { MSSQL: 'danger', MySQL: '', Oracle: 'warning', SNMP: 'success', SSH: 'info', Ping: '' }
  return map[label] || 'info'
}

function getStatusType(status) {
  return { active: 'success', draft: 'info', paused: 'warning', archived: 'info' }[status] || 'info'
}

async function loadPlans() {
  loading.value = true
  try {
    const res = await axios.get('/api/inspection/plans/')
    plans.value = (res.results || res.data?.results || []).map(p => ({ ...p, _executing: false }))
  } catch { ElMessage.error('加载失败') }
  finally { loading.value = false }
}

async function loadAssets() {
  try {
    const res = await axios.get('/api/assets/assets/', { params: { page_size: 100 } })
    assets.value = res.results || res.data?.results || []
  } catch { /* ignore */ }
}

function showCreate() {
  Object.assign(form, { name: '', code: '', description: '', protocol: 'mssql', cycle: 'daily', scheduled_time: '09:00:00', is_auto_execute: true, asset_ids: [] })
  createVisible.value = true
}

async function createPlan() {
  if (!form.name || !form.code) { ElMessage.warning('请填写名称和编码'); return }
  creating.value = true
  try {
    const data = { ...form, status: 'active' }
    await axios.post('/api/inspection/plans/', data)
    ElMessage.success('创建成功')
    createVisible.value = false
    loadPlans()
  } catch { ElMessage.error('创建失败') }
  finally { creating.value = false }
}

async function executePlan(row) {
  row._executing = true
  try {
    // 创建巡检任务并执行
    const taskRes = await axios.post('/api/inspection/tasks/', {
      plan: row.id,
      asset: 2, // TODO: 从计划关联的资产中选择
      scheduled_time: new Date().toISOString(),
      priority: 'high',
      status: 'pending'
    })
    const taskId = taskRes.id || taskRes.data?.id

    // 执行巡检
    await axios.post(`/api/inspection/tasks/${taskId}/execute_db_inspection/`)
    ElMessage.success('巡检已执行')
    router.push('/inspection/records')
  } catch (e) {
    ElMessage.error(`执行失败: ${e.message || ''}`)
  } finally { row._executing = false }
}

function viewResults(row) {
  router.push('/inspection/records')
}

async function deletePlan(row) {
  await ElMessageBox.confirm('确定删除此计划?', '提示')
  try {
    await axios.delete(`/api/inspection/plans/${row.id}/`)
    ElMessage.success('已删除')
    loadPlans()
  } catch { ElMessage.error('删除失败') }
}

onMounted(() => {
  loadPlans()
  loadAssets()
})
</script>

<style scoped>
.inspection-plan { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; font-size: 18px; font-weight: 500; }

.protocol-cards { margin-bottom: 16px; }
.protocol-card {
  text-align: center; cursor: pointer; transition: all 0.2s;
}
.protocol-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.protocol-card.active { border: 2px solid #409eff; }
.protocol-icon { font-size: 28px; margin-bottom: 8px; }
.protocol-name { font-weight: 500; font-size: 14px; }
.protocol-count { font-size: 12px; color: #909399; margin-top: 4px; }

.table-card { background: white; }
</style>
