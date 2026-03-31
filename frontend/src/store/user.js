import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login } from '@/api/user'

export const useUserStore = defineStore('user', () => {
  // 状态 - 使用 ops_ 前缀避免与其他项目冲突
  const token = ref(localStorage.getItem('ops_token') || '')
  const userInfo = ref(null)
  const loading = ref(false)

  // 计算属性
  const isLoggedIn = computed(() => !!token.value)
  const username = computed(() => userInfo.value?.username || '')
  const fullName = computed(() => userInfo.value?.full_name || '')
  const role = computed(() => userInfo.value?.role || '')

  // 登录
  async function loginAction(credentials) {
    loading.value = true
    try {
      const response = await login(credentials)
      
      // 保存用户信息
      if (response.user) {
        userInfo.value = response.user
        // 生成一个简单的token用于标识登录状态
        token.value = 'logged_in_' + Date.now()
        localStorage.setItem('ops_token', token.value)
        localStorage.setItem('ops_userInfo', JSON.stringify(response.user))
      }
      
      return { success: true }
    } catch (error) {
      console.error('登录失败:', error)
      return { success: false, error: error.message || '登录失败' }
    } finally {
      loading.value = false
    }
  }

  // 获取用户信息
  async function fetchUserInfo() {
    const savedUserInfo = localStorage.getItem('ops_userInfo')
    if (savedUserInfo) {
      try {
        userInfo.value = JSON.parse(savedUserInfo)
      } catch (e) {
        console.error('解析用户信息失败:', e)
      }
    }
  }

  // 登出
  async function logoutAction() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('ops_token')
    localStorage.removeItem('ops_userInfo')
    localStorage.removeItem('ops_refreshToken')
  }

  // 初始化
  if (token.value && !userInfo.value) {
    fetchUserInfo()
  }

  return {
    // 状态
    token,
    userInfo,
    loading,
    
    // 计算属性
    isLoggedIn,
    username,
    fullName,
    role,
    
    // 方法
    loginAction,
    fetchUserInfo,
    logoutAction
  }
})