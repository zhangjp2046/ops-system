import api from './index'

// 获取资产列表
export function getAssetList(params) {
  return api.get('/assets/assets/', { params })
}

// 获取资产详情
export function getAsset(id) {
  return api.get(`/assets/assets/${id}/`)
}

// 创建资产
export function createAsset(data) {
  return api.post('/assets/assets/', data)
}

// 更新资产
export function updateAsset(id, data) {
  return api.put(`/assets/assets/${id}/`, data)
}

// 部分更新资产
export function partialUpdateAsset(id, data) {
  return api.patch(`/assets/assets/${id}/`, data)
}

// 删除资产
export function deleteAsset(id) {
  return api.delete(`/assets/assets/${id}/`)
}

// 批量导入资产
export function importAssets(data) {
  return api.post('/assets/assets/import/', data)
}

// 获取资产统计
export function getAssetStats() {
  return api.get('/assets/assets/stats/')
}

// 获取资产字段数据
export function getAssetFieldData(id) {
  return api.get(`/assets/assets/${id}/field-data/`)
}

// 更新资产字段
export function updateAssetField(id, fieldCode, value) {
  return api.post(`/assets/assets/${id}/update-field/`, { field_code: fieldCode, value })
}

// 激活资产
export function activateAsset(id) {
  return api.post(`/assets/assets/${id}/activate/`)
}

// 停用资产
export function deactivateAsset(id) {
  return api.post(`/assets/assets/${id}/deactivate/`)
}

// 获取资产类型列表
export function getAssetTypeList(params) {
  return api.get('/assets/types/', { params })
}

// 获取资产类型详情
export function getAssetType(id) {
  return api.get(`/assets/types/${id}/`)
}

// 创建资产类型
export function createAssetType(data) {
  return api.post('/assets/types/', data)
}

// 更新资产类型
export function updateAssetType(id, data) {
  return api.put(`/assets/types/${id}/`, data)
}

// 删除资产类型
export function deleteAssetType(id) {
  return api.delete(`/assets/types/${id}/`)
}

// 获取资产类型的字段
export function getAssetTypeFields(id) {
  return api.get(`/assets/types/${id}/fields/`)
}
// ========== 资产调拨 API ==========

export function getTransferList(params) {
  return api.get('/assets/transfers/', { params })
}

export function getTransfer(id) {
  return api.get(`/assets/transfers/${id}/`)
}

export function createTransfer(data) {
  return api.post('/assets/transfers/', data)
}

export function updateTransfer(id, data) {
  return api.put(`/assets/transfers/${id}/`, data)
}

export function deleteTransfer(id) {
  return api.delete(`/assets/transfers/${id}/`)
}

export function approveTransfer(id, comment) {
  return api.post(`/assets/transfers/${id}/approve/`, { comment })
}

export function rejectTransfer(id, comment) {
  return api.post(`/assets/transfers/${id}/reject/`, { comment })
}

export function executeTransfer(id) {
  return api.post(`/assets/transfers/${id}/execute/`)
}

// ========== 资产维修 API ==========

export function getRepairList(params) {
  return api.get('/assets/repairs/', { params })
}

export function getRepair(id) {
  return api.get(`/assets/repairs/${id}/`)
}

export function createRepair(data) {
  return api.post('/assets/repairs/', data)
}

export function updateRepair(id, data) {
  return api.put(`/assets/repairs/${id}/`, data)
}

export function deleteRepair(id) {
  return api.delete(`/assets/repairs/${id}/`)
}

export function assignRepair(id, assignee, assigneePhone) {
  return api.post(`/assets/repairs/${id}/assign/`, { assignee, assignee_phone: assigneePhone })
}

export function acceptRepair(id) {
  return api.post(`/assets/repairs/${id}/accept/`)
}

export function processRepair(id) {
  return api.post(`/assets/repairs/${id}/process/`)
}

export function completeRepair(id, repairResult, repairCost, partsCost) {
  return api.post(`/assets/repairs/${id}/complete/`, { repair_result: repairResult, repair_cost: repairCost, parts_cost: partsCost })
}

export function acceptRepairInspect(id, acceptResult, acceptComment) {
  return api.post(`/assets/repairs/${id}/accept-inspect/`, { accept_result: acceptResult, accept_comment: acceptComment })
}

// ========== 资产报废 API ==========

export function getScrapList(params) {
  return api.get('/assets/scraps/', { params })
}

export function getScrap(id) {
  return api.get(`/assets/scraps/${id}/`)
}

export function createScrap(data) {
  return api.post('/assets/scraps/', data)
}

export function updateScrap(id, data) {
  return api.put(`/assets/scraps/${id}/`, data)
}

export function deleteScrap(id) {
  return api.delete(`/assets/scraps/${id}/`)
}

export function approveScrap(id, action, comment) {
  return api.post(`/assets/scraps/${id}/approve/`, { action, comment })
}

export function executeScrap(id, disposalResult) {
  return api.post(`/assets/scraps/${id}/execute/`, { disposal_result: disposalResult })
}

// ========== 资产出借 API ==========

export function getLendList(params) {
  return api.get('/assets/lends/', { params })
}

export function getLend(id) {
  return api.get(`/assets/lends/${id}/`)
}

export function createLend(data) {
  return api.post('/assets/lends/', data)
}

export function updateLend(id, data) {
  return api.put(`/assets/lends/${id}/`, data)
}

export function deleteLend(id) {
  return api.delete(`/assets/lends/${id}/`)
}

export function approveLend(id, action, comment) {
  return api.post(`/assets/lends/${id}/approve/`, { action, comment })
}

export function lendOut(id) {
  return api.post(`/assets/lends/${id}/lend_out/`)
}

export function returnLend(id, returnAcceptance) {
  return api.post(`/assets/lends/${id}/return_asset/`, { return_acceptance: returnAcceptance })
}

export function checkOverdue(id) {
  return api.post(`/assets/lends/${id}/check_overdue/`)}
