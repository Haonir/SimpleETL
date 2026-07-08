import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Modal from '../Modal.vue'

describe('Modal.vue', () => {
  it('renders when show is true', () => {
    const wrapper = mount(Modal, {
      props: { show: true, title: 'Test' },
      global: { stubs: { teleport: true } }
    })
    expect(wrapper.text()).toContain('Test')
  })

  it('does not render when show is false', () => {
    const wrapper = mount(Modal, {
      props: { show: false },
      global: { stubs: { teleport: true } }
    })
    expect(wrapper.find('.modal-backdrop').exists()).toBe(false)
  })

  it('emits close on close button click', async () => {
    const wrapper = mount(Modal, {
      props: { show: true, title: 'X' },
      global: { stubs: { teleport: true } }
    })
    await wrapper.find('.modal-close').trigger('click')
    expect(wrapper.emitted('close')).toHaveLength(1)
  })
})
