import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import Select from '../Select.vue'

const options = [
  { value: 'a', label: 'Alpha' },
  { value: 'b', label: 'Beta' },
]

describe('Select.vue', () => {
  it('renders all options', () => {
    const wrapper = mount(Select, { props: { modelValue: 'a', options } })
    expect(wrapper.findAll('option')).toHaveLength(2)
  })

  it('emits update:modelValue on change', async () => {
    const wrapper = mount(Select, { props: { modelValue: 'a', options } })
    await wrapper.find('select').setValue('b')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['b'])
  })

  it('matches selected value', () => {
    const wrapper = mount(Select, { props: { modelValue: 'b', options } })
    expect((wrapper.find('select').element as HTMLSelectElement).value).toBe('b')
  })
})
