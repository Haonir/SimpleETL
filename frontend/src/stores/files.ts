import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getFiles, uploadFiles, deleteFile } from '@/services/api'
import type { FileItem } from '@/types/file'

export const useFilesStore = defineStore('files', () => {
  const files = ref<FileItem[]>([])
  const selectedIds = ref<string[]>([])
  const uploading = ref(false)

  const hasFiles = computed(() => files.value.length > 0)
  const selectedCount = computed(() => selectedIds.value.length)
  const hasPdf = computed(() => files.value.some(f => f.filename.toLowerCase().endsWith('.pdf')))

  async function fetchFiles() {
    try {
      const response = await getFiles()
      files.value = response.files
    } catch {
      // Backend unreachable or error — clear stale file list
      files.value = []
    }
  }

  async function upload(fileList: File[]) {
    uploading.value = true
    try {
      const response = await uploadFiles(fileList)
      files.value = response.files
    } finally {
      uploading.value = false
    }
  }

  async function removeFile(id: string) {
    await deleteFile(id)
    files.value = files.value.filter(f => f.id !== id)
    selectedIds.value = selectedIds.value.filter(sid => sid !== id)
  }

  async function removeSelected() {
    const ids = [...selectedIds.value]
    await Promise.all(ids.map(id => deleteFile(id)))
    files.value = files.value.filter(f => !ids.includes(f.id))
    selectedIds.value = []
  }

  function toggleSelect(id: string) {
    const idx = selectedIds.value.indexOf(id)
    if (idx === -1) selectedIds.value.push(id)
    else selectedIds.value.splice(idx, 1)
  }

  function selectAll() {
    selectedIds.value = files.value.map(f => f.id)
  }

  function clearSelection() {
    selectedIds.value = []
  }

  return {
    files, selectedIds, uploading,
    hasFiles, selectedCount, hasPdf,
    fetchFiles, upload, removeFile, removeSelected, toggleSelect, selectAll, clearSelection,
  }
})
