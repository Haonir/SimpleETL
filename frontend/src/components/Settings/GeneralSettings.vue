<script setup lang="ts">
import { useConfigStore } from '@/stores/config'
import { useUiStore } from '@/stores/ui'
import Button from '@/components/UI/Button.vue'

const configStore = useConfigStore()
const uiStore = useUiStore()

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
    <h4 class="section-title">Config</h4>
    <div class="config-actions">
      <Button variant="secondary" size="md" @click="configStore.exportConfig()">Export Config</Button>
      <label class="import-label">
        <span class="btn btn--secondary btn--md">Import Config</span>
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
</style>
