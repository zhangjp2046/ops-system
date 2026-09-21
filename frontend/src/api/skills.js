import api from './index'

// ========== 技能库 ==========
export function getSkillList() {
  return api.get('/skills/')
}

export function getSkill(code) {
  return api.get(`/skills/${code}/`)
}

export function executeSkill(data) {
  return api.post('/skills/execute/', data)
}

// ========== 巡检计划 ==========
export function getInspectionPlans(params) {
  return api.get('/inspection/plans/', { params })
}

export function getInspectionPlan(id) {
  return api.get(`/inspection/plans/${id}/`)
}

export function createInspectionPlan(data) {
  return api.post('/inspection/plans/', data)
}

export function updateInspectionPlan(id, data) {
  return api.put(`/inspection/plans/${id}/`, data)
}

export function deleteInspectionPlan(id) {
  return api.delete(`/inspection/plans/${id}/`)
}

export function executeInspectionPlan(id) {
  return api.post(`/inspection/plans/${id}/execute/`)
}

export function getInspectionTasks(params) {
  return api.get('/inspection/tasks/', { params })
}

// ========== 巡检记录 ==========
export function getInspectionRecords(params) {
  return api.get('/inspection/inspections/', { params })
}

export function getInspectionRecord(id) {
  return api.get(`/inspection/inspections/${id}/`)
}

// ========== 任务模板 ==========
export function getTaskTemplates() {
  return api.get('/scheduler/v2/templates/')
}

export function useTaskTemplate(templateId, data) {
  return api.post(`/scheduler/v2/templates/${templateId}/use_template/`, data)
}

// ========== 调度计划 ==========
export function getSchedulerPlans(params) {
  return api.get('/scheduler/v2/plans/', { params })
}

export function getSchedulerPlan(id) {
  return api.get(`/scheduler/v2/plans/${id}/`)
}

export function createSchedulerPlan(data) {
  return api.post('/scheduler/v2/plans/', data)
}

export function updateSchedulerPlan(id, data) {
  return api.put(`/scheduler/v2/plans/${id}/`, data)
}

export function deleteSchedulerPlan(id) {
  return api.delete(`/scheduler/v2/plans/${id}/`)
}

export function executeSchedulerPlan(id) {
  return api.post(`/scheduler/v2/plans/${id}/execute/`)
}

export function toggleSchedulerPlan(id, enabled) {
  return enabled
    ? api.post(`/scheduler/v2/plans/${id}/enable/`)
    : api.post(`/scheduler/v2/plans/${id}/disable/`)
}

export function getSchedulerExecutions(params) {
  return api.get('/scheduler/v2/executions/', { params })
}

// ========== 临时任务 ==========
export function getAdhocTasks(params) {
  return api.get('/scheduler/v2/adhoc/', { params })
}

export function cancelAdhocTask(id) {
  return api.post(`/scheduler/v2/adhoc/${id}/cancel/`)
}

export function rerunAdhocTask(id) {
  return api.post(`/scheduler/v2/adhoc/${id}/rerun/`)
}
