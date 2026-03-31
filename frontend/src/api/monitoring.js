import api from './index'

// 获取监控任务列表
export function getMonitoringTasks(params) {
  return api.get('/monitoring/tasks/', { params })
}

// 获取监控任务详情
export function getMonitoringTask(id) {
  return api.get(`/monitoring/tasks/${id}/`)
}

// 创建监控任务
export function createMonitoringTask(data) {
  return api.post('/monitoring/tasks/', data)
}

// 更新监控任务
export function updateMonitoringTask(id, data) {
  return api.put(`/monitoring/tasks/${id}/`, data)
}

// 删除监控任务
export function deleteMonitoringTask(id) {
  return api.delete(`/monitoring/tasks/${id}/`)
}

// 执行监控任务
export function runMonitoringTask(id) {
  return api.post(`/monitoring/tasks/${id}/run/`)
}

// 获取监控结果
export function getMonitoringResults(params) {
  return api.get('/monitoring/results/', { params })
}

// 获取监控结果详情
export function getMonitoringResult(id) {
  return api.get(`/monitoring/results/${id}/`)
}

// 获取监控统计
export function getMonitoringStats() {
  return api.get('/monitoring/stats/')
}

// 获取告警列表
export function getAlerts(params) {
  return api.get('/monitoring/alerts/', { params })
}

// 获取告警详情
export function getAlert(id) {
  return api.get(`/monitoring/alerts/${id}/`)
}

// 更新告警状态
export function updateAlertStatus(id, data) {
  return api.patch(`/monitoring/alerts/${id}/`, data)
}

// 确认告警
export function acknowledgeAlert(id, data) {
  return api.post(`/monitoring/alerts/${id}/acknowledge/`, data)
}

// 解决告警
export function resolveAlert(id, data) {
  return api.post(`/monitoring/alerts/${id}/resolve/`, data)
}

// 获取告警统计
export function getAlertStats() {
  return api.get('/monitoring/alerts/stats/')
}

// 获取告警规则列表
export function getAlertRules(params) {
  return api.get('/monitoring/alert-rules/', { params })
}

// 创建告警规则
export function createAlertRule(data) {
  return api.post('/monitoring/alert-rules/', data)
}

// 更新告警规则
export function updateAlertRule(id, data) {
  return api.put(`/monitoring/alert-rules/${id}/`, data)
}

// 删除告警规则
export function deleteAlertRule(id) {
  return api.delete(`/monitoring/alert-rules/${id}/`)
}
