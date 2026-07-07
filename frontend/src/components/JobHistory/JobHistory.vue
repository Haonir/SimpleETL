<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useJobStore } from '@/stores/job'
import { List, X, Trash2 } from '@lucide/vue'
import { useUiStore } from '@/stores/ui'

const { t } = useI18n()


const jobStore = useJobStore()
const uiStore = useUiStore()


onMounted(() => {
  jobStore.fetchJobs()
})


function formatDate(iso: string | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function statusClass(status: string): string {
  return `job-history__status--${status}`
}


function statusLabel(status: string): string {
  const key = `jobHistory.status.${status}`
  return t(key) || status
}

function getJobFormat(job: { config?: Record<string, unknown> }): string {
  const processing = job.config?.processing as Record<string, unknown> | undefined
  const format = processing?.output_format as string | undefined
  return format?.toUpperCase() || '—'
}



const showDeleteDialog = ref(false)
const jobToDelete = ref<string | null>(null)
const keepSourceFiles = ref(true)
const showBulkDeleteDialog = ref(false)


const selectedJobIds = ref<Set<string>>(new Set())
const allSelected = computed(() => jobStore.jobs.length > 0 && jobStore.jobs.every(j => selectedJobIds.value.has(j.id)))
const hasSelection = computed(() => selectedJobIds.value.size > 0)

function toggleSelectAll() {
  if (allSelected.value) {
    selectedJobIds.value = new Set()
  } else {
    selectedJobIds.value = new Set(jobStore.jobs.map(j => j.id))
  }
}

function toggleSelectJob(jobId: string) {
  const next = new Set(selectedJobIds.value)
  if (next.has(jobId)) {
    next.delete(jobId)
  } else {
    next.add(jobId)
  }
  selectedJobIds.value = next
}


function confirmDelete(jobId: string) {
  jobToDelete.value = jobId
  keepSourceFiles.value = true
  showDeleteDialog.value = true
}


async function handleDelete() {
  if (!jobToDelete.value) return
  await jobStore.deleteJob(jobToDelete.value, keepSourceFiles.value)
  showDeleteDialog.value = false
  jobToDelete.value = null
}


function cancelDelete() {
  showDeleteDialog.value = false
  jobToDelete.value = null
}


function confirmBulkDelete() {
  keepSourceFiles.value = true
  showBulkDeleteDialog.value = true
}

async function handleBulkDelete() {
  const ids = [...selectedJobIds.value]
  for (const id of ids) {
    await jobStore.deleteJob(id, keepSourceFiles.value)
  }
  selectedJobIds.value = new Set()
  showBulkDeleteDialog.value = false
}

function cancelBulkDelete() {
  showBulkDeleteDialog.value = false
}


function getJobFileNames(job: { file_names?: string[], file_ids: string[] }): string[] {
  if (job.file_names && job.file_names.length > 0) return job.file_names
  return job.file_ids.map(id => id.slice(0, 8))
}


function getFirstFileName(job: { file_names?: string[], file_ids: string[] }): string {
  return getJobFileNames(job)[0] || '—'
}


const popoverJobId = ref<string | null>(null)


function togglePopover(jobId: string) {
  popoverJobId.value = popoverJobId.value === jobId ? null : jobId
}


function closePopovers() {
  popoverJobId.value = null
}




</script>


<template>
  <div class="job-history" @click="closePopovers">
    <h2 class="job-history__title">{{ $t('jobHistory.title') }}</h2>


    <div v-if="jobStore.jobs.length === 0" class="job-history__empty">
      <p>{{ $t('jobHistory.empty') }}</p>
    </div>


    <table v-else class="job-history__table">
      <thead>
        <tr>
          <th class="job-history__th-checkbox"><input type="checkbox" :checked="allSelected" @change="toggleSelectAll" /></th>
          <th>{{ $t('jobHistory.colId') }}</th>
          <th>{{ $t('jobHistory.colStatus') }}</th>
          <th>{{ $t('jobHistory.colFiles') }}</th>
          <th>{{ $t('jobHistory.colCreated') }}</th>
          <th>{{ $t('jobHistory.colCompleted') }}</th>
          <th class="job-history__th-action">
            <button class="job-history__delete-btn" :disabled="!hasSelection" @click.stop="confirmBulkDelete" :title="$t('jobHistory.deleteTooltip')"><Trash2 :size="14" /></button>
          </th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="job in jobStore.jobs" :key="job.id" class="job-history__row" :class="{ 'job-history__row--selected': jobStore.selectedJobId === job.id }" @click="jobStore.selectJob(job.id)">
          <td class="job-history__cell-checkbox" @click.stop><input type="checkbox" :checked="selectedJobIds.has(job.id)" @change="toggleSelectJob(job.id)" /></td>
           <td class="job-history__cell-id">
             <span class="job-history__id-text">#{{ job.id.slice(0, 8) }}</span>
             <span class="job-history__format">{{ getJobFormat(job) }}</span>
</td>
          <td>
            <span :class="['job-history__status', statusClass(job.status)]">{{ statusLabel(job.status) }}</span>
          </td>
          <td class="job-history__cell-files">
            <div class="job-history__files-preview">
              <span class="job-history__file-name">{{ getFirstFileName(job) }}</span>
              <span v-if="job.file_ids.length > 1" class="job-history__file-more">+{{ job.file_ids.length - 1 }}</span>
                <button v-if="job.file_ids.length > 1" class="job-history__files-btn" @click.stop="togglePopover(job.id)" title="Show all files"><List :size="14" /></button>
            </div>
            <!-- Popover -->
            <div v-if="popoverJobId === job.id" class="job-history__popover" @click.stop>
              <div class="job-history__popover-title">Files ({{ job.file_ids.length }})</div>
              <ul class="job-history__popover-list">
                <li v-for="fileName in getJobFileNames(job)" :key="fileName" class="job-history__popover-item">{{ fileName }}</li>
              </ul>
            </div>
          </td>
          <td>{{ formatDate(job.created_at) }}</td>
          <td>{{ formatDate(job.completed_at) }}</td>
          <td class="job-history__cell-action">
            <button class="job-history__delete-btn" @click.stop="confirmDelete(job.id)" :title="$t('jobHistory.deleteTooltip')"><X :size="14" /></button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>


  <!-- Delete confirmation dialog -->
  <div v-if="showDeleteDialog" class="job-history__dialog-overlay" @click.self="cancelDelete">
    <div class="job-history__dialog">
      <h3 class="job-history__dialog-title">{{ $t('jobHistory.confirmTitle') }}</h3>
      <p class="job-history__dialog-text">
        {{ $t('jobHistory.confirmIntro') }}
      </p>
      <ul class="job-history__dialog-list">
        <li>{{ $t('jobHistory.deleteJobRecord') }}</li>
        <li :class="{ 'job-history__dialog-struck': keepSourceFiles }">{{ $t('jobHistory.deleteSourceFiles') }}</li>
        <li>{{ $t('jobHistory.deleteOutputFiles') }}</li>
      </ul>
      <label class="job-history__dialog-checkbox">
        <input type="checkbox" v-model="keepSourceFiles" />
        <span>{{ $t('jobHistory.keepSource') }}</span>
      </label>
      <p class="job-history__dialog-warning">
        {{ $t('jobHistory.warning') }}
      </p>
      <div class="job-history__dialog-actions">
        <button class="job-history__dialog-btn job-history__dialog-btn--cancel" @click="cancelDelete">{{ $t('common.cancel') }}</button>
        <button class="job-history__dialog-btn job-history__dialog-btn--danger" @click="handleDelete">{{ $t('common.delete') }}</button>
      </div>
    </div>
  </div>


  <!-- Bulk delete confirmation dialog -->
  <div v-if="showBulkDeleteDialog" class="job-history__dialog-overlay" @click.self="cancelBulkDelete">
    <div class="job-history__dialog">
      <h3 class="job-history__dialog-title">{{ $t('jobHistory.confirmTitleBatch', { count: selectedJobIds.size }) }}</h3>
      <p class="job-history__dialog-text">
        {{ $t('jobHistory.confirmIntro') }}
      </p>
      <ul class="job-history__dialog-list">
        <li>{{ $t('jobHistory.deleteJobRecord') }}</li>
        <li :class="{ 'job-history__dialog-struck': keepSourceFiles }">{{ $t('jobHistory.deleteSourceFiles') }}</li>
        <li>{{ $t('jobHistory.deleteOutputFiles') }}</li>
      </ul>
      <label class="job-history__dialog-checkbox">
        <input type="checkbox" v-model="keepSourceFiles" />
        <span>{{ $t('jobHistory.keepSource') }}</span>
      </label>
      <p class="job-history__dialog-warning">
        {{ $t('jobHistory.warning') }}
      </p>
      <div class="job-history__dialog-actions">
        <button class="job-history__dialog-btn job-history__dialog-btn--cancel" @click="cancelBulkDelete">{{ $t('common.cancel') }}</button>
        <button class="job-history__dialog-btn job-history__dialog-btn--danger" @click="handleBulkDelete">{{ $t('common.delete') }}</button>
      </div>
    </div>
  </div>

</template>


<style scoped>
.job-history__title { font-size: 16px; font-weight: 600; color: var(--fg-title); margin: 0 0 1rem; }
.job-history__empty { padding: 2rem; text-align: center; color: var(--fg-label); }
.job-history__table { width: 100%; border-collapse: collapse; background: var(--bg-card); border-radius: 8px; }
.job-history__table th { padding: 10px 16px; text-align: left; font-size: 12px; font-weight: 600; color: var(--fg-header); border-bottom: 1px solid var(--border); background: var(--bg-main); }
.job-history__table td { padding: 10px 16px; font-size: 13px; border-bottom: 1px solid var(--border); }
.job-history__cell-id { font-family: monospace; font-size: 12px; white-space: nowrap; }

.job-history__id-text { font-family: var(--font-mono); font-size: var(--font-size-sm); color: var(--fg-muted); }

.job-history__format { font-size: 10px; font-weight: 600; padding: 2px 6px; border-radius: 4px; background: var(--badge-bg-muted); color: var(--badge-fg-muted); text-transform: uppercase; letter-spacing: 0.5px; vertical-align: middle; margin-left: 8px; }
.job-history__status { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 500; }
.job-history__status--pending { background: var(--badge-bg-muted); color: var(--badge-fg-muted); }
.job-history__status--running { background: var(--badge-bg-running); color: var(--badge-fg-running); }
.job-history__status--completed { background: var(--badge-bg-success); color: var(--badge-fg-success); }
.job-history__status--partial { background: var(--badge-bg-warning); color: var(--badge-fg-warning); }
.job-history__status--stopped { background: var(--badge-bg-warning); color: var(--badge-fg-warning); }
.job-history__status--error { background: var(--badge-bg-error); color: var(--badge-fg-error); }
.job-history__row { cursor: pointer; transition: background 0.15s; }
.job-history__row:hover { background: var(--bg-hover-subtle); }
.job-history__row--selected { background: var(--bg-active-subtle); }

.job-history__th-checkbox, .job-history__cell-checkbox { width: 40px; text-align: center; }
.job-history__th-checkbox input[type="checkbox"], .job-history__cell-checkbox input[type="checkbox"] { width: 14px; height: 14px; cursor: pointer; }


/* Delete button */
.job-history__th-action, .job-history__cell-action { width: 50px; text-align: center; }


.job-history__delete-btn {
  background: none;
  border: 1px solid transparent;
  color: var(--fg-muted);
  font-size: 16px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.15s;
}


.job-history__delete-btn:hover {
  color: var(--color-error);
  background: var(--btn-danger-bg-light);
  border-color: var(--border-danger);
}


.job-history__delete-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

.job-history__delete-btn:disabled:hover {
  color: var(--fg-muted);
  background: none;
  border-color: transparent;
}


/* Dialog styles */
.job-history__dialog-overlay {
  position: fixed;
  inset: 0;
  background: var(--bg-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}


.job-history__dialog {
  background: var(--bg-card);
  border-radius: 12px;
  padding: 24px;
  max-width: 420px;
  width: 90%;
  box-shadow: var(--shadow-dialog);
}


.job-history__dialog-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--fg-on-card);
  margin: 0 0 16px 0;
}


.job-history__dialog-text {
  font-size: 14px;
  color: var(--fg-title);
  margin: 0 0 12px 0;
}


.job-history__dialog-list {
  font-size: 14px;
  color: var(--fg-on-card);
  margin: 0 0 16px 0;
  padding-left: 20px;
}


.job-history__dialog-list li {
  margin-bottom: 4px;
}


.job-history__dialog-warning {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-error);
  margin: 0 0 20px 0;
  padding: 10px;
  background: var(--btn-danger-bg-light);
  border-radius: 6px;
  border: 1px solid var(--border-danger);
}


.job-history__dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}


.job-history__dialog-btn {
  padding: 8px 16px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid var(--border);
  transition: all 0.15s;
}


.job-history__dialog-btn--cancel {
  background: var(--bg-card);
  color: var(--fg-on-card);
}


.job-history__dialog-btn--cancel:hover {
  background: var(--bg-hover-subtle);
}


.job-history__dialog-btn--danger {
  background: var(--btn-danger-bg);
  color: var(--btn-danger-fg);
  border-color: var(--btn-danger-border);
}


.job-history__dialog-btn--danger:hover {
  background: var(--btn-danger-hover);
}


/* Files preview & popover */
.job-history__cell-files {
  position: relative;
  max-width: 200px;
}


.job-history__files-preview {
  display: flex;
  align-items: center;
  gap: 6px;
}


.job-history__file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
}


.job-history__file-more {
  font-size: 11px;
  color: var(--fg-label);
  background: var(--bg-main);
  padding: 1px 6px;
  border-radius: 10px;
  white-space: nowrap;
}


.job-history__files-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 14px;
  padding: 2px;
  opacity: 0.6;
  transition: opacity 0.15s;
}


.job-history__files-btn:hover {
  opacity: 1;
}


.job-history__popover {
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 100;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border);
  border-radius: 8px;
  box-shadow: var(--shadow-modal);
  min-width: 200px;
  max-width: 300px;
  padding: 8px 0;
}


.job-history__popover-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--fg-label);
  padding: 4px 12px 8px;
  border-bottom: 1px solid var(--border);
}


.job-history__popover-list {
  list-style: none;
  margin: 0;
  padding: 4px 0;
  max-height: 200px;
  overflow-y: auto;
}


.job-history__popover-item {
  font-size: 13px;
  padding: 4px 12px;
  color: var(--fg-title);
  word-break: break-all;
}


.job-history__popover-item:hover {
  background: var(--bg-main);
}


/* Delete confirmation dialog */
.job-history__dialog-struck {
  text-decoration: line-through;
  opacity: 0.4;
}


.job-history__dialog-checkbox {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--fg-title);
  margin: 8px 0 16px;
  cursor: pointer;
}


.job-history__dialog-checkbox input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
}


</style>
