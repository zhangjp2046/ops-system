<template>
  <div class="asset-form">
    <div class="header">
      <el-button @click="goBack">
        <el-icon><Back /></el-icon>
        返回
      </el-button>
      <h2>{{ isEdit ? '编辑资产' : '新建资产' }}</h2>
    </div>
    
    <el-card>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
      >
        <!-- 基本信息 -->
        <el-divider content-position="left">基本信息</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="所属客户" prop="customer">
              <el-select
                v-model="form.customer"
                placeholder="请选择客户"
                style="width: 100%"
                :disabled="isEdit"
                @change="handleCustomerChange"
              >
                <el-option
                  v-for="customer in customers"
                  :key="customer.id"
                  :label="customer.customer_name"
                  :value="customer.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="资产类型" prop="asset_type">
              <el-select
                v-model="form.asset_type"
                placeholder="请选择资产类型"
                style="width: 100%"
                :disabled="isEdit"
                @change="handleAssetTypeChange"
              >
                <el-option
                  v-for="type in filteredAssetTypes"
                  :key="type.id"
                  :label="type.type_name"
                  :value="type.id"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="资产编号" prop="asset_code">
              <el-input v-model="form.asset_code" placeholder="请输入资产编号" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="资产名称" prop="asset_name">
              <el-input v-model="form.asset_name" placeholder="请输入资产名称" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="状态" prop="status">
              <el-select v-model="form.status" style="width: 100%">
                <el-option label="活跃" value="ACTIVE" />
                <el-option label="停用" value="INACTIVE" />
                <el-option label="维护中" value="MAINTENANCE" />
                <el-option label="已退役" value="DECOMMISSIONED" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="重要等级" prop="importance_level">
              <el-select v-model="form.importance_level" style="width: 100%">
                <el-option label="低" value="LOW" />
                <el-option label="中" value="MEDIUM" />
                <el-option label="高" value="HIGH" />
                <el-option label="关键" value="CRITICAL" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- 网络信息 -->
        <el-divider content-position="left">网络信息</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="IP地址">
              <el-input v-model="form.ip_address" placeholder="请输入IP地址，如 192.168.1.100" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="采集协议">
              <el-select v-model="form.protocol" placeholder="请选择协议" style="width: 100%">
                <el-option label="SNMP" value="snmp" />
                <el-option label="SSH" value="ssh" />
                <el-option label="Ping" value="ping" />
                <el-option label="MySQL" value="mysql" />
                <el-option label="MSSQL" value="mssql" />
                <el-option label="Oracle" value="oracle" />
                <el-option label="PostgreSQL" value="postgresql" />
                <el-option label="端口检测" value="port" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20" v-if="form.protocol && form.protocol !== 'ping' && form.protocol !== 'snmp'">
          <el-col :span="12">
            <el-form-item label="端口">
              <el-input v-model="form.port" placeholder="请输入端口" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="用户名">
              <el-input v-model="form.username" placeholder="请输入用户名" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20" v-if="form.protocol && form.protocol !== 'ping' && form.protocol !== 'snmp'">
          <el-col :span="12">
            <el-form-item label="密码">
              <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="数据库类型" v-if="isDbProtocol">
              <el-select v-model="form.db_type" placeholder="请选择数据库类型" style="width: 100%">
                <el-option label="MySQL" value="mysql" v-if="form.protocol === 'mysql'" />
                <el-option label="MSSQL" value="mssql" v-if="form.protocol === 'mssql'" />
                <el-option label="Oracle" value="oracle" v-if="form.protocol === 'oracle'" />
                <el-option label="PostgreSQL" value="postgresql" v-if="form.protocol === 'postgresql'" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20" v-if="isDbProtocol">
          <el-col :span="12">
            <el-form-item label="数据库名">
              <el-input v-model="form.database" placeholder="请输入数据库名" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- 位置信息 -->
        <el-divider content-position="left">位置信息</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="位置">
              <el-input v-model="form.location" placeholder="请输入位置" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="机房">
              <el-input v-model="form.room" placeholder="请输入机房" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="机柜">
              <el-input v-model="form.rack" placeholder="请输入机柜" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- 责任信息 -->
        <el-divider content-position="left">责任信息</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="负责人">
              <el-input v-model="form.owner" placeholder="请输入负责人" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="部门">
              <el-input v-model="form.department" placeholder="请输入部门" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="供应商">
              <el-input v-model="form.vendor" placeholder="请输入供应商" />
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- 采购信息 -->
        <el-divider content-position="left">采购信息</el-divider>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="购买日期">
              <el-date-picker
                v-model="form.purchase_date"
                type="date"
                placeholder="选择日期"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="保修到期">
              <el-date-picker
                v-model="form.warranty_end"
                type="date"
                placeholder="选择日期"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-row :gutter="20">
          <el-col :span="24">
            <el-form-item label="描述">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="3"
                placeholder="请输入描述"
              />
            </el-form-item>
          </el-col>
        </el-row>
        
        <!-- 动态字段 -->
        <template v-if="currentTypeFields.length > 0">
          <el-divider content-position="left">配置信息</el-divider>
          
          <el-row :gutter="20">
            <el-col
              v-for="field in currentTypeFields"
              :key="field.id"
              :span="field.field_type === 'textarea' ? 24 : 12"
            >
              <el-form-item
                :label="field.field_label"
                :prop="`field_values.${field.field_code}`"
                :required="field.is_required"
              >
                <template v-if="field.field_type === 'string'">
                  <el-input v-model="form.field_values[field.field_code]" :placeholder="field.placeholder" />
                </template>
                
                <template v-else-if="field.field_type === 'number'">
                  <el-input-number
                    v-model="form.field_values[field.field_code]"
                    :min="0"
                    style="width: 100%"
                  />
                </template>
                
                <template v-else-if="field.field_type === 'select'">
                  <el-select
                    v-model="form.field_values[field.field_code]"
                    placeholder="请选择"
                    style="width: 100%"
                  >
                    <el-option
                      v-for="option in field.options"
                      :key="option.value"
                      :label="option.label"
                      :value="option.value"
                    />
                  </el-select>
                </template>
                
                <template v-else-if="field.field_type === 'date'">
                  <el-date-picker
                    v-model="form.field_values[field.field_code]"
                    type="date"
                    placeholder="选择日期"
                    style="width: 100%"
                  />
                </template>
                
                <template v-else-if="field.field_type === 'textarea'">
                  <el-input
                    v-model="form.field_values[field.field_code]"
                    type="textarea"
                    :rows="3"
                    :placeholder="field.placeholder"
                  />
                </template>
                
                <template v-else-if="field.field_type === 'password'">
                  <el-input
                    v-model="form.field_values[field.field_code]"
                    type="password"
                    :placeholder="field.placeholder"
                    show-password
                  />
                </template>
                
                <template v-else>
                  <el-input v-model="form.field_values[field.field_code]" :placeholder="field.placeholder" />
                </template>
              </el-form-item>
            </el-col>
          </el-row>
        </template>
        
        <!-- 提交按钮 -->
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleSubmit">
            {{ isEdit ? '保存' : '创建' }}
          </el-button>
          <el-button @click="goBack">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getAsset, createAsset, updateAsset, getAssetTypeList, getAssetTypeFields } from '@/api/asset'
import { getCustomerList } from '@/api/customer'
import { Back } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const formRef = ref(null)
const loading = ref(false)
const isEdit = computed(() => !!route.params.id)
const assetId = route.params.id

const customers = ref([])
const assetTypes = ref([])
const currentTypeFields = ref([])

// 判断是否为数据库协议
const isDbProtocol = computed(() => {
  return ['mssql', 'oracle', 'mysql', 'postgresql'].includes(form.protocol)
})

const form = reactive({
  customer: null,
  asset_type: null,
  asset_code: '',
  asset_name: '',
  status: 'ACTIVE',
  importance_level: 'MEDIUM',
  ip_address: '',
  location: '',
  room: '',
  rack: '',
  owner: '',
  department: '',
  vendor: '',
  purchase_date: null,
  warranty_end: null,
  description: '',
  protocol: '',
  db_type: '',
  port: '',
  username: '',
  password: '',
  database: '',
  field_values: {}
})

const rules = {
  customer: [{ required: true, message: '请选择客户', trigger: 'change' }],
  asset_type: [{ required: true, message: '请选择资产类型', trigger: 'change' }],
  asset_code: [{ required: true, message: '请输入资产编号', trigger: 'blur' }],
  asset_name: [{ required: true, message: '请输入资产名称', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
  importance_level: [{ required: true, message: '请选择重要等级', trigger: 'change' }]
}

const filteredAssetTypes = computed(() => {
  if (!form.customer) return []
  return assetTypes.value.filter(t => t.customer === form.customer)
})

onMounted(async () => {
  await loadCustomers()
  await loadAssetTypes()
  
  if (isEdit.value) {
    await loadAsset()
  }
})

async function loadCustomers() {
  try {
    const res = await getCustomerList({ page_size: 100 })
    customers.value = res.results || []
    // 新建时默认选中第一个客户
    if (!isEdit.value && customers.value.length > 0 && !form.customer) {
      form.customer = customers.value[0].id
    }
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

async function loadAsset() {
  try {
    const res = await getAsset(assetId)
    
    // 填充表单数据
    form.customer = res.customer
    form.asset_type = res.asset_type
    form.asset_code = res.asset_code
    form.asset_name = res.asset_name
    form.status = res.status
    form.importance_level = res.importance_level
    form.ip_address = res.ip_address || ''
    form.location = res.location
    form.room = res.room
    form.rack = res.rack
    form.owner = res.owner
    form.department = res.department
    form.vendor = res.vendor
    form.purchase_date = res.purchase_date
    form.warranty_end = res.warranty_end
    form.description = res.description
    form.protocol = res.protocol || ''
    form.db_type = res.db_type || ''
    form.port = res.port || ''
    form.username = res.username || ''
    form.password = res.password || ''
    form.database = res.database || ''
    
    // 加载字段数据
    if (res.field_data) {
      for (const [key, data] of Object.entries(res.field_data)) {
        form.field_values[key] = data.value
      }
    }
    
    // 加载资产类型字段
    await loadTypeFields(res.asset_type)
  } catch (error) {
    console.error('加载资产失败:', error)
    ElMessage.error('加载资产失败')
  }
}

async function handleCustomerChange() {
  form.asset_type = null
  currentTypeFields.value = []
}

async function handleAssetTypeChange() {
  if (form.asset_type) {
    await loadTypeFields(form.asset_type)
  }
}

async function loadTypeFields(typeId) {
  try {
    const res = await getAssetTypeFields(typeId)
    currentTypeFields.value = res || []
  } catch (error) {
    console.error('加载类型字段失败:', error)
  }
}

function goBack() {
  router.back()
}

async function handleSubmit() {
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  loading.value = true
  
  try {
    const data = {
      customer: form.customer,
      asset_type: form.asset_type,
      asset_code: form.asset_code,
      asset_name: form.asset_name,
      status: form.status,
      importance_level: form.importance_level,
      ip_address: form.ip_address || null,
      location: form.location,
      room: form.room,
      rack: form.rack,
      owner: form.owner,
      department: form.department,
      vendor: form.vendor,
      purchase_date: form.purchase_date,
      warranty_end: form.warranty_end,
      description: form.description,
      protocol: form.protocol,
      db_type: form.db_type,
      port: form.port,
      username: form.username,
      password: form.password,
      database: form.database,
      field_values: form.field_values
    }
    
    if (isEdit.value) {
      await updateAsset(assetId, data)
      ElMessage.success('保存成功')
    } else {
      await createAsset(data)
      ElMessage.success('创建成功')
    }
    
    router.push('/assets')
  } catch (error) {
    console.error('保存失败:', error)
    ElMessage.error('保存失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.asset-form {
  padding: 20px;
}

.header {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  font-size: 24px;
}

:deep(.el-divider__text) {
  font-size: 15px;
  font-weight: 600;
  color: #303133;
}
</style>
