<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'

type ConnState = 'connected' | 'disconnected' | 'checking'

const state = ref<ConnState>('checking')

const statusText = computed(() => {
  switch (state.value) {
    case 'connected':    return 'Connected'
    case 'disconnected': return 'Disconnected'
    default:             return 'Checking…'
  }
})

const statusClass = computed(() => `connection-status--${state.value}`)

let timer: ReturnType<typeof setInterval> | null = null

async function checkHealth() {
  try {
    const stored = localStorage.getItem('simpleetl_api_base_url')
    const base = stored || import.meta.env.VITE_API_BASE_URL || ''
    await axios.get(`${base}/health`, { timeout: 5000 })
    state.value = 'connected'
  } catch {
    state.value = 'disconnected'
  }
}

onMounted(() => {
  checkHealth()
  timer = setInterval(checkHealth, 15_000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
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
.connection-status--checking .connection-status__dot { background: #f59e0b; animation: pulse 1s infinite; }
.connection-status--disconnected .connection-status__dot { background: #6b7280; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
