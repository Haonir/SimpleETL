import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ProgressBar from '../ProgressBar.vue'

describe('ProgressBar.vue', () => {
  it('renders with default value', () => {
    const wrapper = mount(ProgressBar)
    expect(wrapper.find('.progress-track').exists()).toBe(true)
  })

  it('applies width from value prop', () => {
    const wrapper = mount(ProgressBar, { props: { value: 75 } })
    const fill = wrapper.find('.progress-fill')
    expect(fill.attributes('style')).toContain('width: 75%')
  })

  it('renders indeterminate animation', () => {
    const wrapper = mount(ProgressBar, { props: { indeterminate: true } })
    expect(wrapper.find('.progress-fill--indeterminate').exists()).toBe(true)
  })
})
