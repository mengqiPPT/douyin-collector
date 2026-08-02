<template>
  <div class="stat-card" :class="`accent-${color}`">
    <div class="stat-icon-wrap">
      <el-icon size="20"><component :is="icon" /></el-icon>
    </div>
    <div class="stat-body">
      <div class="stat-num">
        <span ref="numRef">{{ displayNum }}</span>
      </div>
      <div class="stat-label">{{ label }}</div>
    </div>
    <div class="stat-accent" v-if="trend !== undefined">
      <el-icon size="14"><component :is="trend >= 0 ? 'CaretTop' : 'CaretBottom'" /></el-icon>
      <span>{{ Math.abs(trend) }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { CaretTop, CaretBottom } from '@element-plus/icons-vue'

const props = defineProps({
  icon: { type: [String, Object], required: true },
  color: { type: String, default: 'blue' },
  num: { type: Number, default: 0 },
  label: { type: String, default: '' },
  trend: { type: Number, default: undefined },
})

const displayNum = ref(0)
const numRef = ref(null)

function animate(from, to) {
  const duration = 600
  const start = performance.now()
  const tick = (now) => {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3) // ease-out cubic
    displayNum.value = Math.round(from + (to - from) * eased)
    if (progress < 1) requestAnimationFrame(tick)
  }
  requestAnimationFrame(tick)
}

watch(() => props.num, (val, old) => {
  animate(old || 0, val)
})

onMounted(() => {
  animate(0, props.num)
})
</script>

<style scoped>
.stat-card {
  position: relative;
  background: #fff;
  border-radius: 14px;
  padding: 22px 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid #eef0f5;
  transition: all 0.25s ease;
  overflow: hidden;
}
.stat-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; bottom: 0;
  width: 4px;
  border-radius: 4px 0 0 4px;
  transition: all 0.3s;
}
.stat-card:hover {
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
  transform: translateY(-2px);
}
.stat-card.accent-red::before { background: linear-gradient(180deg, #fe2c55, #ff6b8b); }
.stat-card.accent-blue::before { background: linear-gradient(180deg, #409eff, #79bbff); }
.stat-card.accent-green::before { background: linear-gradient(180deg, #67c23a, #95d475); }
.stat-card.accent-amber::before { background: linear-gradient(180deg, #e6a23c, #f0c78a); }
.stat-card.accent-purple::before { background: linear-gradient(180deg, #a855f7, #c084fc); }

.stat-icon-wrap {
  width: 48px; height: 48px; border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
  transition: transform 0.25s;
}
.stat-card:hover .stat-icon-wrap { transform: scale(1.06); }
.accent-red .stat-icon-wrap { background: #fff0f3; color: #fe2c55; }
.accent-blue .stat-icon-wrap { background: #ecf5ff; color: #409eff; }
.accent-green .stat-icon-wrap { background: #f0f9eb; color: #67c23a; }
.accent-amber .stat-icon-wrap { background: #fdf6ec; color: #e6a23c; }
.accent-purple .stat-icon-wrap { background: #f5f0ff; color: #a855f7; }

.stat-body { flex: 1; min-width: 0; }
.stat-num {
  font-size: 30px; font-weight: 800; color: #1a1a2e;
  line-height: 1.1; font-variant-numeric: tabular-nums;
}
.stat-label { font-size: 13px; color: #909399; margin-top: 2px; }

.stat-accent {
  display: flex; align-items: center; gap: 2px;
  font-size: 12px; font-weight: 600;
  padding: 4px 8px; border-radius: 6px;
  background: #f0f9eb; color: #67c23a;
  white-space: nowrap;
}
</style>
