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

import { usePromptsStore } from '@/stores/prompts'
import { useConfigStore } from '@/stores/config'

describe('prompts store', () => {
  let configStore: ReturnType<typeof useConfigStore>

  beforeEach(() => {
    setActivePinia(createPinia())
    configStore = useConfigStore()
    vi.clearAllMocks()
  })

  it('fetchPrompts populates from configStore', async () => {
    mockLoadConfigFile.mockResolvedValue({
      llm: { model: '', base_url: '', api_key: '' },
      processing: { chunk_size: 10000, chunk_overlap: 1500, max_workers: 1, output_format: 'spr' },
      prompts: [{ name: 'p1', text: 'text1' }, { name: 'p2', text: 'text2' }],
      current_prompt_name: '',
    })

    const store = usePromptsStore()
    await store.fetchPrompts()

    expect(store.prompts).toHaveLength(2)
    expect(store.promptNames).toEqual(['p1', 'p2'])
  })

  it('addPrompt creates via configStore and appends', async () => {
    mockLoadConfigFile.mockResolvedValue({
      llm: { model: '', base_url: '', api_key: '' },
      processing: { chunk_size: 10000, chunk_overlap: 1500, max_workers: 1, output_format: 'spr' },
      prompts: [],
      current_prompt_name: '',
    })

    const store = usePromptsStore()
    await store.addPrompt('new', 'new text')

    expect(store.prompts).toHaveLength(1)
    expect(store.prompts[0].name).toBe('new')
  })

  it('removePrompt deletes from configStore and removes from state', async () => {
    mockLoadConfigFile.mockResolvedValue({
      llm: { model: '', base_url: '', api_key: '' },
      processing: { chunk_size: 10000, chunk_overlap: 1500, max_workers: 1, output_format: 'spr' },
      prompts: [{ name: 'a', text: 't1' }, { name: 'b', text: 't2' }],
      current_prompt_name: '',
    })

    const store = usePromptsStore()
    await store.fetchPrompts()
    store.setCurrentPrompt('a')
    await store.removePrompt('a')

    expect(store.prompts).toHaveLength(1)
    expect(store.currentPromptName).toBe('b')
  })

  it('setCurrentPrompt updates currentPromptName', async () => {
    mockLoadConfigFile.mockResolvedValue({
      llm: { model: '', base_url: '', api_key: '' },
      processing: { chunk_size: 10000, chunk_overlap: 1500, max_workers: 1, output_format: 'spr' },
      prompts: [],
      current_prompt_name: '',
    })

    const store = usePromptsStore()
    await configStore.loadConfig()
    await store.setCurrentPrompt('test')
    expect(store.currentPromptName).toBe('test')
    expect(mockSaveConfigFile).toHaveBeenCalledOnce()
  })
})
