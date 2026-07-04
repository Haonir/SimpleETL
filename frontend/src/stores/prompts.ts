import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getPrompts, createPrompt, deletePrompt } from '@/services/api'
import type { PromptEntry } from '@/types/config'
import { useUiStore } from './ui'

export const usePromptsStore = defineStore('prompts', () => {
  const prompts = ref<PromptEntry[]>([])
  const currentPromptName = ref('')

  const currentPrompt = computed(() =>
    prompts.value.find(p => p.name === currentPromptName.value) || null,
  )
  const promptNames = computed(() => prompts.value.map(p => p.name))

  async function fetchPrompts() {
    try {
      const response = await getPrompts()
      prompts.value = response.prompts
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load prompt library'
      useUiStore().showNotification('error', message)
    }
  }

  async function addPrompt(name: string, text: string) {
    try {
      const entry = await createPrompt({ name, text })
      prompts.value.push(entry)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save prompt'
      useUiStore().showNotification('error', message)
    }
  }

  async function removePrompt(name: string) {
    try {
      await deletePrompt(name)
      prompts.value = prompts.value.filter(p => p.name !== name)
      if (currentPromptName.value === name) {
        currentPromptName.value = prompts.value[0]?.name || ''
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete prompt'
      useUiStore().showNotification('error', message)
    }
  }

  function setCurrentPrompt(name: string) {
    currentPromptName.value = name
  }

  return {
    prompts, currentPromptName,
    currentPrompt, promptNames,
    fetchPrompts, addPrompt, removePrompt, setCurrentPrompt,
  }
})
