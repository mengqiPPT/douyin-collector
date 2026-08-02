<template>
  <div class="actions-card">
    <div class="actions-title">快捷操作</div>

    <!-- 有数据时的操作区 -->
    <div class="actions-list" v-if="total > 0">
      <button class="action-btn primary" @click="$emit('collect')">
        <span class="action-icon"><el-icon><Plus /></el-icon></span>
        <span class="action-text">收藏新视频</span>
        <el-icon class="action-arrow"><ArrowRight /></el-icon>
      </button>
      <button
        v-if="pending > 0"
        class="action-btn warn"
        @click="$emit('view-pending')"
      >
        <span class="action-icon"><el-icon><Clock /></el-icon></span>
        <span class="action-text">{{ pending }} 个视频待分析</span>
        <el-icon class="action-arrow"><ArrowRight /></el-icon>
      </button>
      <button
        v-if="analyzed > 0"
        class="action-btn"
        @click="$emit('search')"
      >
        <span class="action-icon"><el-icon><Search /></el-icon></span>
        <span class="action-text">搜索已分析内容</span>
        <el-icon class="action-arrow"><ArrowRight /></el-icon>
      </button>
    </div>

    <!-- 空状态：新手指引 -->
    <div class="onboarding" v-else>
      <div class="onboard-steps">
        <div class="ob-step">
          <div class="ob-num">1</div>
          <div class="ob-content">
            <div class="ob-title">粘贴抖音分享链接</div>
            <div class="ob-desc">在抖音 App 中复制分享文本，粘贴到弹窗中</div>
          </div>
        </div>
        <div class="ob-line"></div>
        <div class="ob-step">
          <div class="ob-num">2</div>
          <div class="ob-content">
            <div class="ob-title">自动提取视频信息</div>
            <div class="ob-desc">系统自动解析标题、作者、标签和封面图</div>
          </div>
        </div>
        <div class="ob-line"></div>
        <div class="ob-step">
          <div class="ob-num">3</div>
          <div class="ob-content">
            <div class="ob-title">AI 智能分析内容</div>
            <div class="ob-desc">点击"AI 分析"按钮，自动生成摘要和核心要点</div>
          </div>
        </div>
        <div class="ob-line"></div>
        <div class="ob-step">
          <div class="ob-num"><el-icon><Search /></el-icon></div>
          <div class="ob-content">
            <div class="ob-title">全文检索随时回顾</div>
            <div class="ob-desc">支持按标题、描述、标签和 AI 摘要搜索</div>
          </div>
        </div>
      </div>
      <button class="onboard-cta" @click="$emit('collect')">
        <el-icon><Plus /></el-icon>
        <span>开始收藏第一个视频</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { Plus, ArrowRight, Clock, Search } from '@element-plus/icons-vue'

defineProps({
  total: { type: Number, default: 0 },
  pending: { type: Number, default: 0 },
  analyzed: { type: Number, default: 0 },
})

defineEmits(['collect', 'view-pending', 'search'])
</script>

<style scoped>
.actions-card {
  background: #fff; border-radius: 14px; padding: 22px 24px;
  border: 1px solid #eef0f5;
  display: flex; flex-direction: column; height: 100%;
}
.actions-title { font-size: 15px; font-weight: 600; color: #1a1a2e; margin-bottom: 14px; }

.actions-list { display: flex; flex-direction: column; gap: 8px; }

.action-btn {
  display: flex; align-items: center; gap: 12px;
  width: 100%; padding: 14px 16px;
  border: 1px solid #eef0f5; border-radius: 10px;
  background: #fafbfc;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 14px; color: #606266;
  font-family: inherit;
}
.action-btn:hover {
  background: #fff; border-color: #d0d5dd;
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.action-btn.primary:hover { border-color: #fe2c55; color: #fe2c55; }
.action-btn.warn:hover { border-color: #e6a23c; color: #e6a23c; }

.action-icon {
  width: 36px; height: 36px; border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  background: #f0f2f5; flex-shrink: 0;
}
.action-btn.primary .action-icon { background: #fff0f3; color: #fe2c55; }
.action-btn.warn .action-icon { background: #fdf6ec; color: #e6a23c; }

.action-text { flex: 1; text-align: left; }
.action-arrow { color: #c0c4cc; font-size: 14px; }

/* 新手指引 */
.onboarding { padding: 4px 0; }
.onboard-steps { display: flex; flex-direction: column; position: relative; }

.ob-step { display: flex; gap: 14px; padding: 6px 0; }

.ob-num {
  width: 32px; height: 32px; border-radius: 50%;
  background: #fff0f3; color: #fe2c55;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; flex-shrink: 0;
  border: 2px solid #ffe0e8;
}

.ob-line {
  width: 2px; height: 14px; background: #ffe0e8;
  margin-left: 15px;
}

.ob-content { flex: 1; padding-top: 2px; }
.ob-title { font-size: 13px; font-weight: 600; color: #303133; }
.ob-desc { font-size: 12px; color: #909399; margin-top: 2px; line-height: 1.5; }

.onboard-cta {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  width: 100%; margin-top: 18px; padding: 12px;
  background: linear-gradient(135deg, #fe2c55, #ff6b8b);
  color: #fff; border: none; border-radius: 10px;
  font-size: 14px; font-weight: 600; cursor: pointer;
  font-family: inherit;
  transition: all 0.2s;
}
.onboard-cta:hover { transform: translateY(-1px); box-shadow: 0 4px 15px rgba(254,44,85,0.35); }
</style>
