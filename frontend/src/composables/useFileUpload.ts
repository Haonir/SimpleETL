import { ref } from 'vue'
import { uploadFiles as apiUploadFiles } from '@/services/api'
import { useFilesStore } from '@/stores/files'

export function useFileUpload() {
  const uploading = ref(false)
  const error = ref<string | null>(null)
  const filesStore = useFilesStore()

  async function upload(fileList: File[]) {
    if (fileList.length === 0) return
    uploading.value = true
    error.value = null
    try {
      await apiUploadFiles(fileList)
      await filesStore.fetchFiles()
    } catch (e) {
      error.value = e instanceof Error ? e.message : String(e)
    } finally {
      uploading.value = false
    }
  }

  return { uploading, error, upload }
}
