import api from './index'

export default {
  // ============ 任务计划 ============
  getPlans(params = {}) {
    return api.get('/scheduler/v2/plans/', { params })
  },
  getPlan(id) {
    return api.get(`/scheduler/v2/plans/${id}/`)
  },
  createPlan(data) {
    return api.post('/scheduler/v2/plans/', data)
  },
  updatePlan(id, data) {
    return api.put(`/scheduler/v2/plans/${id}/`, data)
  },
  deletePlan(id) {
    return api.delete(`/scheduler/v2/plans/${id}/`)
  },
  executePlan(id) {
    return api.post(`/scheduler/v2/plans/${id}/execute/`)
  },
  enablePlan(id) {
    return api.post(`/scheduler/v2/plans/${id}/enable/`)
  },
  disablePlan(id) {
    return api.post(`/scheduler/v2/plans/${id}/disable/`)
  },
  getPlanExecutions(id) {
    return api.get(`/scheduler/v2/plans/${id}/executions/`)
  },
  getPlanStatistics() {
    return api.get('/scheduler/v2/plans/statistics/')
  },

  // ============ 计划任务 ============
  getPlanTasks(params = {}) {
    return api.get('/scheduler/v2/plan-tasks/', { params })
  },
  createPlanTask(data) {
    return api.post('/scheduler/v2/plan-tasks/', data)
  },
  updatePlanTask(id, data) {
    return api.put(`/scheduler/v2/plan-tasks/${id}/`, data)
  },
  deletePlanTask(id) {
    return api.delete(`/scheduler/v2/plan-tasks/${id}/`)
  },
  reorderPlanTasks(ordering) {
    return api.post('/scheduler/v2/plan-tasks/reorder/', ordering)
  },

  // ============ 执行记录 ============
  getExecutions(params = {}) {
    return api.get('/scheduler/v2/executions/', { params })
  },
  getExecution(id) {
    return api.get(`/scheduler/v2/executions/${id}/`)
  },
  getRecentExecutions(limit = 20) {
    return api.get('/scheduler/v2/executions/recent/', { params: { limit } })
  },
  processDuePlans() {
    return api.post('/scheduler/v2/executions/process_due/')
  },

  // ============ 任务模板 ============
  getTemplates(params = {}) {
    return api.get('/scheduler/v2/templates/', { params })
  },
  getTemplate(id) {
    return api.get(`/scheduler/v2/templates/${id}/`)
  },
  useTemplate(id, data) {
    return api.post(`/scheduler/v2/templates/${id}/use_template/`, data)
  },

  // ============ 临时任务 ============
  getAdhocTasks(params = {}) {
    return api.get('/scheduler/v2/adhoc/', { params })
  },
  createAdhocTask(data) {
    return api.post('/scheduler/v2/adhoc/', data)
  },
  cancelAdhocTask(id) {
    return api.post(`/scheduler/v2/adhoc/${id}/cancel/`)
  },
  rerunAdhocTask(id) {
    return api.post(`/scheduler/v2/adhoc/${id}/rerun/`)
  },
  getPendingAdhocTasks() {
    return api.get('/scheduler/v2/adhoc/pending/')
  },

  // ============ 巡检计划联动 ============
  fromInspection(data) {
    return api.post('/scheduler/v2/plans/from_inspection/', data)
  },
  syncSchedule(id, direction = 'to_inspection') {
    return api.post(`/scheduler/v2/plans/${id}/sync_schedule/`, { direction })
  },
  getSchedulePresets() {
    return api.get('/scheduler/v2/plans/schedule_presets/')
  },
  getLinkedInspectionPlans() {
    return api.get('/scheduler/v2/plans/linked_inspection/')
  },

  // ============ 巡检计划列表（供选择）===========
  getInspectionPlans(params = {}) {
    return api.get('/inspection/plans/', { params })
  }
}
