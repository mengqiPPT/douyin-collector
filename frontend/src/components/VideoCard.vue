<template>
  <div
    class="video-card"
    @click="$emit('select', video)"
  >
    <div class="card-cover">
      <img
        v-if="video.cover_url"
        :src="coverUrl"
        :alt="video.title"
        class="cover-img"
        :class="{ hidden: !coverLoaded }"
        @load="onCoverLoad"
        @error="onCoverError"
        ref="coverImgRef"
      />
      <div v-if="!coverLoaded" class="cover-fallback" :class="fallbackClass">
        <div class="fallback-content">
          <el-icon size="28"><VideoCamera /></el-icon>
          <p class="fallback-title">{{ cleanTitle(video.title) || '视频收藏' }}</p>
          <span class="fallback-cat" v-if="video.category">{{ video.category }}</span>
        </div>
      </div>
      <div class="status-corner" :class="video.analyze_status" v-if="video.analyze_status">
        <el-icon v-if="video.analyze_status === 'done'" title="已分析"><CircleCheck /></el-icon>
        <el-icon v-else-if="video.analyze_status === 'analyzing'" class="is-loading" title="分析中"><Loading /></el-icon>
        <el-icon v-else title="待分析"><Clock /></el-icon>
      </div>
    </div>
    <div class="card-info">
      <h3 class="card-title">{{ cleanTitle(video.title) }}</h3>
      <div class="card-meta">
        <img v-if="video.author_avatar" :src="video.author_avatar" class="meta-avatar" @error="e => e.target.style.display='none'" />
        <span v-else class="meta-avatar-placeholder"></span>
        <span class="meta-author">{{ video.author || '未知' }}</span>
        <span class="meta-date">{{ formatDate(video.created_at) }}</span>
      </div>

      <!-- 标签区：始终占位，保证高度一致 -->
      <div class="card-tags" :class="{ empty: !video.tags?.length }">
        <template v-if="video.tags && video.tags.length">
          <span v-for="tag in video.tags.slice(0, 3)" :key="tag" class="tag">{{ tag }}</span>
        </template>
      </div>

      <!-- AI 摘要区：始终占位 -->
      <div class="card-summary" :class="{ empty: !video.ai_summary }">
        {{ truncate(video.ai_summary, 48) || ' ' }}
      </div>

      <!-- 互动数据：始终占位 -->
      <div class="card-stats">
        <span class="stat-item"><el-icon size="12"><StarFilled /></el-icon> {{ fmtNum(video.like_count) || '-' }}</span>
        <span class="stat-item"><el-icon size="12"><ChatDotSquare /></el-icon> {{ fmtNum(video.comment_count) || '-' }}</span>
        <span class="stat-item"><el-icon size="12"><Share /></el-icon> {{ fmtNum(video.share_count) || '-' }}</span>
      </div>

      <div class="card-bottom">
        <span class="category-pill" v-if="video.category">{{ video.category }}</span>
        <span v-for="tag in (video.ai_tags || []).slice(0, 2)" :key="tag" class="ai-tag">{{ tag }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { VideoCamera, CircleCheck, Loading, Clock, StarFilled, ChatDotSquare, Share } from '@element-plus/icons-vue'

const props = defineProps({
  video: { type: Object, required: true },
  coverUrl: { type: String, default: '' },
})

defineEmits(['select', 'img-error'])

const coverLoaded = ref(false)
const coverImgRef = ref(null)

function onCoverLoad() { coverLoaded.value = true }
function onCoverError() { coverLoaded.value = false }

// 切换视频时重置封面状态
watch(() => props.video?.id, () => {
  coverLoaded.value = false
  nextTick(() => {
    if (props.video?.cover_url && coverImgRef.value?.complete && coverImgRef.value?.naturalWidth > 0) {
      coverLoaded.value = true
    }
  })
}, { immediate: false })

// 无封面时用分类颜色区分卡片
const fallbackColors = {
  'AI内容创作': 'grad-ai',
  'AI工具应用': 'grad-tool',
  'AI与数据': 'grad-data',
  '编程开发': 'grad-dev',
  '设计创意': 'grad-design',
  '科技数码': 'grad-tech',
  '职场商业': 'grad-biz',
  '学习成长': 'grad-learn',
  '生活兴趣': 'grad-life',
  '娱乐综艺': 'grad-fun',
}
const fallbackClass = computed(() => {
  for (const [key, cls] of Object.entries(fallbackColors)) {
    if ((props.video.category || '').startsWith(key)) return cls
  }
  return 'grad-default'
})

function cleanTitle(title) {
  return (title || '').replace(/#\S+/g, '').trim()
}

function formatDate(dateStr) {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  return isNaN(d) ? dateStr : `${d.getMonth() + 1}/${d.getDate()}`
}

function truncate(text, len) {
  return text?.length > len ? text.slice(0, len) + '...' : text || ''
}

function fmtNum(n) {
  if (n == null || n === '') return '0'
  const num = Number(n) || 0
  if (num >= 10000) return (num / 10000).toFixed(1) + 'w'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'k'
  return String(num)
}
</script>

<style scoped>
.video-card {
  background: #fff; border-radius: 12px;
  overflow: hidden; cursor: pointer;
  border: 1px solid #eef0f5;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  display: flex; flex-direction: column; height: 100%;
}

.video-card:hover {
  border-color: #fe2c55;
  box-shadow: 0 8px 24px rgba(0,0,0,0.08);
  transform: translateY(-3px);
}

.card-cover {
  position: relative; width: 100%; aspect-ratio: 16/9;
  overflow: hidden; background: #f5f7fa;
}

.cover-img { width: 100%; height: 100%; object-fit: cover; transition: transform 0.3s; }
.cover-img.hidden { opacity: 0; position: absolute; }
.video-card:hover .cover-img { transform: scale(1.03); }

/* 封面加载失败 / 无封面时的渐变文字卡片 */
.cover-fallback {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  padding: 16px; text-align: center;
}
.fallback-content {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
}
.fallback-content .el-icon { opacity: 0.5; }
.fallback-title {
  font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.9);
  line-height: 1.4;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  max-width: 100%;
}
.fallback-cat {
  font-size: 11px; padding: 2px 10px; border-radius: 10px;
  background: rgba(255,255,255,0.2); color: rgba(255,255,255,0.85);
}

/* 8 种分类渐变背景色 */
.grad-ai     { background: linear-gradient(135deg, #667eea, #764ba2); }
.grad-tool   { background: linear-gradient(135deg, #4facfe, #00f2fe); }
.grad-data   { background: linear-gradient(135deg, #43e97b, #38f9d7); }
.grad-dev    { background: linear-gradient(135deg, #f093fb, #f5576c); }
.grad-design { background: linear-gradient(135deg, #fa709a, #fee140); }
.grad-tech   { background: linear-gradient(135deg, #a18cd1, #fbc2eb); }
.grad-biz    { background: linear-gradient(135deg, #fccb90, #d57eeb); }
.grad-learn  { background: linear-gradient(135deg, #96fbc4, #f9f586); }
.grad-life   { background: linear-gradient(135deg, #ffecd2, #fcb69f); }
.grad-fun    { background: linear-gradient(135deg, #ff9a9e, #fecfef); }
.grad-default{ background: linear-gradient(135deg, #e0c3fc, #8ec5fc); }

.status-corner {
  position: absolute; top: 10px; right: 10px;
  width: 26px; height: 26px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
}
.status-corner.done { background: rgba(82,196,26,0.92); color: white; }
.status-corner.pending { background: rgba(255,169,64,0.92); color: white; }
.status-corner.analyzing { background: rgba(24,144,255,0.92); color: white; }

.card-info { padding: 14px 16px 16px; flex: 1; display: flex; flex-direction: column; }

.card-title {
  font-size: 14px; font-weight: 600; line-height: 1.5;
  margin: 0 0 8px; color: #1a1a2e;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}

.card-meta {
  display: flex; align-items: center; gap: 12px;
  font-size: 12px; color: #8c8c8c; margin-bottom: 10px;
}

.meta-avatar {
  width: 18px; height: 18px; border-radius: 50%;
  object-fit: cover; flex-shrink: 0;
}
.meta-avatar-placeholder {
  width: 18px; height: 18px; border-radius: 50%;
  background: #e8e8e8; flex-shrink: 0;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23999'%3E%3Cpath d='M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z'/%3E%3C/svg%3E");
  background-size: 12px; background-position: center; background-repeat: no-repeat;
}

.meta-author { display: flex; align-items: center; gap: 4px; }

.card-tags {
  display: flex; flex-wrap: wrap; gap: 6px;
  min-height: 26px;  /* 保证无标签时也占一行高度 */
  margin-bottom: 8px;
}
.card-tags.empty { min-height: 26px; }

.tag {
  font-size: 11px; line-height: 1.4;
  padding: 3px 8px; border-radius: 10px;
  background: #f4f4f5; color: #606266;
  border: 1px solid #e4e7ed;
}

.card-summary {
  font-size: 12px; color: #8c8c8c; line-height: 1.5;
  min-height: 36px;  /* 始终保留 2 行高度 */
  margin: 0 0 10px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}
.card-summary.empty { opacity: 0; }  /* 占位但不可见，保持布局 */

.card-stats {
  display: flex; gap: 12px;
  min-height: 20px;
  margin-bottom: 10px;
  padding: 4px 0;
  font-size: 12px; color: #606266;
}
.stat-item { display: flex; align-items: center; gap: 3px; }
.stat-item .el-icon { color: #fe2c55; }

  .card-bottom {
  display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
  padding-top: 10px; border-top: 1px solid #f2f3f5;
  margin-top: auto; min-height: 32px;
}

.category-pill {
  font-size: 11px; font-weight: 500;
  padding: 3px 10px; border-radius: 4px;
  background: #fff0f3; color: #fe2c55;
}

.ai-tag {
  font-size: 11px; font-weight: 500;
  padding: 3px 10px; border-radius: 4px;
  background: #f0f5ff; color: #2a7bf6;
}
</style>
