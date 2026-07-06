<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useFilesStore } from '@/stores/files'
import { useJobStore } from '@/stores/job'
import { useConfigStore } from '@/stores/config'
import { usePromptsStore } from '@/stores/prompts'
import { useUiStore } from '@/stores/ui'
import type { OutputFormat } from '@/types/config'
import Button from '@/components/UI/Button.vue'
import { Play, Square, Save, RefreshCw } from '@lucide/vue'

const filesStore = useFilesStore()
const jobStore = useJobStore()
const configStore = useConfigStore()
const promptsStore = usePromptsStore()
const uiStore = useUiStore()

const selectedPromptName = ref(promptsStore.currentPromptName || '')

// Sync local ref when prompts store loads
watch(() => promptsStore.currentPromptName, (newVal) => {
  if (newVal && !selectedPromptName.value) {
    selectedPromptName.value = newVal
  }
})
const selectedFormat = ref<OutputFormat>(configStore.processing.output_format)

// Sync local ref when config store loads
watch(() => configStore.processing.output_format, (newVal) => {
  if (newVal) {
    selectedFormat.value = newVal
  }
})

async function handleSaveDefaults() {
  configStore.processing.output_format = selectedFormat.value
  configStore.processing.skip_llm = !selectedPromptName.value
  if (selectedPromptName.value) {
    await promptsStore.setCurrentPrompt(selectedPromptName.value)
  } else {
    configStore.currentPromptName = ''
    await configStore.save()
  }
  uiStore.showNotification('success', 'Format & prompt saved')
}

function handleClearJob() {
  jobStore.clearActiveJob()
}

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

function statusBadgeText(status: string | null): string {
  switch (status) {
    case 'completed': return '✓ Completed'
    case 'partial':   return '⚠ Partial'
    case 'running':   return '▶ Running'
    case 'error':     return '✗ Error'
    default:          return jobStore.activeJobId ? `#${jobStore.activeJobId.slice(0, 8)}…` : 'Idle'
  }
}
</script>

<template>
  <div class="job-toolbar">
    <Button
      variant="primary"
      size="md"
      :disabled="!filesStore.hasFiles || filesStore.selectedIds.length === 0"
      class="toolbar-start-btn"
      @click="handleStart"
    >
      <Play :size="14" /> Start
    </Button>
    <div class="toolbar-stop-area">
      <Button
        variant="secondary"
        size="md"
        :disabled="!jobStore.isRunning || jobStore.stopRequested"
        class="toolbar-stop-btn"
        @click="handleStop"
      >
        <Square :size="14" /> Stop
      </Button>
      <span v-if="jobStore.stopRequested" class="toolbar-hint toolbar-hint--stop">
        Stop requested…
      </span>
    </div>

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
    <button class="toolbar-save-btn" title="Save format & prompt to config" @click="handleSaveDefaults">
      <Save :size="14" />
    </button>
    <span v-if="!selectedPromptName" class="toolbar-hint">⚡ LLM step will be skipped</span>

    <button v-if="jobStore.activeJobId" class="toolbar-save-btn" title="Clear current job" @click="handleClearJob">
      <RefreshCw :size="14" />
    </button>
    <span v-if="jobStore.activeJobId" :class="['status-badge', `status-badge--${jobStore.activeStatus || 'idle'}`]">
      {{ statusBadgeText(jobStore.activeStatus) }}
    </span>
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

.toolbar-stop-btn {
  min-width: 100px;
}

.toolbar-stop-area {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toolbar-hint--stop {
  color: #f5740b;
  font-size: 12px;
  white-space: nowrap;
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

.toolbar-save-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-input);
  color: var(--fg-label);
  cursor: pointer;
  flex-shrink: 0;
  transition: color 0.15s, border-color 0.15s;
}

.toolbar-save-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
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

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  margin-left: auto;
}

.status-badge--idle    { background: #f3f4f6; color: #6b7280; }
.status-badge--pending { background: #e5e7eb; color: #6b7280; }
.status-badge--running { background: #dbeafe; color: #1d4ed8; }
.status-badge--completed { background: #dcfce7; color: #166534; }
.status-badge--partial  { background: #fef3c7; color: #92400e; }
.status-badge--error   { background: #fee2e2; color: #991b1b; }

</style>
