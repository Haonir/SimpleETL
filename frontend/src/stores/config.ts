import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import i18n from '@/i18n'
import { loadConfigFile, saveConfigFile, downloadConfigFile, importConfigFile, clearConfigFile } from '@/services/configFile'
import type { LLMConfig, ProcessingConfig, ConfigResponse, PromptEntry, Language, NotificationConfig } from '@/types/config'
import { useUiStore } from './ui'

const DEFAULT_PROCESSING: ProcessingConfig = {
  chunk_size: 10000,
  chunk_overlap: 1500,
  max_workers: 1,
  output_format: 'spr',
  skip_llm: false,
  skip_chunking: false,
  ocr_enabled: false,
  ocr_languages: 'rus+eng',
}

const DEFAULT_NOTIFICATIONS: NotificationConfig = {
  enabled: true,
  sound: true,
}

export const useConfigStore = defineStore('config', () => {
  const llm = ref<LLMConfig>({ model: '', base_url: '', api_key: '' })
  const processing = ref<ProcessingConfig>({ ...DEFAULT_PROCESSING })
  const prompts = ref<PromptEntry[]>([])
  const currentPromptName = ref('')
  const language = ref<Language>('en')
  const notifications = ref<NotificationConfig>({ ...DEFAULT_NOTIFICATIONS })

  // Sync language to i18n locale
  watch(language, (lang) => {
    i18n.global.locale = lang
  }, { immediate: true })

  const loaded = ref(false)

  async function loadConfig() {
    try {
      const config = await loadConfigFile()
      llm.value = config.llm
      processing.value = { ...DEFAULT_PROCESSING, ...config.processing }
      prompts.value = config.prompts || []
      currentPromptName.value = config.current_prompt_name || ''
      language.value = config.language || 'en'
      notifications.value = { ...DEFAULT_NOTIFICATIONS, ...config.notifications }
      i18n.global.locale = language.value
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
        notifications: notifications.value,
      }
      await saveConfigFile(fullConfig)
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
    processing.value = { ...DEFAULT_PROCESSING, ...config.processing }
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
    processing.value = { ...DEFAULT_PROCESSING }
    notifications.value = { ...DEFAULT_NOTIFICATIONS }
    loaded.value = false
    language.value = 'en'
  }

  function updateNotifications(partial: Partial<NotificationConfig>) {
    notifications.value = { ...notifications.value, ...partial }
  }

  return { llm, processing, loaded, loadConfig, save, updateLLM, updateProcessing, exportConfig, importConfig, clearConfig, prompts, currentPromptName, language, notifications, updateNotifications }
})
