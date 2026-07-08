import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import SettingsPanel from '../SettingsPanel.vue'

const { mockLoadConfigFile, mockSaveConfigFile } = vi.hoisted(() => ({
  mockLoadConfigFile: vi.fn(),
  mockSaveConfigFile: vi.fn(),
}))

vi.mock('@/services/configFile', () => ({
  loadConfigFile: mockLoadConfigFile,
  saveConfigFile: mockSaveConfigFile,
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
    expect(wrapper.findAll('.tab')).toHaveLength(3)
    expect(wrapper.text()).toContain('LLM')
    expect(wrapper.text()).toContain('Processing')
    expect(wrapper.text()).toContain('Cleanup')
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

    // Find the Save button by text content (not index), since Export/Import buttons follow it
    const saveButton = wrapper.findAll('button').find((btn) => btn.text() === 'Save')
    expect(saveButton).toBeDefined()

    await saveButton!.trigger('click')
    await wrapper.vm.$nextTick()

    expect(store.save).toHaveBeenCalled()
  })

  it('only renders LLMSettings when activeTab is llm', async () => {
    const wrapper = mount(SettingsPanel, {
      global: { stubs: { teleport: true } },
    })
    await wrapper.vm.$nextTick()

    // LLMSettings contains a label "Model"
    expect(wrapper.text()).toContain('Model')

    ;(wrapper.vm as any).activeTab = 'processing'
    await wrapper.vm.$nextTick()

    // After switching to processing, Model text should no longer be visible (LLMSettings hidden)
    expect(wrapper.text()).not.toContain('Model')
  })

  it('only renders ProcessingSettings when activeTab is processing', async () => {
    const wrapper = mount(SettingsPanel, {
      global: { stubs: { teleport: true } },
    })
    await wrapper.vm.$nextTick()

    ;(wrapper.vm as any).activeTab = 'processing'
    await wrapper.vm.$nextTick()

    // ProcessingSettings contains a label "Chunk Size"
    expect(wrapper.text()).toContain('Chunk Size')

    ;(wrapper.vm as any).activeTab = 'llm'
    await wrapper.vm.$nextTick()

    // After switching to LLM, Chunk Size text should no longer be visible (ProcessingSettings hidden)
    expect(wrapper.text()).not.toContain('Chunk Size')
  })

  it('switching tabs toggles visibility of both content components', async () => {
    const wrapper = mount(SettingsPanel, {
      global: { stubs: { teleport: true } },
    })
    await wrapper.vm.$nextTick()

    // Initial state: LLM tab active → only LLMSettings visible (contains "Model")
    expect(wrapper.text()).toContain('Model')

    ;(wrapper.vm as any).activeTab = 'processing'
    await wrapper.vm.$nextTick()

    // Processing tab active → settings form hidden (LLMSettings gone, no "Model" text)
    expect(wrapper.text()).not.toContain('Model')

    ;(wrapper.vm as any).activeTab = 'llm'
    await wrapper.vm.$nextTick()

    // Back to LLM → settings visible again ("Model" text appears)
    expect(wrapper.text()).toContain('Model')
  })
})
