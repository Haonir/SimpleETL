<script setup lang="ts">
import type { LogEntry } from '@/types/ws'

interface Props {
  entry: LogEntry
}

const props = defineProps<Props>()

function formatTime(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return iso
  }
}

const colorMap: Record<string, string> = {
  info: 'var(--color-info)',
  warning: 'var(--color-warning)',
  error: 'var(--color-error)',
}
</script>

<template>
  <div class="log-entry" :class="`log-entry--${entry.level}`">
    <span class="log-entry__timestamp">{{ formatTime(entry.timestamp) }}</span>
    <span
      class="log-entry__badge"
      :style="{ background: colorMap[entry.level] }"
    >
      {{ entry.level }}
    </span>
    <span class="log-entry__message">{{ entry.message }}</span>
  </div>
</template>

<style scoped>
.log-entry {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  padding: 2px 0;
}

.log-entry__timestamp {
  color: #9ca3af;
  white-space: nowrap;
  min-width: 80px;
}

.log-entry__badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 9999px;
  font-size: var(--font-size-sm);
  font-weight: 600;
  color: white;
  white-space: nowrap;
}

.log-entry__message {
  flex: 1;
  word-break: break-word;
}

/* Level colors */
.log-entry--info .log-entry__badge { background: var(--color-info); }
.log-entry--warning .log-entry__badge { background: var(--color-warning); }
.log-entry--error .log-entry__badge { background: var(--color-error); }
</style>
