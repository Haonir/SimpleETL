<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { useFilesStore } from '@/stores/files'
import { useJobStore } from '@/stores/job'
import Button from '@/components/UI/Button.vue'
import Checkbox from '@/components/UI/Checkbox.vue'
import FileProgressBar from '@/components/Progress/FileProgressBar.vue'
import FileDropZone from '@/components/Processing/FileDropZone.vue'
import JobToolbar from '@/components/Processing/JobToolbar.vue'
import GlobalProgressBar from '@/components/Progress/GlobalProgressBar.vue'
import LogEntry from '@/components/LogPanel/LogEntry.vue'

import { downloadJobFile, downloadJobZip } from '@/services/api'
import { Download } from '@lucide/vue'

const store = useFilesStore()
const jobStore = useJobStore()
const { t } = useI18n()

// Delete dialog state
const showDeleteDialog = ref(false)
const deleteMode = ref<'single' | 'batch'>('single')
const fileToDelete = ref<string | null>(null)

function handleSelectAll(checked: boolean) {
  if (checked) store.selectAll()
  else store.clearSelection()
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  const mb = kb / 1024
  return `${mb.toFixed(1)} MB`
}

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return iso
  }
}

function confirmDelete(id: string) {
  deleteMode.value = 'single'
  fileToDelete.value = id
  showDeleteDialog.value = true
}

function confirmDeleteSelected() {
  if (store.selectedIds.length === 0) return
  deleteMode.value = 'batch'
  fileToDelete.value = null
  showDeleteDialog.value = true
}

async function handleDeleteConfirm() {
  if (deleteMode.value === 'single' && fileToDelete.value) {
    await store.removeFile(fileToDelete.value)
  } else if (deleteMode.value === 'batch') {
    await store.removeSelected()
  }
  showDeleteDialog.value = false
  fileToDelete.value = null
}

function cancelDelete() {
  showDeleteDialog.value = false
  fileToDelete.value = null
}

const allSelected = computed(() => store.files.length > 0 && store.selectedIds.length === store.files.length)

// ── Output files panel ────────────────────────────────────────
const outputLoading = ref(false)

async function loadOutputFiles() {
  const jobId = jobStore.selectedJobId || jobStore.currentJobId
  if (!jobId) return
  outputLoading.value = true
  try {
    await jobStore.fetchJobFiles(jobId)
  } finally {
    outputLoading.value = false
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

onMounted(loadOutputFiles)
watch(() => jobStore.currentJobId, loadOutputFiles)
watch(() => jobStore.selectedJobId, loadOutputFiles)
watch(() => jobStore.status, (newStatus) => {
  if (newStatus === 'completed') loadOutputFiles()
})

// ── Log panel state ───────────────────────────────────────────
const LOG_DRAWER_KEY = 'simpleetl_log_drawer_expanded'
const logContainerRef = ref<HTMLElement | null>(null)
const logsExpanded = ref(localStorage.getItem(LOG_DRAWER_KEY) === 'true')

function toggleLogDrawer() {
  logsExpanded.value = !logsExpanded.value
  localStorage.setItem(LOG_DRAWER_KEY, String(logsExpanded.value))
}

watch(
  () => jobStore.activeLogs.length,
  async () => {
    if (logsExpanded.value) {
      await nextTick()
      logContainerRef.value?.scrollTo({ top: 99999, behavior: 'smooth' })
    }
  },
)
</script>

<template>
  <div class="processing-layout">
    <!-- Left column (1/3) — output files -->
    <div class="processing-output">
      <div class="processing-output__header">
        <span class="processing-output__title">{{ t('processedFiles.title') }}</span>
        <Button v-if="jobStore.currentJobFiles.length > 0" variant="secondary" size="sm" @click="handleDownloadAll"><Download :size="14" /> {{ t('jobOutput.zip') }}</Button>
      </div>
      <div
        v-for="file in jobStore.currentJobFiles"
        :key="file.filename"
        class="processing-output__file"
      >
        <div class="processing-output__file-info">
          <div class="processing-output__file-name">{{ file.filename }}</div>
          <span class="processing-output__file-size">{{ formatSize(file.size_bytes) }}</span>
        </div>
        <Button variant="secondary" size="sm" @click="handleDownload(file.filename)"><Download :size="14" /></Button>
      </div>
      <div v-if="jobStore.currentJobFiles.length === 0 && !outputLoading" class="processing-output__empty">
        {{ t('processedFiles.empty') }}
      </div>

    </div>

    <!-- Right column (2/3) — existing content -->
    <div class="processing-main">
      <!-- Drop zone (always visible) -->
      <FileDropZone :disabled="jobStore.isRunning" />

      <!-- Job toolbar (Start, prompt, format, skip LLM) -->
      <JobToolbar />

      <!-- Progress bar + status badge -->
      <div class="file-list__progress-row">
        <GlobalProgressBar />
      </div>

      <!-- Empty state -->
      <div v-if="!store.hasFiles" class="file-list__empty">
        <p class="file-list__empty-text">{{ $t('fileList.empty') }}</p>
        <p class="file-list__empty-hint">{{ $t('fileList.dragHint') }}</p>
      </div>

      <!-- Table -->
      <table v-else class="file-list__table">
        <thead>
          <tr class="file-list__header">
            <th class="file-list__header-cell file-list__header-cell--checkbox">
              <Checkbox
                :modelValue="allSelected"
                @update:modelValue="handleSelectAll($event)"
              />
            </th>
            <th class="file-list__header-cell">{{ $t('fileList.filename') }}</th>
            <th class="file-list__header-cell file-list__header-cell--size">{{ $t('fileList.size') }}</th>
            <th class="file-list__header-cell file-list__header-cell--date">{{ $t('fileList.uploaded') }}</th>
            <th class="file-list__header-cell file-list__header-cell--actions">
              <Button variant="danger" size="sm" :disabled="store.selectedIds.length === 0" @click="confirmDeleteSelected">{{ $t('fileList.deleteSelected') }}</Button>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(file, fileIndex) in store.files" :key="file.id" class="file-list__row">
            <td class="file-list__cell file-list__cell--checkbox">
              <Checkbox
                :modelValue="store.selectedIds.includes(file.id)"
                @update:modelValue="store.toggleSelect(file.id)"
              />
            </td>
            <td class="file-list__cell file-list__cell--name">
              <span :title="file.filename">{{ file.filename }}</span>
              <FileProgressBar :fileId="file.id" :fileName="file.filename" />
            </td>
            <td class="file-list__cell file-list__cell--size">{{ formatSize(file.size_bytes) }}</td>
            <td class="file-list__cell file-list__cell--date">{{ formatDate(file.uploaded_at) }}</td>
            <td class="file-list__cell file-list__cell--actions">
              <Button variant="secondary" size="sm" @click="confirmDelete(file.id)">{{ $t('common.delete') }}</Button>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Footer -->
      <div v-if="store.hasFiles" class="file-list__footer">
        <span>{{ $t('common.selected', { count: store.selectedCount, total: store.files.length }) }}</span>
      </div>

      <!-- Delete confirmation dialog -->
      <div v-if="showDeleteDialog" class="file-list__dialog-overlay" @click.self="cancelDelete">
        <div class="file-list__dialog">
          <h3 class="file-list__dialog-title">{{ $t('fileList.confirmTitle') }}</h3>
          <p class="file-list__dialog-text">
            <template v-if="deleteMode === 'single'">
              {{ $t('fileList.confirmSingle') }}
            </template>
            <template v-else>
              {{ $t('fileList.confirmBatch', { count: store.selectedIds.length }) }}
            </template>
          </p>
          <p class="file-list__dialog-warning">
            {{ $t('fileList.warning') }}
          </p>
          <div class="file-list__dialog-actions">
            <button class="file-list__dialog-btn file-list__dialog-btn--cancel" @click="cancelDelete">{{ $t('common.cancel') }}</button>
            <button class="file-list__dialog-btn file-list__dialog-btn--danger" @click="handleDeleteConfirm">Delete</button>
          </div>
        </div>
      </div>
      <!-- Log drawer (slides up from bottom) -->
      <div class="processing-log-drawer" :class="{ 'processing-log-drawer--expanded': logsExpanded }">
        <div class="processing-log-drawer__handle" @click="toggleLogDrawer">
          <span class="processing-log-drawer__handle-bar"></span>
          <span class="processing-log-drawer__title">{{ t('logPanel.title') }}</span>
          <span class="processing-log-drawer__count" v-if="jobStore.activeLogs.length > 0">{{ jobStore.activeLogs.length }}</span>
        </div>
        <div ref="logContainerRef" class="processing-log-drawer__content" :class="{ 'processing-log-drawer__content--expanded': logsExpanded }">
          <template v-if="jobStore.activeLogs.length === 0">
            <p class="processing-log-drawer__empty">{{ t('logPanel.empty') }}</p>
          </template>
          <LogEntry v-for="(entry, i) in jobStore.activeLogs" :key="i" :entry="entry" />
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>

/* ── Two-column layout ──────────────────────────────────────── */
.processing-layout {
  display: flex;
  gap: 16px;
  height: 100%;
  font-family: 'Segoe UI', system-ui, sans-serif;
}

/* ── Left column: output files (1/3) ────────────────────────── */
.processing-output {
  flex: 1;
  min-width: 220px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.processing-output__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-main);
  position: sticky;
  top: 0;
  z-index: 1;
}

.processing-output__title {
  font-size: 13px;
  font-weight: 600;
  color: var(--fg-title);
}

.processing-output__file {
  padding: 10px 14px;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.processing-output__file:last-child {
  border-bottom: none;
}

.processing-output__file-info {
  min-width: 0;
  flex: 1;
}

.processing-output__file-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--fg-title);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.processing-output__file-size {
  font-size: 11px;
  color: var(--fg-label);
}

.processing-output__empty {
  padding: 2rem;
  text-align: center;
  color: var(--fg-label);
  font-size: 13px;
}

/* ── Right column: main content (2/3) ───────────────────────── */
.processing-main {
  flex: 4;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Empty state */
.file-list__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem 1rem;
  color: var(--fg-label);
}

.file-list__empty-text {
  font-size: 16px;
  margin-bottom: 0.5rem;
}

.file-list__empty-hint {
  font-size: 13px;
  opacity: 0.7;
}

/* Table */
.file-list__table {
  width: 100%;
  border-collapse: collapse;
  background: var(--bg-card);
  border-radius: 8px;
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}

.file-list__header {
  background: var(--bg-main);
}

.file-list__header-cell {
  padding: 12px 16px;
  text-align: left;
  font-size: 12px;
  font-weight: 600;
  color: var(--fg-header);
  border-bottom: 1px solid var(--border);
}

.file-list__header-cell--checkbox { width: 48px; }
.file-list__header-cell--size { width: 120px; text-align: right; }
.file-list__header-cell--date { width: 160px; }
.file-list__header-cell--actions { width: 140px; text-align: center; }

.file-list__row {
  border-bottom: 1px solid var(--border);
  transition: background-color 0.15s;
}

.file-list__row:last-child {
  border-bottom: none;
}

.file-list__row:hover {
  background-color: var(--bg-hover-subtle);
}

.file-list__cell {
  padding: 12px 16px;
  font-size: 13px;
  color: var(--fg-title);
}

.file-list__cell--checkbox { width: 48px; }
.file-list__cell--name { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-list__cell--size { text-align: right; color: var(--fg-label); font-variant-numeric: tabular-nums; }
.file-list__cell--date { color: var(--fg-label); }
.file-list__cell--actions { width: 140px; text-align: center; }

/* Footer */
.file-list__footer {
  padding: 8px 16px;
  font-size: 12px;
  color: var(--fg-label);
  opacity: 0.7;
}

/* Delete dialog */
.file-list__dialog-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.file-list__dialog {
  background: var(--bg-card, #fff);
  border-radius: 12px;
  padding: 24px;
  max-width: 420px;
  width: 90%;
  box-shadow: var(--shadow-dialog);
}

.file-list__dialog-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--fg-on-card);
  margin: 0 0 16px 0;
}

.file-list__dialog-text {
  font-size: 14px;
  color: var(--fg-subtle);
  margin: 0 0 16px 0;
}

.file-list__dialog-warning {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-error);
  margin: 0 0 20px 0;
  padding: 10px;
  background: var(--btn-danger-bg-light);
  border-radius: 6px;
  border: 1px solid var(--border-danger);
}

.file-list__dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.file-list__dialog-btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border);
  transition: all 0.15s;
}

.file-list__dialog-btn--cancel {
  background: var(--bg-card);
  color: var(--fg-on-card);
}

.file-list__dialog-btn--cancel:hover {
  background: var(--bg-hover-subtle);
}

.file-list__dialog-btn--danger {
  background: var(--btn-danger-bg);
  color: var(--btn-danger-fg);
  border-color: var(--btn-danger-border);
}

.file-list__dialog-btn--danger:hover {
  background: var(--btn-danger-hover);
}

/* Progress row */
.file-list__progress-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-list__progress-row .global-progress {
  flex: 1;
  margin-bottom: 0;
}

/* ── Log drawer — slides up from bottom of right column ─────── */
.processing-log-drawer {
  margin-top: auto;
  border-top: 1px solid var(--border);
  background: var(--bg-card);
  border-radius: 8px;
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.processing-log-drawer--expanded {
  border-radius: 8px;
}

.processing-log-drawer__handle {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  cursor: pointer;
  user-select: none;
  border-bottom: 1px solid transparent;
}

.processing-log-drawer--expanded .processing-log-drawer__handle {
  border-bottom-color: var(--border);
}

.processing-log-drawer__handle:hover {
  background: var(--bg-hover-subtle);
}

.processing-log-drawer__handle-bar {
  display: block;
  width: 24px;
  height: 3px;
  background: var(--fg-label);
  border-radius: 2px;
  opacity: 0.5;
}

.processing-log-drawer__title {
  font-size: 12px;
  font-weight: 600;
  color: var(--fg-header);
}

.processing-log-drawer__count {
  font-size: 10px;
  background: var(--badge-bg-muted);
  color: var(--badge-fg-muted);
  padding: 1px 6px;
  border-radius: 10px;
}

.processing-log-drawer__content {
  height: 0;
  overflow-y: auto;
  padding: 0 14px;
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  line-height: 1.6;
  transition: height 0.3s ease, padding 0.3s ease;
}

.processing-log-drawer__content--expanded {
  height: 30vh;
  padding: 8px 14px;
}

.processing-log-drawer__empty {
  color: var(--fg-subtle);
  text-align: center;
  padding: 1rem 0;
  font-size: 12px;
}
</style>
