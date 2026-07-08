import { describe, it, expect, vi, beforeEach } from 'vitest'

// ── Mock setup ────────────────────────────────────────────────────────────
// vi.hoisted() ensures these are hoisted alongside vi.mock(), so they exist
// when the factory runs (vitest hoists both above variable declarations).
const { mockPost, mockDelete } = vi.hoisted(() => ({
  mockPost: vi.fn(),
  mockDelete: vi.fn(),
}))

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      post: mockPost,
      delete: mockDelete,
      interceptors: { response: { use: vi.fn() } },
      defaults: { headers: { common: {} } },
    })),
  },
}))

import { uploadFiles, deleteFile } from '@/services/api'

describe('api.ts — REST client', () => {
  beforeEach(() => {
    // Clear call history only — don't destroy the mock references
    mockPost.mockClear()
    mockDelete.mockClear()
  })

  it('uploadFiles sends FormData to POST /api/v1/files/upload', async () => {
    const file = new File(['content'], 'test.txt', { type: 'text/plain' })
    const fakeResp = { files: [], total: 0, message: 'ok' }
    mockPost.mockResolvedValue({ data: fakeResp })

    const result = await uploadFiles([file])

    expect(mockPost).toHaveBeenCalledWith(
      '/api/v1/files/upload',
      expect.any(FormData),
      expect.objectContaining({ headers: { 'Content-Type': undefined } }),
    )
    expect(result).toEqual(fakeResp)
  })

  it('deleteFile calls DELETE /api/v1/files/{id}', async () => {
    mockDelete.mockResolvedValue({})

    await deleteFile('abc-123')

    expect(mockDelete).toHaveBeenCalledWith('/api/v1/files/abc-123')
  })
})
