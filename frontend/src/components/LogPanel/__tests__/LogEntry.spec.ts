import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import LogEntry from '../LogEntry.vue'

describe('LogEntry.vue', () => {
  const makeEntry = (level: 'error' | 'info' | 'warning' | 'llm') => ({
    timestamp: '2024-01-01T12:00:00.000Z',
    level,
    message: 'Test log message',
  })

  it('renders timestamp, level badge, and message', () => {
    const entry = makeEntry('info')
    const wrapper = mount(LogEntry, { props: { entry } })

    expect(wrapper.find('.log-entry').exists()).toBe(true)
    expect(wrapper.text()).toContain('Test log message')
  })

  it('level badge has correct color class', () => {
    const infoEntry = makeEntry('info')
    const warningEntry = makeEntry('warning')
    const errorEntry = makeEntry('error')

    const wrapperInfo = mount(LogEntry, { props: { entry: infoEntry } })
    expect(wrapperInfo.find('.log-entry--info').exists()).toBe(true)

    const wrapperWarning = mount(LogEntry, { props: { entry: warningEntry } })
    expect(wrapperWarning.find('.log-entry--warning').exists()).toBe(true)

    const wrapperError = mount(LogEntry, { props: { entry: errorEntry } })
    expect(wrapperError.find('.log-entry--error').exists()).toBe(true)
  })
})
