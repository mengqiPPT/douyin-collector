import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

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
  return `/api/proxy-image?url=${encodeURIComponent(url)}`
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
