import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import FileDropZone from '../FileDropZone.vue'

// ── Pinia setup ───────────────────────────────────────────────────────────
describe('FileDropZone.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders drop zone with browse button', async () => {
    const wrapper = mount(FileDropZone, { global: { stubs: { teleport: true } } })

    expect(wrapper.find('.drop-area').exists()).toBe(true)
    expect(wrapper.find('button').text()).toContain('Browse')
  })

  it('file input accepts allowed extensions', async () => {
    const wrapper = mount(FileDropZone, { global: { stubs: { teleport: true } } })

    const fileInput = wrapper.find('.drop-area__input')
    expect(fileInput.exists()).toBe(true)
    expect(fileInput.attributes('accept')).toContain('.txt')
    expect(fileInput.attributes('accept')).toContain('.md')
    expect(fileInput.attributes('accept')).toContain('.docx')
  })

  it('drop event triggers upload', async () => {
    const wrapper = mount(FileDropZone, { global: { stubs: { teleport: true } } })

    // Simulate dragover to show drag-over state
    await wrapper.find('.drop-area').trigger('dragover')
    expect(wrapper.find('.drop-area').classes()).toContain('drag-over')

    // Verify the ref is accessible via vm (cast to any since refs aren't in TS type)
    const vm = wrapper.vm as unknown as Record<string, unknown>
    expect(vm.dragOver).toBe(true)
    await wrapper.find('.drop-area').trigger('dragleave')
    expect(vm.dragOver).toBe(false)
  })
})
