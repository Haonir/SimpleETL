<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { useJobStore } from '@/stores/job'
import { useUiStore } from '@/stores/ui'
import LogEntry from './LogEntry.vue'

const job = useJobStore()
const ui = useUiStore()

const containerRef = ref<HTMLElement | null>(null)

const filters = [
  { value: 'all', label: 'All' },
  { value: 'info', label: 'Info' },
  { value: 'warning', label: 'Warning' },
  { value: 'error', label: 'Error' },
]

const filteredLogs = computed(() => {
  const filter = ui.logFilter
  if (filter === 'all') return job.activeLogs
  return job.activeLogs.filter((l) => l.level === filter)
})

watch(
  () => job.activeLogs.length,
  async () => {
    await nextTick()
    containerRef.value?.scrollTo({ top: 99999, behavior: 'smooth' })
  },
  { immediate: true }
)
</script>

<template>
  <div class="log-panel">
    <!-- Filter bar -->
    <div class="log-panel__filters">
      <button
        v-for="f in filters"
        :key="f.value"
        :class="['filter-btn', { 'filter-btn--active': ui.logFilter === f.value }]"
        @click="ui.setLogFilter(f.value)"
      >
        {{ f.label }}
      </button>
    </div>

    <!-- Logs container -->
    <div ref="containerRef" class="log-panel__content">
      <template v-if="filteredLogs.length === 0">
        <p class="log-panel__empty">No logs yet. Start a job to see output.</p>
      </template>
      <LogEntry v-for="(entry, i) in filteredLogs" :key="i" :entry="entry" />
    </div>
  </div>
</template>

<style scoped>
.log-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.log-panel__filters {
  display: flex;
  gap: 4px;
  padding: 8px 12px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-card);
}

.filter-btn {
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: var(--font-size-sm);
  padding: 4px 12px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: transparent;
  color: var(--fg-label);
  cursor: pointer;
  transition: all var(--transition-fast);
}

.filter-btn:hover {
  background: var(--btn-hover);
}

.filter-btn--active {
  background: var(--accent);
  border-color: var(--accent);
  color: white;
}

.log-panel__content {
  flex: 1;
  overflow-y: auto;
  padding: 8px 12px;
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  line-height: 1.6;
}

.log-panel__empty {
  color: #9ca3af;
  text-align: center;
  padding: 2rem 0;
}
</style>
