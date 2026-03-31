import api from './index'

// 用户登录
export function login(data) {
  return api.post('/auth/users/login/', data)
}

// 获取当前用户信息
export function getUserInfo() {
  return api.get('/auth/users/me/')
}

// 登出
export function logout() {
  return api.post('/auth/users/logout/')
}

// 修改密码
export function changePassword(data) {
  return api.put('/auth/users/change-password/', data)
}

// 获取用户列表
export function getUserList(params) {
  return api.get('/auth/users/', { params })
}

// 创建用户
export function createUser(data) {
  return api.post('/auth/users/', data)
}

// 更新用户
export function updateUser(id, data) {
  return api.put(`/auth/users/${id}/`, data)
}

// 删除用户
export function deleteUser(id) {
  return api.delete(`/auth/users/${id}/`)
}

// 激活用户
export function activateUser(id) {
  return api.post(`/auth/users/${id}/activate/`)
}

// 禁用用户
export function deactivateUser(id) {
  return api.post(`/auth/users/${id}/deactivate/`)
}