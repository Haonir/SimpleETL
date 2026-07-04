<script setup lang="ts">
import { computed } from 'vue'
import { useJobStore } from '@/stores/job'
import ProgressBar from './ProgressBar.vue'

const props = defineProps<{ fileIdx: number; fileName: string }>()
const jobStore = useJobStore()

const fileProgress = computed(() => {
  if (!jobStore.isRunning.value) return 0
  return jobStore.progress[props.fileIdx] ?? 0
})

const isActive = computed(() => jobStore.isRunning.value && fileProgress.value > 0 && fileProgress.value < 100)
</script>

<template>
  <div v-if="jobStore.isRunning.value" class="file-progress">
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
