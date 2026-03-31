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
        label-width="120px"
      >
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
        
        <el-form-item label="资产编号" prop="asset_code">
          <el-input v-model="form.asset_code" placeholder="请输入资产编号" />
        </el-form-item>
        
        <el-form-item label="资产名称" prop="asset_name">
          <el-input v-model="form.asset_name" placeholder="请输入资产名称" />
        </el-form-item>
        
        <el-form-item label="状态" prop="status">
          <el-select v-model="form.status" style="width: 100%">
            <el-option label="活跃" value="ACTIVE" />
            <el-option label="停用" value="INACTIVE" />
            <el-option label="维护中" value="MAINTENANCE" />
            <el-option label="已退役" value="DECOMMISSIONED" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="重要等级" prop="importance_level">
          <el-select v-model="form.importance_level" style="width: 100%">
            <el-option label="低" value="LOW" />
            <el-option label="中" value="MEDIUM" />
            <el-option label="高" value="HIGH" />
            <el-option label="关键" value="CRITICAL" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="位置" prop="location">
          <el-input v-model="form.location" placeholder="请输入位置" />
        </el-form-item>
        
        <el-form-item label="机房">
          <el-input v-model="form.room" placeholder="请输入机房" />
        </el-form-item>
        
        <el-form-item label="机柜">
          <el-input v-model="form.rack" placeholder="请输入机柜" />
        </el-form-item>
        
        <el-form-item label="负责人">
          <el-input v-model="form.owner" placeholder="请输入负责人" />
        </el-form-item>
        
        <el-form-item label="部门">
          <el-input v-model="form.department" placeholder="请输入部门" />
        </el-form-item>
        
        <el-form-item label="供应商">
          <el-input v-model="form.vendor" placeholder="请输入供应商" />
        </el-form-item>
        
        <el-form-item label="购买日期">
          <el-date-picker
            v-model="form.purchase_date"
            type="date"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        
        <el-form-item label="保修到期">
          <el-date-picker
            v-model="form.warranty_end"
            type="date"
            placeholder="选择日期"
            style="width: 100%"
          />
        </el-form-item>
        
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入描述"
          />
        </el-form-item>
        
        <!-- 动态字段 -->
        <template v-if="currentTypeFields.length > 0">
          <el-divider>配置信息</el-divider>
          
          <el-form-item
            v-for="field in currentTypeFields"
            :key="field.id"
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
        </template>
        
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

const form = reactive({
  customer: null,
  asset_type: null,
  asset_code: '',
  asset_name: '',
  status: 'ACTIVE',
  importance_level: 'MEDIUM',
  location: '',
  room: '',
  rack: '',
  owner: '',
  department: '',
  vendor: '',
  purchase_date: null,
  warranty_end: null,
  description: '',
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
    form.location = res.location
    form.room = res.room
    form.rack = res.rack
    form.owner = res.owner
    form.department = res.department
    form.vendor = res.vendor
    form.purchase_date = res.purchase_date
    form.warranty_end = res.warranty_end
    form.description = res.description
    
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
      location: form.location,
      room: form.room,
      rack: form.rack,
      owner: form.owner,
      department: form.department,
      vendor: form.vendor,
      purchase_date: form.purchase_date,
      warranty_end: form.warranty_end,
      description: form.description,
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
</style>