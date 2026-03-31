import api from './index'

// 获取定时任务列表
export function getScheduledTasks(params) {
  return api.get('/scheduler/tasks/', { params })
}

// 获取定时任务详情
export function getScheduledTask(id) {
  return api.get(`/scheduler/tasks/${id}/`)
}

// 创建定时任务
export function createScheduledTask(data) {
  return api.post('/scheduler/tasks/', data)
}

// 更新定时任务
export function updateScheduledTask(id, data) {
  return api.put(`/scheduler/tasks/${id}/`, data)
}

// 删除定时任务
export function deleteScheduledTask(id) {
  return api.delete(`/scheduler/tasks/${id}/`)
}

// 触发定时任务
export function triggerScheduledTask(id) {
  return api.post(`/scheduler/tasks/${id}/trigger/`)
}

// 获取任务执行记录
export function getTaskExecutions(params) {
  return api.get('/scheduler/executions/', { params })
}

// 获取执行记录详情
export function getTaskExecution(id) {
  return api.get(`/scheduler/executions/${id}/`)
}
