<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useJobStore } from '@/stores/job'
import { downloadJobFile, downloadJobZip } from '@/services/api'
import Button from '@/components/UI/Button.vue'
import { Download } from '@lucide/vue'

const jobStore = useJobStore()
const loading = ref(false)
const selectedFile = ref<string | null>(null)
const previewContent = ref<string | null>(null)
const previewType = ref<'text' | 'html' | 'md'>('text')
const previewLoading = ref(false)
const { t } = useI18n()

const activeJob = computed(() => {
  const id = jobStore.selectedJobId || jobStore.currentJobId
  if (!id) return null
  return jobStore.jobs.find(j => j.id === id) || { id, created_at: null, status: null }
})

function formatDate(iso: string | undefined | null): string {
  if (!iso) return ''
  return new Date(iso).toLocaleString('ru-RU', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

async function loadFiles() {
  const jobId = jobStore.selectedJobId || jobStore.currentJobId
  if (!jobId) return
  loading.value = true
  try {
    await jobStore.fetchJobFiles(jobId)
  } finally {
    loading.value = false
  }
}

async function handleDownload(filename: string) {
  const jobId = jobStore.selectedJobId || jobStore.currentJobId
  if (!jobId) return
  const blob = await downloadJobFile(jobId, filename)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

async function handleDownloadAll() {
  const jobId = jobStore.selectedJobId || jobStore.currentJobId
  if (!jobId) return
  const blob = await downloadJobZip(jobId)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `job-${jobId.slice(0, 8)}.zip`
  a.click()
  URL.revokeObjectURL(url)
}

async function selectFile(filename: string) {
  selectedFile.value = filename
  previewLoading.value = true
  previewContent.value = null
  previewType.value = 'text'
  try {
    const jobId = jobStore.selectedJobId || jobStore.currentJobId
    if (!jobId) return
    const blob = await downloadJobFile(jobId, filename)
    const text = await blob.text()
    previewContent.value = text
    // Detect file type
    const ext = filename.split('.').pop()?.toLowerCase()
    if (ext === 'html' || ext === 'htm') {
      previewType.value = 'html'
    } else if (ext === 'md') {
      previewType.value = 'md'
    }
  } catch {
    previewContent.value = null
  } finally {
    previewLoading.value = false
  }
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}

onMounted(loadFiles)
watch(() => jobStore.currentJobId, loadFiles)
watch(() => jobStore.selectedJobId, loadFiles)
</script>

<template>
  <div class="job-output">
      <h2 class="job-output__title">{{ t('jobOutput.title') }}</h2>
    <div class="job-output__content">
    <!-- Left panel (1/4) -->
    <div class="job-output__list">
      <!-- Header: job info + ZIP -->
      <div class="job-output__list-header">
        <div class="job-output__list-info">
          <span v-if="activeJob" class="job-output__job-id">#{{ activeJob.id.slice(0, 8) }}</span>
          <span v-if="activeJob?.created_at" class="job-output__job-date">{{ formatDate(activeJob.created_at) }}</span>
        </div>
        <Button v-if="jobStore.currentJobFiles.length > 0" variant="secondary" size="sm" @click="handleDownloadAll"><Download :size="14" /> {{ t('jobOutput.zip') }}</Button>
      </div>
      <!-- File entries -->
      <div
        v-for="file in jobStore.currentJobFiles"
        :key="file.filename"
        :class="['job-output__file', { 'job-output__file--selected': selectedFile === file.filename }]"
        @click="selectFile(file.filename)"
      >
        <div class="job-output__file-name">{{ file.filename }}</div>
        <div class="job-output__file-meta">
          <span class="job-output__file-size">{{ formatSize(file.size_bytes) }}</span>
          <Button variant="secondary" size="sm" @click.stop="handleDownload(file.filename)"><Download :size="14" /></Button>
        </div>
      </div>
      <div v-if="jobStore.currentJobFiles.length === 0" class="job-output__list-empty">
        {{ t('jobOutput.empty') }}
      </div>
    </div>

    <!-- Right panel (3/4) — preview -->
    <div class="job-output__preview">
      <div v-if="!selectedFile" class="job-output__preview-empty">
        {{ t('jobOutput.selectPreview') }}
      </div>
      <div v-else-if="previewLoading" class="job-output__preview-empty">
        {{ t('jobOutput.loadingPreview') }}
      </div>
      <div v-else class="job-output__preview-content">
        <div class="job-output__preview-header">{{ selectedFile }}</div>
        <pre class="job-output__preview-text">{{ previewContent }}</pre>
      </div>
    </div><!-- /job-output__preview -->
    </div><!-- /job-output__content -->
  </div>
</template>

<style scoped>
.job-output {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.job-output__list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-main);
}

.job-output__list-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.job-output__list-empty {
  padding: 2rem;
  text-align: center;
  color: var(--fg-label);
  font-size: 13px;
}
.job-output__job-id { font-family: monospace; font-size: 13px; color: var(--fg-title); font-weight: 600; }
.job-output__job-date { font-size: 12px; color: var(--fg-label); }
.job-output__loading, .job-output__empty { padding: 2rem; text-align: center; color: var(--fg-label); }
.job-output__hint { font-size: 13px; opacity: 0.7; }

.job-output__title {
  font-size: 16px;
  font-weight: 600;
  color: var(--fg-title);
  margin: 0 0 1rem;
}

.job-output__content {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

/* Left panel — file list */
.job-output__list {
  width: 25%;
  min-width: 200px;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card);
}

.job-output__file {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  cursor: pointer;
  transition: background 0.15s;
}

.job-output__file:hover {
  background: var(--bg-hover-subtle);
}

.job-output__file--selected {
  background: var(--bg-active-subtle);
  border-left: 3px solid var(--accent);
}

.job-output__file-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--fg-title);
  word-break: break-all;
}

.job-output__file-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 4px;
}

.job-output__file-size {
  font-size: 11px;
  color: var(--fg-label);
}

/* Right panel — preview */
.job-output__preview {
  flex: 1;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card);
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.job-output__preview-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--fg-label);
  font-size: 13px;
}

.job-output__preview-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.job-output__preview-header {
  padding: 10px 14px;
  font-size: 12px;
  font-weight: 600;
  color: var(--fg-title);
  border-bottom: 1px solid var(--border);
  background: var(--bg-main);
}

.job-output__preview-text {
  flex: 1;
  margin: 0;
  padding: 8px;
  font-family: var(--font-mono);
  font-size: 12px;
  line-height: 1.6;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: break-word;
  color: var(--fg-title);
}
</style>
