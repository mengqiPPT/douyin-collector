<template>
  <el-dialog v-model="visible" title="收藏视频" width="500px" @closed="$emit('closed')">
    <el-input
      v-model="text"
      type="textarea"
      :rows="4"
      placeholder="粘贴抖音分享文本..."
      clearable
    />
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="loading" @click="$emit('submit', text)" :disabled="!text.trim()">
        收藏
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  loading: Boolean,
})

const emit = defineEmits(['update:modelValue', 'submit', 'closed'])

const visible = ref(props.modelValue)
const text = ref('')

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val) text.value = ''
})

watch(visible, (val) => emit('update:modelValue', val))
</script>
