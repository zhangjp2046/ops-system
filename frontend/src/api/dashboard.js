import api from './index'

// 获取驾驶舱统计数据
export function getDashboardStats() {
  return api.get('/dashboard/stats/')
}

// 获取监控统计
export function getMonitoringStats() {
  return api.get('/dashboard/monitoring/')
}

// 获取告警统计
export function getAlertStats() {
  return api.get('/dashboard/alerts/')
}

// 获取巡检统计
export function getInspectionStats() {
  return api.get('/dashboard/inspection/')
}

// 获取任务统计
export function getTaskStats() {
  return api.get('/dashboard/tasks/')
}

// 获取资产健康状态
export function getAssetHealth() {
  return api.get('/dashboard/health/')
}
