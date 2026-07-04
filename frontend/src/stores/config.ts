import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getConfig, saveConfig } from '@/services/api'
import type { LLMConfig, ProcessingConfig, ConfigUpdateRequest } from '@/types/config'

export const useConfigStore = defineStore('config', () => {
  const llm = ref<LLMConfig>({ model: '', base_url: '', api_key: '' })
  const processing = ref<ProcessingConfig>({
    chunk_size: 10000,
    chunk_overlap: 1500,
    max_workers: 1,
    output_format: 'spr',
  })
  const loaded = ref(false)

  async function loadConfig() {
    const config = await getConfig()
    llm.value = config.llm
    processing.value = config.processing
    loaded.value = true
  }

  async function save() {
    const update: ConfigUpdateRequest = { llm: llm.value, processing: processing.value }
    const config = await saveConfig(update)
    llm.value = config.llm
    processing.value = config.processing
  }

  function updateLLM(partial: Partial<LLMConfig>) {
    llm.value = { ...llm.value, ...partial }
  }

  function updateProcessing(partial: Partial<ProcessingConfig>) {
    processing.value = { ...processing.value, ...partial }
  }

  return { llm, processing, loaded, loadConfig, save, updateLLM, updateProcessing }
})
