<template>
  <div class="threshold-config">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>告警阈值配置</span>
          <el-button type="primary" size="small" @click="loadThresholds">刷新</el-button>
        </div>
      </template>

      <!-- 协议筛选 -->
      <el-radio-group v-model="filterProtocol" @change="loadThresholds" style="margin-bottom: 16px;">
        <el-radio-button value="">全部</el-radio-button>
        <el-radio-button value="mysql">MySQL</el-radio-button>
        <el-radio-button value="oracle">Oracle</el-radio-button>
        <el-radio-button value="mssql">MSSQL</el-radio-button>
        <el-radio-button value="postgresql">PostgreSQL</el-radio-button>
        <el-radio-button value="snmp">SNMP设备</el-radio-button>
        <el-radio-button value="ssh">SSH服务器</el-radio-button>
        <el-radio-button value="ping">Ping</el-radio-button>
      </el-radio-group>

      <!-- 阈值列表 -->
      <el-table :data="thresholdList" stripe border>
        <el-table-column prop="protocol_display" label="协议" width="100" />
        <el-table-column prop="check_item_name" label="检查项" width="140" />
        <el-table-column label="阈值方向" width="100">
          <template #default="{ row }">
            <el-tag :type="row.threshold_direction === 'upper' ? 'danger' : 'success'" size="small">
              {{ row.threshold_direction === 'upper' ? '↑ 越高越严重' : row.threshold_direction === 'lower' ? '↓ 越低越严重' : row.direction_display }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="警告" width="100" align="center">
          <template #default="{ row }">
            <span class="threshold-warn">{{ row.warning_threshold }}{{ row.unit }}</span>
          </template>
        </el-table-column>
        <el-table-column label="错误" width="100" align="center">
          <template #default="{ row }">
            <span class="threshold-error">{{ row.error_threshold }}{{ row.unit }}</span>
          </template>
        </el-table-column>
        <el-table-column label="严重" width="100" align="center">
          <template #default="{ row }">
            <span class="threshold-critical">{{ row.critical_threshold }}{{ row.unit }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="200" show-overflow-tooltip />
        <el-table-column label="状态" width="70" align="center">
          <template #default="{ row }">
            <el-switch :model-value="row.is_active" disabled size="small" />
          </template>
        </el-table-column>
        <el-table-column label="监控" width="80" align="center">
          <template #default="{ row }">
            <el-tooltip content="开启后每次巡检记录该指标值，可从监控中心查看趋势">
              <el-switch :model-value="row.is_monitoring_item" disabled size="small" />
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" text @click="handleEdit(row)">编辑</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 编辑对话框 -->
    <el-dialog v-model="dialogVisible" title="修改阈值" width="500px" :close-on-click-modal="false">
      <el-form :model="formData" ref="formRef" label-width="100px">
        <el-form-item label="检查项">
          <span>{{ formData.check_item_name }}</span>
          <span style="color: #999; margin-left: 8px;">({{ formData.protocol }})</span>
        </el-form-item>
        <el-form-item label="阈值方向">
          <el-radio-group v-model="formData.threshold_direction">
            <el-radio-button value="upper">↑ 越高越严重</el-radio-button>
            <el-radio-button value="lower">↓ 越低越严重</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="警告阈值">
          <el-input v-model="formData.warning_threshold" style="width: 200px;">
            <template #append>{{ formData.unit }}</template>
          </el-input>
          <span class="form-tip">超过此值触发 ⚠️ 警告</span>
        </el-form-item>
        <el-form-item label="错误阈值">
          <el-input v-model="formData.error_threshold" style="width: 200px;">
            <template #append>{{ formData.unit }}</template>
          </el-input>
          <span class="form-tip">超过此值触发 🔴 错误</span>
        </el-form-item>
        <el-form-item label="严重阈值">
          <el-input v-model="formData.critical_threshold" style="width: 200px;">
            <template #append>{{ formData.unit }}</template>
          </el-input>
          <span class="form-tip">超过此值触发 🚨 严重</span>
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="formData.unit" style="width: 100px;" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="formData.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="formData.is_active" />
        </el-form-item>
        <el-form-item>
          <el-switch v-model="formData.is_monitoring_item" />
          <span style="margin-left: 8px; color: #888; font-size: 13px;">
            开启监控项：每次巡检记录该指标值，可从监控中心查看趋势变化
          </span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'

export default {
  name: 'ThresholdConfig',
  setup() {
    const thresholdList = ref([])
    const filterProtocol = ref('')
    const dialogVisible = ref(false)
    const formRef = ref(null)
    const currentEditId = ref(null)

    const formData = reactive({
      protocol: '',
      check_item_code: '',
      check_item_name: '',
      threshold_direction: 'upper',
      warning_threshold: '',
      error_threshold: '',
      critical_threshold: '',
      unit: '%',
      description: '',
      is_active: true,
      is_monitoring_item: false,
    })

    const loadThresholds = async () => {
      try {
        const params = {}
        if (filterProtocol.value) params.protocol = filterProtocol.value
        const res = await axios.get('/api/alerts/thresholds/', { params })
        thresholdList.value = res.data.results || res.data
      } catch (error) {
        ElMessage.error('加载失败')
      }
    }

    const handleEdit = (row) => {
      currentEditId.value = row.id
      Object.assign(formData, {
        protocol: row.protocol,
        check_item_code: row.check_item_code,
        check_item_name: row.check_item_name,
        threshold_direction: row.threshold_direction,
        warning_threshold: row.warning_threshold,
        error_threshold: row.error_threshold,
        critical_threshold: row.critical_threshold,
        unit: row.unit,
        description: row.description,
        is_active: row.is_active,
        is_monitoring_item: row.is_monitoring_item || false,
      })
      dialogVisible.value = true
    }

    const handleSubmit = async () => {
      try {
        await axios.patch(`/api/alerts/thresholds/${currentEditId.value}/`, {
          threshold_direction: formData.threshold_direction,
          warning_threshold: formData.warning_threshold,
          error_threshold: formData.error_threshold,
          critical_threshold: formData.critical_threshold,
          unit: formData.unit,
          description: formData.description,
          is_active: formData.is_active,
          is_monitoring_item: formData.is_monitoring_item,
        })
        ElMessage.success('保存成功')
        dialogVisible.value = false
        loadThresholds()
      } catch (error) {
        ElMessage.error('保存失败')
      }
    }

    onMounted(() => {
      loadThresholds()
    })

    return {
      thresholdList,
      filterProtocol,
      dialogVisible,
      formData,
      formRef,
      loadThresholds,
      handleEdit,
      handleSubmit
    }
  }
}
</script>

<style scoped>
.threshold-config {
  padding: 4px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.threshold-warn {
  color: #E6A23C;
  font-weight: bold;
}

.threshold-error {
  color: #F56C6C;
  font-weight: bold;
}

.threshold-critical {
  color: #C45656;
  font-weight: bold;
}

.form-tip {
  color: #999;
  font-size: 12px;
  margin-left: 12px;
}
</style>
