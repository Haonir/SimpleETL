<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usePromptsStore } from '@/stores/prompts'
import { useUiStore } from '@/stores/ui'
import type { PromptEntry } from '@/types/config'
import PromptEditor from './PromptEditor.vue'

const promptsStore = usePromptsStore()
const uiStore = useUiStore()

const showEditor = ref(false)
const editingPrompt = ref<PromptEntry | null>(null)

function openCreateMode() {
  editingPrompt.value = null
  showEditor.value = true
}

async function handleSave(payload: { name: string; text: string }) {
  if (editingPrompt) {
    // Edit mode — update the existing prompt
    const idx = promptsStore.prompts.findIndex((p) => p.name === editingPrompt!.name)
    if (idx !== -1) {
      promptsStore.prompts[idx] = payload as PromptEntry
    }
  } else {
    // Create mode
    await promptsStore.addPrompt(payload.name, payload.text)
  }
  showEditor.value = false
  uiStore.showNotification('success', 'Prompt saved.')
}

function handleCancel() {
  showEditor.value = false
}

async function handleDelete(name: string) {
  const confirmed = window.confirm(`Delete prompt "${name}"?`)
  if (!confirmed) return
  await promptsStore.removePrompt(name)
  uiStore.showNotification('success', 'Prompt deleted.')
}

function isCurrent(p: PromptEntry): boolean {
  return p.name === promptsStore.currentPromptName
}
</script>

<template>
  <div class="prompt-library">
    <div class="library-header">
      <h3>Prompt Library</h3>
      <Button variant="primary" size="sm" @click="openCreateMode">Add New</Button>
    </div>

    <div v-if="promptsStore.prompts.length === 0" class="empty-state">
      No prompts yet. Create your first prompt.
    </div>

    <div v-else class="prompt-list">
      <div
        v-for="p in promptsStore.prompts"
        :key="p.name"
        class="prompt-card"
        :class="{ 'prompt-card--active': isCurrent(p) }"
      >
        <span class="prompt-name">{{ p.name }}</span>
        <div class="prompt-actions">
          <Button variant="secondary" size="sm" @click="$emit('select', p)">Select</Button>
          <Button variant="secondary" size="sm" @click="handleDelete(p.name)">Delete</Button>
        </div>
      </div>
    </div>

    <PromptEditor
      :show="showEditor"
      :prompt="editingPrompt"
      @save="handleSave"
      @cancel="handleCancel"
    />
  </div>
</template>

<style scoped>
.prompt-library {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.library-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.library-header h3 {
  margin: 0;
  font-size: 14px;
  color: var(--fg-title);
}

.empty-state {
  text-align: center;
  padding: 24px;
  color: var(--fg-label);
  font-size: 13px;
}

.prompt-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.prompt-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card);
}

.prompt-card--active {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--accent) 0.08, transparent);
}

.prompt-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--fg-title);
  flex-shrink: 0;
}

.prompt-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
</style>
