import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import LogPanel from '../LogPanel.vue'

describe('LogPanel.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    // Mock scrollTo for jsdom — elements don't have a native scrollTo method in jsdom
    Element.prototype.scrollTo = vi.fn()
  })

  it('renders empty state when no logs', async () => {
    const store = (await import('@/stores/job')).useJobStore()
    store.logs = []

    const wrapper = mount(LogPanel, {
      global: { stubs: { teleport: true } },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.log-panel__empty').exists()).toBe(true)
    expect(wrapper.text()).toContain('No logs yet')
  })

  it('renders log entries from store', async () => {
    const store = (await import('@/stores/job')).useJobStore()
    store.logs = [
      { timestamp: '2024-01-01T00:00:00.000Z', level: 'info' as const, message: 'Processing started' },
      { timestamp: '2024-01-01T00:00:01.000Z', level: 'error' as const, message: 'Chunk failed' },
    ]

    const wrapper = mount(LogPanel, {
      global: { stubs: { teleport: true } },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.log-entry')).toHaveLength(2)
    expect(wrapper.text()).toContain('Processing started')
    expect(wrapper.text()).toContain('Chunk failed')
  })

  it('filteredLogs computed filters by level when filter is set', async () => {
    const store = (await import('@/stores/job')).useJobStore()
    store.logs = [
      { timestamp: '2024-01-01T00:00:00.000Z', level: 'info' as const, message: 'Info msg' },
      { timestamp: '2024-01-01T00:00:01.000Z', level: 'warning' as const, message: 'Warning msg' },
      { timestamp: '2024-01-01T00:00:02.000Z', level: 'error' as const, message: 'Error msg' },
    ]

    const uiStore = (await import('@/stores/ui')).useUiStore()
    uiStore.setLogFilter('error')

    const wrapper = mount(LogPanel, {
      global: { stubs: { teleport: true } },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.findAll('.log-entry')).toHaveLength(1)
    expect(wrapper.text()).toContain('Error msg')
  })
})
