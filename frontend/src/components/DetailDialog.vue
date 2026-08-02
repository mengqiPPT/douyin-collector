<template>
  <el-dialog
    v-model="visible"
    width="560px"
    class="detail-dialog"
    :show-close="true"
    destroy-on-close
    @closed="$emit('closed')"
  >
    <template v-if="video">
      <div class="detail-scroll">
        <div class="detail-cover" v-if="video.cover_url">
          <img :src="coverUrl" :alt="video.title" />
        </div>

        <div class="detail-body">
          <h2 class="detail-title">{{ video.title }}</h2>
          <div class="detail-author">
            <img v-if="video.author_avatar" :src="video.author_avatar" class="author-avatar" @error="e=>e.target.style.display='none'" />
            <div v-else class="author-avatar placeholder"><el-icon><User /></el-icon></div>
            <span class="author-name">{{ video.author || '未知' }}</span>
          </div>
          <div class="detail-meta">
            <span>{{ video.created_at }}</span>
            <span v-if="video.duration">{{ fmtDuration(video.duration) }}</span>
          </div>

          <!-- 互动数据 -->
          <div class="detail-stats" v-if="video.like_count || video.comment_count || video.share_count">
            <span class="dstat"><el-icon><StarFilled /></el-icon> {{ fmtNum(video.like_count) }}</span>
            <span class="dstat"><el-icon><ChatDotSquare /></el-icon> {{ fmtNum(video.comment_count) }}</span>
            <span class="dstat"><el-icon><Share /></el-icon> {{ fmtNum(video.share_count) }}</span>
          </div>

          <div class="detail-tags" v-if="video.tags && video.tags.length">
            <span v-for="tag in video.tags" :key="tag" class="tag">{{ tag }}</span>
          </div>

          <div class="detail-actions">
            <el-button
              type="primary"
              size="small"
              :loading="analyzing"
              :disabled="video.analyze_status === 'done' && !reAnalyze"
              @click="$emit('analyze')"
            >
              <el-icon><MagicStick /></el-icon>
              {{ video.analyze_status === 'done' ? '重新分析' : 'AI 分析' }}
            </el-button>
            <el-button size="small" @click="$emit('open-url')" v-if="video.url">
              <el-icon><Link /></el-icon> 打开原视频
            </el-button>
            <el-button size="small" type="danger" plain @click="$emit('delete')">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>

          <div class="detail-category">
            <span class="label">分类</span>
            <el-select v-model="editingCategory" size="small" style="width: 120px">
              <el-option v-for="cat in categoryOptions" :key="cat" :label="cat" :value="cat" />
            </el-select>
            <el-button size="small" type="primary" plain @click="$emit('save-category', editingCategory)">保存</el-button>
          </div>

          <!-- AI 分析结果 -->
          <div class="analyze-section">
            <div class="analyze-header">
              <span class="analyze-title">AI 分析结果</span>
              <div class="ai-badges" v-if="envInfo?.ai_providers?.length">
                <span class="ai-badge" v-for="p in envInfo.ai_providers" :key="p">{{ p }}</span>
                <span class="ai-badge multimodal" v-if="envInfo.ai_multimodal">🖼️ 多模态</span>
              </div>
            </div>

            <div v-if="video.analyze_status === 'analyzing'" class="analyzing-state">
              <el-icon class="is-loading" size="20"><Loading /></el-icon>
              <span>正在分析视频内容...</span>
            </div>

            <div v-if="video.analyze_status === 'done' && !reAnalyze" class="analyze-content">
              <div class="result-block" v-if="video.ai_summary">
                <div class="block-title">内容摘要</div>
                <p class="summary-text">{{ video.ai_summary }}</p>
              </div>

              <div class="result-block" v-if="video.ai_keypoints && video.ai_keypoints.length">
                <div class="block-title">核心要点</div>
                <ul class="keypoint-list">
                  <li v-for="(point, idx) in video.ai_keypoints" :key="idx">
                    <span class="bullet"></span>
                    <span>{{ point }}</span>
                  </li>
                </ul>
              </div>

              <div class="result-block" v-if="video.ai_tags && video.ai_tags.length">
                <div class="block-title">AI 标签</div>
                <div class="tag-row">
                  <span v-for="tag in video.ai_tags" :key="tag" class="ai-tag">{{ tag }}</span>
                </div>
              </div>

              <div class="result-block" v-if="video.transcribe_text">
                <div class="block-title">语音内容</div>
                <div class="transcribe-box">{{ video.transcribe_text }}</div>
              </div>

              <div class="analyze-time" v-if="video.analyzed_at">
                <el-icon size="12"><Clock /></el-icon>
                分析于 {{ video.analyzed_at }}
              </div>
            </div>

            <div v-if="video.analyze_status === 'pending' && !analyzing" class="analyze-empty">
              暂未分析，点击"AI 分析"按钮生成内容摘要
            </div>
          </div>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { User, MagicStick, Link, Delete, Loading, Clock, StarFilled, ChatDotSquare, Share } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: Boolean,
  video: Object,
  coverUrl: String,
  analyzing: Boolean,
  reAnalyze: Boolean,
  envInfo: Object,
  categoryOptions: { type: Array, default: () => [] },
})

const emit = defineEmits([
  'update:modelValue', 'analyze', 'open-url', 'delete',
  'save-category', 'closed',
])

const visible = ref(props.modelValue)
const editingCategory = ref('')

function fmtNum(n) {
  if (!n) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  return String(n)
}

function fmtDuration(sec) {
  if (!sec) return ''
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val && props.video) {
    editingCategory.value = props.video.category || ''
  }
})

watch(visible, (val) => emit('update:modelValue', val))
</script>

<style scoped>
.detail-dialog :deep(.el-dialog) {
  border-radius: 16px;
  overflow: hidden;
  max-width: 92vw;
}
.detail-dialog :deep(.el-dialog__header) { padding: 0; margin: 0; }
.detail-dialog :deep(.el-dialog__headerbtn) {
  top: 12px; right: 12px; z-index: 10;
  width: 32px; height: 32px;
  background: rgba(0,0,0,0.3); border-radius: 50%;
}
.detail-dialog :deep(.el-dialog__headerbtn .el-dialog__close) { color: #fff; font-size: 16px; }
.detail-dialog :deep(.el-dialog__body) { padding: 0; }

.detail-scroll { height: 100%; overflow-y: auto; }

.detail-cover {
  width: 100%; aspect-ratio: 16/9; overflow: hidden; background: #f5f7fa;
}
.detail-cover img { width: 100%; height: 100%; object-fit: cover; }

.detail-body { padding: 20px 24px 24px; }
.detail-title { font-size: 18px; font-weight: 700; line-height: 1.4; margin-bottom: 8px; }

/* 作者信息行 */
.detail-author {
  display: flex; align-items: center; gap: 10px; margin-bottom: 10px;
}
.author-avatar {
  width: 36px; height: 36px; border-radius: 50%; object-fit: cover; flex-shrink: 0;
}
.author-avatar.placeholder {
  background: #f0f2f5; display: flex; align-items: center; justify-content: center;
  color: #909399;
}
.author-name { font-size: 15px; font-weight: 600; color: #303133; }

.detail-meta {
  display: flex; align-items: center; gap: 12px;
  font-size: 12px; color: #909399; margin-bottom: 10px;
}

/* 互动数据 */
.detail-stats {
  display: flex; gap: 16px; margin-bottom: 14px;
  font-size: 13px; color: #606266;
}
.dstat { display: flex; align-items: center; gap: 3px; }

.detail-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 14px; }
.detail-actions { display: flex; gap: 8px; margin-bottom: 14px; flex-wrap: wrap; }

.detail-category {
  display: flex; align-items: center; gap: 8px;
  font-size: 13px; margin-bottom: 16px;
}
.detail-category .label { color: #909399; }

.analyze-section { border-top: 1px solid #e4e7ed; padding-top: 16px; }
.analyze-header { display: flex; flex-direction: column; margin-bottom: 12px; }
.analyze-title { font-size: 15px; font-weight: 600; color: #1a1a2e; margin-bottom: 8px; }

.ai-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 12px; }
.ai-badge {
  font-size: 10px; padding: 2px 8px; border-radius: 10px;
  background: linear-gradient(135deg, #667eea, #764ba2); color: #fff;
  font-weight: 500;
}
.ai-badge.multimodal { background: linear-gradient(135deg, #f093fb, #f5576c); }

.analyzing-state {
  display: flex; align-items: center; gap: 8px;
  color: #fe2c55; padding: 16px 0; font-size: 14px;
}

.analyze-content { margin-top: 4px; }
.result-block { margin-bottom: 18px; }

.block-title { font-size: 13px; font-weight: 600; color: #606266; margin-bottom: 8px; }

.summary-text {
  font-size: 14px; line-height: 1.7; color: #606266;
  background: #f8f9fa; border-radius: 8px;
  padding: 12px;
  border-left: 3px solid #fe2c55;
}

.keypoint-list { list-style: none; padding: 0; }
.keypoint-list li {
  display: flex; align-items: flex-start; gap: 8px;
  padding: 6px 0; font-size: 13px; line-height: 1.6;
  color: #606266; border-bottom: 1px dashed #e4e7ed;
}
.keypoint-list li:last-child { border-bottom: none; }

.bullet {
  width: 6px; height: 6px; border-radius: 50%;
  background: #fe2c55; margin-top: 7px; flex-shrink: 0;
}

.tag-row { display: flex; flex-wrap: wrap; gap: 6px; }

.tag {
  font-size: 11px; line-height: 1;
  padding: 4px 10px; border-radius: 12px;
  background: #f4f4f5; color: #606266;
  border: 1px solid #e4e7ed;
}

.ai-tag {
  font-size: 11px; font-weight: 500;
  padding: 3px 10px; border-radius: 4px;
  background: #f0f5ff; color: #2a7bf6;
}

.transcribe-box {
  font-size: 12px; line-height: 1.8; color: #606266;
  background: #f8f9fa; border-radius: 8px;
  padding: 10px 12px; max-height: 180px; overflow-y: auto;
}

.analyze-time {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: #c0c4cc; margin-top: 8px;
}

.analyze-empty {
  text-align: center; padding: 20px 0;
  color: #c0c4cc; font-size: 13px;
}
</style>
