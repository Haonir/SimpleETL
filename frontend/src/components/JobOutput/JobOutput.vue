<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useJobStore } from '@/stores/job'
import { downloadJobFile, downloadJobZip } from '@/services/api'
import Button from '@/components/UI/Button.vue'
import { Download } from '@lucide/vue'
import { marked } from 'marked'

const jobStore = useJobStore()
const { t } = useI18n()
const loading = ref(false)
const selectedFile = ref<string | null>(null)
const previewContent = ref<string | null>(null)
const previewType = ref<'text' | 'html' | 'md'>('text')
const previewLoading = ref(false)

const renderedContent = computed(() => {
  if (!previewContent.value) return ''
  if (previewType.value === 'md') {
    return marked(previewContent.value) as string
  }
  return ''
})

const themedHtmlContent = computed(() => {
  if (!previewContent.value || previewType.value !== 'html') return ''
  const allStyles = getThemeStyles()
  const styleTag = `<style>${allStyles}</style>`
  // Inject styles into <head> or add <head> if missing
  if (previewContent.value.includes('<head>')) {
    return previewContent.value.replace('<head>', `<head>${styleTag}`)
  }
  if (previewContent.value.includes('<html>')) {
    return previewContent.value.replace('<html>', `<html>${styleTag}`)
  }
  // Plain HTML without structure
  return `${styleTag}\n${previewContent.value}`
})

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

function getThemeStyles(): string {
  const root = document.documentElement
  const cs = getComputedStyle(root)
  const get = (v: string) => cs.getPropertyValue(v).trim()

  return `
    :root {
      --bg-main: ${get('--bg-main')};
      --bg-card: ${get('--bg-card')};
      --bg-input: ${get('--bg-input')};
      --fg-title: ${get('--fg-title')};
      --fg-label: ${get('--fg-label')};
      --fg-header: ${get('--fg-header')};
      --fg-muted: ${get('--fg-muted')};
      --fg-subtle: ${get('--fg-subtle')};
      --border: ${get('--border')};
      --accent: ${get('--accent')};
      --accent-hover: ${get('--accent-hover')};
      --font-mono: ${get('--font-mono')};
    }
    body, html {
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      font-size: 14px;
      line-height: 1.6;
      color: ${get('--fg-title')} !important;
      background: ${get('--bg-card')} !important;
      margin: 0;
      padding: 16px;
    }
    h1, h2, h3, h4, h5, h6 {
      color: ${get('--fg-title')} !important;
      font-weight: 600;
      margin-top: 1.5em;
      margin-bottom: 0.5em;
    }
    h1 { font-size: 1.8em; }
    h2 { font-size: 1.5em; }
    h3 { font-size: 1.3em; }
    h4 { font-size: 1.1em; }
    p { margin-bottom: 0.75em; color: ${get('--fg-label')}; }
    a { color: ${get('--accent')}; text-decoration: none; }
    a:hover { text-decoration: underline; }
    strong, b { color: ${get('--fg-title')}; font-weight: 600; }
    em, i { color: ${get('--fg-label')}; }
    code, pre {
      font-family: ${get('--font-mono')};
      background: ${get('--bg-main')} !important;
      color: ${get('--fg-title')} !important;
    }
    pre {
      padding: 12px;
      border-radius: 6px;
      overflow-x: auto;
      margin-bottom: 1em;
    }
    code {
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.9em;
    }
    pre code {
      background: transparent !important;
      padding: 0;
    }
    table { border-collapse: collapse; width: 100%; margin-bottom: 1em; }
    th, td { border: 1px solid ${get('--border')}; padding: 8px 12px; text-align: left; }
    th { background: ${get('--bg-main')}; font-weight: 600; color: ${get('--fg-title')}; }
    td { color: ${get('--fg-label')}; }
    img { max-width: 100%; border-radius: 6px; }
    blockquote {
      border-left: 3px solid ${get('--accent')};
      padding-left: 1em;
      margin-left: 0;
      margin-bottom: 1em;
      color: ${get('--fg-muted')};
      font-style: italic;
    }
    ul, ol { padding-left: 1.5em; margin-bottom: 0.75em; }
    li { margin-bottom: 0.25em; color: ${get('--fg-label')}; }
    hr { border: none; border-top: 1px solid ${get('--border')}; margin: 1.5em 0; }
    small { color: ${get('--fg-muted')}; }
    mark { background: ${get('--badge-bg-warning') || '#fef3c7'}; color: ${get('--fg-title')}; padding: 2px 4px; border-radius: 2px; }
  `
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
        <div v-if="previewType === 'text'" class="job-output__preview-text">
          <pre>{{ previewContent }}</pre>
        </div>
        <div v-else-if="previewType === 'html'" class="job-output__preview-iframe-wrap">
          <iframe class="job-output__preview-iframe" :srcdoc="themedHtmlContent" sandbox></iframe>
        </div>
        <div v-else class="job-output__preview-rendered" v-html="renderedContent"></div>
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

.job-output__preview-rendered {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  font-size: 14px;
  line-height: 1.6;
  color: var(--fg-title);
}

.job-output__preview-rendered :deep(h1),
.job-output__preview-rendered :deep(h2),
.job-output__preview-rendered :deep(h3),
.job-output__preview-rendered :deep(h4) {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: 600;
  color: var(--fg-title);
}

.job-output__preview-rendered :deep(h1) { font-size: 1.5em; }
.job-output__preview-rendered :deep(h2) { font-size: 1.3em; }
.job-output__preview-rendered :deep(h3) { font-size: 1.1em; }

.job-output__preview-rendered :deep(p) {
  margin-bottom: 0.75em;
}

.job-output__preview-rendered :deep(code) {
  font-family: var(--font-mono);
  font-size: 0.9em;
  background: var(--bg-main);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--fg-title);
}

.job-output__preview-rendered :deep(pre) {
  background: var(--bg-main);
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin-bottom: 1em;
}

.job-output__preview-rendered :deep(pre code) {
  background: none;
  padding: 0;
}

.job-output__preview-rendered :deep(ul),
.job-output__preview-rendered :deep(ol) {
  padding-left: 1.5em;
  margin-bottom: 0.75em;
}

.job-output__preview-rendered :deep(li) {
  margin-bottom: 0.25em;
}

.job-output__preview-rendered :deep(blockquote) {
  border-left: 3px solid var(--accent);
  padding-left: 1em;
  margin-left: 0;
  color: var(--fg-label);
  margin-bottom: 0.75em;
}

.job-output__preview-rendered :deep(a) {
  color: var(--accent);
  text-decoration: none;
}

.job-output__preview-rendered :deep(a:hover) {
  text-decoration: underline;
}

.job-output__preview-rendered :deep(img) {
  max-width: 100%;
  border-radius: 6px;
}

.job-output__preview-rendered :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 1em;
}

.job-output__preview-rendered :deep(th),
.job-output__preview-rendered :deep(td) {
  border: 1px solid var(--border);
  padding: 8px 12px;
  text-align: left;
}

.job-output__preview-rendered :deep(th) {
  background: var(--bg-main);
  font-weight: 600;
}

.job-output__preview-rendered :deep(hr) {
  border: none;
  border-top: 1px solid var(--border);
  margin: 1.5em 0;
}

.job-output__preview-iframe-wrap {
  flex: 1;
  overflow: hidden;
}

.job-output__preview-iframe {
  width: 100%;
  height: 100%;
  border: none;
  background: var(--bg-card);
}
</style>
