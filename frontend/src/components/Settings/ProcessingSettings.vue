<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ProcessingConfig } from '@/types/config'
import { getCapabilities } from '@/services/api'

const { t } = useI18n()

interface CapabilitiesResponse {
  ocr_available: boolean
  supported_input_formats: string[]
}

const ocrAvailable = ref(false)
onMounted(async () => {
  try {
    const caps = await getCapabilities() as CapabilitiesResponse
    ocrAvailable.value = caps.ocr_available ?? false
  } catch {
    // Backend may not expose the endpoint — treat OCR as unavailable
    ocrAvailable.value = false
  }
})

interface Option {
  value: string
  labelKey: string
}

interface Props {
  modelValue: ProcessingConfig
  disabled: boolean
}

const props = withDefaults(defineProps<Props>(), {})

const outputOptions: Option[] = [
  { value: 'markdown', labelKey: 'formats.rawMarkdown' },
  { value: 'frontmatter', labelKey: 'formats.frontmatter' },
  { value: 'html', labelKey: 'formats.html' },
  { value: 'spr', labelKey: 'formats.spr' },
]

defineEmits<{
  'update:modelValue': [value: ProcessingConfig]
}>()
</script>

<template>
  <div class="settings-form">
    <label class="settings-label">{{ t('settingsProcessing.chunkSize') }}</label>
    <input
      v-model.number="modelValue.chunk_size"
      type="number"
      :min="1"
      :disabled="props.disabled || modelValue.skip_chunking"
      class="settings-input"
    />

    <label class="settings-label">{{ t('settingsProcessing.chunkOverlap') }}</label>
    <input
      v-model.number="modelValue.chunk_overlap"
      type="number"
      :min="0"
      :disabled="props.disabled || modelValue.skip_chunking"
      class="settings-input"
    />

    <!-- Skip Chunking -->
    <div class="settings-skip-chunking-row">
      <input
        type="checkbox"
        v-model="modelValue.skip_chunking"
        :disabled="props.disabled"
        class="settings-checkbox"
      />
      <label class="settings-skip-chunking-label">{{ t('settingsProcessing.skipChunking') }}</label>
    </div>

    <label class="settings-label">{{ t('settingsProcessing.maxWorkers') }}</label>
    <input
      v-model.number="modelValue.max_workers"
      type="number"
      :min="1"
      :disabled="props.disabled"
      class="settings-input"
    />

    <label class="settings-label">{{ t('settingsProcessing.outputFormat') }}</label>
    <select
      v-model="modelValue.output_format"
      :disabled="props.disabled"
      class="settings-select"
    >
      <option v-for="opt in outputOptions" :key="opt.value" :value="opt.value">
        {{ t(opt.labelKey) }}
      </option>
    </select>

    <!-- OCR Settings -->
    <div class="settings-divider"></div>
    <label class="settings-label">{{ t('settingsProcessing.ocrEnabled') }}</label>
    <div class="settings-ocr-row">
      <input
        type="checkbox"
        v-model="modelValue.ocr_enabled"
        :disabled="props.disabled || !ocrAvailable"
        class="settings-checkbox"
      />
      <span class="settings-ocr-hint">{{ t('settingsProcessing.ocrHint') }}</span>
    </div>
    <input
      v-model="modelValue.ocr_languages"
      type="text"
      :placeholder="t('settingsProcessing.ocrLanguages')"
      :disabled="props.disabled || !ocrAvailable || !modelValue.ocr_enabled"
      class="settings-input settings-ocr-languages"
    />
  </div>
</template>

<style scoped>
.settings-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 480px;
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

.settings-divider {
  height: 1px;
  background: var(--border);
  margin: 4px 0;
}

.settings-ocr-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.settings-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--accent);
}

.settings-ocr-hint {
  font-size: 12px;
  color: var(--fg-label);
  opacity: 0.75;
}

.settings-ocr-languages {
  width: 100%;
}

.settings-skip-chunking-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.settings-skip-chunking-label {
  font-size: 12px;
  color: var(--fg-label);
  cursor: pointer;
}

</style>
