import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import FileList from '../FileList.vue'

vi.mock('@/services/api', () => ({
  getFiles: vi.fn().mockResolvedValue({ files: [], total: 0 }),
  uploadFiles: vi.fn().mockResolvedValue({ files: [], total: 0, message: 'ok' }),
  deleteFile: vi.fn().mockResolvedValue(undefined),
  createJob: vi.fn(),
  getJobs: vi.fn(),
  getJob: vi.fn(),
  stopJob: vi.fn(),
  getJobFiles: vi.fn(),
  downloadJobFile: vi.fn(),
  downloadJobZip: vi.fn(),
  getConfig: vi.fn(),
  saveConfig: vi.fn(),
  getPrompts: vi.fn(),
  createPrompt: vi.fn(),
  deletePrompt: vi.fn(),
}))

describe('FileList.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders file list from store', async () => {
    const store = (await import('@/stores/files')).useFilesStore()
    store.files = [
      { id: '1', filename: 'report.txt', size_bytes: 1024, content_type: 'text/plain', uploaded_at: new Date().toISOString() },
      { id: '2', filename: 'notes.md', size_bytes: 512, content_type: 'text/markdown', uploaded_at: new Date().toISOString() },
    ]

    const wrapper = mount(FileList, {
      global: {
        stubs: { teleport: true, Checkbox: { template: '<div class="checkbox-stub" />' } },
      },
    })
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.file-list__table').exists()).toBe(true)
    expect(wrapper.text()).toContain('report.txt')
    expect(wrapper.text()).toContain('notes.md')
  })

  it('shows empty state when no files', () => {
    const wrapper = mount(FileList, {
      global: {
        stubs: { teleport: true, Checkbox: { template: '<div class="checkbox-stub" />' } },
      },
    })
    expect(wrapper.find('.file-list__empty').exists()).toBe(true)
    expect(wrapper.text()).toContain('Нет загруженных файлов')
  })

  it('select all checkbox toggles all file selections', async () => {
    const store = (await import('@/stores/files')).useFilesStore()
    store.files = [
      { id: '1', filename: 'a.txt', size_bytes: 100, content_type: 'text/plain', uploaded_at: new Date().toISOString() },
      { id: '2', filename: 'b.txt', size_bytes: 200, content_type: 'text/plain', uploaded_at: new Date().toISOString() },
    ]

    const wrapper = mount(FileList, {
      global: {
        stubs: { teleport: true, Checkbox: { template: '<div class="checkbox-stub" />', props: ['modelValue'] } },
      },
    })
    await wrapper.vm.$nextTick()

    // Directly call the select all function
    ;(wrapper.vm as any).handleSelectAll(true)
    await wrapper.vm.$nextTick()

    expect(store.selectedIds).toHaveLength(2)
  })

  it('delete button calls removeFile with confirmation', async () => {
    const store = (await import('@/stores/files')).useFilesStore()
    store.files = [
      { id: '1', filename: 'report.txt', size_bytes: 1024, content_type: 'text/plain', uploaded_at: new Date().toISOString() },
    ]

    const wrapper = mount(FileList, {
      global: {
        stubs: {
          teleport: true,
          Checkbox: { template: '<div class="checkbox-stub" />', props: ['modelValue'] },
          Button: { template: '<button><slot /></button>', props: ['variant', 'size', 'disabled'] },
        },
      },
    })
    await wrapper.vm.$nextTick()

    vi.spyOn(window, 'confirm').mockImplementation(() => true)
    
    // Find button with text "Удалить"
    const deleteButton = wrapper.findAll('button').find(b => b.text() === 'Удалить')
    expect(deleteButton).toBeDefined()
    
    await deleteButton!.trigger('click')
    // Wait for async removeFile to complete
    await wrapper.vm.$nextTick()
    await wrapper.vm.$nextTick()
    
    expect(store.files).toHaveLength(0)
    vi.restoreAllMocks()
  })
})
