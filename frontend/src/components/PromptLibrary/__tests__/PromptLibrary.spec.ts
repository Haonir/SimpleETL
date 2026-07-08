import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import PromptLibrary from '../PromptLibrary.vue'

vi.mock('@/services/api', () => ({
  getPrompts: vi.fn().mockResolvedValue({ prompts: [], total: 0 }),
  createPrompt: vi.fn().mockResolvedValue({ name: '', text: '' }),
  deletePrompt: vi.fn().mockResolvedValue({ deleted: '', message: 'ok' }),
}))

describe('PromptLibrary.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('renders empty state when no prompts', async () => {
    const store = (await import('@/stores/prompts')).usePromptsStore()
    store.prompts = []

    const wrapper = mount(PromptLibrary, {
      global: { stubs: { teleport: true } },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.empty-state').exists()).toBe(true)
    expect(wrapper.text()).toContain('No prompts yet')
  })

  it('renders prompt list from store', async () => {
    const store = (await import('@/stores/prompts')).usePromptsStore()
    store.prompts = [
      { name: 'test-prompt-1', text: 'Prompt text 1' },
      { name: 'test-prompt-2', text: 'Prompt text 2' },
    ]

    const wrapper = mount(PromptLibrary, {
      global: { stubs: { teleport: true } },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.prompt-card')).toHaveLength(2)
    expect(wrapper.text()).toContain('test-prompt-1')
    expect(wrapper.text()).toContain('test-prompt-2')
  })

  it('add button opens editor modal', async () => {
    const wrapper = mount(PromptLibrary, {
      global: { stubs: { teleport: true } },
    })
    await wrapper.vm.$nextTick()

    const addButton = wrapper.findAll('button').find(b => b.text() === 'Add New')
    expect(addButton).toBeDefined()

    await addButton!.trigger('click')
    await wrapper.vm.$nextTick()

    // The PromptEditor modal should be rendered (it uses a Modal component)
    expect(wrapper.find('.prompt-editor').exists()).toBe(true)
  })
})
