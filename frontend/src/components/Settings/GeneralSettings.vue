<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { ref, computed } from 'vue'
import { useConfigStore } from '@/stores/config'
import { useUiStore } from '@/stores/ui'
import { useThemeStore } from '@/stores/theme'
import { usePromptsStore } from '@/stores/prompts'
import Button from '@/components/UI/Button.vue'
import Checkbox from '@/components/UI/Checkbox.vue'

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
const promptsStore = usePromptsStore()

const showResetDialog = ref(false)

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

async function confirmResetPrompts() {
  showResetDialog.value = true
}

async function handleResetPrompts() {
  await promptsStore.resetToDefaults()
  uiStore.showNotification('success', t('settingsGeneral.resetPromptsDone'))
  showResetDialog.value = false
}

function cancelReset() {
  showResetDialog.value = false
}
</script>

<template>
  <div class="general-settings">
    <h4 class="section-title">{{ t('settingsGeneral.notifications') }}</h4>
    <div class="notification-settings">
      <label class="notification-option">
        <Checkbox
          :modelValue="configStore.notifications.enabled"
          @update:modelValue="configStore.updateNotifications({ enabled: $event as boolean })"
        />
        <span class="notification-option__label">{{ t('settingsGeneral.notificationsEnabled') }}</span>
      </label>
      <label class="notification-option" :class="{ 'notification-option--disabled': !configStore.notifications.enabled }">
        <Checkbox
          :modelValue="configStore.notifications.enabled && configStore.notifications.sound"
          :disabled="!configStore.notifications.enabled"
          @update:modelValue="configStore.updateNotifications({ sound: $event as boolean })"
        />
        <span class="notification-option__label">{{ t('settingsGeneral.notificationsSound') }}</span>
      </label>
    </div>

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
      <Button variant="secondary" size="md" @click="confirmResetPrompts">{{ t('settingsGeneral.resetPrompts') }}</Button>
    </div>

    <!-- Reset prompts confirmation dialog -->
    <div v-if="showResetDialog" class="dialog-overlay" @click.self="cancelReset">
      <div class="dialog">
        <h3 class="dialog-title">{{ t('settingsGeneral.resetConfirmTitle') }}</h3>
        <p class="dialog-text">{{ t('settingsGeneral.resetConfirmText') }}</p>
        <p class="dialog-recommend">{{ t('settingsGeneral.resetConfirmRecommend') }}</p>
        <p class="dialog-warning">{{ t('settingsGeneral.resetConfirmWarning') }}</p>
        <div class="dialog-actions">
          <button class="dialog-btn dialog-btn--cancel" @click="cancelReset">{{ t('common.cancel') }}</button>
          <button class="dialog-btn dialog-btn--danger" @click="handleResetPrompts">{{ t('settingsGeneral.resetPrompts') }}</button>
        </div>
      </div>
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

/* Confirmation dialog */
.notification-settings {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notification-option {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.notification-option--disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.notification-option__label {
  font-size: 12px;
  color: var(--fg-label);
}

.dialog-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.dialog {
  background: var(--bg-card, #fff);
  border-radius: 12px;
  padding: 24px;
  max-width: 420px;
  width: 90%;
  box-shadow: var(--shadow-dialog);
}

.dialog-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--fg-on-card);
  margin: 0 0 16px 0;
}

.dialog-text {
  font-size: 14px;
  color: var(--fg-title);
  margin: 0 0 16px 0;
}

.dialog-recommend {
  font-size: 13px;
  color: var(--fg-label);
  margin: 0 0 16px 0;
  opacity: 0.85;
}

.dialog-warning {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-error);
  margin: 0 0 20px 0;
  padding: 10px;
  background: var(--btn-danger-bg-light);
  border-radius: 6px;
  border: 1px solid var(--border-danger);
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.dialog-btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border);
  transition: all 0.15s;
}

.dialog-btn--cancel {
  background: var(--bg-card);
  color: var(--fg-on-card);
}

.dialog-btn--cancel:hover {
  background: var(--bg-hover-subtle);
}

.dialog-btn--danger {
  background: var(--btn-danger-bg);
  color: var(--btn-danger-fg);
  border-color: var(--btn-danger-border);
}

.dialog-btn--danger:hover {
  background: var(--btn-danger-hover);
}
</style>
