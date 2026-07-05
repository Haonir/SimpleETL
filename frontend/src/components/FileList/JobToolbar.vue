<script setup lang="ts">
import { ref } from 'vue'
import { useFilesStore } from '@/stores/files'
import { useJobStore } from '@/stores/job'
import { useConfigStore } from '@/stores/config'
import { usePromptsStore } from '@/stores/prompts'
import { useUiStore } from '@/stores/ui'
import type { OutputFormat } from '@/types/config'
import Button from '@/components/UI/Button.vue'

const filesStore = useFilesStore()
const jobStore = useJobStore()
const configStore = useConfigStore()
const promptsStore = usePromptsStore()
const uiStore = useUiStore()

const selectedPromptName = ref(promptsStore.currentPromptName || '')
const selectedFormat = ref<OutputFormat>(configStore.processing.output_format)

const formatOptions: { value: OutputFormat; label: string }[] = [
  { value: 'markdown', label: 'Raw Markdown' },
  { value: 'frontmatter', label: 'Frontmatter' },
  { value: 'html', label: 'HTML' },
  { value: 'spr', label: 'SPR' },
]

async function handleStart() {
  if (!filesStore.hasFiles || filesStore.selectedIds.length === 0) return

  // Apply toolbar selections to config
  configStore.processing.output_format = selectedFormat.value
  const noPrompt = !selectedPromptName.value
  configStore.processing.skip_llm = noPrompt

  if (selectedPromptName.value) {
    promptsStore.setCurrentPrompt(selectedPromptName.value)
  }

  const promptEntry = promptsStore.prompts.find(p => p.name === selectedPromptName.value)

  try {
    await jobStore.createAndStartJob(
      filesStore.selectedIds,
      {
        llm: configStore.llm,
        processing: configStore.processing,
        prompt_text: promptEntry?.text ?? '',
        skip_llm: noPrompt,
      },
    )
  } catch (err) {
    uiStore.showNotification('error', `Failed to start job: ${err instanceof Error ? err.message : String(err)}`)
  }
}

function handleStop() {
  jobStore.stopJob()
}
</script>

<template>
  <div class="job-toolbar">
    <Button
      v-if="!jobStore.isRunning"
      variant="primary"
      size="md"
      :disabled="!filesStore.hasFiles || filesStore.selectedIds.length === 0"
      class="toolbar-start-btn"
      @click="handleStart"
    >
      ▶ Start
    </Button>
    <Button
      v-else
      variant="secondary"
      size="md"
      class="toolbar-start-btn"
      @click="handleStop"
    >
      ⏹ Stop
    </Button>

    <div class="toolbar-separator" />

    <label class="toolbar-label">Format</label>
    <select v-model="selectedFormat" class="toolbar-select toolbar-select--sm">
      <option v-for="opt in formatOptions" :key="opt.value" :value="opt.value">
        {{ opt.label }}
      </option>
    </select>

    <label class="toolbar-label">Prompt</label>
    <select v-model="selectedPromptName" class="toolbar-select">
      <option value="">— None / No LLM —</option>
      <option v-for="p in promptsStore.prompts" :key="p.name" :value="p.name">
        {{ p.name }}
      </option>
    </select>
    <span v-if="!selectedPromptName" class="toolbar-hint">⚡ LLM step will be skipped</span>
  </div>
</template>

<style scoped>
.job-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card);
}

.toolbar-separator {
  width: 1px;
  height: 20px;
  background: var(--border);
  flex-shrink: 0;
}

.toolbar-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--fg-label);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  flex-shrink: 0;
}

.toolbar-start-btn {
  min-width: 180px;
}

.toolbar-select {
  height: 30px;
  padding: 0 8px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 12px;
  color: var(--fg-title);
  outline: none;
  cursor: pointer;
}

.toolbar-select:focus {
  border-color: var(--accent);
}

.toolbar-select--sm {
  max-width: 140px;
}

.toolbar-hint {
  font-size: 12px;
  color: #f5740b;
  white-space: nowrap;
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>
