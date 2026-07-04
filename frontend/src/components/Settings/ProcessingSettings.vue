<script setup lang="ts">
import type { OutputFormat, ProcessingConfig } from '@/types/config'

interface Option {
  value: string
  label: string
}

interface Props {
  modelValue: ProcessingConfig
  disabled: boolean
}

const props = withDefaults(defineProps<Props>(), {})

const outputOptions: Option[] = [
  { value: 'spr', label: 'SPR' },
  { value: 'frontmatter', label: 'Frontmatter' },
  { value: 'markdown', label: 'Raw Markdown' },
  { value: 'html', label: 'HTML' },
]

defineEmits<{
  'update:modelValue': [value: ProcessingConfig]
}>()
</script>

<template>
  <div class="settings-form">
    <label class="settings-label">Chunk Size</label>
    <input
      v-model.number="modelValue.chunk_size"
      type="number"
      :min="1"
      :disabled="props.disabled"
      class="settings-input"
    />

    <label class="settings-label">Chunk Overlap</label>
    <input
      v-model.number="modelValue.chunk_overlap"
      type="number"
      :min="0"
      :disabled="props.disabled"
      class="settings-input"
    />

    <label class="settings-label">Max Workers</label>
    <input
      v-model.number="modelValue.max_workers"
      type="number"
      :min="1"
      :disabled="props.disabled"
      class="settings-input"
    />

    <label class="settings-label">Output Format</label>
    <select
      v-model="modelValue.output_format"
      :disabled="props.disabled"
      class="settings-select"
    >
      <option v-for="opt in outputOptions" :key="opt.value" :value="opt.value">
        {{ opt.label }}
      </option>
    </select>
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

.settings-select {
  appearance: none;
  height: 34px;
  padding: 0 28px 0 10px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 12px;
  color: var(--fg-title);
  cursor: pointer;
  outline: none;
  transition: border-color 0.15s;
}

.settings-select:focus {
  border-color: var(--accent);
}

.settings-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.settings-select option {
  background: var(--bg-surface);
}
</style>
