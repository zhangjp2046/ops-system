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
        <el-table-column label="设备类型" width="150">
          <template #default="{ row }">
            <div v-if="row.asset_type_names?.length">
              <el-tag v-for="t in row.asset_type_names" :key="t.id" size="small" style="margin:1px">
                {{ t.name }}
              </el-tag>
            </div>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="设备数" width="80">
          <template #default="{ row }">
            <el-tag type="primary" size="small">{{ row.asset_count || '-' }}</el-tag>
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

        </el-row>

        <!-- 设备类型选择（按协议筛选后） -->
        <el-form-item label="设备类型" v-if="assetGroups.length > 0">
          <div class="asset-type-select">
            <div class="asset-type-header">
              <el-checkbox
                v-model="assetTypeAll"
                :indeterminate="assetTypeIndeterminate"
                @change="handleAssetTypeAll"
              >
                全选
              </el-checkbox>
              <span class="asset-type-count">
                已选 <b>{{ selectedTypeIds.length }}</b> 个类型，共 <b>{{ selectedAssetCount }}</b> 台设备
                <el-button link type="primary" size="small" style="margin-left:8px" @click="showSelectedAssets">
                  查看设备清单
                </el-button>
              </span>
            </div>
            <div class="asset-type-grid">
              <div
                v-for="group in assetGroups"
                :key="group.type_id"
                class="asset-type-card"
                :class="{ selected: selectedTypeIds.includes(group.type_id) }"
                @click="toggleAssetType(group.type_id)"
              >
                <el-checkbox
                  :model-value="selectedTypeIds.includes(group.type_id)"
                  @click.stop
                  @change="() => toggleAssetType(group.type_id)"
                />
                <div class="asset-type-body">
                  <div class="asset-type-name">{{ group.type_name }}</div>
                  <div class="asset-type-count-label">{{ group.asset_count }} 台设备</div>
                </div>
              </div>
            </div>
            <div v-if="assetGroups.length === 0" class="no-assets">
              暂未加载资产数据
            </div>
          </div>
        </el-form-item>

        <!-- 设备清单弹窗 -->
        <el-dialog v-model="assetDialogVisible" title="选中的设备清单" width="700px" append-to-body>
          <el-table :data="selectedAssetsList" stripe size="small" max-height="400">
            <el-table-column prop="name" label="资产名称" min-width="200" />
            <el-table-column prop="asset_code" label="资产编号" width="120" />
            <el-table-column prop="ip" label="IP地址" width="140" />
            <el-table-column label="类型" width="120">
              <template #default="{ row }">
                {{ getAssetTypeName(row.type_id) }}
              </template>
            </el-table-column>
          </el-table>
          <template #footer>
            <span>共 <b>{{ selectedAssetsList.length }}</b> 台设备</span>
            <el-button @click="assetDialogVisible = false">关闭</el-button>
          </template>
        </el-dialog>

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
            <!-- 时间同步告警阈值（仅勾选「时间同步」时显示） -->
            <div v-if="selectedCodes.includes('TIME_SYNC')" class="time-sync-threshold">
              <span class="ts-label">时间同步告警阈值：</span>
              <el-radio-group v-model="timeSyncThreshold" size="small">
                <el-radio-button :value="10">10 秒</el-radio-button>
                <el-radio-button :value="60">60 秒</el-radio-button>
                <el-radio-button :value="180">180 秒</el-radio-button>
              </el-radio-group>
              <span class="ts-hint">服务器时间与本机偏差超过该值即报警告</span>
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
const timeSyncThreshold = ref(60)          // 「时间同步」告警阈值（秒），选 10/60/180
const TIME_SYNC_THRESHOLDS = [10, 60, 180] // 可选档位（1 秒档已撤：设备时间精度只到秒，1s 档必然误报）
// 老计划可能存着旧档位（1/10/60），归一到当前可选档位，
// 否则 el-radio-group 找不到匹配按钮会显示成「未选中」，提交时还会把失效值写回去
function normalizeTimeSyncThreshold(v) {
  const n = Number(v)
  if (!Number.isFinite(n) || n <= 0) return 60
  if (TIME_SYNC_THRESHOLDS.includes(n)) return n
  return TIME_SYNC_THRESHOLDS.reduce((a, b) => (Math.abs(b - n) < Math.abs(a - n) ? b : a))
}
// 设备类型筛选
const assetGroups = ref([])               // 按类型分组的资产数据
const selectedTypeIds = ref([])           // 选中的类型ID列表
const assetDialogVisible = ref(false)     // 设备清单弹窗

// 全选状态
const assetTypeAll = ref(false)
const assetTypeIndeterminate = ref(false)

// 计算选中的设备总数
const selectedAssetCount = computed(() => {
  return assetGroups.value
    .filter(g => selectedTypeIds.value.includes(g.type_id))
    .reduce((sum, g) => sum + g.asset_count, 0)
})

// 选中的设备清单（用于展示）
const selectedAssetsList = computed(() => {
  const list = []
  for (const group of assetGroups.value) {
    if (selectedTypeIds.value.includes(group.type_id)) {
      for (const asset of group.assets) {
        list.push({ ...asset, type_id: group.type_id, type_name: group.type_name })
      }
    }
  }
  return list
})

function updateAssetTypeState() {
  const total = assetGroups.value.length
  const selected = selectedTypeIds.value.length
  assetTypeAll.value = total > 0 && selected === total
  assetTypeIndeterminate.value = selected > 0 && selected < total
}

function handleAssetTypeAll(val) {
  selectedTypeIds.value = val ? assetGroups.value.map(g => g.type_id) : []
  updateAssetTypeState()
}

function toggleAssetType(typeId) {
  const idx = selectedTypeIds.value.indexOf(typeId)
  if (idx >= 0) {
    selectedTypeIds.value.splice(idx, 1)
  } else {
    selectedTypeIds.value.push(typeId)
  }
  updateAssetTypeState()
}

function getAssetTypeName(typeId) {
  const g = assetGroups.value.find(g => g.type_id === typeId)
  return g ? g.type_name : ''
}

function showSelectedAssets() {
  assetDialogVisible.value = true
}

// 加载某协议下的资产（按类型分组）
async function loadAssetsByProtocol(protocol) {
  if (!protocol) {
    assetGroups.value = []
    selectedTypeIds.value = []
    return
  }
  try {
    const res = await axios.get(`/api/inspection/plans/assets_by_protocol/?protocol=${protocol}`)
    const body = res.data ?? res
    const data = (body.data || body)
    // data 可能是 { type_groups: [...] } 或直接是数组
    if (data?.type_groups) {
      assetGroups.value = data.type_groups
    } else if (Array.isArray(data)) {
      assetGroups.value = data
    } else {
      assetGroups.value = []
    }
    // 默认全选
    selectedTypeIds.value = assetGroups.value.map(g => g.type_id)
    updateAssetTypeState()
  } catch (e) {
    console.error('加载资产失败:', e)
    assetGroups.value = []
    selectedTypeIds.value = []
  }
}

// 表单（只存基本字段，巡检项目用 selectedCodes）
const form = reactive({
  name: '', code: '', description: '', protocol: 'mysql',

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
  loadAssetsByProtocol(protocol)
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
    const res = await axios.get('/api/assets/assets/', { params: { page_size: 99999 } })
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

    status: 'active'
  })
  await loadCheckItems('mysql')
  await loadAssetsByProtocol('mysql')
  timeSyncThreshold.value = 60          // 重置阈值，避免残留上一次的选择
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

    status: row.status || 'active'
  })
  // 先加载该协议的字典
  await loadCheckItems(form.protocol)
  await loadAssetsByProtocol(form.protocol)
  // 恢复设备类型选择
  if (row.asset_type_ids?.length) {
    selectedTypeIds.value = [...row.asset_type_ids]
  } else {
    selectedTypeIds.value = assetGroups.value.map(g => g.type_id)
  }
  updateAssetTypeState()
  // 再恢复已选中项（兼容对象数组和 code 数组）
  const existing = row.check_items || []
  if (existing.length > 0 && typeof existing[0] === 'object') {
    selectedCodes.value = existing.map(i => i.code)
    // 回显「时间同步」阈值（老计划无该字段时默认 60s）
    const ts = existing.find(i => i.code === 'TIME_SYNC')
    timeSyncThreshold.value = normalizeTimeSyncThreshold(ts?.threshold)
  } else if (existing.length > 0 && typeof existing[0] === 'string') {
    selectedCodes.value = [...existing]
    timeSyncThreshold.value = 60
  } else {
    selectedCodes.value = availableChecks.value.map(c => c.code)
    timeSyncThreshold.value = 60
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
        const obj = { code, name: item?.name || code, method: item?.method || '', description: item?.description || '' }
        // 「时间同步」带上用户选择的告警阈值（秒）
        if (code === 'TIME_SYNC') obj.threshold = timeSyncThreshold.value
        return obj
      }),
      asset_type_ids: selectedTypeIds.value,
      asset_count: selectedAssetCount.value,
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
    // 找到所有匹配协议的资产（按设备类型过滤）
    const p = (row.protocol || '').toLowerCase()
    const allowedTypeIds = (row.asset_type_ids || []).length ? row.asset_type_ids : null
    const matchedAssets = assets.value.filter(a => {
      const typeId = a.asset_type ?? a.asset_type_id
      if (allowedTypeIds && !allowedTypeIds.includes(typeId)) return false
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

        // 执行巡检（数据库巡检可能超过30s，设120s超时）
        if (isDb) {
          await axios.post(`/api/inspection/tasks/${taskId}/execute_db_inspection/`, {}, { timeout: 120000 })
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

function viewResults(row) { router.push('/inspection') }

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

/* 时间同步告警阈值 */
.time-sync-threshold {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  padding: 10px 14px;
  background: #ecf5ff;
  border: 1px solid #d9ecff;
  border-radius: 6px;
  flex-wrap: wrap;
}
.time-sync-threshold .ts-label {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
}
.time-sync-threshold .ts-hint {
  font-size: 12px;
  color: #909399;
}

/* 设备类型选择 */
.asset-type-select {
  width: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  padding: 12px;
  background: #fafafa;
  max-height: 260px;
  overflow-y: auto;
}
.asset-type-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #ebeef5;
  position: sticky;
  top: 0;
  background: #fafafa;
  z-index: 1;
}
.asset-type-count { font-size: 13px; color: #909399; }
.asset-type-count b { color: #409eff; }
.asset-type-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 6px;
}
.asset-type-card {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  border-radius: 6px;
  background: #fff;
  border: 1.5px solid #e4e7ed;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
}
.asset-type-card:hover {
  border-color: #409eff;
  background: #f0f7ff;
}
.asset-type-card.selected {
  border-color: #409eff;
  background: #ecf5ff;
}
.asset-type-body { flex: 1; min-width: 0; }
.asset-type-name { font-size: 13px; font-weight: 600; color: #303133; }
.asset-type-count-label { font-size: 11px; color: #909399; margin-top: 1px; }
.no-assets {
  text-align: center;
  color: #c0c4cc;
  padding: 16px 0;
  font-size: 13px;
}
.text-muted { color: #c0c4cc; }
</style>
