<template>
  <div class="app-layout">
    <!-- 侧边栏 -->
    <Sidebar
      :collapsed="sidebarCollapsed"
      :active-page="activePage"
      :selected-category="selectedCategory"
      :categories="categories"
      :total="total"
      :env-info="envInfo"
      @toggle="sidebarCollapsed = !sidebarCollapsed"
      @navigate="activePage = $event"
      @go-library="goToLibrary"
      @collect="showCollectDialog = true"
    />

    <!-- 主内容区 -->
    <main class="main-content">
      <!-- 仪表盘页 -->
      <template v-if="activePage === 'dashboard'">
        <header class="page-header">
          <div>
            <h1>数据概览</h1>
            <p class="page-subtitle">了解你的视频收藏情况</p>
          </div>
          <el-button type="primary" round @click="showCollectDialog = true">
            <el-icon><Plus /></el-icon>
            <span>收藏视频</span>
          </el-button>
        </header>

        <Dashboard
          :total="total"
          :analyzed-count="analyzedCount"
          :pending-count="pendingCount"
          :analyzing-count="analyzingCount"
          :categories="categories"
          :videos="videos"
          :proxy-cover-url="proxyCoverUrl"
          @collect="showCollectDialog = true"
          @view-all="activePage = 'library'"
          @view-category="goToLibrary"
          @view-pending="goToPending"
          @search="activePage = 'library'"
          @select-video="showDetail"
        />
      </template>

      <!-- 视频库页 -->
      <template v-if="activePage === 'library'">
        <header class="page-header">
          <div>
            <h1>{{ selectedCategory || '全部视频' }}</h1>
            <p class="page-subtitle">{{ total }} 个视频</p>
          </div>
          <div class="header-actions">
            <el-input
              v-model="searchQuery"
              placeholder="搜索标题、描述、标签、AI 分析..."
              clearable
              style="width: 280px"
              @keyup.enter="handleSearch"
              @clear="handleSearch"
            >
              <template #prefix><el-icon><Search /></el-icon></template>
            </el-input>
          </div>
        </header>

        <VideoLibrary
          :videos="videos"
          :total="total"
          :current-page="currentPage"
          :page-size="pageSize"
          :loading="loading"
          :search-query="searchQuery"
          :cover-url-fn="proxyCoverUrl"
          @select-video="showDetail"
          @collect="showCollectDialog = true"
          @page-change="(p) => { currentPage = p; loadVideos() }"
        />
      </template>
    </main>

    <!-- 收藏弹窗 -->
    <CollectDialog
      v-model="showCollectDialog"
      :loading="collecting"
      @submit="handleCollect"
      @closed="shareText = ''"
    />

    <!-- 详情弹窗 -->
    <DetailDialog
      v-model="detailVisible"
      :video="detailVideo"
      :cover-url="detailVideo ? proxyCoverUrl(detailVideo.cover_url) : ''"
      :analyzing="analyzing"
      :re-analyze="reAnalyzeMode"
      :env-info="envInfo"
      :category-options="categoryOptions"
      @analyze="handleAnalyze"
      @open-url="openVideoUrl"
      @delete="handleDelete(detailVideo)"
      @save-category="(cat) => saveCategory(cat)"
      @closed="stopAnalyzePolling()"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus } from '@element-plus/icons-vue'
import {
  collectVideo, fetchVideos, fetchVideoDetail, deleteVideo,
  fetchCategories, updateVideoCategory, proxyImageUrl,
  analyzeVideo, getAnalyzeStatus, checkEnv,
} from './api.js'
import Sidebar from './components/Sidebar.vue'
import Dashboard from './components/Dashboard.vue'
import VideoLibrary from './components/VideoLibrary.vue'
import CollectDialog from './components/CollectDialog.vue'
import DetailDialog from './components/DetailDialog.vue'

// --- 状态 ---
const activePage = ref('dashboard')
const sidebarCollapsed = ref(false)
const shareText = ref('')
const collecting = ref(false)
const videos = ref([])
const loading = ref(false)
const searchQuery = ref('')
const selectedCategory = ref('')
const categories = ref([])
const currentPage = ref(1)
const pageSize = 20
const total = ref(0)
const showCollectDialog = ref(false)
const detailVisible = ref(false)
const detailVideo = ref(null)
const analyzing = ref(false)
const reAnalyzeMode = ref(false)
const envInfo = ref(null)
let analyzePollTimer = null

const categoryOptions = ['美食', '科技', '教育', '娱乐', '生活', '财经', '健身', '旅游', '设计', '编程']

const analyzedCount = computed(() => videos.value.filter(v => v.analyze_status === 'done').length)
const pendingCount = computed(() => videos.value.filter(v => v.analyze_status !== 'done' && v.analyze_status !== 'analyzing').length)
const analyzingCount = computed(() => videos.value.filter(v => v.analyze_status === 'analyzing').length)

// --- 工具函数 ---
function proxyCoverUrl(url) { return proxyImageUrl(url) }

function goToLibrary(cat) {
  selectedCategory.value = cat
  activePage.value = 'library'
  currentPage.value = 1
  loadVideos()
}

function goToPending() {
  selectedCategory.value = ''
  searchQuery.value = ''
  activePage.value = 'library'
  currentPage.value = 1
  loadVideos()
}

function openVideoUrl() {
  if (detailVideo.value?.url) window.open(detailVideo.value.url, '_blank')
}

// --- 数据加载 ---
async function loadVideos() {
  loading.value = true
  try {
    const res = await fetchVideos(currentPage.value, pageSize, searchQuery.value, selectedCategory.value)
    videos.value = res.data.videos || []
    total.value = res.data.total || 0
  } catch {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  try {
    categories.value = (await fetchCategories()).data || []
  } catch {
    categories.value = []
  }
}

function handleSearch() {
  currentPage.value = 1
  loadVideos()
}

// --- 收藏 ---
async function handleCollect(text) {
  if (!text?.trim()) return
  shareText.value = text
  collecting.value = true
  try {
    const res = await collectVideo(text)
    if (res.data?.is_existing) {
      ElMessage.info(res.data.message || '该视频已在收藏列表中')
    } else {
      const msg = res.data?.auto_analyze ? '收藏成功，AI 分析已自动开始' : '收藏成功'
      ElMessage.success(msg)
    }
    showCollectDialog.value = false
    shareText.value = ''
    await loadVideos()
    await loadCategories()
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '收藏失败')
  } finally {
    collecting.value = false
  }
}

// --- 详情 ---
async function showDetail(video) {
  try {
    detailVideo.value = (await fetchVideoDetail(video.id)).data
    reAnalyzeMode.value = false
    detailVisible.value = true
    if (detailVideo.value.analyze_status === 'analyzing') startAnalyzePolling(video.id)
    else stopAnalyzePolling()
  } catch {
    ElMessage.error('加载详情失败')
  }
}

async function saveCategory(category) {
  if (!detailVideo.value) return
  try {
    const res = await updateVideoCategory(detailVideo.value.id, category)
    detailVideo.value = res.data.video
    ElMessage.success('分类已更新')
    await loadVideos()
    await loadCategories()
  } catch {
    ElMessage.error('更新失败')
  }
}

async function handleDelete(video) {
  if (!video) return
  try {
    await ElMessageBox.confirm('确定删除这个视频？', '提示', { confirmButtonText: '删除', type: 'warning' })
    await deleteVideo(video.id)
    ElMessage.success('已删除')
    detailVisible.value = false
    await loadVideos()
    await loadCategories()
  } catch (err) {
    if (err !== 'cancel') ElMessage.error('删除失败')
  }
}

// --- AI 分析 ---
async function handleAnalyze() {
  if (!detailVideo.value) return
  analyzing.value = true
  reAnalyzeMode.value = false
  try {
    const res = await analyzeVideo(detailVideo.value.id)
    const result = res.data
    if (result.status === 'analyzing') {
      // 异步模式：开始轮询
      detailVideo.value = result.video
      startAnalyzePolling(detailVideo.value.id)
    } else {
      // 同步模式（旧版兼容）
      detailVideo.value = result.video
      ElMessage.success('分析完成')
      await loadVideos()
    }
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '分析失败')
  } finally {
    analyzing.value = false
  }
}

function startAnalyzePolling(videoId) {
  stopAnalyzePolling()
  analyzePollTimer = setInterval(async () => {
    try {
      const res = await getAnalyzeStatus(videoId)
      detailVideo.value = res.data
      if (res.data.analyze_status !== 'analyzing') {
        stopAnalyzePolling()
        if (res.data.analyze_status === 'done') ElMessage.success('分析完成')
        await loadVideos()
      }
    } catch { /* 跳过轮询错误 */ }
  }, 3000)
}

function stopAnalyzePolling() {
  if (analyzePollTimer) { clearInterval(analyzePollTimer); analyzePollTimer = null }
}

// --- 生命周期 ---
onMounted(async () => {
  await loadVideos()
  await loadCategories()
  try { envInfo.value = (await checkEnv()).data } catch { /* ignore */ }
})

onUnmounted(() => stopAnalyzePolling())
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
  background: #f5f7fa;
  color: #303133;
}

/* 布局 */
.app-layout { display: flex; min-height: 100vh; }

/* 主内容区 */
.main-content { flex: 1; display: flex; flex-direction: column; overflow-y: auto; }

/* 页面头部 */
.page-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 24px 32px 16px;
}

.page-header h1 { font-size: 24px; font-weight: 600; color: #1a1a2e; }
.page-subtitle { font-size: 13px; color: #909399; margin-top: 2px; }
.header-actions { display: flex; align-items: center; gap: 12px; }

/* 响应式 */
@media (max-width: 900px) {
  .page-header { flex-direction: column; align-items: flex-start; gap: 12px; }
}
</style>
