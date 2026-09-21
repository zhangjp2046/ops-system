import api from './index'

export default {
  // ============ 发现任务 ============

  /** 获取发现任务列表 */
  getTasks(params = {}) {
    return api.get('/discovery/tasks/', { params })
  },

  /** 获取单个任务 */
  getTask(id) {
    return api.get(`/discovery/tasks/${id}/`)
  },

  /** 创建发现任务 */
  createTask(data) {
    return api.post('/discovery/tasks/', data)
  },

  /** 启动扫描 */
  startScan(taskId) {
    return api.post(`/discovery/tasks/${taskId}/start/`)
  },

  /** 取消扫描 */
  cancelScan(taskId) {
    return api.post(`/discovery/tasks/${taskId}/cancel/`)
  },

  /** 获取任务发现的设备 */
  getTaskDevices(taskId) {
    return api.get(`/discovery/tasks/${taskId}/devices/`)
  },

  // ============ 快速扫描 ============

  /** 快速扫描（同步） */
  quickScan(params) {
    return api.get('/discovery/tasks/quick_scan/', { params })
  },

  /** 端口扫描 */
  portsScan(params) {
    return api.get('/discovery/tasks/ports_scan/', { params })
  },

  // ============ 智能扫描 ============

  /** 分析已有资产，推断网段 */
  analyzeSubnets(customerId) {
    return api.get('/discovery/tasks/analyze_subnets/', { params: { customer: customerId } })
  },

  /** 智能扫描（后台执行，返回任务ID） */
  smartScan(data) {
    return api.post('/discovery/tasks/smart_scan/', data, { timeout: 600000 })
  },

  /** 查询智能扫描结果 */
  getSmartScanResult(taskId) {
    return api.get(`/discovery/tasks/${taskId}/smart_scan_result/`)
  },

  /** 批量导入新设备为资产 */
  importNewDevices(data) {
    return api.post('/discovery/tasks/import_new_devices/', data)
  },

  // ============ 发现设备 ============

  /** 获取发现设备列表 */
  getDevices(params = {}) {
    return api.get('/discovery/devices/', { params })
  },

  /** 导入设备为资产 */
  importAsset(deviceId) {
    return api.post(`/discovery/devices/${deviceId}/import_asset/`)
  },

  // ============ 拓扑图 ============

  /** 获取拓扑图 */
  getTopologyGraph(customerId) {
    return api.get('/discovery/topology/graph/', { params: { customer: customerId } })
  },

  /** 从发现任务构建拓扑 */
  buildFromDiscovery(taskId, customerId) {
    return api.post('/discovery/topology/build_from_discovery/', {
      task_id: taskId,
      customer_id: customerId
    })
  },

  /** 更新节点位置 */
  updateNodePosition(nodeId, x, y) {
    return api.post(`/discovery/topology/${nodeId}/update_position/`, { x, y })
  },

  /** 添加连线 */
  addEdge(data) {
    return api.post('/discovery/topology/add_edge/', data)
  },

  /** 删除连线 */
  removeEdge(edgeId) {
    return api.delete('/discovery/topology/remove_edge/', { data: { edge_id: edgeId } })
  },

  /** 导出拓扑图（D3格式） */
  exportGraph(customerId) {
    return api.get('/discovery/topology/export_graph/', { params: { customer: customerId } })
  }
}
