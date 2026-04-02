<template>
  <div class="system-settings">
    <div class="page-header">
      <h2>系统设置</h2>
    </div>

    <el-tabs v-model="activeCategory" type="border-card">
      <!-- ========== 推送设置 ========== -->
      <el-tab-pane label="推送设置" name="push">
        <div class="settings-group">
          <div class="group-header">
            <h3>推送到 ops-center</h3>
            <p class="group-desc">将巡检结果、告警、资产状态推送到运维中心平台</p>
          </div>

          <el-form label-width="160px" class="settings-form">
            <el-form-item label="启用推送">
              <el-switch v-model="pushForm['push.enabled']" @change="markDirty('push.enabled')" />
              <span class="form-hint">开启后将自动推送数据到中心平台</span>
            </el-form-item>

            <template v-if="pushForm['push.enabled']">
              <el-form-item label="中心平台地址">
                <el-input v-model="pushForm['push.center_url']" placeholder="如 http://center.example.com:9000" @input="markDirty('push.center_url')" style="width: 400px" />
              </el-form-item>

              <el-form-item label="API Key">
                <el-input v-model="pushForm['push.api_key']" placeholder="从ops-center租户管理获取" @input="markDirty('push.api_key')" style="width: 520px" show-password />
              </el-form-item>

              <!-- 验证结果 -->
              <el-form-item v-if="verifyResult">
                <el-alert
                  :type="verifyResult.success ? 'success' : 'error'"
                  :title="verifyResult.success ? '验证成功' : '验证失败'"
                  :closable="false"
                  show-icon
                >
                  <template v-if="verifyResult.success && verifyResult.data">
                    <div class="verify-info">
                      <div><b>租户名称：</b>{{ verifyResult.data.tenant }}</div>
                      <div><b>租户编码：</b>{{ verifyResult.data.tenant_code }}</div>
                      <div v-if="verifyResult.data.contact_name"><b>联系人：</b>{{ verifyResult.data.contact_name }}</div>
                      <div v-if="verifyResult.data.contact_email"><b>邮箱：</b>{{ verifyResult.data.contact_email }}</div>
                      <div><b>API版本：</b>{{ verifyResult.data.api_version }}</div>
                      <div v-if="verifyResult.data.push_endpoints"><b>推送接口：</b>
                        <div v-for="(url, name) in verifyResult.data.push_endpoints" :key="name" class="endpoint-item">
                          <el-tag size="small" type="info">{{ name }}</el-tag> {{ url }}
                        </div>
                      </div>
                    </div>
                  </template>
                  <template v-else>
                    {{ verifyResult.message }}
                  </template>
                </el-alert>
              </el-form-item>

              <el-form-item label="推送内容">
                <el-checkbox v-model="pushForm['push.push_alerts']" @change="markDirty('push.push_alerts')">告警</el-checkbox>
                <el-checkbox v-model="pushForm['push.push_inspections']" @change="markDirty('push.push_inspections')">巡检结果</el-checkbox>
                <el-checkbox v-model="pushForm['push.push_asset_status']" @change="markDirty('push.push_asset_status')">资产状态</el-checkbox>
              </el-form-item>

              <el-form-item label="超时时间(秒)">
                <el-input-number v-model="pushForm['push.timeout']" :min="3" :max="60" @change="markDirty('push.timeout')" />
              </el-form-item>

              <el-form-item label="重试次数">
                <el-input-number v-model="pushForm['push.retry_count']" :min="0" :max="10" @change="markDirty('push.retry_count')" />
              </el-form-item>

              <el-form-item>
                <el-button type="primary" @click="testPush" :loading="testing">
                  验证连接
                </el-button>
              </el-form-item>
            </template>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- ========== 通知设置 ========== -->
      <el-tab-pane label="通知设置" name="notification">
        <div class="settings-group">
          <div class="group-header">
            <h3>邮件通知</h3>
            <p class="group-desc">配置SMTP服务器用于告警邮件通知</p>
          </div>

          <el-form label-width="160px" class="settings-form">
            <el-form-item label="SMTP服务器">
              <el-input v-model="notifForm['notification.email_host']" placeholder="如 smtp.example.com" @input="markDirty('notification.email_host')" style="width: 300px" />
            </el-form-item>
            <el-form-item label="SMTP端口">
              <el-input v-model="notifForm['notification.email_port']" placeholder="465" @input="markDirty('notification.email_port')" style="width: 120px" />
            </el-form-item>
            <el-form-item label="发件人邮箱">
              <el-input v-model="notifForm['notification.email_user']" @input="markDirty('notification.email_user')" style="width: 300px" />
            </el-form-item>
            <el-form-item label="邮箱密码">
              <el-input v-model="notifForm['notification.email_password']" @input="markDirty('notification.email_password')" style="width: 300px" show-password />
            </el-form-item>
            <el-form-item label="使用SSL">
              <el-switch v-model="notifForm['notification.email_use_ssl']" @change="markDirty('notification.email_use_ssl')" />
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 保存栏 -->
    <div class="save-bar" v-if="dirtyKeys.size > 0">
      <el-button type="primary" @click="saveSettings" :loading="saving">
        保存设置 ({{ dirtyKeys.size }} 项已修改)
      </el-button>
      <el-button @click="loadSettings">取消</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api/index'

const activeCategory = ref('push')
const saving = ref(false)
const testing = ref(false)
const verifyResult = ref(null)

const pushForm = reactive({})
const notifForm = reactive({})
const dirtyKeys = ref(new Set())

function markDirty(key) {
  dirtyKeys.value.add(key)
}

async function loadSettings() {
  dirtyKeys.value = new Set()
  verifyResult.value = null

  const pushRes = await api.get('/system/settings/', { params: { category: 'push' } })
  const pushList = pushRes.results || pushRes.data?.results || []
  for (const s of pushList) {
    pushForm[s.key] = parseValue(s)
  }

  const notifRes = await api.get('/system/settings/', { params: { category: 'notification' } })
  const notifList = notifRes.results || notifRes.data?.results || []
  for (const s of notifList) {
    notifForm[s.key] = parseValue(s)
  }
}

function parseValue(setting) {
  if (setting.field_type === 'boolean') {
    return setting.value === 'true' || setting.value === true
  }
  return setting.value
}

async function saveSettings() {
  saving.value = true
  try {
    const settings = {}
    for (const key of dirtyKeys.value) {
      let val
      if (key.startsWith('push.')) val = pushForm[key]
      else if (key.startsWith('notification.')) val = notifForm[key]
      else continue
      if (typeof val === 'boolean') val = val ? 'true' : 'false'
      settings[key] = String(val ?? '')
    }
    await api.post('/system/settings/batch_update/', { settings })
    ElMessage.success('保存成功')
    dirtyKeys.value = new Set()
    // 验证成功后自动验证一次
    if (pushForm['push.enabled']) {
      await testPush()
    }
    await loadSettings()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function testPush() {
  testing.value = true
  verifyResult.value = null
  try {
    // 先保存当前修改
    if (dirtyKeys.value.size > 0) {
      const settings = {}
      for (const key of dirtyKeys.value) {
        let val
        if (key.startsWith('push.')) val = pushForm[key]
        else continue
        if (typeof val === 'boolean') val = val ? 'true' : 'false'
        settings[key] = String(val ?? '')
      }
      await api.post('/system/settings/batch_update/', { settings })
      dirtyKeys.value = new Set()
    }
    const res = await api.post('/system/settings/test_push/')
    verifyResult.value = res
  } catch (e) {
    verifyResult.value = { success: false, message: e.response?.data?.message || '连接失败' }
  } finally {
    testing.value = false
  }
}

onMounted(loadSettings)
</script>

<style scoped>
.system-settings { padding: 20px; }
.page-header { margin-bottom: 20px; }
.page-header h2 { margin: 0; font-size: 18px; font-weight: 500; }

.settings-group { padding: 16px 0; }
.group-header { margin-bottom: 20px; }
.group-header h3 { margin: 0 0 4px 0; font-size: 16px; }
.group-desc { margin: 0; font-size: 13px; color: #909399; }

.settings-form { max-width: 700px; }
.form-hint { font-size: 12px; color: #909399; margin-left: 12px; }

.verify-info { margin-top: 8px; font-size: 13px; line-height: 1.8; }
.verify-info b { color: #606266; }
.endpoint-item { padding-left: 12px; font-size: 12px; color: #909399; }

.save-bar {
  position: fixed; bottom: 20px; right: 20px; z-index: 100;
  background: #fff; padding: 12px 20px; border-radius: 8px;
  box-shadow: 0 -2px 12px rgba(0,0,0,0.1);
  display: flex; gap: 12px; align-items: center;
}
</style>
