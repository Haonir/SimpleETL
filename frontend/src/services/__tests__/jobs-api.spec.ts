import { describe, it, expect, vi, beforeEach } from 'vitest'

// ── Mock setup ────────────────────────────────────────────────────────────
const { mockGet, mockPost, mockDelete } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
  mockDelete: vi.fn(),
}))

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: mockGet,
      post: mockPost,
      delete: mockDelete,
      interceptors: { response: { use: vi.fn() } },
      defaults: { headers: { common: {} } },
    })),
  },
}))

import { createJob, getJobs, stopJob } from '@/services/api'

describe('jobs-api.ts — job endpoints', () => {
  beforeEach(() => {
    mockGet.mockClear()
    mockPost.mockClear()
    mockDelete.mockClear()
  })

  it('createJob calls POST /api/v1/jobs', async () => {
    const request = { file_ids: ['1', '2'], config: {} }
    const fakeResponse = { job: { id: 'job-abc' } }
    mockPost.mockResolvedValue({ data: fakeResponse })

    const result = await createJob(request)

    expect(mockPost).toHaveBeenCalledWith('/api/v1/jobs', request)
    expect(result).toEqual(fakeResponse)
  })

  it('getJobs calls GET /api/v1/jobs', async () => {
    const fakeResponse = { jobs: [] }
    mockGet.mockResolvedValue({ data: fakeResponse })

    const result = await getJobs()

    expect(mockGet).toHaveBeenCalledWith('/api/v1/jobs')
    expect(result).toEqual(fakeResponse)
  })

  it('stopJob calls DELETE /api/v1/jobs/{id}', async () => {
    const jobId = 'job-xyz'
    mockDelete.mockResolvedValue({})

    await stopJob(jobId)

    expect(mockDelete).toHaveBeenCalledWith(`/api/v1/jobs/${encodeURIComponent(jobId)}`)
  })
})
