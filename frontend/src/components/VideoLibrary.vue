<template>
  <div class="library-body" v-loading="loading">
    <div v-if="!loading && videos.length === 0" class="empty-state">
      <el-icon size="48" color="#c0c4cc"><VideoCamera /></el-icon>
      <p>{{ searchQuery ? '没有找到匹配的视频' : '还没有收藏视频' }}</p>
      <el-button v-if="!searchQuery" type="primary" round @click="$emit('collect')">
        <el-icon><Plus /></el-icon>
        添加第一个
      </el-button>
    </div>

    <div class="video-grid" v-else>
      <VideoCard
        v-for="video in videos"
        :key="video.id"
        :video="video"
        :cover-url="coverUrlFn(video.cover_url)"
        @select="$emit('select-video', $event)"
        @img-error="handleImgError"
      />
    </div>

    <div class="pagination-bar" v-if="total > pageSize">
      <el-pagination
        :model-value="currentPage"
        :page-size="pageSize"
        :total="total"
        layout="prev, pager, next"
        @update:model-value="$emit('page-change', $event)"
      />
    </div>
  </div>
</template>

<script setup>
import { VideoCamera, Plus } from '@element-plus/icons-vue'
import VideoCard from './VideoCard.vue'

defineProps({
  videos: Array,
  total: Number,
  currentPage: Number,
  pageSize: Number,
  loading: Boolean,
  searchQuery: String,
  coverUrlFn: Function,
})

defineEmits(['select-video', 'collect', 'page-change'])

function handleImgError(e) {
  e.target.style.display = 'none'
}
</script>

<style scoped>
.library-body { flex: 1; padding: 0 32px 32px; overflow-y: auto; }

.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
  margin: 0;
  align-items: stretch;  /* 确保所有卡片等高对齐 */
}

.empty-state {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; gap: 12px; padding: 80px 0;
  color: #909399;
}
.empty-state p { font-size: 14px; }

.pagination-bar { margin-top: 24px; display: flex; justify-content: center; }
</style>
