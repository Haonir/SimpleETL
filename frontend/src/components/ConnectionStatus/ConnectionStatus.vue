<script setup lang="ts">
import { computed } from 'vue'
import { useJobStore } from '@/stores/job'

const jobStore = useJobStore()

const statusText = computed(() => {
  if (!jobStore.currentJobId) return 'Disconnected'
  if (jobStore.ws?.isConnected) return 'Connected'
  return 'Reconnecting...'
})

const statusClass = computed(() => {
  if (!jobStore.currentJobId) return 'connection-status--disconnected'
  if (jobStore.ws?.isConnected) return 'connection-status--connected'
  return 'connection-status--reconnecting'
})
</script>

<template>
  <span :class="['connection-status', statusClass]">
    <span class="connection-status__dot" />
    {{ statusText }}
  </span>
</template>

<style scoped>
.connection-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--fg-label);
}
.connection-status__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.connection-status--connected .connection-status__dot { background: #22c55e; }
.connection-status--reconnecting .connection-status__dot { background: #f59e0b; animation: pulse 1s infinite; }
.connection-status--disconnected .connection-status__dot { background: #6b7280; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
