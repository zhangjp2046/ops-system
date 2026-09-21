<template>
  <div class="discovery-page">
    <div class="header">
      <h2>资产自动发现</h2>
    </div>

    <el-tabs v-model="activeTab" class="main-tabs">

      <!-- ========== 智能扫描 ========== -->
      <el-tab-pane label="智能扫描" name="smart">
        <div class="smart-scan">
          <!-- 网段分析结果 -->
          <el-card class="subnet-card" shadow="never">
            <template #header>
              <div class="card-header">
                <span>网段分析</span>
                <el-button size="small" @click="loadSubnets" :loading="loadingSubnets">
                  <el-icon><Refresh /></el-icon>
                  重新分析
                </el-button>
              </div>
            </template>

            <div v-if="subnetInfo" class="subnet-summary">
              <el-statistic title="已有资产IP数" :value="subnetInfo.total_assets" />
              <el-statistic title="推断网段数" :value="subnetInfo.total_subnets" />
            </div>

            <el-table v-if="subnetList.length > 0" :data="subnetList" stripe size="small" class="subnet-table">
              <el-table-column prop="subnet" label="网段" width="160" />
              <el-table-column prop="asset_count" label="已有资产数" width="120" />
              <el-table-column label="已有资产IP" min-width="200">
                <template #default="{ row }">
                  <el-tag
                    v-for="ip in row.asset_ips.slice(0, 5)"
                    :key="ip"
                    size="small"
                    style="margin-right: 4px"
                  >{{ ip }}</el-tag>
                  <span v-if="row.asset_ips.length > 5" style="color: #999; font-size: 12px">
                    +{{ row.asset_ips.length - 5 }} 更多
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="200">
                <template #default="{ row }">
                  <el-checkbox
                    v-model="row.selected"
                    :label="`扫描 ${row.subnet}`"
                    @change="toggleSubnet(row)"
                  />
                </template>
              </el-table-column>
            </el-table>

            <el-empty v-else-if="!loadingSubnets" description="暂无网段数据，请先添加资产" />

            <div v-if="selectedSubnets.length > 0" class="scan-actions">
              <span>已选 {{ selectedSubnets.length }} 个网段</span>
              <el-button
                type="primary"
                @click="runSmartScan"
                :loading="smartScanning"
              >
                <el-icon><Search /></el-icon>
                开始扫描
              </el-button>
            </div>
          </el-card>

          <!-- 扫描结果 -->
          <el-card v-if="smartResults.length > 0 || knownResults.length > 0" class="results-card" shadow="never">
            <template #header>
              <div class="card-header">
                <span>扫描结果</span>
                <el-button size="small" @click="clearSmartResults">清除结果</el-button>
              </div>
            </template>

            <!-- 已有资产 (在线) -->
            <div v-if="knownResults.length > 0" class="result-section">
              <div class="section-title">
                <el-badge :value="knownResults.length" type="success" />
                <span>已有资产（在线）</span>
              </div>
              <el-table :data="knownResults" stripe size="small">
                <el-table-column prop="ip" label="IP地址" width="140" />
                <el-table-column prop="asset_name" label="资产名称" min-width="150" />
                <el-table-column prop="asset_code" label="资产编号" width="160" />
                <el-table-column prop="device_type" label="设备类型" width="100">
                  <template #default="{ row }">
                    {{ getDeviceTypeLabel(row.device_type) }}
                  </template>
                </el-table-column>
                <el-table-column prop="vendor" label="厂商" width="120" />
                <el-table-column prop="response_time" label="响应" width="80">
                  <template #default="{ row }">
                    <span v-if="row.response_time">{{ row.response_time.toFixed(1) }}ms</span>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="100">
                  <template #default="{ row }">
                    <el-button size="small" @click="goToAsset(row.asset_id)">查看资产</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <!-- 新发现设备 -->
            <div v-if="newResults.length > 0" class="result-section">
              <div class="section-title">
                <el-badge :value="newResults.length" type="warning" />
                <span>新发现设备（不在资产库）</span>
                <el-button
                  type="primary"
                  size="small"
                  style="margin-left: 12px"
                  @click="importAllNew"
                  :disabled="newResults.length === 0"
                >
                  <el-icon><Plus /></el-icon>
                  批量添加
                </el-button>
              </div>
              <el-table :data="newResults" stripe size="small">
                <el-table-column type="selection" width="40" />
                <el-table-column prop="ip" label="IP地址" width="140" />
                <el-table-column prop="mac" label="MAC地址" width="170" />
                <el-table-column prop="hostname" label="主机名" min-width="120" />
                <el-table-column prop="device_type" label="设备类型" width="100">
                  <template #default="{ row }">
                    <el-tag size="small">{{ getDeviceTypeLabel(row.device_type) }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="vendor" label="厂商" width="120" />
                <el-table-column prop="open_ports" label="开放端口" min-width="180">
                  <template #default="{ row }">
                    <el-tag
                      v-for="port in (row.open_ports || []).slice(0, 5)"
                      :key="port"
                      size="small"
                      style="margin-right: 3px"
                    >{{ port }}</el-tag>
                    <span v-if="(row.open_ports || []).length > 5" style="color: #999; font-size: 11px">
                      +{{ row.open_ports.length - 5 }}
                    </span>
                  </template>
                </el-table-column>
                <el-table-column prop="response_time" label="响应" width="80">
                  <template #default="{ row }">
                    <span v-if="row.response_time">{{ row.response_time.toFixed(1) }}ms</span>
                    <span v-else>-</span>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120" fixed="right">
                  <template #default="{ row }">
                    <el-button type="primary" size="small" @click="addSingleDevice(row)">
                      添加
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>

            <!-- 无新设备 -->
            <el-empty v-if="knownResults.length === 0 && newResults.length === 0 && !smartScanning"
              description="在所选网段内未发现在线设备" />
          </el-card>
        </div>
      </el-tab-pane>

      <!-- ========== 快速扫描 ========== -->
      <el-tab-pane label="快速扫描" name="quick">
        <el-card class="quick-scan-card" shadow="never">
          <el-form :inline="true" :model="quickForm">
            <el-form-item label="目标网段">
              <el-input
                v-model="quickForm.target"
                placeholder="192.168.1.1-254 或 192.168.1.0/24"
                style="width: 260px"
              />
            </el-form-item>
            <el-form-item label="扫描类型">
              <el-select v-model="quickForm.scanType" style="width: 120px">
                <el-option label="完整扫描" value="full" />
                <el-option label="Ping扫描" value="ping" />
                <el-option label="TCP扫描" value="tcp" />
              </el-select>
            </el-form-item>
            <el-form-item label="超时">
              <el-input-number v-model="quickForm.timeout" :min="1" :max="30" style="width: 100px" /> 秒
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleQuickScan" :loading="quickScanning">
                <el-icon><Search /></el-icon>
                开始扫描
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-card v-if="quickResults.length > 0" class="results-card" shadow="never">
          <template #header>
            <div class="card-header">
              <span>扫描结果 ({{ quickResults.length }} 台设备)</span>
              <el-button size="small" @click="quickResults = []">清除</el-button>
            </div>
          </template>
          <el-table :data="quickResults" stripe>
            <el-table-column prop="ip" label="IP地址" width="140" />
            <el-table-column prop="mac" label="MAC地址" width="170" />
            <el-table-column prop="hostname" label="主机名" width="150" />
            <el-table-column prop="device_type" label="设备类型" width="120">
              <template #default="{ row }">
                <el-tag size="small">{{ getDeviceTypeLabel(row.device_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="vendor" label="厂商" width="120" />
            <el-table-column prop="os_type" label="操作系统" width="100" />
            <el-table-column prop="open_ports" label="开放端口" min-width="200">
              <template #default="{ row }">
                <el-tag
                  v-for="port in (row.open_ports || []).slice(0, 6)"
                  :key="port"
                  size="small"
                  style="margin-right: 4px; margin-bottom: 2px"
                >{{ port }}</el-tag>
                <span v-if="(row.open_ports || []).length > 6">+{{ row.open_ports.length - 6 }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="response_time" label="响应时间" width="100">
              <template #default="{ row }">
                <span v-if="row.response_time">{{ row.response_time.toFixed(1) }} ms</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- ========== 任务列表 ========== -->
      <el-tab-pane label="任务列表" name="tasks">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>发现任务</span>
              <el-button size="small" @click="loadTasks">刷新</el-button>
            </div>
          </template>

          <el-table :data="tasks" stripe v-loading="loadingTasks">
            <el-table-column prop="name" label="任务名称" min-width="150" />
            <el-table-column prop="scan_type" label="扫描类型" width="100">
              <template #default="{ row }">
                {{ getScanTypeLabel(row.scan_type) }}
              </template>
            </el-table-column>
            <el-table-column prop="target_ranges" label="目标网段" min-width="200">
              <template #default="{ row }">
                <span v-for="(r, i) in (row.target_ranges || [])" :key="i">{{ r }} </span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">
                  {{ getStatusLabel(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="progress" label="进度" width="120">
              <template #default="{ row }">
                <el-progress
                  v-if="row.status === 'running'"
                  :percentage="row.progress || 0"
                  :stroke-width="12"
                />
                <span v-else-if="row.status === 'completed'">{{ row.found_devices }} 台</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="160">
              <template #default="{ row }">
                {{ formatTime(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <el-button
                  v-if="row.status === 'pending'"
                  type="primary"
                  size="small"
                  @click="handleStartScan(row)"
                >启动</el-button>
                <el-button
                  v-if="row.status === 'completed'"
                  type="success"
                  size="small"
                  @click="handleViewDevices(row)"
                >设备</el-button>
                <el-button
                  v-if="row.status === 'completed'"
                  type="warning"
                  size="small"
                  @click="handleBuildTopology(row)"
                >拓扑</el-button>
                <el-button
                  v-if="row.status === 'running'"
                  type="danger"
                  size="small"
                  @click="handleCancelScan(row.id)"
                >取消</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 设备列表对话框（任务详情） -->
    <el-dialog v-model="showDevicesDialog" title="任务设备列表" width="960px" top="5vh">
      <el-table :data="taskDevices" stripe max-height="60vh">
        <el-table-column prop="ip_address" label="IP地址" width="140" />
        <el-table-column prop="hostname" label="主机名" width="130" />
        <el-table-column prop="device_type" label="类型" width="90">
          <template #default="{ row }">
            <el-tag size="small">{{ getDeviceTypeLabel(row.device_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="vendor" label="厂商" width="110" />
        <el-table-column label="资产关联" width="200">
          <template #default="{ row }">
            <template v-if="row.is_known">
              <el-tag type="success" size="small" style="margin-right: 4px">已有</el-tag>
              <el-link type="success" :underline="false" @click="goToAsset(row.asset_id)">
                {{ row.asset_name }}
              </el-link>
            </template>
            <el-tag v-else-if="row.is_imported" type="warning" size="small">已导入</el-tag>
            <span v-else style="color: #999; font-size: 12px">未在资产库</span>
          </template>
        </el-table-column>
        <el-table-column prop="open_ports" label="端口" min-width="150">
          <template #default="{ row }">
            <el-tag
              v-for="port in (row.open_ports || []).slice(0, 4)"
              :key="port"
              size="small"
              style="margin-right: 3px"
            >{{ port }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="!row.is_known && !row.is_imported"
              type="primary"
              size="small"
              @click="handleImportDevice(row)"
            >添加</el-button>
            <el-button
              v-if="row.is_known && !row.is_imported"
              type="success"
              size="small"
              @click="handleImportDevice(row)"
            >同步</el-button>
            <el-button
              v-if="row.is_imported"
              size="small"
              @click="goToAsset(row.imported_asset || row.asset_id)"
            >查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import discoveryApi from '@/api/discovery'

const router = useRouter()

// Tab
const activeTab = ref('smart')

// 智能扫描状态
const loadingSubnets = ref(false)
const subnetInfo = ref(null)
const subnetList = ref([])
const selectedSubnets = ref([])
const smartScanning = ref(false)
const knownResults = ref([])
const newResults = ref([])
const smartResults = ref([])

// 快速扫描
const quickScanning = ref(false)
const quickResults = ref([])
const quickForm = ref({
  target: '192.168.1.1-10',
  scanType: 'full',
  timeout: 3
})

// 任务列表
const loadingTasks = ref(false)
const tasks = ref([])
const showDevicesDialog = ref(false)
const taskDevices = ref([])

// 当前客户ID（默认1）
const customerId = ref(1)

// ========== 智能扫描 ==========

async function loadSubnets() {
  loadingSubnets.value = true
  try {
    const res = await discoveryApi.analyzeSubnets(customerId.value)
    subnetInfo.value = {
      total_assets: res.total_assets,
      total_subnets: res.total_subnets
    }
    subnetList.value = (res.subnets || []).map(s => ({
      ...s,
      selected: false
    }))
  } catch (e) {
    console.error('分析网段失败', e)
    ElMessage.error('分析网段失败')
  } finally {
    loadingSubnets.value = false
  }
}

function toggleSubnet(row) {
  if (row.selected) {
    selectedSubnets.value.push(row.subnet)
  } else {
    selectedSubnets.value = selectedSubnets.value.filter(s => s !== row.subnet)
  }
}

let smartPollTimer = null

async function runSmartScan() {
  if (selectedSubnets.value.length === 0) {
    ElMessage.warning('请先选择要扫描的网段')
    return
  }

  smartScanning.value = true
  knownResults.value = []
  newResults.value = []
  smartResults.value = []

  try {
    // 1. 发起扫描，返回 task_id
    const res = await discoveryApi.smartScan({
      customer_id: customerId.value,
      subnets: selectedSubnets.value,
      scan_type: 'ping',
      timeout: 3
    })

    const taskId = res.task_id
    ElMessage.success('扫描已启动，正在后台扫描...')

    // 2. 轮询查询结果
    smartPollTimer = setInterval(async () => {
      try {
        const result = await discoveryApi.getSmartScanResult(taskId)

        if (result.status === 'completed') {
          clearInterval(smartPollTimer)
          smartPollTimer = null
          smartScanning.value = false

          knownResults.value = result.known_devices || []
          newResults.value = result.new_devices || []
          smartResults.value = result.all_devices || []

          ElMessage.success(
            `扫描完成：已有 ${result.known_count} 台，新发现 ${result.new_count} 台设备`
          )
        } else if (result.status === 'running') {
          // 仍在运行，更新进度
          console.log(`扫描进度: ${result.progress || 0}%`)
        } else {
          // 失败
          clearInterval(smartPollTimer)
          smartPollTimer = null
          smartScanning.value = false
          ElMessage.error(result.message || '扫描失败')
        }
      } catch (e) {
        console.error('轮询失败', e)
      }
    }, 3000)

  } catch (e) {
    console.error('智能扫描失败', e)
    ElMessage.error('启动扫描失败')
    smartScanning.value = false
  }
}

async function importAllNew() {
  if (newResults.value.length === 0) return

  try {
    await ElMessageBox.confirm(
      `确定要将 ${newResults.value.length} 台新设备导入为资产吗？`,
      '批量导入',
      { type: 'info' }
    )

    const res = await discoveryApi.importNewDevices({
      customer_id: customerId.value,
      devices: newResults.value
    })

    if (res.success) {
      ElMessage.success(`成功导入 ${res.imported_count} 台资产`)
      // 从列表中移除已导入的
      newResults.value = []
    } else {
      ElMessage.error(res.message || '导入失败')
    }
  } catch (e) {
    if (e !== 'cancel') {
      console.error('导入失败', e)
      ElMessage.error('导入失败')
    }
  }
}

async function addSingleDevice(device) {
  try {
    const res = await discoveryApi.importNewDevices({
      customer_id: customerId.value,
      devices: [device]
    })
    if (res.success && res.imported_count > 0) {
      ElMessage.success(`已添加: ${res.imported[0].asset_name}`)
      // 从列表移除
      newResults.value = newResults.value.filter(d => d.ip !== device.ip)
    }
  } catch (e) {
    console.error('添加失败', e)
    ElMessage.error('添加失败')
  }
}

function clearSmartResults() {
  knownResults.value = []
  newResults.value = []
  smartResults.value = []
}

// ========== 快速扫描 ==========

async function handleQuickScan() {
  if (!quickForm.value.target) {
    ElMessage.warning('请输入扫描目标')
    return
  }
  quickScanning.value = true
  quickResults.value = []
  try {
    const res = await discoveryApi.quickScan({
      target: quickForm.value.target,
      scan_type: quickForm.value.scanType,
      timeout: quickForm.value.timeout
    })
    quickResults.value = res.devices || []
    ElMessage.success(`发现 ${quickResults.value.length} 台设备`)
  } catch (e) {
    console.error('扫描失败', e)
    ElMessage.error('扫描失败')
  } finally {
    quickScanning.value = false
  }
}

// ========== 任务列表 ==========

async function loadTasks() {
  loadingTasks.value = true
  try {
    const res = await discoveryApi.getTasks({ customer: customerId.value })
    tasks.value = res.results || res || []
  } catch (e) {
    console.error('加载任务失败', e)
  } finally {
    loadingTasks.value = false
  }
}

async function handleStartScan(task) {
  try {
    await discoveryApi.startScan(task.id)
    ElMessage.success('扫描已启动')
    loadTasks()
  } catch (e) {
    ElMessage.error('启动失败')
  }
}

async function handleCancelScan(taskId) {
  try {
    await discoveryApi.cancelScan(taskId)
    ElMessage.success('已取消')
    loadTasks()
  } catch (e) {
    ElMessage.error('取消失败')
  }
}

async function handleViewDevices(task) {
  try {
    const res = await discoveryApi.getTaskDevices(task.id)
    taskDevices.value = res.devices || []
    showDevicesDialog.value = true
  } catch (e) {
    ElMessage.error('获取设备失败')
  }
}

async function handleImportDevice(device) {
  // 已有资产但未导入：同步信息
  if (device.is_known && !device.is_imported) {
    try {
      const res = await discoveryApi.importAsset(device.id)
      if (res.success) {
        ElMessage.success(`已同步到资产: ${res.asset_code}`)
        device.is_imported = true
        device.imported_asset = res.asset_id
      }
    } catch (e) {
      ElMessage.error('同步失败')
    }
    return
  }
  // 新设备：创建资产
  try {
    const res = await discoveryApi.importNewDevices({
      customer_id: customerId.value,
      devices: [device]
    })
    if (res.success && res.imported_count > 0) {
      ElMessage.success(`已添加: ${res.imported[0].asset_name}`)
      device.is_imported = true
      device.imported_asset = res.imported[0].asset_id
    } else {
      ElMessage.error(res.message || '添加失败')
    }
  } catch (e) {
    ElMessage.error('添加失败')
  }
}

async function handleBuildTopology(task) {
  try {
    await discoveryApi.buildFromDiscovery(task.id, customerId.value)
    ElMessage.success('拓扑已生成')
  } catch (e) {
    ElMessage.error('生成拓扑失败')
  }
}

function goToAsset(assetId) {
  if (assetId) router.push(`/assets/${assetId}`)
}

// ========== 辅助 ==========

function getDeviceTypeLabel(type) {
  const map = {
    server: '服务器', router: '路由器', switch: '交换机', firewall: '防火墙',
    loadbalancer: '负载均衡', storage: '存储', printer: '打印机', camera: '摄像头',
    access_point: '无线AP', workstation: '工作站', virtual: '虚拟机', cloud: '云',
    network: '网络设备', unknown: '未知'
  }
  return map[type] || type || '未知'
}

function getScanTypeLabel(type) {
  const map = { ping: 'Ping扫描', tcp: 'TCP扫描', snmp: 'SNMP扫描', full: '完整扫描', arp: 'ARP扫描' }
  return map[type] || type
}

function getStatusLabel(status) {
  const map = { pending: '待执行', running: '执行中', completed: '已完成', failed: '失败', cancelled: '已取消' }
  return map[status] || status
}

function getStatusType(status) {
  const map = { pending: 'info', running: 'warning', completed: 'success', failed: 'danger', cancelled: 'info' }
  return map[status] || 'info'
}

function formatTime(timeStr) {
  if (!timeStr) return '-'
  return new Date(timeStr).toLocaleString('zh-CN')
}

// ========== Init ==========

onMounted(() => {
  loadSubnets()
  loadTasks()
})
</script>

<style scoped>
.discovery-page {
  padding: 20px;
}

.header {
  margin-bottom: 16px;
}

.header h2 {
  margin: 0;
}

.main-tabs {
  background: white;
  padding: 0 4px;
}

.smart-scan {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.subnet-card .card-header,
.results-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.subnet-summary {
  display: flex;
  gap: 40px;
  margin-bottom: 16px;
  padding: 12px;
  background: #f5f7fa;
  border-radius: 4px;
}

.subnet-table {
  margin-top: 12px;
}

.scan-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #eee;
}

.result-section {
  margin-bottom: 24px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  font-weight: 500;
  font-size: 14px;
}

.quick-scan-card {
  margin-bottom: 16px;
}

.results-card {
  margin-bottom: 16px;
}
</style>
