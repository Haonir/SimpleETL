import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import App from '../App.vue'

describe('App.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders header with title', () => {
    const wrapper = mount(App, { global: { stubs: { teleport: true } } })
    expect(wrapper.find('.app-header__title').text()).toBe('SimpleETL')
  })

  it('sidebar navigation switches panels', async () => {
    const wrapper = mount(App, { global: { stubs: { teleport: true } } })
    const buttons = wrapper.findAll('.sidebar__item')
    expect(buttons.length).toBeGreaterThanOrEqual(2)
    await buttons[1].trigger('click')
    const uiStore = (wrapper.vm as any).uiStore
    expect(uiStore.activePanel).toBe('settings')
  })

  it('start button disabled when no files', async () => {
    const wrapper = mount(App, { global: { stubs: { teleport: true } } })
    // The start button uses Button component with text "▶ Start"
    const startButton = wrapper.findAll('button').find(b => b.text().includes('Start'))
    expect(startButton).toBeDefined()
    expect(startButton!.attributes('disabled')).toBeDefined()
  })

  it('notification bar shows notification', async () => {
    const wrapper = mount(App, { global: { stubs: { teleport: true } } })
    const uiStore = (wrapper.vm as any).uiStore
    uiStore.showNotification('success', 'Job completed!')
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.notification-bar').exists()).toBe(true)
    expect(wrapper.text()).toContain('Job completed!')
  })
})
