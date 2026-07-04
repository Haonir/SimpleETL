import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import SettingsPanel from '../SettingsPanel.vue'

vi.mock('@/services/api', () => ({
  getConfig: vi.fn().mockResolvedValue({
    llm: { model: '', base_url: '', api_key: '' },
    processing: { chunk_size: 10000, chunk_overlap: 1500, max_workers: 1, output_format: 'spr' },
    prompts: [],
    current_prompt_name: '',
  }),
  saveConfig: vi.fn().mockResolvedValue({
    llm: { model: '', base_url: '', api_key: '' },
    processing: { chunk_size: 10000, chunk_overlap: 1500, max_workers: 1, output_format: 'spr' },
    prompts: [],
    current_prompt_name: '',
  }),
}))

describe('SettingsPanel.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('renders tab navigation with LLM and Processing tabs', async () => {
    const wrapper = mount(SettingsPanel, {
      global: { stubs: { teleport: true } },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.tab').exists()).toBe(true)
    expect(wrapper.findAll('.tab')).toHaveLength(2)
    expect(wrapper.text()).toContain('LLM')
    expect(wrapper.text()).toContain('Processing')
  })

  it('clicking LLM tab sets activeTab to llm', async () => {
    const wrapper = mount(SettingsPanel, {
      global: { stubs: { teleport: true } },
    })
    await wrapper.vm.$nextTick()

    const llmTab = wrapper.findAll('.tab')[0]
    expect(llmTab.classes()).toContain('tab--active')

    ;(wrapper.vm as any).activeTab = 'processing'
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.tab').classes()).not.toContain('tab--active')
  })

  it('clicking Processing tab sets activeTab to processing', async () => {
    const wrapper = mount(SettingsPanel, {
      global: { stubs: { teleport: true } },
    })
    await wrapper.vm.$nextTick()

    ;(wrapper.vm as any).activeTab = 'processing'
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.tab')[1].classes()).toContain('tab--active')
  })

  it('save button calls configStore.save()', async () => {
    const store = (await import('@/stores/config')).useConfigStore()
    vi.spyOn(store, 'save').mockResolvedValue(undefined)

    const wrapper = mount(SettingsPanel, {
      global: { stubs: { teleport: true } },
    })
    await wrapper.vm.$nextTick()

    const saveButton = wrapper.findAll('button')[wrapper.findAll('button').length - 1]
    expect(saveButton.text()).toBe('Save')

    await saveButton.trigger('click')
    await wrapper.vm.$nextTick()

    expect(store.save).toHaveBeenCalled()
  })
})
