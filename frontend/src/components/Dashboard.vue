<template>
  <div class="dashboard-body">
    <!-- 统计卡片行 -->
    <div class="stat-row">
      <StatCard :icon="Collection" color="red" :num="total" label="已收藏" />
      <StatCard :icon="CircleCheck" color="green" :num="analyzedCount" label="已分析" />
      <StatCard :icon="DataAnalysis" color="blue" :num="analyzeRate" label="分析完成率" suffix="%" />
      <StatCard :icon="FolderOpened" color="purple" :num="categories.length" label="分类数" />
    </div>

    <!-- 三栏核心区 -->
    <div class="three-col">
      <AnalysisRing
        :total="total"
        :analyzed="analyzedCount"
        :pending="pendingCount"
        :analyzing="analyzingCount"
      />

      <CategoryCloud
        :categories="categories"
        :total="total"
        @select="$emit('view-category', $event)"
      />

      <QuickActions
        :total="total"
        :pending="pendingCount"
        :analyzed="analyzedCount"
        @collect="$emit('collect')"
        @view-pending="$emit('view-pending')"
        @search="$emit('search')"
      />
    </div>

    <!-- 最近收藏 — 全宽 -->
    <div class="section-card">
      <div class="section-title flex-between">
        <span>最近收藏</span>
        <el-button size="small" text @click="$emit('view-all')">
          查看全部 <el-icon><ArrowRight /></el-icon>
        </el-button>
      </div>

      <div class="recent-list" v-if="videos.length > 0">
        <div
          v-for="video in videos.slice(0, 8)"
          :key="video.id"
          class="recent-item"
          @click="$emit('select-video', video)"
        >
          <div class="recent-cover" v-if="video.cover_url">
            <img :src="proxyCoverUrl(video.cover_url)"
              :alt="video.title"
              loading="lazy"
              @error="e => e.target.style.display = 'none'" />
          </div>
          <div v-else class="recent-cover placeholder">
            <el-icon><VideoCamera /></el-icon>
          </div>
          <div class="recent-info">
            <div class="recent-title">{{ cleanTitle(video.title) }}</div>
            <div class="recent-meta">
              <span class="recent-author">{{ video.author || '未知' }}</span>
              <span class="recent-date">{{ fmtDate(video.created_at) }}</span>
              <span class="status-tag" :class="video.analyze_status">
                {{ statusMap[video.analyze_status] || '待分析' }}
              </span>
            </div>
          </div>
        </div>
      </div>

      <div class="recent-empty" v-else>
        <el-icon size="36" color="#dcdfe6"><FolderAdd /></el-icon>
        <p>暂无收藏，点击上方"收藏新视频"开始</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowRight, VideoCamera, FolderAdd, Collection, CircleCheck, DataAnalysis, FolderOpened } from '@element-plus/icons-vue'
import StatCard from './dashboard/StatCard.vue'
import AnalysisRing from './dashboard/AnalysisRing.vue'
import CategoryCloud from './dashboard/CategoryCloud.vue'
import QuickActions from './dashboard/QuickActions.vue'

const props = defineProps({
  total: Number,
  analyzedCount: Number,
  pendingCount: Number,
  analyzingCount: Number,
  categories: Array,
  videos: Array,
  proxyCoverUrl: Function,
})

defineEmits(['collect', 'view-all', 'view-category', 'view-pending', 'search', 'select-video'])

const analyzeRate = computed(() => {
  if (props.total === 0) return 0
  return Math.round((props.analyzedCount / props.total) * 100)
})

const statusMap = { done: '已分析', analyzing: '分析中', pending: '待分析', '': '待分析' }

function cleanTitle(t) { return (t || '').replace(/#\S+/g, '').trim() }
function fmtDate(d) {
  if (!d) return ''
  const dt = new Date(d)
  return isNaN(dt) ? d : `${dt.getMonth() + 1}/${dt.getDate()}`
}
</script>

<style scoped>
.dashboard-body { padding: 0 32px 32px; flex: 1; }

/* 统计卡片 */
.stat-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 22px;
}

/* 三栏均分 — stretch 让三栏等高 */
.three-col {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 18px;
  margin-bottom: 22px;
}

/* 全宽卡片 */
.section-card {
  background: #fff;
  border-radius: 14px;
  padding: 22px 24px;
  border: 1px solid #eef0f5;
}
.section-title {
  font-size: 15px; font-weight: 600; color: #1a1a2e;
  margin-bottom: 16px;
}
.section-title.flex-between {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

/* 最近收藏 — 水平多列网格 */
.recent-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 8px;
}

.recent-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; border-radius: 10px;
  cursor: pointer; transition: all 0.15s;
}
.recent-item:hover { background: #f8f9fb; }

.recent-cover {
  width: 60px; height: 40px; border-radius: 6px;
  overflow: hidden; flex-shrink: 0; background: #f0f2f5;
}
.recent-cover img { width: 100%; height: 100%; object-fit: cover; }
.recent-cover.placeholder {
  display: flex; align-items: center; justify-content: center; color: #c0c4cc;
}

.recent-info { flex: 1; min-width: 0; }
.recent-title {
  font-size: 13px; font-weight: 500; color: #303133; line-height: 1.3;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.recent-meta {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; color: #b0b3bb; margin-top: 3px;
  flex-wrap: wrap;
}

.status-tag {
  font-size: 10px; padding: 1px 6px; border-radius: 4px; font-weight: 500;
}
.status-tag.done { background: #f0f9eb; color: #67c23a; }
.status-tag.pending { background: #fdf6ec; color: #e6a23c; }
.status-tag.analyzing { background: #ecf5ff; color: #409eff; }

.recent-empty {
  display: flex; flex-direction: column; align-items: center;
  gap: 8px; padding: 36px 0;
  color: #c0c4cc; font-size: 13px;
}

/* 响应式 */
@media (max-width: 1200px) {
  .three-col { grid-template-columns: 1fr 1fr; }
  .recent-list { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 900px) {
  .stat-row { grid-template-columns: repeat(2, 1fr); }
  .three-col { grid-template-columns: 1fr; }
  .recent-list { grid-template-columns: 1fr; }
  .dashboard-body { padding: 0 16px 16px; }
}
</style>
