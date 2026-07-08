import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Button from '../Button.vue'

describe('Button.vue', () => {
  it('renders slot content', () => {
    const wrapper = mount(Button, { slots: { default: 'Click me' } })
    expect(wrapper.text()).toBe('Click me')
  })

  it('emits click event on click', async () => {
    const wrapper = mount(Button, { slots: { default: 'Go' } })
    await wrapper.find('button').trigger('click')
    expect(wrapper.emitted('click')).toHaveLength(1)
  })

  it('applies primary variant class', () => {
    const wrapper = mount(Button, { props: { variant: 'primary' } })
    expect(wrapper.find('button').classes()).toContain('btn--primary')
  })
})
