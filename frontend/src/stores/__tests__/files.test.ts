import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const { mockGetFiles, mockUploadFiles, mockDeleteFile } = vi.hoisted(() => ({
  mockGetFiles: vi.fn(),
  mockUploadFiles: vi.fn(),
  mockDeleteFile: vi.fn(),
}))

vi.mock('@/services/api', () => ({
  getFiles: mockGetFiles,
  uploadFiles: mockUploadFiles,
  deleteFile: mockDeleteFile,
}))

import { useFilesStore } from '@/stores/files'

describe('files store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('fetchFiles populates files from API', async () => {
    mockGetFiles.mockResolvedValue({
      files: [{ id: '1', filename: 'a.txt', size_bytes: 100, content_type: 'text/plain', uploaded_at: '' }],
      total: 1,
    })

    const store = useFilesStore()
    await store.fetchFiles()

    expect(store.files).toHaveLength(1)
    expect(store.hasFiles).toBe(true)
  })

  it('upload adds files and sets uploading flag', async () => {
    mockUploadFiles.mockResolvedValue({
      files: [{ id: '2', filename: 'b.md', size_bytes: 200, content_type: 'text/markdown', uploaded_at: '' }],
      total: 1,
      message: 'ok',
    })

    const store = useFilesStore()
    const file = new File(['x'], 'b.md', { type: 'text/markdown' })
    await store.upload([file])

    expect(store.files).toHaveLength(1)
    expect(store.uploading).toBe(false)
  })

  it('removeFile deletes via API and removes from state', async () => {
    mockGetFiles.mockResolvedValue({
      files: [
        { id: '1', filename: 'a.txt', size_bytes: 100, content_type: 'text/plain', uploaded_at: '' },
        { id: '2', filename: 'b.md', size_bytes: 200, content_type: 'text/markdown', uploaded_at: '' },
      ],
      total: 2,
    })
    mockDeleteFile.mockResolvedValue(undefined)

    const store = useFilesStore()
    await store.fetchFiles()
    store.toggleSelect('1')
    await store.removeFile('1')

    expect(store.files).toHaveLength(1)
    expect(store.files[0].id).toBe('2')
    expect(store.selectedIds).toEqual([])
  })

  it('toggleSelect adds and removes from selectedIds', () => {
    const store = useFilesStore()
    store.toggleSelect('a')
    store.toggleSelect('b')
    expect(store.selectedIds).toEqual(['a', 'b'])

    store.toggleSelect('a')
    expect(store.selectedIds).toEqual(['b'])
  })

  it('clearSelection empties selectedIds', () => {
    const store = useFilesStore()
    store.toggleSelect('x')
    store.toggleSelect('y')
    store.clearSelection()
    expect(store.selectedIds).toEqual([])
  })
})
