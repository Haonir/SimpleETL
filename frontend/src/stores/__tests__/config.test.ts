import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const { mockLoadConfigFile, mockSaveConfigFile } = vi.hoisted(() => ({
  mockLoadConfigFile: vi.fn(),
  mockSaveConfigFile: vi.fn(),
}))

vi.mock('@/services/configFile', () => ({
  loadConfigFile: mockLoadConfigFile,
  saveConfigFile: mockSaveConfigFile,
}))

import { useConfigStore } from '@/stores/config'

describe('config store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockLoadConfigFile.mockClear()
    mockSaveConfigFile.mockClear()
  })

  it('loadConfig populates state from API', async () => {
    mockLoadConfigFile.mockResolvedValue({
      llm: { model: 'gpt-4', base_url: 'http://x', api_key: 'k' },
      processing: { chunk_size: 5000, chunk_overlap: 500, max_workers: 2, output_format: 'spr' },
      prompts: [],
      current_prompt_name: '',
    })

    const store = useConfigStore()
    await store.loadConfig()

    expect(store.llm.model).toBe('gpt-4')
    expect(store.processing.chunk_size).toBe(5000)
    expect(store.loaded).toBe(true)
  })

  it('save sends correct update to API', async () => {
    mockLoadConfigFile.mockResolvedValue({
      llm: { model: 'a', base_url: 'b', api_key: 'c' },
      processing: { chunk_size: 1, chunk_overlap: 1, max_workers: 1, output_format: 'spr' },
      prompts: [],
      current_prompt_name: '',
    })

    const store = useConfigStore()
    await store.loadConfig()
    store.updateLLM({ model: 'updated' })
    await store.save()

    expect(mockSaveConfigFile).toHaveBeenCalledWith({
      llm: { model: 'updated', base_url: 'b', api_key: 'c' },
      processing: { chunk_size: 1, chunk_overlap: 1, max_workers: 1, output_format: 'spr' },
      prompts: [],
      current_prompt_name: '',
      cleanup: { enabled: false, max_age_hours: 24 },
    })
  })

  it('updateLLM merges partial state', () => {
    const store = useConfigStore()
    store.updateLLM({ model: 'new-model' })

    expect(store.llm.model).toBe('new-model')
    expect(store.llm.base_url).toBe('')
  })

  it('updateProcessing merges partial state', () => {
    const store = useConfigStore()
    store.updateProcessing({ max_workers: 4 })

    expect(store.processing.max_workers).toBe(4)
    expect(store.processing.chunk_size).toBe(10000)
  })
})
