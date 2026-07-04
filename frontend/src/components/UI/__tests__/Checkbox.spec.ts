import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Checkbox from '../Checkbox.vue'

describe('Checkbox.vue', () => {
  it('renders label text', () => {
    const wrapper = mount(Checkbox, { props: { modelValue: false, label: 'Accept' } })
    expect(wrapper.text()).toContain('Accept')
  })

  it('emits update:modelValue on change', async () => {
    const wrapper = mount(Checkbox, { props: { modelValue: false } })
    await wrapper.find('input').setValue(true)
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([true])
  })

  it('reflects checked state', () => {
    const wrapper = mount(Checkbox, { props: { modelValue: true } })
    expect((wrapper.find('input').element as HTMLInputElement).checked).toBe(true)
  })
})
