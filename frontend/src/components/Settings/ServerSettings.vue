<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, onMounted } from 'vue'

const { t } = useI18n()

interface Props {
  disabled: boolean
}

const props = withDefaults(defineProps<Props>(), { disabled: false })

const STORAGE_KEY = 'simpleetl_api_base_url'

const serverUrl = ref('')
const saved = ref(false)

onMounted(() => {
  serverUrl.value = localStorage.getItem(STORAGE_KEY) || ''
})

function save() {
  const url = serverUrl.value.trim().replace(/\/+$/, '')
  if (url) {
    localStorage.setItem(STORAGE_KEY, url)
  } else {
    localStorage.removeItem(STORAGE_KEY)
  }
  saved.value = true
  setTimeout(() => { saved.value = false }, 2000)
}

defineExpose({ save })
</script>

<template>
  <div class="settings-form">
    <label class="settings-label">{{ t('settingsServer.backendUrl') }}</label>
    <input
      v-model="serverUrl"
      type="text"
      :placeholder="$t('settingsServer.backendUrlPlaceholder')"
      :disabled="props.disabled"
      class="settings-input"
    />
    <p class="settings-hint" v-html="$t('settingsServer.backendHint')">
    </p>
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

.settings-hint {
  font-size: 11px;
  color: var(--fg-label);
  line-height: 1.5;
}

.settings-hint code {
  background: var(--bg-input);
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
}

.settings-saved {
  font-size: 11px;
  color: var(--color-success);
}
</style>
