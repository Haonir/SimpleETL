<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useJobStore } from '@/stores/job'
import { downloadJobFile, downloadJobZip } from '@/services/api'
import Button from '@/components/UI/Button.vue'

const jobStore = useJobStore()
const loading = ref(false)

async function loadFiles() {
  if (!jobStore.currentJobId) return
  loading.value = true
  try {
    await jobStore.fetchJobFiles(jobStore.currentJobId)
  } finally {
    loading.value = false
  }
}

async function handleDownload(filename: string) {
  if (!jobStore.currentJobId) return
  const blob = await downloadJobFile(jobStore.currentJobId, filename)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function handleDownloadAll() {
  if (!jobStore.currentJobId) return
  const blob = await downloadJobZip(jobStore.currentJobId)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `job-${jobStore.currentJobId.slice(0, 8)}.zip`
  a.click()
  URL.revokeObjectURL(url)
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}

onMounted(loadFiles)
watch(() => jobStore.currentJobId, loadFiles)
</script>

<template>
  <div class="job-output">
    <div class="job-output__header">
      <h2 class="job-output__title">Output Files</h2>
      <Button v-if="jobStore.currentJobFiles.length > 0" variant="secondary" size="sm" @click="handleDownloadAll">
        ⬇ Download ZIP
      </Button>
    </div>

    <div v-if="loading" class="job-output__loading">Loading...</div>

    <div v-else-if="jobStore.currentJobFiles.length === 0" class="job-output__empty">
      <p>No output files available.</p>
      <p class="job-output__hint">Complete a job to see output files here.</p>
    </div>

    <table v-else class="job-output__table">
      <thead>
        <tr>
          <th>Filename</th>
          <th class="job-output__th-size">Size</th>
          <th class="job-output__th-action" />
        </tr>
      </thead>
      <tbody>
        <tr v-for="file in jobStore.currentJobFiles" :key="file.filename" class="job-output__row">
          <td>{{ file.filename }}</td>
          <td class="job-output__cell-size">{{ formatSize(file.size_bytes) }}</td>
          <td class="job-output__cell-action">
            <Button variant="secondary" size="sm" @click="handleDownload(file.filename)">⬇</Button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.job-output__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
.job-output__title { font-size: 16px; font-weight: 600; color: var(--fg-title); margin: 0; }
.job-output__loading, .job-output__empty { padding: 2rem; text-align: center; color: var(--fg-label); }
.job-output__hint { font-size: 13px; opacity: 0.7; }
.job-output__table { width: 100%; border-collapse: collapse; background: var(--bg-card); border-radius: 8px; overflow: hidden; }
.job-output__table th { padding: 10px 16px; text-align: left; font-size: 12px; font-weight: 600; color: var(--fg-header); border-bottom: 1px solid var(--border); background: var(--bg-main); }
.job-output__table td { padding: 10px 16px; font-size: 13px; border-bottom: 1px solid var(--border); }
.job-output__th-size, .job-output__cell-size { width: 100px; text-align: right; }
.job-output__th-action, .job-output__cell-action { width: 60px; text-align: center; }
</style>
