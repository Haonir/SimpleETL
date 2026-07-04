import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const { mockConnect, mockDisconnect, mockSend } = vi.hoisted(() => ({
  mockConnect: vi.fn(),
  mockDisconnect: vi.fn(),
  mockSend: vi.fn(),
}))

vi.mock('@/services/websocket', () => ({
  WSConnection: class {
    connect = mockConnect
    disconnect = mockDisconnect
    send = mockSend
    isConnected = true
  },
}))

import { useJobStore } from '@/stores/job'

describe('job store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockConnect.mockClear()
    mockDisconnect.mockClear()
    mockSend.mockClear()
  })

  it('startJob sets jobId and status', () => {
    const store = useJobStore()
    store.startJob('job-123')

    expect(store.currentJobId).toBe('job-123')
    expect(store.status).toBe('queued')
    expect(mockConnect).toHaveBeenCalledWith('job-123', expect.any(Function))
  })

  it('handleMessage updates progress from WS message', () => {
    const store = useJobStore()
    store.startJob('job-123')

    // Get the handleMessage callback that was passed to connect
    const onMessage = mockConnect.mock.calls[0][1]

    onMessage({ type: 'progress', job_id: 'job-123', file_name: 'doc.txt', chunk_index: 1, total_chunks: 10, percent: 50 })

    expect(store.progress['doc.txt']).toBe(50)
    expect(store.globalProgress).toBe(50)

    onMessage({ type: 'progress', job_id: 'job-123', file_name: 'doc.txt', chunk_index: 2, total_chunks: 10, percent: 100 })

    expect(store.globalProgress).toBe(100)

    onMessage({ type: 'done', job_id: 'job-123', file_name: 'doc.txt', total_chunks: 10, processed_chunks: 10, error_count: 0 })

    expect(store.status).toBe('completed')
    expect(store.globalProgress).toBe(100)
  })
})
