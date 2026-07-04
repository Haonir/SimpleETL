<script setup lang="ts">
import { ref } from 'vue'
import type { LLMConfig } from '@/types/config'

interface Props {
  modelValue: LLMConfig
  disabled: boolean
}

const props = withDefaults(defineProps<Props>(), {})

const showApiKey = ref(false)

function toggleApiKey() {
  showApiKey.value = !showApiKey.value
}

defineEmits<{
  'update:modelValue': [value: LLMConfig]
}>()
</script>

<template>
  <div class="settings-form">
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
</style>
