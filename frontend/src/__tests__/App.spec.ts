import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import App from '../App.vue'

vi.mock('@/services/websocket', () => ({
  WSConnection: class {
    connect = vi.fn()
    disconnect = vi.fn()
    send = vi.fn()
    isConnected = true
  },
}))

vi.mock('@/services/api', () => ({
  getConfig: vi.fn().mockResolvedValue({
    llm: { model: '', base_url: '', api_key: '' },
    processing: { chunk_size: 10000, chunk_overlap: 1500, max_workers: 1, output_format: 'spr' },
    prompts: [],
    current_prompt_name: '',
  }),
  saveConfig: vi.fn().mockResolvedValue({}),
  getFiles: vi.fn().mockResolvedValue({ files: [], total: 0 }),
  uploadFiles: vi.fn().mockResolvedValue({ files: [], total: 0, message: 'ok' }),
  deleteFile: vi.fn().mockResolvedValue(undefined),
  getPrompts: vi.fn().mockResolvedValue({ prompts: [], total: 0 }),
  createPrompt: vi.fn().mockResolvedValue({ name: '', text: '' }),
  deletePrompt: vi.fn().mockResolvedValue({ deleted: '', message: 'ok' }),
  createJob: vi.fn().mockResolvedValue({ job: { id: 'test-id', status: 'pending' } }),
  getJobs: vi.fn().mockResolvedValue({ jobs: [], total: 0 }),
  getJob: vi.fn().mockResolvedValue({ job: null }),
  stopJob: vi.fn().mockResolvedValue({ job: null }),
  getJobFiles: vi.fn().mockResolvedValue({ job_id: '', files: [], total: 0 }),
  downloadJobFile: vi.fn().mockResolvedValue(new Blob()),
  downloadJobZip: vi.fn().mockResolvedValue(new Blob()),
}))

vi.mock('@/stores/job', () => {
  const mock = {
    currentJobId: null,
    status: null,
    progress: {},
    globalProgress: 0,
    logs: [],
    jobs: [],
    currentJobFiles: [],
    isRunning: false,
    isCompleted: false,
    startJob: vi.fn(),
    stopJob: vi.fn(),
    connectWS: vi.fn(),
    disconnectWS: vi.fn(),
    addLog: vi.fn(),
    createAndStartJob: vi.fn(),
    fetchJobs: vi.fn(),
    fetchJobFiles: vi.fn(),
  }
  return { useJobStore: () => mock }
})

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
