<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'
import type { Language } from '@/types/config'
import { useConfigStore } from '@/stores/config'
import { useUiStore } from '@/stores/ui'
import { useThemeStore } from '@/stores/theme'
import Button from '@/components/UI/Button.vue'

const { t } = useI18n()

interface Option { value: string; label: string }
const languageOptions: Option[] = [
  { value: 'en', label: 'English' },
  { value: 'ru', label: 'Русский' },
]

const themeOptions = computed<Option[]>(() => [
  { value: 'system', label: t('settingsGeneral.themeSystem') },
  { value: 'light', label: t('settingsGeneral.themeLight') },
  { value: 'dark', label: t('settingsGeneral.themeDark') },
])

const configStore = useConfigStore()
const uiStore = useUiStore()
const themeStore = useThemeStore()

async function handleImport(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    await configStore.importConfig(file)
    uiStore.showNotification('success', 'Config imported')
  } catch {
    uiStore.showNotification('error', 'Failed to import config')
  }
  input.value = ''
}
</script>

<template>
  <div class="general-settings">
    <h4 class="section-title">{{ t('settingsGeneral.language') }}</h4>
    <label class="settings-label">{{ t('settingsGeneral.interfaceLanguage') }}</label>
    <select v-model="configStore.language" class="settings-select">
      <option v-for="opt in languageOptions" :key="opt.value" :value="opt.value">
        {{ opt.label }}
      </option>
    </select>

    <h4 class="section-title">{{ t('settingsGeneral.theme') }}</h4>
    <label class="settings-label">{{ t('settingsGeneral.colorTheme') }}</label>
    <select v-model="themeStore.mode" class="settings-select">
      <option v-for="opt in themeOptions" :key="opt.value" :value="opt.value">
        {{ opt.label }}
      </option>
    </select>

    <h4 class="section-title">{{ t('settingsGeneral.config') }}</h4>
    <div class="config-actions">
      <Button variant="secondary" size="md" @click="configStore.exportConfig()">{{ t('settingsGeneral.export') }}</Button>
      <label class="import-label">
        <span class="btn btn--secondary btn--md">{{ t('settingsGeneral.import') }}</span>
        <input type="file" accept=".json" class="hidden-input" @change="handleImport" />
      </label>
    </div>
  </div>
</template>

<style scoped>
.general-settings {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 480px;
}

.section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--fg-title);
  margin: 0;
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

.import-label .btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 34px;
  padding: 0 16px;
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 12px;
  font-weight: 500;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--btn-bg);
  color: var(--btn-fg);
  cursor: pointer;
  transition: background-color 0.15s;
}

.import-label .btn:hover {
  background: var(--btn-hover);
}

.hidden-input {
  display: none;
}

.settings-label {
  font-size: 12px;
  color: var(--fg-label);
  margin-bottom: -4px;
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

.settings-select option {
  background: var(--bg-surface);
}
</style>
