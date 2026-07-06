<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import type { LLMConfig, ProcessingConfig } from '@/types/config'
import { Server, Cog, SlidersHorizontal, Save } from '@lucide/vue'
import { useConfigStore } from '@/stores/config'
import { useUiStore } from '@/stores/ui'

const { t } = useI18n()
import LLMSettings from './LLMSettings.vue'
import GeneralSettings from './GeneralSettings.vue'
import ProcessingSettings from './ProcessingSettings.vue'

const configStore = useConfigStore()
const uiStore = useUiStore()

type TabId = 'llm' | 'processing' | 'general'
const activeTab = ref<TabId>('processing')

const llmValue = ref<LLMConfig>(configStore.llm)
const processingValue = ref<ProcessingConfig>(configStore.processing)

// Sync local refs from store after async config load completes
watch(() => configStore.loaded, (isLoaded) => {
  if (isLoaded) {
    llmValue.value = { ...configStore.llm }
    processingValue.value = { ...configStore.processing }
  }
})

onMounted(() => {
  if (!configStore.loaded) {
    configStore.loadConfig()
  }
})

async function saveSettings() {
  configStore.llm = llmValue.value
  configStore.processing = processingValue.value
  await configStore.save()
  uiStore.showNotification('success', t('settings.saved'))
}

</script>

<template>
  <div class="settings-panel">
    <div class="settings-header">
      <h2 class="settings-panel__title">{{ t('settings.title') }}</h2>
      <button class="settings-save-btn" :title="$t('settings.saveTooltip')" @click="saveSettings">
        <Save :size="14" /> Save
      </button>
    </div>
    <!-- Tab navigation -->
    <div class="tabs">
      <div class="tabs-row">
        <button
          :class="['tab', { 'tab--active': activeTab === 'processing' }]"
          @click="activeTab = 'processing'"
        >
          <Cog :size="14" /> {{ t('settings.tabProcessing') }}
        </button>
        <button
          :class="['tab', { 'tab--active': activeTab === 'llm' }]"
          @click="activeTab = 'llm'"
        >
          <Server :size="14" /> {{ t('settings.tabProviders') }}
        </button>
        <button
          :class="['tab', { 'tab--active': activeTab === 'general' }]"
          @click="activeTab = 'general'"
        >
          <SlidersHorizontal :size="14" /> {{ t('settings.tabGeneral') }}
        </button>
      </div>
    </div>

    <!-- Tab content -->
    <div class="tab-content">
      <LLMSettings v-model="llmValue" :disabled="false" v-if="activeTab === 'llm'" />
      <ProcessingSettings v-model="processingValue" :disabled="false" v-if="activeTab === 'processing'" />
      <GeneralSettings v-if="activeTab === 'general'" />
    </div>


  </div>
</template>

<style scoped>
.settings-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  max-width: 480px;
}

.settings-panel__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--fg-title);
  margin: 0;
}

.settings-save-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  background: none;
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 12px;
  font-weight: 500;
  color: var(--fg-label);
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
}

.settings-save-btn:hover {
  color: var(--accent);
  border-color: var(--accent);
}


.tab-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tabs {
  display: flex;
  gap: 2px;
  padding-bottom: 2px;
  border-bottom: 1px solid var(--border);
  align-items: flex-start;
}

.tabs-row {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
}

.tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 8px 16px;
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



</style>
