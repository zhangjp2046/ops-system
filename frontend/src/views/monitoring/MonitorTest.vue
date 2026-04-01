<template>
  <div class="monitor-test">
    <div class="page-header">
      <h2>采集测试</h2>
      <div>
        <el-button @click="loadHistory">
          <el-icon><Clock /></el-icon> 历史记录
        </el-button>
        <el-button type="primary" @click="showCreateDialog">
          <el-icon><Plus /></el-icon> 新建配置
        </el-button>
      </div>
    </div>

    <!-- 快速测试 -->
    <el-card class="quick-test-card">
      <template #header>
        <div class="card-header">
          <span>⚡ 快速测试</span>
          <span class="hint">选择协议 → 填写参数 → 点击测试 → 查看结果</span>
        </div>
      </template>

      <el-form :model="quickForm" label-width="80px">
        <el-row :gutter="16">
          <el-col :span="6">
            <el-form-item label="协议">
              <el-select v-model="quickForm.protocol" @change="onProtocolChange" style="width:100%">
                <el-option-group label="网络">
                  <el-option label="Ping (ICMP)" value="ping" />
                  <el-option label="端口检测" value="port" />
                  <el-option label="SNMP" value="snmp" />
                </el-option-group>
                <el-option-group label="服务器">
                  <el-option label="SSH" value="ssh" />
                </el-option-group>
                <el-option-group label="数据库">
                  <el-option label="MySQL" value="mysql" />
                  <el-option label="MSSQL" value="mssql" />
                  <el-option label="Oracle" value="oracle" />
                  <el-option label="PostgreSQL" value="postgresql" />
                </el-option-group>
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="主机">
              <el-input v-model="quickForm.host" placeholder="IP 或主机名" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="端口">
              <el-input v-model="quickForm.port" :placeholder="defaultPort" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label="超时">
              <el-input-number v-model="quickForm.timeout" :min="3" :max="60" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="4">
            <el-form-item label=" ">
              <el-button type="primary" @click="runQuickTest" :loading="testing" style="width:100%">
                <el-icon><VideoPlay /></el-icon> 开始测试
              </el-button>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 协议特定字段 -->
        <el-row :gutter="16" v-if="showAuthFields">
          <el-col :span="6">
            <el-form-item label="用户名">
              <el-input v-model="quickForm.username" placeholder="用户名" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="密码">
              <el-input v-model="quickForm.password" type="password" show-password placeholder="密码" />
            </el-form-item>
          </el-col>
          <el-col :span="6" v-if="showDbField">
            <el-form-item label="数据库">
              <el-input v-model="quickForm.database" :placeholder="dbPlaceholder" />
            </el-form-item>
          </el-col>
          <el-col :span="6" v-if="quickForm.protocol === 'snmp'">
            <el-form-item label="Community">
              <el-input v-model="quickForm.community" placeholder="public" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <!-- 测试结果 -->
    <el-card v-if="testResult" class="result-card" :class="testResult.success ? 'success' : 'error'">
      <template #header>
        <div class="card-header">
          <span>
            {{ testResult.success ? '✅ 测试成功' : '❌ 测试失败' }}
            <el-tag :type="testResult.success ? 'success' : 'danger'" size="small" style="margin-left:8px">
              {{ testResult.test_duration }}ms
            </el-tag>
          </span>
          <el-button link type="primary" @click="copyResult">复制结果</el-button>
        </div>
      </template>

      <!-- 基本信息 -->
      <el-descriptions :column="3" border size="small" class="result-info">
        <el-descriptions-item label="协议">{{ testResult.protocol }}</el-descriptions-item>
        <el-descriptions-item label="主机">{{ testResult.host }}</el-descriptions-item>
        <el-descriptions-item label="端口">{{ testResult.port || '-' }}</el-descriptions-item>
        <el-descriptions-item label="状态" :span="3">
          <el-tag :type="testResult.success ? 'success' : 'danger'">
            {{ testResult.success ? '连接成功' : '连接失败' }}
          </el-tag>
        </el-descriptions-item>
      </el-descriptions>

      <!-- 数据库测试结果 -->
      <template v-if="isDbProtocol && testResult.success">
        <el-divider content-position="left">数据库信息</el-divider>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="版本">{{ testResult.version || testResult.data?.version || '-' }}</el-descriptions-item>
          <el-descriptions-item label="驱动">{{ testResult.data?.driver || testResult.data?.method || '-' }}</el-descriptions-item>
          <el-descriptions-item label="响应时间">{{ testResult.response_time || testResult.test_duration || '-' }}ms</el-descriptions-item>
          <el-descriptions-item label="连接方式">{{ testResult.data?.method || testResult.message || '-' }}</el-descriptions-item>
        </el-descriptions>
      </template>

      <!-- SNMP测试结果 -->
      <template v-if="quickForm.protocol === 'snmp' && testResult.success">
        <el-divider content-position="left">SNMP设备信息</el-divider>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="系统描述" :span="2">
            <div class="text-wrap">{{ testResult.sysDescr || '-' }}</div>
          </el-descriptions-item>
        </el-descriptions>
      </template>

      <!-- SSH测试结果 -->
      <template v-if="quickForm.protocol === 'ssh' && testResult.success">
        <el-divider content-position="left">SSH连接信息</el-divider>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="认证状态">
            <el-tag :type="testResult.authenticated ? 'success' : 'warning'">
              {{ testResult.authenticated ? '已认证' : '未认证' }}
            </el-tag>
          </el-descriptions-item>
        </el-descriptions>
      </template>

      <!-- 错误信息 -->
      <template v-if="testResult.error">
        <el-divider content-position="left">错误信息</el-divider>
        <div class="error-box">
          <pre>{{ testResult.error }}</pre>
        </div>
      </template>

      <!-- 原始响应（开发者用） -->
      <el-collapse class="raw-collapse">
        <el-collapse-item title="📋 原始响应数据（开发者）">
          <pre class="raw-json">{{ JSON.stringify(testResult, null, 2) }}</pre>
        </el-collapse-item>
      </el-collapse>
    </el-card>

    <!-- 测试配置列表 -->
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <span>📋 测试配置</span>
          <el-input v-model="configSearch" placeholder="搜索配置" size="small" style="width:200px" clearable>
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>
      </template>

      <el-table :data="filteredConfigs" v-loading="configLoading" stripe>
        <el-table-column prop="name" label="名称" min-width="150" />
        <el-table-column prop="protocol" label="协议" width="120">
          <template #default="{ row }">
            <el-tag :type="getProtocolTagType(row.protocol)" size="small">{{ row.protocol.toUpperCase() }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="host" label="主机" min-width="140" />
        <el-table-column prop="port" label="端口" width="80" />
        <el-table-column prop="last_test_status" label="最近状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.last_test_status" :type="row.last_test_status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.last_test_status === 'success' ? '成功' : '失败' }}
            </el-tag>
            <span v-else class="text-muted">未测试</span>
          </template>
        </el-table-column>
        <el-table-column prop="last_test_time" label="最近测试" width="160">
          <template #default="{ row }">
            {{ row.last_test_time ? formatTime(row.last_test_time) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="runConfigTest(row)" :loading="row._testing">
              <el-icon><VideoPlay /></el-icon> 测试
            </el-button>
            <el-button link type="info" size="small" @click="viewConfigResults(row)">
              <el-icon><View /></el-icon> 结果
            </el-button>
            <el-button link type="danger" size="small" @click="deleteConfig(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新建配置弹窗 -->
    <el-dialog v-model="createVisible" title="新建测试配置" width="600px">
      <el-form :model="configForm" label-width="100px">
        <el-form-item label="名称">
          <el-input v-model="configForm.name" placeholder="如：核心交换机SNMP测试" />
        </el-form-item>
        <el-form-item label="协议">
          <el-select v-model="configForm.protocol" style="width:100%">
            <el-option v-for="p in protocols" :key="p.code" :label="p.name" :value="p.code" />
          </el-select>
        </el-form-item>
        <el-form-item label="主机">
          <el-input v-model="configForm.host" placeholder="IP地址" />
        </el-form-item>
        <el-form-item label="端口">
          <el-input v-model="configForm.port" />
        </el-form-item>
        <el-form-item label="间隔(秒)">
          <el-input-number v-model="configForm.interval" :min="10" :max="86400" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" @click="createConfig" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <!-- 历史结果弹窗 -->
    <el-dialog v-model="historyVisible" title="测试历史记录" width="900px">
      <el-table :data="historyData" stripe size="small" max-height="400">
        <el-table-column prop="created_at" label="时间" width="160">
          <template #default="{ row }">{{ formatTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.status === 'success' ? 'success' : 'danger'" size="small">
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="response_time" label="响应时间" width="100">
          <template #default="{ row }">{{ row.response_time ? row.response_time + 'ms' : '-' }}</template>
        </el-table-column>
        <el-table-column prop="error_message" label="错误信息" show-overflow-tooltip />
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, VideoPlay, Search, View, Clock } from '@element-plus/icons-vue'
import axios from '@/utils/axios'

const testing = ref(false)
const creating = ref(false)
const configLoading = ref(false)
const createVisible = ref(false)
const historyVisible = ref(false)
const testResult = ref(null)
const configs = ref([])
const historyData = ref([])
const configSearch = ref('')
const protocols = ref([])

const quickForm = reactive({
  protocol: 'ping', host: '', port: '', timeout: 10,
  username: '', password: '', database: '', community: 'public'
})

const configForm = reactive({
  name: '', protocol: 'ping', host: '', port: '', interval: 300, customer: 1
})

// 计算属性
const defaultPort = computed(() => {
  const map = { snmp: '161', ssh: '22', mysql: '3306', mssql: '1433', oracle: '1521', postgresql: '5432', port: '80' }
  return map[quickForm.protocol] || ''
})

const showAuthFields = computed(() => ['ssh', 'mysql', 'mssql', 'oracle', 'postgresql', 'snmp'].includes(quickForm.protocol))
const showDbField = computed(() => ['mysql', 'mssql', 'oracle', 'postgresql'].includes(quickForm.protocol))
const isDbProtocol = computed(() => ['mysql', 'mssql', 'oracle', 'postgresql'].includes(quickForm.protocol))

const dbPlaceholder = computed(() => {
  const map = { mysql: 'mysql', mssql: 'master', oracle: 'ORCL', postgresql: 'postgres' }
  return map[quickForm.protocol] || '数据库名'
})

const filteredConfigs = computed(() => {
  if (!configSearch.value) return configs.value
  const s = configSearch.value.toLowerCase()
  return configs.value.filter(c =>
    (c.name || '').toLowerCase().includes(s) ||
    (c.host || '').toLowerCase().includes(s) ||
    (c.protocol || '').toLowerCase().includes(s)
  )
})

function getProtocolTagType(p) {
  const map = { ping: 'info', port: 'info', snmp: 'success', ssh: 'warning', mysql: '', mssql: 'danger', oracle: 'warning', postgresql: '' }
  return map[p] || 'info'
}

function formatTime(t) {
  return new Date(t).toLocaleString('zh-CN')
}

function onProtocolChange() {
  quickForm.port = defaultPort.value
  if (quickForm.protocol === 'snmp') { quickForm.community = 'public'; quickForm.port = '161' }
}

async function runQuickTest() {
  if (!quickForm.host) { ElMessage.warning('请输入主机地址'); return }
  testing.value = true
  testResult.value = null

  const data = { protocol: quickForm.protocol, host: quickForm.host, timeout: quickForm.timeout }
  if (quickForm.port) data.port = parseInt(quickForm.port)
  if (showAuthFields.value) {
    data.username = quickForm.username
    data.password = quickForm.password
  }
  if (showDbField.value) data.database = quickForm.database
  if (quickForm.protocol === 'snmp') data.community = quickForm.community

  try {
    const res = await axios.post('/api/monitoring/quick-test/', data)
    testResult.value = res.data || res
    if (testResult.value.success) {
      ElMessage.success(`测试成功 (${testResult.value.test_duration}ms)`)
    } else {
      ElMessage.error(`测试失败: ${testResult.value.error || '未知错误'}`)
    }
  } catch (e) {
    testResult.value = { success: false, error: e.message || '请求失败', protocol: quickForm.protocol, host: quickForm.host }
    ElMessage.error('测试请求失败')
  } finally {
    testing.value = false
  }
}

function copyResult() {
  const text = JSON.stringify(testResult.value, null, 2)
  navigator.clipboard.writeText(text).then(() => ElMessage.success('已复制'))
}

async function loadProtocols() {
  try {
    const res = await axios.get('/api/monitoring/test-configs/protocols/')
    protocols.value = res.data || res
  } catch { protocols.value = [] }
}

async function loadConfigs() {
  configLoading.value = true
  try {
    const res = await axios.get('/api/monitoring/test-configs/')
    configs.value = (res.results || res.data?.results || []).map(c => ({ ...c, _testing: false }))
  } catch { /* ignore */ }
  finally { configLoading.value = false }
}

async function runConfigTest(row) {
  row._testing = true
  try {
    const res = await axios.post(`/api/monitoring/test-configs/${row.id}/test/`)
    const result = res.data || res
    row.last_test_status = result.success ? 'success' : 'failed'
    row.last_test_time = new Date().toISOString()
    testResult.value = result
    ElMessage[result.success ? 'success' : 'error'](result.success ? '测试成功' : `测试失败: ${result.error || ''}`)
  } catch { ElMessage.error('测试失败') }
  finally { row._testing = false }
}

async function viewConfigResults(row) {
  try {
    const res = await axios.get('/api/monitoring/test-results/', { params: { config: row.id, page_size: 20 } })
    historyData.value = res.results || res.data?.results || []
    historyVisible.value = true
  } catch { ElMessage.error('加载失败') }
}

function showCreateDialog() {
  Object.assign(configForm, { name: '', protocol: 'ping', host: '', port: '', interval: 300 })
  createVisible.value = true
}

async function createConfig() {
  if (!configForm.name || !configForm.host) { ElMessage.warning('请填写名称和主机'); return }
  creating.value = true
  try {
    await axios.post('/api/monitoring/test-configs/', configForm)
    ElMessage.success('创建成功')
    createVisible.value = false
    loadConfigs()
  } catch { ElMessage.error('创建失败') }
  finally { creating.value = false }
}

async function deleteConfig(row) {
  await ElMessageBox.confirm('确定删除?', '提示')
  try {
    await axios.delete(`/api/monitoring/test-configs/${row.id}/`)
    ElMessage.success('已删除')
    loadConfigs()
  } catch { ElMessage.error('删除失败') }
}

async function loadHistory() {
  try {
    const res = await axios.get('/api/monitoring/test-results/', { params: { page_size: 50 } })
    historyData.value = res.results || res.data?.results || []
    historyVisible.value = true
  } catch { ElMessage.error('加载失败') }
}

onMounted(() => {
  loadProtocols()
  loadConfigs()
})
</script>

<style scoped>
.monitor-test { padding: 20px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h2 { margin: 0; font-size: 18px; font-weight: 500; }

.card-header { display: flex; justify-content: space-between; align-items: center; }
.hint { font-size: 12px; color: #909399; font-weight: normal; }

.quick-test-card { margin-bottom: 16px; }
.result-card { margin-bottom: 16px; }
.result-card.success { border: 1px solid #67c23a; }
.result-card.error { border: 1px solid #f56c6c; }

.config-card { margin-bottom: 16px; }

.text-wrap { word-break: break-all; white-space: pre-wrap; }
.text-muted { color: #c0c4cc; }

.result-info { margin-bottom: 16px; }

.error-box {
  background: #fef0f0; border: 1px solid #fbc4c4; border-radius: 4px;
  padding: 12px 16px; margin: 8px 0;
}
.error-box pre { margin: 0; color: #f56c6c; white-space: pre-wrap; word-break: break-all; font-size: 13px; }

.raw-collapse { margin-top: 12px; }
.raw-json {
  background: #f5f7fa; padding: 12px; border-radius: 4px;
  font-size: 12px; max-height: 300px; overflow-y: auto;
  white-space: pre-wrap; word-break: break-all;
}
</style>
