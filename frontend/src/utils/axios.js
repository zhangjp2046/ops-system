// Axios 实例 - 用于直接调用 API（不带 baseURL）
// MonitorTest.vue 等直接调用场景使用
import axios from 'axios'

// 创建无 baseURL 的 axios 实例
const rawAxios = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

export default rawAxios
