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