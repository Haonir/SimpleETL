import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Input from '../Input.vue'

describe('Input.vue', () => {
  it('renders with modelValue', () => {
    const wrapper = mount(Input, { props: { modelValue: 'hello' } })
    expect((wrapper.find('input').element as HTMLInputElement).value).toBe('hello')
  })

  it('emits update:modelValue on input', async () => {
    const wrapper = mount(Input, { props: { modelValue: '' } })
    await wrapper.find('input').setValue('test')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['test'])
  })

  it('shows error message when error prop is set', () => {
    const wrapper = mount(Input, { props: { modelValue: '', error: 'Required' } })
    expect(wrapper.text()).toContain('Required')
  })
})
