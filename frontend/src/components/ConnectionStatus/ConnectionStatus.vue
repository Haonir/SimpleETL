<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ compact?: boolean }>()
const { t } = useI18n()

type ConnState = 'connected' | 'disconnected' | 'checking'

const state = ref<ConnState>('checking')

const statusText = computed(() => {
  switch (state.value) {
    case 'connected':    return t('connection.connected')
    case 'disconnected': return t('connection.disconnected')
    default:             return t('connection.checking')
  }
})

const statusClass = computed(() => `connection-status--${state.value}`)

let timer: ReturnType<typeof setInterval> | null = null

async function checkHealth() {
  try {
    const stored = localStorage.getItem('simpleetl_api_base_url')
    const base = stored || import.meta.env.VITE_API_BASE_URL || ''
    const key = localStorage.getItem('simpleetl_api_server_key') || ''
    const url = `${base}/health`
    const headers: Record<string, string> = {}
    if (key) headers['X-API-Key'] = key
    const res = await axios.get(url, { timeout: 5000, headers })
    // Verify it's actually our backend (not Vite SPA returning index.html)
    if (res.data?.status === 'ok') {
      state.value = 'connected'
    } else {
      state.value = 'disconnected'
    }
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
    <span v-if="!compact" class="connection-status__text">{{ statusText }}</span>
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
.connection-status--connected .connection-status__dot { background: var(--color-success); }
.connection-status--checking .connection-status__dot { background: var(--color-warning); animation: pulse 1s infinite; }
.connection-status--disconnected .connection-status__dot { background: var(--fg-muted); }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
