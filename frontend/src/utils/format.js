import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'

// 格式化日期
export function formatDate(date, format = 'YYYY-MM-DD') {
  if (!date) return '-'
  return dayjs(date).format(format)
}

// 格式化日期时间
export function formatDateTime(date, format = 'YYYY-MM-DD HH:mm:ss') {
  if (!date) return '-'
  return dayjs(date).format(format)
}

// 相对时间
export function formatRelativeTime(date) {
  if (!date) return '-'
  return dayjs(date).locale('zh-cn').fromNow()
}

// 格式化数字
export function formatNumber(num, decimals = 0) {
  if (num === null || num === undefined) return '-'
  return Number(num).toFixed(decimals)
}

// 格式化文件大小
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// 状态颜色
export function getStatusType(status) {
  const types = {
    'ACTIVE': 'success',
    'INACTIVE': 'info',
    'MAINTENANCE': 'warning',
    'DECOMMISSIONED': 'danger',
    'OPEN': 'danger',
    'ACKNOWLEDGED': 'warning',
    'RESOLVED': 'success'
  }
  return types[status] || 'info'
}

// 状态文本
export function getStatusText(status) {
  const texts = {
    'ACTIVE': '活跃',
    'INACTIVE': '停用',
    'MAINTENANCE': '维护中',
    'DECOMMISSIONED': '已退役',
    'OPEN': '未处理',
    'ACKNOWLEDGED': '已确认',
    'RESOLVED': '已解决'
  }
  return texts[status] || status
}

// 重要等级颜色
export function getImportanceType(level) {
  const types = {
    'LOW': 'info',
    'MEDIUM': 'warning',
    'HIGH': 'danger',
    'CRITICAL': 'danger'
  }
  return types[level] || 'info'
}

// 重要等级文本
export function getImportanceText(level) {
  const texts = {
    'LOW': '低',
    'MEDIUM': '中',
    'HIGH': '高',
    'CRITICAL': '关键'
  }
  return texts[level] || level
}