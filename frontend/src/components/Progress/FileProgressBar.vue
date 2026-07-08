<script setup lang="ts">
import { computed } from 'vue'
import { useJobStore } from '@/stores/job'
import ProgressBar from './ProgressBar.vue'

const props = defineProps<{ fileId: string; fileName: string }>()
const jobStore = useJobStore()

const fileProgress = computed(() => {
  return jobStore.progress[props.fileId] ?? 0
})

const visible = computed(() => {
  const s = jobStore.activeStatus
  return (s === 'running' || s === 'completed' || s === 'stopped' || s === 'partial') && jobStore.activeJobFileIds.length > 0
})
</script>

<template>
  <div v-if="visible" class="file-progress">
    <ProgressBar
      :value="fileProgress"
      :height="4"
      :color="fileProgress >= 100 ? 'var(--success, #22c55e)' : 'var(--accent)'"
    />
  </div>
</template>

<style scoped>
.file-progress { margin-top: 4px; }
</style>
