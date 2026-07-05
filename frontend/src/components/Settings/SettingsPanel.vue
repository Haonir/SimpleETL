<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useConfigStore } from '@/stores/config'
import { useUiStore } from '@/stores/ui'
import type { LLMConfig, ProcessingConfig, CleanupConfig } from '@/types/config'
import LLMSettings from './LLMSettings.vue'
import ProcessingSettings from './ProcessingSettings.vue'
import CleanupSettings from './CleanupSettings.vue'

const configStore = useConfigStore()
const uiStore = useUiStore()

type TabId = 'llm' | 'processing' | 'cleanup'
const activeTab = ref<TabId>('llm')

const llmValue = ref<LLMConfig>(configStore.llm)
const processingValue = ref<ProcessingConfig>(configStore.processing)
const cleanupValue = ref<CleanupConfig>(configStore.cleanup)

onMounted(() => {
  if (!configStore.loaded) {
    configStore.loadConfig()
  }
})

async function saveSettings() {
  configStore.llm = llmValue.value
  configStore.processing = processingValue.value
  configStore.cleanup = cleanupValue.value
  await configStore.save()
  uiStore.showNotification('success', 'Settings saved')
}

async function runCleanup() {
  try {
    const res = await fetch(`/api/v1/jobs/cleanup?max_age_hours=${cleanupValue.value.max_age_hours}`, { method: 'POST' })
    if (res.ok) {
      const data = await res.json()
      uiStore.showNotification('success', `Cleaned up ${data.removed} old jobs`)
    } else {
      uiStore.showNotification('error', 'Cleanup failed')
    }
  } catch {
    uiStore.showNotification('error', 'Cleanup request failed')
  }
}

async function handleImport(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    await configStore.importConfig(file)
    llmValue.value = configStore.llm
    processingValue.value = configStore.processing
    uiStore.showNotification('success', 'Config imported')
  } catch (err) {
    uiStore.showNotification('error', 'Failed to import config')
  }
  input.value = ''
}
</script>

<template>
  <div class="settings-panel">
    <!-- Tab navigation -->
    <div class="tabs">
      <button
        :class="['tab', { 'tab--active': activeTab === 'llm' }]"
        @click="activeTab = 'llm'"
      >
        Providers
      </button>
      <button
        :class="['tab', { 'tab--active': activeTab === 'processing' }]"
        @click="activeTab = 'processing'"
      >
        Processing
      </button>
      <button
        :class="['tab', { 'tab--active': activeTab === 'cleanup' }]"
        @click="activeTab = 'cleanup'"
      >
        Cleanup
      </button>
    </div>

    <!-- Tab content -->
    <div class="tab-content">
      <LLMSettings v-model="llmValue" :disabled="false" v-if="activeTab === 'llm'" />
      <ProcessingSettings v-model="processingValue" :disabled="false" v-if="activeTab === 'processing'" />
      <CleanupSettings v-model="cleanupValue" @run-cleanup="runCleanup" v-if="activeTab === 'cleanup'" />
    </div>

    <!-- Save button -->
    <button class="btn btn--primary btn--md" @click="saveSettings">Save</button>

    <!-- Export / Import config -->
    <div class="config-actions">
      <button class="btn btn--secondary btn--md" @click="configStore.exportConfig()">Export Config</button>
      <label class="btn btn--secondary btn--md import-label">
        Import Config
        <input type="file" accept=".json" class="hidden-input" @change="handleImport" />
      </label>
    </div>
  </div>
</template>

<style scoped>
.settings-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.tabs {
  display: flex;
  border-bottom: 1px solid var(--border);
}

.tab {
  padding: 8px 20px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 13px;
  color: var(--fg-label);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}

.tab:hover {
  color: var(--fg-title);
}

.tab--active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.btn {
  height: 34px;
  padding: 0 16px;
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 12px;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.15s, opacity 0.15s;
}

.btn--primary {
  background: var(--accent);
  color: white;
  border: 1px solid var(--accent);
}

.btn--primary:hover:not(:disabled) {
  background: var(--accent-hover);
}

.btn--primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.config-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.import-label {
  display: inline-flex;
  cursor: pointer;
}

.hidden-input {
  display: none;
}
</style>
