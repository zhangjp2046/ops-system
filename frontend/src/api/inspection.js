import api from './index'

// 获取巡检记录列表
export function getInspectionList(params) {
  return api.get('/inspection/inspections/', { params })
}

// 获取巡检记录详情
export function getInspection(id) {
  return api.get(`/inspection/inspections/${id}/`)
}

// 获取巡检记录列表(简化接口)
export function getInspectionListSimple(params) {
  return api.get('/inspection/list/', { params })
}

// 获取巡检状态
export function getInspectionStatus(id) {
  return api.get(`/inspection/status/${id}/`)
}

// 手工执行巡检
export function runInspection(data) {
  return api.post('/inspection/run/', data)
}

// 批量执行巡检
export function batchRunInspection(data) {
  return api.post('/inspection/batch-run/', data)
}

// 获取巡检模板列表
export function getInspectionTemplates(params) {
  return api.get('/inspection/templates/', { params })
}

// 获取巡检模板详情
export function getInspectionTemplate(id) {
  return api.get(`/inspection/templates/${id}/`)
}

// 创建巡检模板
export function createInspectionTemplate(data) {
  return api.post('/inspection/templates/', data)
}

// 更新巡检模板
export function updateInspectionTemplate(id, data) {
  return api.put(`/inspection/templates/${id}/`, data)
}

// 删除巡检模板
export function deleteInspectionTemplate(id) {
  return api.delete(`/inspection/templates/${id}/`)
}

// 获取巡检统计
export function getInspectionStats() {
  return api.get('/inspection/inspections/stats/')
}
