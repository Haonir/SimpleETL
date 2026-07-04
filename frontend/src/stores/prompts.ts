import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getPrompts, createPrompt, deletePrompt } from '@/services/api'
import type { PromptEntry } from '@/types/config'

export const usePromptsStore = defineStore('prompts', () => {
  const prompts = ref<PromptEntry[]>([])
  const currentPromptName = ref('')

  const currentPrompt = computed(() =>
    prompts.value.find(p => p.name === currentPromptName.value) || null,
  )
  const promptNames = computed(() => prompts.value.map(p => p.name))

  async function fetchPrompts() {
    const response = await getPrompts()
    prompts.value = response.prompts
  }

  async function addPrompt(name: string, text: string) {
    const entry = await createPrompt({ name, text })
    prompts.value.push(entry)
  }

  async function removePrompt(name: string) {
    await deletePrompt(name)
    prompts.value = prompts.value.filter(p => p.name !== name)
    if (currentPromptName.value === name) {
      currentPromptName.value = prompts.value[0]?.name || ''
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
