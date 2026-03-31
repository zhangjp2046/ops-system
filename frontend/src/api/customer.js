import api from './index'

// 获取客户列表
export function getCustomerList(params) {
  return api.get('/customers/customers/', { params })
}

// 获取客户详情
export function getCustomer(id) {
  return api.get(`/customers/customers/${id}/`)
}

// 创建客户
export function createCustomer(data) {
  return api.post('/customers/customers/', data)
}

// 更新客户
export function updateCustomer(id, data) {
  return api.put(`/customers/customers/${id}/`, data)
}

// 删除客户
export function deleteCustomer(id) {
  return api.delete(`/customers/customers/${id}/`)
}