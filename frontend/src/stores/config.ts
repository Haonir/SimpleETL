import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getConfig, saveConfig } from '@/services/api'
import type { LLMConfig, ProcessingConfig, ConfigUpdateRequest } from '@/types/config'
import { useUiStore } from './ui'

export const useConfigStore = defineStore('config', () => {
  const llm = ref<LLMConfig>({ model: '', base_url: '', api_key: '' })
  const processing = ref<ProcessingConfig>({
    chunk_size: 10000,
    chunk_overlap: 1500,
    max_workers: 1,
    output_format: 'spr',
    skip_llm: false,
  })
  const loaded = ref(false)

  async function loadConfig() {
    try {
      const config = await getConfig()
      llm.value = config.llm
      processing.value = config.processing
      loaded.value = true
      // Restore current_prompt_name into the prompts store
      if (config.current_prompt_name) {
        const { usePromptsStore } = await import('./prompts')
        usePromptsStore().currentPromptName = config.current_prompt_name
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load configuration'
      useUiStore().showNotification('error', message)
    }
  }

  async function save() {
    try {
      const update: ConfigUpdateRequest = { llm: llm.value, processing: processing.value }
      const config = await saveConfig(update)
      llm.value = config.llm
      processing.value = config.processing
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to save configuration'
      useUiStore().showNotification('error', message)
    }
  }

  function updateLLM(partial: Partial<LLMConfig>) {
    llm.value = { ...llm.value, ...partial }
  }

  function updateProcessing(partial: Partial<ProcessingConfig>) {
    processing.value = { ...processing.value, ...partial }
  }

  return { llm, processing, loaded, loadConfig, save, updateLLM, updateProcessing }
})
