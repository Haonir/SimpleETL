<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Server, Cog, SlidersHorizontal } from '@lucide/vue'
import { useConfigStore } from '@/stores/config'
import { useUiStore } from '@/stores/ui'
import type { LLMConfig, ProcessingConfig } from '@/types/config'
import LLMSettings from './LLMSettings.vue'
import GeneralSettings from './GeneralSettings.vue'
import ProcessingSettings from './ProcessingSettings.vue'

const configStore = useConfigStore()
const uiStore = useUiStore()

type TabId = 'llm' | 'processing' | 'general'
const activeTab = ref<TabId>('processing')

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
    <h2 class="settings-panel__title">Settings</h2>
    <!-- Tab navigation -->
    <div class="tabs">
      <button
        :class="['tab', { 'tab--active': activeTab === 'processing' }]"
        @click="activeTab = 'processing'"
      >
        <Cog :size="14" /> Processing
      </button>
      <button
        :class="['tab', { 'tab--active': activeTab === 'llm' }]"
        @click="activeTab = 'llm'"
      >
        <Server :size="14" /> Providers
      </button>
      <button
        :class="['tab', { 'tab--active': activeTab === 'general' }]"
        @click="activeTab = 'general'"
      >
        <SlidersHorizontal :size="14" /> General
      </button>
    </div>

    <!-- Tab content -->
    <div class="tab-content">
      <LLMSettings v-model="llmValue" :disabled="false" v-if="activeTab === 'llm'" />
      <ProcessingSettings v-model="processingValue" :disabled="false" v-if="activeTab === 'processing'" />
      <GeneralSettings v-if="activeTab === 'general'" />
    </div>

    <!-- Save button -->
    <button class="btn btn--primary btn--md settings-save-btn" @click="saveSettings">Save</button>
  </div>
</template>

<style scoped>
.settings-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.settings-panel__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--fg-title);
  margin: 0 0 1rem;
}

.tabs {
  display: flex;
  border-bottom: 1px solid var(--border);
}

.tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
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

.settings-save-btn {
  align-self: flex-end;
  min-width: 120px;
}
</style>
