<script setup lang="ts">
import { useJobStore } from '@/stores/job'
import ProgressBar from './ProgressBar.vue'

const jobStore = useJobStore()
</script>

<template>
  <div v-if="jobStore.activeJobId && (jobStore.activeStatus === 'running' || jobStore.activeStatus === 'completed')" class="global-progress">
    <div class="global-progress__header">
      <span class="global-progress__label">Progress</span>
      <span class="global-progress__value">{{ Math.round(jobStore.activeProgress) }}%</span>
    </div>
    <ProgressBar :value="jobStore.activeProgress" :height="10" />
  </div>
</template>

<style scoped>
.global-progress { margin-bottom: 1rem; }
.global-progress__header { display: flex; justify-content: space-between; margin-bottom: 4px; }
.global-progress__label { font-size: 12px; font-weight: 600; color: var(--fg-header); }
.global-progress__value { font-size: 12px; color: var(--fg-label); font-variant-numeric: tabular-nums; }
</style>
