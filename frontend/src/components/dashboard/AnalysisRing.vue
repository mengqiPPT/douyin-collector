<template>
  <div class="ring-card">
    <div class="ring-title">分析完成率</div>
    <div class="ring-body">
      <svg class="ring-svg" viewBox="0 0 140 140">
        <!-- 背景环 -->
        <circle cx="70" cy="70" r="58"
          fill="none" stroke="#f0f2f5" stroke-width="12" />
        <!-- 进度环 -->
        <circle cx="70" cy="70" r="58"
          fill="none" :stroke="gradientIdRef ? `url(#ringGrad)` : '#fe2c55'"
          stroke-width="12"
          stroke-linecap="round"
          :stroke-dasharray="circumference"
          :stroke-dashoffset="dashOffset"
          class="ring-progress"
          transform="rotate(-90 70 70)" />
        <defs>
          <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#fe2c55" />
            <stop offset="100%" stop-color="#ff6b8b" />
          </linearGradient>
        </defs>
        <!-- 中心文字 -->
        <text x="70" y="62" text-anchor="middle" class="ring-pct">{{ percent }}%</text>
        <text x="70" y="84" text-anchor="middle" class="ring-sub">
          {{ analyzed }} / {{ total }}
        </text>
      </svg>

      <div class="ring-stats">
        <div class="ring-stat done">
          <span class="rs-dot"></span>
          <span class="rs-label">已分析</span>
          <span class="rs-num">{{ analyzed }}</span>
        </div>
        <div class="ring-stat pending">
          <span class="rs-dot"></span>
          <span class="rs-label">待分析</span>
          <span class="rs-num">{{ pending }}</span>
        </div>
        <div class="ring-stat" v-if="analyzing > 0">
          <span class="rs-dot analyzing"></span>
          <span class="rs-label">分析中</span>
          <span class="rs-num">{{ analyzing }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  total: { type: Number, default: 0 },
  analyzed: { type: Number, default: 0 },
  pending: { type: Number, default: 0 },
  analyzing: { type: Number, default: 0 },
})

const circumference = 2 * Math.PI * 58 // ≈ 364.4
const percent = computed(() => {
  if (props.total === 0) return 0
  return Math.round((props.analyzed / props.total) * 100)
})
const dashOffset = computed(() => {
  return circumference * (1 - percent.value / 100)
})
const gradientIdRef = 'ringGrad'
</script>

<style scoped>
.ring-card {
  background: #fff; border-radius: 14px; padding: 22px 24px;
  border: 1px solid #eef0f5;
  display: flex; flex-direction: column; height: 100%;
}
.ring-title { font-size: 15px; font-weight: 600; color: #1a1a2e; margin-bottom: 16px; }

.ring-body { display: flex; align-items: center; gap: 28px; flex: 1; }
.ring-svg { width: 130px; height: 130px; flex-shrink: 0; }

.ring-progress { transition: stroke-dashoffset 0.8s cubic-bezier(0.4, 0, 0.2, 1); }

.ring-pct { font-size: 28px; font-weight: 800; fill: #1a1a2e; }
.ring-sub { font-size: 11px; fill: #909399; }

.ring-stats { display: flex; flex-direction: column; gap: 12px; flex: 1; }
.ring-stat { display: flex; align-items: center; gap: 8px; }

.rs-dot {
  width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
}
.ring-stat.done .rs-dot { background: #67c23a; }
.ring-stat.pending .rs-dot { background: #e6a23c; }
.rs-dot.analyzing { background: #409eff; animation: pulse 1.5s ease-in-out infinite; }

.rs-label { font-size: 13px; color: #606266; }
.rs-num { margin-left: auto; font-size: 14px; font-weight: 700; color: #1a1a2e; }

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>
