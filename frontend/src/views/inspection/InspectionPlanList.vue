<template>
  <div class="inspection-plan">
    <div class="page-header">
      <h2>巡检计划</h2>
      <el-button type="primary" @click="showCreate">
        <el-icon><Plus /></el-icon> 新建计划
      </el-button>
    </div>

    <!-- 按协议分组的卡片 -->
    <div class="protocol-section" v-for="cat in categories" :key="cat.code">
      <div class="category-title">{{ cat.name }}</div>
      <el-row :gutter="12" class="protocol-cards">
        <el-col :span="4" v-for="g in cat.protocols" :key="g.code">
          <el-card
            class="protocol-card"
            :class="{ active: selectedProtocol === g.code }"
            @click="filterByProtocol(g.code)"
            shadow="hover"
          >
            <div class="protocol-icon">{{ g.icon }}</div>
            <div class="protocol-name">{{ g.name }}</div>
            <div class="protocol-count">{{ getProtocolCount(g.code) }} 个计划</div>
            <div class="protocol-checks">{{ g.check_count }} 项检查</div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar" v-if="selectedProtocol">
      <el-tag closable @close="selectedProtocol = null" type="primary" size="large">
        当前筛选: {{ getProtocolName(selectedProtocol) }}
      </el-tag>
      <span class="filter-count">共 {{ filteredPlans.length }} 个计划</span>
    </div>

    <!-- 计划列表 -->
    <el-card class="table-card">
      <el-table :data="filteredPlans" v-loading="loading" stripe>
        <el-table-column prop="name" label="计划名称" min-width="160" />
        <el-table-column prop="code" label="编码" width="140" />
        <el-table-column label="协议类型" width="110">
          <template #default="{ row }">
            <el-tag :type="getProtocolTagType(row.protocol)" size="small">
              {{ getProtocolIcon(row.protocol) }} {{ row.protocol_display || getProtocolName(row.protocol) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="巡检项目" min-width="280">
          <template #default="{ row }">
            <div class="check-items-preview">
              <el-tag
                v-for="(item, idx) in extractCheckItems(row).slice(0, 4)"
                :key="idx"
                size="small"
                type="info"
                class="check-item-tag"
              >
                {{ item.name }}
              </el-tag>
              <el-tooltip
                v-if="extractCheckItems(row).length > 4"
                :content="extractCheckItems(row).slice(4).map(i => i.name).join(', ')"
                placement="top"
              >
                <el-tag size="small" type="info">+{{ extractCheckItems(row).length - 4 }}项</el-tag>
              </el-tooltip>
              <span v-if="extractCheckItems(row).length === 0" class="no-items">未配置</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="周期" width="70">
          <template #default="{ row }">{{ row.cycle_display }}</template>
        </el-table-column>
        <el-table-column label="执行时间" width="80">
          <template #default="{ row }">{{ row.scheduled_time }}</template>
        </el-table-column>
        <el-table-column label="自动" width="60" align="center">
          <template #default="{ row }">
            <el-tag :type="row.is_auto_execute ? 'success' : 'info'" size="small">
              {{ row.is_auto_execute ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="70">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">{{ row.status_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="executePlan(row)" :loading="row._executing">
              <el-icon><VideoPlay /></el-icon> 执行
            </el-button>
            <el-button link type="warning" size="small" @click="showEdit(row)">
              <el-icon><Edit /></el-icon> 编辑
            </el-button>
            <el-button link type="info" size="small" @click="viewResults(row)">
              <el-icon><View /></el-icon> 记录
            </el-button>
            <el-button link type="danger" size="small" @click="deletePlan(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-empty v-if="!loading && filteredPlans.length === 0" description="暂无巡检计划" />
    </el-card>

    <!-- 新建/编辑计划弹窗 -->
    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑巡检计划' : '新建巡检计划'" width="800px" destroy-on-close>
      <el-form :model="form" label-width="100px">
        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="计划名称" required>
              <el-input v-model="form.name" placeholder="如：MSSQL日常巡检" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="计划编码" required>
              <el-input v-model="form.code" placeholder="如：db-mssql-daily" :disabled="isEdit" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="巡检计划描述" />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="协议类型" required>
              <el-select v-model="form.protocol" style="width:100%" @change="handleProtocolChange">
                <el-option-group label="数据库">
                  <el-option label="🐬 MySQL" value="mysql" />
                  <el-option label="🗄️ MSSQL" value="mssql" />
                  <el-option label="🔴 Oracle" value="oracle" />
                  <el-option label="🐘 PostgreSQL" value="postgresql" />
                </el-option-group>
                <el-option-group label="设备">
                  <el-option label="📡 SNMP设备" value="snmp" />
                  <el-option label="🖥️ SSH服务器" value="ssh" />
                </el-option-group>
                <el-option-group label="网络">
                  <el-option label="🌐 Ping检测" value="ping" />
                  <el-option label="🔌 端口检测" value="port" />
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
          <el-col :span="8">
            <el-form-item label="执行时间">
              <el-time-picker v-model="form.scheduled_time" format="HH:mm" value-format="HH:mm:ss" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="自动执行">
              <el-switch v-model="form.is_auto_execute" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="状态">
              <el-select v-model="form.status" style="width:100%">
                <el-option label="启用" value="active" />
                <el-option label="草稿" value="draft" />
                <el-option label="暂停" value="paused" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 巡检项目选择 -->
        <el-form-item label="巡检项目">
          <div class="check-items-select" v-loading="checkItemsLoading">
            <div class="check-items-header">
              <el-checkbox
                v-model="checkAll"
                :indeterminate="isIndeterminate"
                @change="handleCheckAll"
              >
                全选
              </el-checkbox>
              <span class="check-items-count">
                已选 <b>{{ selectedCodes.length }}</b> / {{ availableChecks.length }} 项
              </span>
            </div>
            <div class="check-items-grid">
              <div
                v-for="item in availableChecks"
                :key="item.code"
                class="check-item-card"
                :class="{ selected: selectedCodes.includes(item.code) }"
                @click="toggleCheckItem(item.code)"
              >
                <el-checkbox
                  :model-value="selectedCodes.includes(item.code)"
                  @click.stop
                  @change="() => toggleCheckItem(item.code)"
                />
                <div class="check-item-body">
                  <div class="check-item-name">{{ item.name }}</div>
                  <div class="check-item-desc">{{ item.description }}</div>
                </div>
              </div>
            </div>
            <div v-if="availableChecks.length === 0" class="no-checks">
              请先选择协议类型
            </div>
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitting">
          {{ isEdit ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, VideoPlay, View, Edit } from '@element-plus/icons-vue'
import axios from '@/utils/axios'
import { useRouter } from 'vue-router'

const router = useRouter()
const loading = ref(false)
const submitting = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const editId = ref(null)
const plans = ref([])
const assets = ref([])
const categories = ref([])
const selectedProtocol = ref(null)
const checkItemsLoading = ref(false)

// 表单（只存基本字段，巡检项目用 selectedCodes）
const form = reactive({
  name: '', code: '', description: '', protocol: 'mysql',
  cycle: 'daily', scheduled_time: '09:00:00', is_auto_execute: true,
  status: 'active'
})

// 当前协议可用的巡检项目字典
const availableChecks = ref([])
// 用户勾选的 code 列表
const selectedCodes = ref([])

// 全选状态
const checkAll = ref(false)
const isIndeterminate = ref(false)

function updateCheckState() {
  const total = availableChecks.value.length
  const selected = selectedCodes.value.length
  checkAll.value = total > 0 && selected === total
  isIndeterminate.value = selected > 0 && selected < total
}

function handleCheckAll(val) {
  selectedCodes.value = val ? availableChecks.value.map(c => c.code) : []
  updateCheckState()
}

function toggleCheckItem(code) {
  const idx = selectedCodes.value.indexOf(code)
  if (idx >= 0) {
    selectedCodes.value.splice(idx, 1)
  } else {
    selectedCodes.value.push(code)
  }
  updateCheckState()
}

// ---------- 工具函数 ----------

function extractCheckItems(row) {
  const items = row.check_items || []
  if (!items.length) return []
  if (typeof items[0] === 'object' && items[0] !== null) {
    return items.map(i => ({ name: i.name || i.code, code: i.code }))
  }
  return items.map(code => {
    const dict = availableChecks.value.find(c => c.code === code)
    return { name: dict?.name || code, code }
  })
}

function getProtocolCount(code) {
  return plans.value.filter(p => p.protocol === code).length
}

const filteredPlans = computed(() => {
  if (!selectedProtocol.value) return plans.value
  return plans.value.filter(p => p.protocol === selectedProtocol.value)
})

function filterByProtocol(code) {
  selectedProtocol.value = selectedProtocol.value === code ? null : code
}

const protocolMap = {
  mysql: { name: 'MySQL', icon: '🐬', type: '' },
  mssql: { name: 'MSSQL', icon: '🗄️', type: 'danger' },
  oracle: { name: 'Oracle', icon: '🔴', type: 'warning' },
  postgresql: { name: 'PostgreSQL', icon: '🐘', type: '' },
  snmp: { name: 'SNMP', icon: '📡', type: 'success' },
  ssh: { name: 'SSH', icon: '🖥️', type: 'info' },
  ping: { name: 'Ping', icon: '🌐', type: '' },
  port: { name: '端口检测', icon: '🔌', type: 'info' },
}

function getProtocolName(code) { return protocolMap[code]?.name || code }
function getProtocolIcon(code) { return protocolMap[code]?.icon || '📋' }
function getProtocolTagType(code) { return protocolMap[code]?.type || 'info' }
function getStatusType(status) {
  return { active: 'success', draft: 'info', paused: 'warning', archived: 'info' }[status] || 'info'
}

// ---------- 数据加载 ----------

function extractArray(res) {
  // 统一从 axios 响应中提取数组
  // axios 响应: { data: { success: true, data: [...] } } 或 { data: { results: [...] } }
  const body = res.data ?? res
  if (Array.isArray(body)) return body
  if (Array.isArray(body.data)) return body.data
  if (Array.isArray(body.results)) return body.results
  return []
}

async function loadCategories() {
  try {
    const res = await axios.get('/api/inspection/plans/categories/')
    categories.value = extractArray(res)
  } catch (e) { console.error('加载分类失败:', e) }
}

async function loadCheckItems(protocol) {
  checkItemsLoading.value = true
  try {
    const res = await axios.get(`/api/inspection/plans/check_items/?protocol=${protocol}`)
    availableChecks.value = extractArray(res)
  } catch (e) {
    console.error('加载巡检项目失败:', e)
    availableChecks.value = []
  } finally {
    checkItemsLoading.value = false
  }
}

function handleProtocolChange(protocol) {
  loadCheckItems(protocol)
  selectedCodes.value = []
}

async function loadPlans() {
  loading.value = true
  try {
    const res = await axios.get('/api/inspection/plans/')
    const body = res.data ?? res
    const list = body.results || body.data?.results || extractArray(res)
    plans.value = list.map(p => ({ ...p, _executing: false }))
  } catch { ElMessage.error('加载失败') }
  finally { loading.value = false }
}

async function loadAssets() {
  try {
    const res = await axios.get('/api/assets/assets/', { params: { page_size: 100 } })
    const body = res.data ?? res
    assets.value = body.results || body.data?.results || extractArray(res)
  } catch { /* ignore */ }
}

// ---------- 新建 ----------

async function showCreate() {
  isEdit.value = false
  editId.value = null
  Object.assign(form, {
    name: '', code: '', description: '', protocol: 'mysql',
    cycle: 'daily', scheduled_time: '09:00:00', is_auto_execute: true,
    status: 'active'
  })
  await loadCheckItems('mysql')
  // 默认全选
  selectedCodes.value = availableChecks.value.map(c => c.code)
  updateCheckState()
  dialogVisible.value = true
}

// ---------- 编辑 ----------

async function showEdit(row) {
  isEdit.value = true
  editId.value = row.id
  Object.assign(form, {
    name: row.name,
    code: row.code,
    description: row.description || '',
    protocol: row.protocol || 'mysql',
    cycle: row.cycle || 'daily',
    scheduled_time: row.scheduled_time || '09:00:00',
    is_auto_execute: row.is_auto_execute ?? true,
    status: row.status || 'active'
  })
  // 先加载该协议的字典
  await loadCheckItems(form.protocol)
  // 再恢复已选中项（兼容对象数组和 code 数组）
  const existing = row.check_items || []
  if (existing.length > 0 && typeof existing[0] === 'object') {
    selectedCodes.value = existing.map(i => i.code)
  } else if (existing.length > 0 && typeof existing[0] === 'string') {
    selectedCodes.value = [...existing]
  } else {
    selectedCodes.value = availableChecks.value.map(c => c.code)
  }
  updateCheckState()
  dialogVisible.value = true
}

// ---------- 提交 ----------

async function handleSubmit() {
  if (!form.name || !form.code) { ElMessage.warning('请填写名称和编码'); return }
  if (!form.protocol) { ElMessage.warning('请选择协议类型'); return }
  if (selectedCodes.value.length === 0) { ElMessage.warning('请至少选择一个巡检项目'); return }

  submitting.value = true
  try {
    const data = {
      ...form,
      check_items: selectedCodes.value.map(code => {
        const item = availableChecks.value.find(c => c.code === code)
        return { code, name: item?.name || code, method: item?.method || '', description: item?.description || '' }
      })
    }

    if (isEdit.value) {
      await axios.patch(`/api/inspection/plans/${editId.value}/`, data)
      ElMessage.success('保存成功')
    } else {
      await axios.post('/api/inspection/plans/', data)
      ElMessage.success('创建成功')
    }

    dialogVisible.value = false
    loadPlans()
    loadCategories()
  } catch (e) {
    ElMessage.error(isEdit.value ? '保存失败' : '创建失败')
    console.error(e)
  } finally {
    submitting.value = false
  }
}

// ---------- 其他操作 ----------

async function executePlan(row) {
  row._executing = true
  try {
    // 找到所有匹配协议的资产
    const p = (row.protocol || '').toLowerCase()
    const matchedAssets = assets.value.filter(a => {
      const name = (a.asset_name || '').toLowerCase()
      const proto = (a.protocol || '').toLowerCase()
      return proto === p || name.includes(p)
    })

    if (matchedAssets.length === 0) {
      ElMessage.warning(`没有找到协议为 ${row.protocol} 的资产`)
      return
    }

    let successCount = 0
    let failCount = 0
    const isDb = ['mysql', 'mssql', 'oracle', 'postgresql'].includes(row.protocol)

    for (const asset of matchedAssets) {
      try {
        // 创建巡检任务
        const taskRes = await axios.post('/api/inspection/tasks/', {
          plan: row.id, asset: asset.id,
          scheduled_time: new Date().toISOString(), priority: 'high', status: 'pending'
        })
        const taskId = taskRes.id || taskRes.data?.id

        // 执行巡检
        if (isDb) {
          await axios.post(`/api/inspection/tasks/${taskId}/execute_db_inspection/`)
        } else {
          await axios.post(`/api/inspection/tasks/${taskId}/execute/`)
        }
        successCount++
      } catch (e) {
        failCount++
        console.error(`巡检失败 ${asset.asset_name}:`, e)
      }
    }

    ElMessage.success(`巡检完成: ${successCount}个成功, ${failCount}个失败 (共${matchedAssets.length}个资产)`)
    router.push('/inspection/records')
  } catch (e) {
    ElMessage.error(`执行失败: ${e.response?.data?.message || e.message || ''}`)
  } finally { row._executing = false }
}

function viewResults(row) { router.push('/inspection/records') }

async function deletePlan(row) {
  await ElMessageBox.confirm('确定删除此计划?', '提示')
  try {
    await axios.delete(`/api/inspection/plans/${row.id}/`)
    ElMessage.success('已删除')
    loadPlans()
    loadCategories()
  } catch { ElMessage.error('删除失败') }
}

onMounted(() => {
  loadCategories()
  loadPlans()
  loadAssets()
})
</script>

<style scoped>
.inspection-plan { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; font-size: 18px; font-weight: 500; }

.protocol-section { margin-bottom: 16px; }
.category-title {
  font-size: 14px; font-weight: 600; color: #606266;
  margin-bottom: 8px; padding-left: 4px;
}
.protocol-cards { margin-bottom: 8px; }
.protocol-card {
  text-align: center; cursor: pointer; transition: all 0.2s;
  min-height: 110px;
}
.protocol-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.1); }
.protocol-card.active { border: 2px solid #409eff; background: #ecf5ff; }
.protocol-icon { font-size: 28px; margin-bottom: 6px; }
.protocol-name { font-weight: 500; font-size: 13px; }
.protocol-count { font-size: 12px; color: #909399; margin-top: 4px; }
.protocol-checks { font-size: 11px; color: #b0b4bb; margin-top: 2px; }

.filter-bar {
  display: flex; align-items: center; gap: 12px;
  margin-bottom: 12px; padding: 8px 12px;
  background: #f5f7fa; border-radius: 8px;
}
.filter-count { font-size: 13px; color: #909399; }

.table-card { background: white; }

/* 表格内巡检项目预览 */
.check-items-preview { display: flex; flex-wrap: wrap; gap: 4px; }
.check-item-tag { margin: 0; }
.no-items { color: #c0c4cc; font-size: 12px; }

/* 弹窗内巡检项目选择 */
.check-items-select {
  width: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  padding: 12px;
  background: #fafafa;
  max-height: 360px;
  overflow-y: auto;
}
.check-items-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
  position: sticky;
  top: 0;
  background: #fafafa;
  z-index: 1;
}
.check-items-count { font-size: 13px; color: #909399; }
.check-items-count b { color: #409eff; }

.check-items-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.check-item-card {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 8px;
  background: #fff;
  border: 1.5px solid #e4e7ed;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
}
.check-item-card:hover {
  border-color: #409eff;
  background: #f0f7ff;
}
.check-item-card.selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.check-item-body {
  flex: 1;
  min-width: 0;
}
.check-item-name {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  line-height: 1.4;
}
.check-item-desc {
  font-size: 11px;
  color: #909399;
  margin-top: 2px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.no-checks {
  text-align: center;
  color: #c0c4cc;
  padding: 24px 0;
  font-size: 13px;
}
</style>
