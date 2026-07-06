<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usePromptsStore } from '@/stores/prompts'
import { useConfigStore } from '@/stores/config'
import { useUiStore } from '@/stores/ui'
import type { PromptEntry } from '@/types/config'
import { ChevronRight } from '@lucide/vue'
import PromptEditor from './PromptEditor.vue'
import Button from '@/components/UI/Button.vue'

const promptsStore = usePromptsStore()
const uiStore = useUiStore()
const configStore = useConfigStore()

const showEditor = ref(false)
const editingPrompt = ref<PromptEntry | null>(null)
const expandedName = ref<string | null>(null)

function toggleExpand(name: string) {
  expandedName.value = expandedName.value === name ? null : name
}

function openCreateMode() {
  editingPrompt.value = null
  showEditor.value = true
}

async function handleSave(payload: { name: string; text: string }) {
  if (editingPrompt.value) {
    // Edit mode — update the existing prompt
    const idx = promptsStore.prompts.findIndex((p) => p.name === editingPrompt.value!.name)
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

async function handleSelectNone() {
  promptsStore.setCurrentPrompt('')
  configStore.processing.skip_llm = true
  await configStore.save()
  uiStore.showNotification('info', 'No prompt selected — LLM step will be skipped.')
}

function isCurrent(p: PromptEntry): boolean {
  return p.name === promptsStore.currentPromptName
}
</script>

<template>
  <div class="prompt-library">
    <div class="library-header">
      <h2 class="prompt-library__title">Prompt Library</h2>
      <Button variant="primary" size="sm" @click="openCreateMode">Add New</Button>
    </div>

    <div class="prompt-card prompt-card--none" :class="{ 'prompt-card--active': !promptsStore.currentPromptName }">
      <div class="prompt-card__header">
        <span class="prompt-name">— None / No LLM —</span>
        <div class="prompt-card__actions-row">
          <Button variant="secondary" size="sm" @click="handleSelectNone">Select</Button>
        </div>
      </div>
    </div>

    <div v-if="promptsStore.prompts.length === 0" class="empty-state">
      No prompts yet. Create your first prompt.
    </div>

    <div v-else class="prompt-list">
      <div
        v-for="p in promptsStore.prompts"
        :key="p.name"
        class="prompt-card"
        :class="{ 'prompt-card--active': isCurrent(p), 'prompt-card--expanded': expandedName === p.name }"
      >
        <div class="prompt-card__header" @click="toggleExpand(p.name)">
          <span class="prompt-name">{{ p.name }}</span>
          <div class="prompt-card__actions-row">
            <Button variant="secondary" size="sm" @click.stop="$emit('select', p)">Select</Button>
            <Button variant="secondary" size="sm" @click.stop="handleDelete(p.name)">Delete</Button>
            <ChevronRight :size="14" class="prompt-expand-arrow" :class="{ 'prompt-expand-arrow--open': expandedName === p.name }" />
          </div>
        </div>
        <div class="prompt-card__body">
          <div class="prompt-card__text">{{ p.text }}</div>
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

.prompt-library__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--fg-title);
  margin: 0 0 1rem;
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
  flex-direction: column;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card);
  overflow: hidden;
  transition: border-color 0.15s;
}

.prompt-card--active {
  border-color: var(--accent);
  box-shadow: 0 0 0 1px var(--accent);
  background: var(--bg-card);
}

.prompt-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 8px 8px;
}

.prompt-card__actions-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.prompt-expand-arrow {
  font-size: 11px;
  color: var(--fg-label);
  cursor: pointer;
  transition: transform 0.2s ease;
  transform: rotate(0deg);
  line-height: 1;
}

.prompt-expand-arrow--open {
  transform: rotate(90deg);
}

.prompt-card__body {
  max-height: 0;
  overflow: hidden;
  transition: max-height 0.25s ease;
}

.prompt-card--expanded .prompt-card__body {
  max-height: 600px;
}

.prompt-card__text {
  padding: 6px 14px 10px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--fg-label);
  white-space: pre-wrap;
  word-break: break-word;
}

.prompt-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--fg-title);
  flex-shrink: 1;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}

.prompt-card--none {
  border-style: dashed;
  opacity: 0.7;
}

.prompt-card--none:hover {
  opacity: 1;
}
</style>
