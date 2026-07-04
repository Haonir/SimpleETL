<script setup lang="ts">
import { ref, onMounted } from 'vue'
import type { LLMConfig } from '@/types/config'

interface Props {
  modelValue: LLMConfig
  disabled: boolean
}

const props = withDefaults(defineProps<Props>(), {})

const showApiKey = ref(false)
const showServerKey = ref(false)

const STORAGE_KEY = 'simpleetl_api_base_url'
const STORAGE_KEY_SECRET = 'simpleetl_api_server_key'
const serverUrl = ref('')
const serverApiKey = ref('')

onMounted(() => {
  serverUrl.value = localStorage.getItem(STORAGE_KEY) || ''
  serverApiKey.value = localStorage.getItem(STORAGE_KEY_SECRET) || ''
})

function toggleApiKey() {
  showApiKey.value = !showApiKey.value
}

function toggleServerKey() {
  showServerKey.value = !showServerKey.value
}

function saveServer() {
  const url = serverUrl.value.trim().replace(/\/+$/, '')
  if (url) {
    localStorage.setItem(STORAGE_KEY, url)
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
  const key = serverApiKey.value.trim()
  if (key) {
    localStorage.setItem(STORAGE_KEY_SECRET, key)
  } else {
    localStorage.removeItem(STORAGE_KEY_SECRET)
  }
}

defineEmits<{
  'update:modelValue': [value: LLMConfig]
}>()
</script>

<template>
  <div class="settings-form">
    <h4 class="section-title">LLM</h4>

    <label class="settings-label">Model</label>
    <input
      v-model="modelValue.model"
      type="text"
      :placeholder="'e.g. llama2'"
      :disabled="props.disabled"
      class="settings-input"
    />

    <label class="settings-label">Base URL</label>
    <input
      v-model="modelValue.base_url"
      type="text"
      :placeholder="'e.g. http://localhost:11434/v1'"
      :disabled="props.disabled"
      class="settings-input"
    />

    <label class="settings-label">API Key</label>
    <div class="input-row">
      <input
        :type="showApiKey ? 'text' : 'password'"
        v-model="modelValue.api_key"
        placeholder="••••••••"
        :disabled="props.disabled"
        class="settings-input"
      />
      <button
        type="button"
        :disabled="props.disabled"
        class="btn--icon"
        @click="toggleApiKey"
      >
        {{ showApiKey ? '👁' : '🙈' }}
      </button>
    </div>

    <!-- ── Backend Server ────────────────────────────────────────────── -->
    <div class="section-divider" />
    <h4 class="section-title">Backend Server</h4>

    <label class="settings-label">Base URL</label>
    <input
      v-model="serverUrl"
      type="text"
      placeholder="http://localhost:8000"
      :disabled="props.disabled"
      class="settings-input"
      @change="saveServer"
    />

    <label class="settings-label">API Key</label>
    <div class="input-row">
      <input
        :type="showServerKey ? 'text' : 'password'"
        v-model="serverApiKey"
        placeholder="••••••••"
        :disabled="props.disabled"
        class="settings-input"
        @change="saveServer"
      />
      <button
        type="button"
        :disabled="props.disabled"
        class="btn--icon"
        @click="toggleServerKey"
      >
        {{ showServerKey ? '👁' : '🙈' }}
      </button>
    </div>
    <p class="settings-hint">
      Leave empty to use the Vite dev proxy (default for local development).
    </p>
  </div>
</template>

<style scoped>
.settings-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.settings-label {
  font-size: 12px;
  color: var(--fg-label);
  margin-bottom: -4px;
}

.settings-input {
  height: 34px;
  padding: 0 10px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 12px;
  color: var(--fg-title);
  outline: none;
  transition: border-color 0.15s;
}

.settings-input:focus {
  border-color: var(--accent);
}

.settings-input:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.input-row .settings-input {
  flex: 2;
}

.btn--icon {
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 0 8px;
  cursor: pointer;
  font-size: 14px;
  color: var(--fg-label);
}

.btn--icon:hover:not(:disabled) {
  background: var(--btn-hover);
}

.btn--icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.section-divider {
  height: 1px;
  background: var(--border);
  margin: 4px 0;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--fg-title);
  margin: 0;
}

.settings-hint {
  font-size: 11px;
  color: var(--fg-label);
  line-height: 1.5;
  margin: -4px 0 0;
}
</style>
