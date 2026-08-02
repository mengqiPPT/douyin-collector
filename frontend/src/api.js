import axios from 'axios'

// API 基础地址：优先级 环境变量 > 同源相对路径
// 开发时 Vite proxy 将 /api 转发到 localhost:8000
// 部署时设置 VITE_API_BASE=https://your-server.com/api
const API_BASE = import.meta.env.VITE_API_BASE || '/api'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
})

// 响应拦截：统一处理错误，避免白屏
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response) {
      console.warn(`[API] ${err.response.status} ${err.config?.url}: ${err.response.data?.detail || err.message}`)
    } else if (err.request) {
      console.warn(`[API] 后端不可达: ${err.config?.url} — 请确认后端已启动`)
    }
    return Promise.reject(err)
  },
)

// 收藏视频
export function collectVideo(shareText) {
  return api.post('/videos', { share_text: shareText })
}

// 获取视频列表
export function fetchVideos(page = 1, size = 20, q = '', category = '') {
  const params = { page, size }
  if (q) params.q = q
  if (category) params.category = category
  return api.get('/videos', { params })
}

// 获取视频详情
export function fetchVideoDetail(id) {
  return api.get(`/videos/${id}`)
}

// 删除视频
export function deleteVideo(id) {
  return api.delete(`/videos/${id}`)
}

// 获取分类列表
export function fetchCategories() {
  return api.get('/categories')
}

// 更新视频分类
export function updateVideoCategory(id, category) {
  return api.patch(`/videos/${id}`, { category })
}

// 封面图代理 URL
export function proxyImageUrl(url) {
  if (!url) return ''
  return `${API_BASE}/proxy-image?url=${encodeURIComponent(url)}`
}

// 触发 AI 分析
export function analyzeVideo(id) {
  return api.post(`/videos/${id}/analyze`, {}, { timeout: 120000 })
}

// 获取分析状态
export function getAnalyzeStatus(id) {
  return api.get(`/videos/${id}/analyze`)
}

// 检查环境依赖
export function checkEnv() {
  return api.get('/env-check')
}

export default api
