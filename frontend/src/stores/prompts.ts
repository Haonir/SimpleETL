import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { PromptEntry } from '@/types/config'
import { useConfigStore } from './config'
import { useUiStore } from './ui'

export const usePromptsStore = defineStore('prompts', () => {
  const prompts = ref<PromptEntry[]>([])
  const currentPromptName = ref('')

  const currentPrompt = computed(() =>
    prompts.value.find(p => p.name === currentPromptName.value) || null,
  )
  const promptNames = computed(() => prompts.value.map(p => p.name))

  const configStore = useConfigStore()

  async function fetchPrompts() {
    try {
      if (!configStore.loaded) {
        await configStore.loadConfig()
      }
      prompts.value = configStore.prompts
      currentPromptName.value = configStore.currentPromptName
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load prompt library'
      useUiStore().showNotification('error', message)
    }
  }

  async function addPrompt(name: string, text: string) {
    try {
      if (prompts.value.some(p => p.name === name)) {
        const ui = useUiStore()
        ui.showNotification('error', `Prompt "${name}" already exists`)
        return
      }
      prompts.value.push({ name, text })
      await configStore.save()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save prompt'
      useUiStore().showNotification('error', message)
    }
  }

  async function removePrompt(name: string) {
    try {
      prompts.value = prompts.value.filter(p => p.name !== name)
      if (currentPromptName.value === name) {
        currentPromptName.value = prompts.value[0]?.name || ''
      }
      await configStore.save()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to delete prompt'
      useUiStore().showNotification('error', message)
    }
  }

  async function setCurrentPrompt(name: string) {
    currentPromptName.value = name
    await configStore.save()
  }

  return {
    prompts, currentPromptName,
    currentPrompt, promptNames,
    fetchPrompts, addPrompt, removePrompt, setCurrentPrompt,
  }
})
