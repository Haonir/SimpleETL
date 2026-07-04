<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useConfigStore } from '@/stores/config'
import { useUiStore } from '@/stores/ui'
import type { LLMConfig, ProcessingConfig } from '@/types/config'
import LLMSettings from './LLMSettings.vue'
import ProcessingSettings from './ProcessingSettings.vue'

const configStore = useConfigStore()
const uiStore = useUiStore()

type TabId = 'llm' | 'processing'
const activeTab = ref<TabId>('llm')

const llmValue = ref<LLMConfig>(configStore.llm)
const processingValue = ref<ProcessingConfig>(configStore.processing)

onMounted(() => {
  if (!configStore.loaded) {
    configStore.loadConfig()
  }
})

async function saveSettings() {
  configStore.llm = llmValue.value
  configStore.processing = processingValue.value
  await configStore.save()
  uiStore.showNotification('success', 'Settings saved')
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
        LLM
      </button>
      <button
        :class="['tab', { 'tab--active': activeTab === 'processing' }]"
        @click="activeTab = 'processing'"
      >
        Processing
      </button>
    </div>

    <!-- Tab content -->
    <div class="tab-content">
      <LLMSettings v-model="llmValue" :disabled="false" v-if="activeTab === 'llm'" />
      <ProcessingSettings v-model="processingValue" :disabled="false" v-if="activeTab === 'processing'" />
    </div>

    <!-- Save button -->
    <button class="btn btn--primary btn--md" @click="saveSettings">Save</button>
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
</style>
