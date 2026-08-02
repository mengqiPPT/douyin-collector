<template>
  <aside class="sidebar" :class="{ collapsed: collapsed }">
    <div class="sidebar-header">
      <div class="logo">
        <div class="logo-icon">
          <el-icon size="20"><VideoCamera /></el-icon>
        </div>
        <span class="logo-text" v-if="!collapsed">视频收藏夹</span>
      </div>
      <el-icon class="collapse-btn" @click="$emit('toggle')">
        <Fold v-if="!collapsed" />
        <Expand v-else />
      </el-icon>
    </div>

    <nav class="sidebar-nav" v-if="!collapsed">
      <div class="nav-section-title">页面</div>
      <div
        class="nav-item"
        :class="{ active: activePage === 'dashboard' }"
        @click="$emit('navigate', 'dashboard')"
      >
        <el-icon><TrendCharts /></el-icon>
        <span>数据概览</span>
      </div>
      <div
        class="nav-item"
        :class="{ active: activePage === 'library' && selectedCategory === '' }"
        @click="$emit('go-library', '')"
      >
        <el-icon><Collection /></el-icon>
        <span>视频库</span>
        <span class="nav-count" v-if="total > 0">{{ total }}</span>
      </div>

      <div class="nav-section-title">分类</div>
      <div
        class="nav-item"
        :class="{ active: selectedCategory === '' && activePage === 'library' }"
        @click="$emit('go-library', '')"
      >
        <el-icon><Files /></el-icon>
        <span>全部分类</span>
      </div>
      <div
        v-for="cat in categories"
        :key="cat.category"
        class="nav-item"
        :class="{ active: selectedCategory === cat.category }"
        @click="$emit('go-library', cat.category)"
      >
        <el-icon><Folder /></el-icon>
        <span>{{ cat.category }}</span>
        <span class="nav-count">{{ cat.count }}</span>
      </div>
    </nav>

    <div class="sidebar-action" v-if="!collapsed">
      <el-button
        type="primary"
        class="sidebar-collect-btn"
        @click="$emit('collect')"
      >
        <el-icon><Plus /></el-icon>
        <span>收藏视频</span>
      </el-button>
    </div>

    <div class="sidebar-footer" v-if="!collapsed">
      <div class="env-info" v-if="envInfo">
        <el-icon size="12"><Cpu /></el-icon>
        <span>{{ envModeText }}</span>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import {
  VideoCamera, Fold, Expand, TrendCharts, Collection, Files, Folder, Plus, Cpu,
} from '@element-plus/icons-vue'

const props = defineProps({
  collapsed: Boolean,
  activePage: String,
  selectedCategory: String,
  categories: Array,
  total: Number,
  envInfo: Object,
})

defineEmits(['toggle', 'navigate', 'go-library', 'collect'])

const envModeText = computed(() => {
  const providers = props.envInfo?.ai_providers || []
  if (providers.length >= 2) return `🤖 DeepSeek + Qwen`
  if (providers.length === 1) return `🤖 ${providers[0].split('/')[0]}`
  const map = { basic: '基础分析', basic_plus: '增强分析', full: '完整 AI' }
  return map[props.envInfo?.mode] || '未知'
})
</script>

<style scoped>
.sidebar {
  width: 220px; background: #fff;
  border-right: 1px solid #e4e7ed;
  display: flex; flex-direction: column; flex-shrink: 0;
  transition: width 0.3s; position: sticky; top: 0; height: 100vh;
}
.sidebar.collapsed { width: 64px; }

.sidebar-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px; border-bottom: 1px solid #e4e7ed;
}

.logo { display: flex; align-items: center; gap: 10px; }

.logo-icon {
  width: 32px; height: 32px; background: #fe2c55;
  border-radius: 8px; display: flex; align-items: center; justify-content: center;
  color: white; flex-shrink: 0;
}

.logo-text { font-size: 15px; font-weight: 600; color: #303133; }
.collapse-btn { font-size: 14px; color: #909399; cursor: pointer; }
.sidebar-nav { flex: 1; padding: 8px; overflow-y: auto; }

.nav-section-title {
  font-size: 11px; font-weight: 600; color: #909399;
  text-transform: uppercase; letter-spacing: 0.5px;
  padding: 12px 12px 4px;
}

.nav-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; border-radius: 8px;
  cursor: pointer; font-size: 14px; color: #606266;
  transition: all 0.15s; margin-bottom: 2px;
}
.nav-item > span:not(.nav-count) { flex: 1; }

.nav-item:hover { background: #f5f7fa; color: #303133; }
.nav-item.active { background: #fff0f3; color: #fe2c55; font-weight: 500; }
.nav-item .el-icon { font-size: 16px; flex-shrink: 0; }

.nav-count {
  margin-left: auto; font-size: 11px; color: #909399;
  background: #f2f3f5; padding: 1px 6px; border-radius: 10px;
}

.sidebar-action { padding: 0 16px 12px; border-top: none; }

.sidebar-collect-btn {
  width: 100%;
  border-radius: 8px;
  height: 40px;
  font-size: 14px;
  font-weight: 500;
}

.sidebar-footer {
  padding: 12px 16px;
  border-top: 1px solid #e4e7ed;
}

.env-info {
  display: flex; align-items: center; gap: 6px;
  font-size: 11px; color: #909399;
}
</style>
