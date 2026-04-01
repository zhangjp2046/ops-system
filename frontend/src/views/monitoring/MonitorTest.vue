<template>
  <div class="monitor-test">
    <div class="page-header">
      <h2>监控采集测试</h2>
      <el-button type="primary" @click="handleCreate">
        <el-icon><Plus /></el-icon> 新建测试配置
      </el-button>
    </div>

    <!-- 快速测试卡片 -->
    <el-card class="quick-test-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span>🔧 快速测试</span>
          <el-tag type="info">现场调试用</el-tag>
        </div>
      </template>
      
      <el-form :inline="true" :model="quickTestForm" class="quick-test-form">
        <el-form-item label="协议">
          <el-select v-model="quickTestForm.protocol" style="width: 140px">
            <el-option
              v-for="p in protocols"
              :key="p.code"
              :label="p.name"
              :value="p.code"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="主机">
          <el-input v-model="quickTestForm.host" placeholder="IP或主机名" style="width: 180px" />
        </el-form-item>
        
        <el-form-item v-if="showPort" label="端口">
          <el-input-number v-model="quickTestForm.port" :min="1" :max="65535" style="width: 120px" />
        </el-form-item>
        
        <!-- SSH额外字段 -->
        <template v-if="quickTestForm.protocol === 'ssh'">
          <el-form-item label="用户名">
            <el-input v-model="quickTestForm.username" placeholder="root" style="width: 120px" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="quickTestForm.password" type="password" show-password placeholder="密码" style="width: 120px" />
          </el-form-item>
        </template>
        
        <!-- SNMP额外字段 -->
        <template v-if="quickTestForm.protocol === 'snmp'">
          <el-form-item label="Community">
            <el-input v-model="quickTestForm.community" placeholder="public" style="width: 120px" />
          </el-form-item>
        </template>
        
        <!-- 数据库额外字段 -->
        <template v-if="isDbProtocol">
          <el-form-item label="用户名">
            <el-input v-model="quickTestForm.username" placeholder="root" style="width: 120px" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="quickTestForm.password" type="password" show-password style="width: 120px" />
          </el-form-item>
          <el-form-item label="数据库">
            <el-input v-model="quickTestForm.database" placeholder="可选" style="width: 120px" />
          </el-form-item>
        </template>
        
        <el-form-item>
          <el-button type="primary" @click="handleQuickTest" :loading="testing">
            {{ testing ? '测试中...' : '测试' }}
          </el-button>
        </el-form-item>
      </el-form>
      
      <!-- 测试结果 -->
      <div v-if="testResult" class="test-result" :class="testResult.success ? 'success' : 'failed'">
        <el-divider content-position="left">📊 测试结果</el-divider>
        
        <!-- 基本信息 -->
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="协议">
            <el-tag :type="getProtocolTagType(testResult.protocol)">{{ testResult.protocol?.toUpperCase() }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="主机">
            <strong>{{ testResult.host }}</strong>
          </el-descriptions-item>
          <el-descriptions-item label="端口">
            {{ testResult.port || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="testResult.success ? 'success' : 'danger'">
              {{ testResult.success ? '✅ 成功' : '❌ 失败' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="响应状态">
            {{ testResult.status || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="测试耗时">
            {{ testResult.test_duration }}ms
          </el-descriptions-item>
        </el-descriptions>
        
        <!-- 指标信息 -->
        <div v-if="testResult.success" class="metrics-section">
          <el-divider content-position="left">📈 指标数据</el-divider>
          
          <!-- Ping 指标 -->
          <template v-if="testResult.protocol === 'ping'">
            <el-row :gutter="20">
              <el-col :span="6">
                <div class="metric-card">
                  <div class="metric-label">可达性</div>
                  <div class="metric-value">{{ testResult.reachable ? '✅ 是' : '❌ 否' }}</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="metric-card">
                  <div class="metric-label">响应时间</div>
                  <div class="metric-value">{{ testResult.response_time ? testResult.response_time + ' ms' : '-' }}</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="metric-card">
                  <div class="metric-label">丢包率</div>
                  <div class="metric-value">{{ testResult.packet_loss !== undefined ? testResult.packet_loss + '%' : '-' }}</div>
                </div>
              </el-col>
              <el-col :span="6">
                <div class="metric-card">
                  <div class="metric-label">平均延迟</div>
                  <div class="metric-value">{{ testResult.avg_rtt ? testResult.avg_rtt + ' ms' : '-' }}</div>
                </div>
              </el-col>
            </el-row>
          </template>
          
          <!-- 端口检测指标 -->
          <template v-else-if="testResult.protocol === 'port'">
            <el-result
              :icon="testResult.port_open ? 'success' : 'error'"
              :title="testResult.port_open ? '端口开放' : '端口关闭'"
            >
              <template #extra>
                <span v-if="testResult.response_time">响应时间: {{ testResult.response_time }}ms</span>
              </template>
            </el-result>
          </template>
          
          <!-- SSH 指标 -->
          <template v-else-if="testResult.protocol === 'ssh'">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="认证状态">
                <el-tag :type="testResult.authenticated ? 'success' : 'danger'">
                  {{ testResult.authenticated ? '✅ 成功' : '❌ 失败' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="系统信息" :span="2">
                <template v-if="testResult.data">
                  <span v-if="testResult.data.hostname">主机名: {{ testResult.data.hostname }}; </span>
                  <span v-if="testResult.data.cpu_usage">CPU: {{ testResult.data.cpu_usage }}; </span>
                  <span v-if="testResult.data.memory_usage">内存: {{ testResult.data.memory_usage }}%; </span>
                  <span v-if="testResult.data.disk_usage">磁盘: {{ testResult.data.disk_usage }}%</span>
                </template>
                <span v-else>-</span>
              </el-descriptions-item>
            </el-descriptions>
          </template>
          
          <!-- 数据库指标 -->
          <template v-else-if="['mysql', 'postgresql', 'mssql', 'oracle'].includes(testResult.protocol)">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="连接状态">
                <el-tag :type="testResult.connected ? 'success' : 'danger'">
                  {{ testResult.connected ? '✅ 已连接' : '❌ 未连接' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="数据库版本">
                {{ (testResult.data?.version || testResult.version) || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="驱动方式">
                {{ testResult.data?.method || testResult.data?.driver || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="响应时间">
                {{ testResult.response_time ? testResult.response_time + 'ms' : '-' }}
              </el-descriptions-item>
            </el-descriptions>
          </template>
          
          <!-- SNMP 指标 -->
          <template v-else-if="testResult.protocol === 'snmp'">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="SNMP状态">
                <el-tag :type="testResult.available ? 'success' : 'danger'">
                  {{ testResult.available ? '✅ 可用' : '❌ 不可用' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="系统描述" :span="2">
                {{ testResult.sysDescr || '-' }}
              </el-descriptions-item>
            </el-descriptions>
          </template>
        </div>
        
        <!-- 错误信息 -->
        <div v-if="testResult.error" class="error-section">
          <el-alert type="error" :title="'测试失败'" show-icon :closable="false">
            <template #default>
              <pre style="margin:0;white-space:pre-wrap;word-break:break-all;font-size:12px">{{ formatError(testResult.error) }}</pre>
            </template>
          </el-alert>
        </div>
        
        <!-- 原始返回数据 (可折叠) -->
        <el-divider content-position="left">🔧 原始返回</el-divider>
        <el-collapse>
          <el-collapse-item title="查看完整返回数据" name="raw">
            <el-input
              type="textarea"
              :model-value="JSON.stringify(testResult, null, 2)"
              :rows="10"
              readonly
              style="font-family: monospace; font-size: 12px;"
            />
          </el-collapse-item>
        </el-collapse>
      </div>
    </el-card>

    <!-- 测试配置列表 -->
    <el-card class="config-list-card">
      <template #header>
        <div class="card-header">
          <span>📋 测试配置</span>
          <el-space>
            <el-select v-model="filterProtocol" placeholder="全部协议" clearable style="width: 120px">
              <el-option
                v-for="p in protocols"
                :key="p.code"
                :label="p.name"
                :value="p.code"
              />
            </el-select>
            <el-button @click="loadConfigs">刷新</el-button>
          </el-space>
        </div>
      </template>
      
      <el-table :data="configs" v-loading="loading" stripe>
        <el-table-column prop="name" label="配置名称" min-width="150" />
        <el-table-column prop="protocol_display" label="协议" width="100">
          <template #default="{ row }">
            <el-tag size="small">{{ row.protocol_display }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="host" label="主机" width="150" />
        <el-table-column prop="port" label="端口" width="80" />
        <el-table-column prop="last_test_status" label="状态" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.last_test_status === 'success'" type="success" size="small">正常</el-tag>
            <el-tag v-else-if="row.last_test_status === 'failed'" type="danger" size="small">失败</el-tag>
            <span v-else class="text-gray">未测试</span>
          </template>
        </el-table-column>
        <el-table-column prop="last_test_time" label="上次测试" width="160">
          <template #default="{ row }">
            {{ row.last_test_time ? formatDateTime(row.last_test_time) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="handleTest(row)">测试</el-button>
            <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
            <el-button link type="danger" @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px">
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="100px">
        <el-form-item label="配置名称" prop="name">
          <el-input v-model="form.name" placeholder="如: 192.168.1.199 SSH测试" />
        </el-form-item>
        
        <el-form-item label="客户">
          <el-select v-model="form.customer" placeholder="选择客户" filterable style="width: 100%">
            <el-option
              v-for="c in customers"
              :key="c.id"
              :label="c.customer_name"
              :value="c.id"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="协议" prop="protocol">
          <el-select v-model="form.protocol" placeholder="选择协议" style="width: 100%">
            <el-option
              v-for="p in protocols"
              :key="p.code"
              :label="p.name"
              :value="p.code"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="主机" prop="host">
          <el-input v-model="form.host" placeholder="IP或主机名" />
        </el-form-item>
        
        <el-form-item label="端口" v-if="showPort">
          <el-input-number v-model="form.port" :min="1" :max="65535" />
        </el-form-item>
        
        <!-- SSH配置 -->
        <template v-if="form.protocol === 'ssh'">
          <el-divider>SSH配置</el-divider>
          <el-form-item label="用户名">
            <el-input v-model="form.config.username" placeholder="root" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.config.password" type="password" show-password />
          </el-form-item>
          <el-form-item label="密钥文件">
            <el-input v-model="form.config.key_file" placeholder="/path/to/key" />
          </el-form-item>
        </template>
        
        <!-- SNMP配置 -->
        <template v-if="form.protocol === 'snmp'">
          <el-divider>SNMP配置</el-divider>
          <el-form-item label="Community">
            <el-input v-model="form.config.community" placeholder="public" />
          </el-form-item>
          <el-form-item label="OID">
            <el-input v-model="form.config.oid" placeholder="1.3.6.1.2.1.1.1.0" />
          </el-form-item>
        </template>
        
        <!-- 数据库配置 -->
        <template v-if="isDbProtocol">
          <el-divider>数据库配置</el-divider>
          <el-form-item label="用户名">
            <el-input v-model="form.config.username" placeholder="root" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="form.config.password" type="password" show-password />
          </el-form-item>
          <el-form-item label="数据库">
            <el-input v-model="form.config.database" placeholder="可选" />
          </el-form-item>
        </template>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit" :loading="submitLoading">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, SuccessFilled, CircleCloseFilled } from '@element-plus/icons-vue'
import axios from '@/utils/axios'

const loading = ref(false)
const submitLoading = ref(false)
const testing = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新建配置')
const formRef = ref(null)
const customers = ref([])
const configs = ref([])
const protocols = ref([])
const testResult = ref(null)

const filterProtocol = ref('')

const quickTestForm = reactive({
  protocol: 'ping',
  host: '',
  port: null,
  username: '',
  password: '',
  community: 'public',
  database: ''
})

const form = reactive({
  id: null,
  name: '',
  customer: null,
  protocol: 'ping',
  host: '',
  port: null,
  config: {
    username: '',
    password: '',
    key_file: '',
    community: 'public',
    oid: '',
    database: ''
  }
})

const formRules = {
  name: [{ required: true, message: '请输入配置名称', trigger: 'blur' }],
  protocol: [{ required: true, message: '请选择协议', trigger: 'change' }],
  host: [{ required: true, message: '请输入主机', trigger: 'blur' }]
}

// 计算属性
const showPort = computed(() => {
  const portProtocols = ['ssh', 'snmp', 'mysql', 'postgresql', 'mssql', 'oracle', 'port']
  return portProtocols.includes(quickTestForm.protocol) || portProtocols.includes(form.protocol)
})

const isDbProtocol = computed(() => {
  return ['mysql', 'postgresql', 'mssql', 'oracle'].includes(form.protocol)
})

// 方法
function formatDateTime(datetime) {
  if (!datetime) return '-'
  return new Date(datetime).toLocaleString('zh-CN')
}

function getProtocolTagType(protocol) {
  const types = {
    'ping': '',
    'port': 'info',
    'ssh': 'warning',
    'snmp': 'success',
    'mysql': '',
    'postgresql': 'warning',
    'mssql': '',
    'oracle': 'danger'
  }
  return types[protocol] || 'info'
}

function formatError(err) {
  if (!err) return ''
  // 把原始错误信息中的控制字符和新行处理成易读的格式
  return String(err)
    .replace(/\\n/g, '\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()
}

function loadProtocols() {
  axios.get('/api/monitoring/test-configs/protocols/')
    .then(res => {
      // 确保 data 是数组 (res 是 Axios 响应，res.data 才是实际数据)
      const data = Array.isArray(res) ? res : (res.data || [])
      protocols.value = data
      // 设置默认端口
      if (data.length > 0 && data[0].code) {
        quickTestForm.protocol = data[0].code
      }
    })
    .catch(err => {
      console.error('加载协议失败:', err)
      protocols.value = []
    })
}

function loadCustomers() {
  axios.get('/api/customers/customers/', { params: { page_size: 100 } })
    .then(res => {
      // res 是 Axios 响应，兼容不同响应格式
      const data = (res.data && res.data.results) ? res.data.results : (res.results || (Array.isArray(res.data) ? res.data : []))
      customers.value = data
    })
    .catch(err => {
      console.error('加载客户失败:', err)
      customers.value = []
    })
}

function loadConfigs() {
  loading.value = true
  const params = {}
  if (filterProtocol.value) {
    params.protocol = filterProtocol.value
  }
  
  axios.get('/api/monitoring/test-configs/', { params })
    .then(res => {
      // res 是 Axios 响应，兼容不同响应格式
      const raw = res.data || res
      const data = (raw.results) ? raw.results : (Array.isArray(raw) ? raw : [])
      configs.value = data
    })
    .catch(() => {
      ElMessage.error('加载配置失败')
      configs.value = []
    })
    .finally(() => {
      loading.value = false
    })
}

function handleQuickTest() {
  if (!quickTestForm.host) {
    ElMessage.warning('请输入主机地址')
    return
  }
  
  testing.value = true
  testResult.value = null
  
  const data = {
    protocol: quickTestForm.protocol,
    host: quickTestForm.host,
    timeout: 15
  }
  
  if (quickTestForm.port) {
    data.port = quickTestForm.port
  }
  
  if (quickTestForm.protocol === 'ssh') {
    if (quickTestForm.username) data.username = quickTestForm.username
    if (quickTestForm.password) data.password = quickTestForm.password
  } else if (quickTestForm.protocol === 'snmp') {
    data.community = quickTestForm.community
  } else if (['mysql', 'postgresql', 'mssql', 'oracle'].includes(quickTestForm.protocol)) {
    if (quickTestForm.username) data.username = quickTestForm.username
    if (quickTestForm.password) data.password = quickTestForm.password
    if (quickTestForm.database) data.database = quickTestForm.database
  }
  
  axios.post('/api/monitoring/quick-test/', data)
    .then(res => {
      // res 是 Axios 响应对象，实际数据在 res.data 中
      testResult.value = res.data || res
    })
    .catch(err => {
      ElMessage.error('测试失败: ' + (err.message || '未知错误'))
    })
    .finally(() => {
      testing.value = false
    })
}

function handleCreate() {
  dialogTitle.value = '新建配置'
  Object.assign(form, {
    id: null,
    name: '',
    customer: null,
    protocol: 'ping',
    host: '',
    port: null,
    config: {
      username: '',
      password: '',
      key_file: '',
      community: 'public',
      oid: '',
      database: ''
    }
  })
  dialogVisible.value = true
}

function handleEdit(row) {
  dialogTitle.value = '编辑配置'
  Object.assign(form, {
    id: row.id,
    name: row.name,
    customer: row.customer,
    protocol: row.protocol,
    host: row.host,
    port: row.port,
    config: row.config || {}
  })
  dialogVisible.value = true
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
    submitLoading.value = true
    
    const method = form.id ? 'put' : 'post'
    const url = form.id ? `/api/monitoring/test-configs/${form.id}/` : '/api/monitoring/test-configs/'
    
    await axios[method](url, {
      name: form.name,
      customer: form.customer,
      protocol: form.protocol,
      host: form.host,
      port: form.port,
      config: form.config
    })
    
    ElMessage.success('保存成功')
    dialogVisible.value = false
    loadConfigs()
  } catch (e) {
    // 验证失败
  } finally {
    submitLoading.value = false
  }
}

function handleTest(row) {
  testResult.value = null  // 清空之前的结果
  axios.post(`/api/monitoring/test-configs/${row.id}/test/`)
    .then(res => {
      // res 是 Axios 响应
      const result = res.data || res
      testResult.value = {
        ...result,
        protocol: row.protocol,
        host: row.host,
        port: row.port
      }
      if (result.success) {
        ElMessage.success(`测试${result.status === 'success' ? '成功' : '失败'}`)
      } else {
        ElMessage.warning('测试失败: ' + (result.error || '未知错误'))
      }
    })
    .catch(err => {
      ElMessage.error('测试请求失败: ' + (err.message || '未知错误'))
    })
}

function handleDelete(row) {
  ElMessageBox.confirm(`确定删除配置「${row.name}」?`, '删除确认', {
    confirmButtonText: '删除',
    cancelButtonText: '取消',
    type: 'warning'
  })
    .then(() => {
      axios.delete(`/api/monitoring/test-configs/${row.id}/`)
        .then(() => {
          ElMessage.success('删除成功')
          loadConfigs()
        })
        .catch(() => {
          ElMessage.error('删除失败')
        })
    })
    .catch(() => {})
}

onMounted(() => {
  loadProtocols()
  loadCustomers()
  loadConfigs()
})
</script>

<style scoped>
.monitor-test {
  padding: 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 500;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quick-test-card {
  margin-bottom: 20px;
}

.quick-test-form {
  margin-bottom: 20px;
}

.test-result {
  display: flex;
  align-items: flex-start;
  padding: 16px;
  border-radius: 8px;
  margin-top: 16px;
}

.test-result.success {
  background: #f0f9ff;
  border: 1px solid #87ceeb;
}

.test-result.failed {
  background: #fff5f5;
  border: 1px solid #ffc0c0;
}

.result-icon {
  font-size: 24px;
  margin-right: 12px;
}

.result-content {
  flex: 1;
}

.result-status {
  font-size: 16px;
  font-weight: 500;
  margin-bottom: 8px;
}

.response-time {
  color: #666;
  font-weight: normal;
}

.result-error {
  color: #f56c6c;
  margin-bottom: 8px;
}

.result-metrics {
  font-size: 14px;
  color: #666;
  margin-bottom: 4px;
}

.result-metrics span {
  margin-right: 16px;
}

.test-duration {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}

.metrics-section {
  margin: 16px 0;
}

.metric-card {
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  padding: 12px;
  text-align: center;
}

.metric-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.error-section {
  margin: 16px 0;
}

.config-list-card {
  margin-top: 20px;
}

.text-gray {
  color: #909399;
}

.config-list-card {
  background: white;
}

.text-gray {
  color: #999;
}
</style>
