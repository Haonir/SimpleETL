import { defineStore } from 'pinia'
import { ref } from 'vue'
import { loadConfigFile, saveConfigFile, downloadConfigFile, importConfigFile, clearConfigFile } from '@/services/configFile'
import type { LLMConfig, ProcessingConfig, ConfigResponse, PromptEntry, Language } from '@/types/config'
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
  const prompts = ref<PromptEntry[]>([])
  const currentPromptName = ref('')
  const language = ref<Language>('en')
  const loaded = ref(false)

  async function loadConfig() {
    try {
      const config = await loadConfigFile()
      llm.value = config.llm
      processing.value = config.processing
      prompts.value = config.prompts || []
      currentPromptName.value = config.current_prompt_name || ''
      language.value = config.language || 'en'
      loaded.value = true
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load configuration'
      useUiStore().showNotification('error', message)
    }
  }

  async function save() {
    try {
      const fullConfig: ConfigResponse = {
        llm: llm.value,
        processing: processing.value,
        prompts: prompts.value,
        current_prompt_name: currentPromptName.value,
        language: language.value,
      }
      saveConfigFile(fullConfig)
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

  async function exportConfig() {
    const { usePromptsStore } = await import('./prompts')
    const promptsStore = usePromptsStore()
    const fullConfig: ConfigResponse = {
      llm: llm.value,
      processing: processing.value,
      prompts: promptsStore.prompts,
      current_prompt_name: promptsStore.currentPromptName,
      language: language.value,
    }
    downloadConfigFile(fullConfig)
  }

  async function importConfig(file: File) {
    const config = await importConfigFile(file)
    llm.value = config.llm
    processing.value = config.processing
    loaded.value = true
    if (config.language) language.value = config.language
    if (config.current_prompt_name) {
      const { usePromptsStore } = await import('./prompts')
      usePromptsStore().currentPromptName = config.current_prompt_name
    }
  }

  function clearConfig() {
    clearConfigFile()
    llm.value = { model: '', base_url: '', api_key: '' }
    processing.value = {
      chunk_size: 10000,
      chunk_overlap: 1500,
      max_workers: 1,
      output_format: 'spr',
      skip_llm: false,
    }
    loaded.value = false
    language.value = 'en'
  }

  return { llm, processing, loaded, loadConfig, save, updateLLM, updateProcessing, exportConfig, importConfig, clearConfig, prompts, currentPromptName, language }
})
