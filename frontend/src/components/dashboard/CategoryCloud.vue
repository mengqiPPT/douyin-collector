<template>
  <div class="cloud-card">
    <div class="cloud-title flex-between">
      <span>分类分布</span>
      <span class="cloud-count">{{ categories.length }} 个分类</span>
    </div>

    <div class="cloud-body" v-if="categories.length > 0">
      <div
        v-for="cat in sizedCategories"
        :key="cat.category"
        class="cloud-bubble"
        :class="cat.colorClass"
        :style="{ fontSize: cat.fontSize + 'px' }"
        @click="$emit('select', cat.category)"
      >
        <span class="bubble-name">{{ cat.category }}</span>
        <span class="bubble-count">{{ cat.count }}</span>
      </div>
    </div>

    <div class="cloud-empty" v-else>收藏视频后将自动归类</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const COLORS = ['red', 'blue', 'green', 'amber', 'purple', 'teal', 'indigo', 'pink']

const props = defineProps({
  categories: { type: Array, default: () => [] },
  total: { type: Number, default: 0 },
})

defineEmits(['select'])

const sizedCategories = computed(() => {
  if (!props.categories.length) return []
  const max = Math.max(...props.categories.map(c => c.count), 1)
  return props.categories.map((cat, i) => ({
    ...cat,
    ratio: cat.count / max,
    fontSize: 13 + Math.round((cat.count / max) * 6),
    colorClass: COLORS[i % COLORS.length],
  }))
})
</script>

<style scoped>
.cloud-card {
  background: #fff; border-radius: 14px; padding: 22px 24px;
  border: 1px solid #eef0f5;
  display: flex; flex-direction: column; height: 100%;
}
.cloud-title { margin-bottom: 16px; }
.cloud-title.flex-between { display: flex; justify-content: space-between; align-items: center; }
.cloud-count { font-size: 12px; color: #909399; font-weight: 400; }

.cloud-body { display: flex; flex-wrap: wrap; gap: 10px; align-items: flex-start; flex: 1; align-content: flex-start; }

.cloud-bubble {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 14px;
  border-radius: 20px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s ease;
  user-select: none;
}
.cloud-bubble:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.cloud-bubble.red { background: #fff0f3; color: #fe2c55; }
.cloud-bubble.blue { background: #ecf5ff; color: #409eff; }
.cloud-bubble.green { background: #f0f9eb; color: #67c23a; }
.cloud-bubble.amber { background: #fdf6ec; color: #e6a23c; }
.cloud-bubble.purple { background: #f5f0ff; color: #a855f7; }
.cloud-bubble.teal { background: #e6fffa; color: #14b8a6; }
.cloud-bubble.indigo { background: #eef2ff; color: #6366f1; }
.cloud-bubble.pink { background: #fdf2f8; color: #ec4899; }

.bubble-count {
  font-size: 0.8em; opacity: 0.7;
  background: rgba(0,0,0,0.06); padding: 1px 6px;
  border-radius: 8px;
}

.cloud-empty {
  text-align: center; padding: 28px 0;
  color: #c0c4cc; font-size: 13px;
}
</style>
