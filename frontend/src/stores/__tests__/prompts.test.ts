import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const { mockGetPrompts, mockCreatePrompt, mockDeletePrompt } = vi.hoisted(() => ({
  mockGetPrompts: vi.fn(),
  mockCreatePrompt: vi.fn(),
  mockDeletePrompt: vi.fn(),
}))

vi.mock('@/services/api', () => ({
  getPrompts: mockGetPrompts,
  createPrompt: mockCreatePrompt,
  deletePrompt: mockDeletePrompt,
}))

import { usePromptsStore } from '@/stores/prompts'

describe('prompts store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchPrompts populates from API', async () => {
    mockGetPrompts.mockResolvedValue({
      prompts: [{ name: 'p1', text: 'text1' }, { name: 'p2', text: 'text2' }],
      total: 2,
    })

    const store = usePromptsStore()
    await store.fetchPrompts()

    expect(store.prompts).toHaveLength(2)
    expect(store.promptNames).toEqual(['p1', 'p2'])
  })

  it('addPrompt creates via API and appends', async () => {
    mockCreatePrompt.mockResolvedValue({ name: 'new', text: 'new text' })

    const store = usePromptsStore()
    await store.addPrompt('new', 'new text')

    expect(store.prompts).toHaveLength(1)
    expect(store.prompts[0].name).toBe('new')
  })

  it('removePrompt deletes via API and removes from state', async () => {
    mockGetPrompts.mockResolvedValue({
      prompts: [{ name: 'a', text: 't1' }, { name: 'b', text: 't2' }],
      total: 2,
    })
    mockDeletePrompt.mockResolvedValue({ deleted: 'a', message: 'ok' })

    const store = usePromptsStore()
    await store.fetchPrompts()
    store.setCurrentPrompt('a')
    await store.removePrompt('a')

    expect(store.prompts).toHaveLength(1)
    expect(store.currentPromptName).toBe('b')
  })

  it('setCurrentPrompt updates currentPromptName', () => {
    const store = usePromptsStore()
    store.setCurrentPrompt('test')
    expect(store.currentPromptName).toBe('test')
  })
})
