<script setup lang="ts">
import { ref, computed } from 'vue'
import { useFilesStore } from '@/stores/files'
import { useJobStore } from '@/stores/job'
import Button from '@/components/UI/Button.vue'
import Checkbox from '@/components/UI/Checkbox.vue'
import FileProgressBar from '@/components/Progress/FileProgressBar.vue'
import FileDropZone from '@/components/FileList/FileDropZone.vue'
import JobToolbar from '@/components/FileList/JobToolbar.vue'
import GlobalProgressBar from '@/components/Progress/GlobalProgressBar.vue'

const store = useFilesStore()
const jobStore = useJobStore()

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
</script>

<template>
  <div class="file-list">
    <!-- Drop zone (always visible) -->
    <FileDropZone :disabled="jobStore.isRunning" />

    <!-- Job toolbar (Start, prompt, format, skip LLM) -->
    <JobToolbar />
    <GlobalProgressBar />

    <!-- Empty state -->
    <div v-if="!store.hasFiles" class="file-list__empty">
      <p class="file-list__empty-text">No files uploaded</p>
      <p class="file-list__empty-hint">Drag files here or use the upload zone</p>
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
          <th class="file-list__header-cell">Filename</th>
          <th class="file-list__header-cell file-list__header-cell--size">Size</th>
          <th class="file-list__header-cell file-list__header-cell--date">Uploaded</th>
          <th class="file-list__header-cell file-list__header-cell--actions">
            <Button variant="danger" size="sm" :disabled="store.selectedIds.length === 0" @click="confirmDeleteSelected">Delete Selected</Button>
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
            <FileProgressBar :fileIdx="fileIndex" :fileName="file.filename" />
          </td>
          <td class="file-list__cell file-list__cell--size">{{ formatSize(file.size_bytes) }}</td>
          <td class="file-list__cell file-list__cell--date">{{ formatDate(file.uploaded_at) }}</td>
          <td class="file-list__cell file-list__cell--actions">
            <Button variant="secondary" size="sm" @click="confirmDelete(file.id)">Delete</Button>
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Footer -->
    <div v-if="store.hasFiles" class="file-list__footer">
      <span>{{ store.selectedCount }} of {{ store.files.length }} selected</span>
    </div>

    <!-- Delete confirmation dialog -->
    <div v-if="showDeleteDialog" class="file-list__dialog-overlay" @click.self="cancelDelete">
      <div class="file-list__dialog">
        <h3 class="file-list__dialog-title">Confirm Deletion</h3>
        <p class="file-list__dialog-text">
          <template v-if="deleteMode === 'single'">
            Are you sure you want to delete this file?
          </template>
          <template v-else>
            Are you sure you want to delete {{ store.selectedIds.length }} selected file(s)?
          </template>
        </p>
        <p class="file-list__dialog-warning">
          ⚠️ This action cannot be undone!
        </p>
        <div class="file-list__dialog-actions">
          <button class="file-list__dialog-btn file-list__dialog-btn--cancel" @click="cancelDelete">Cancel</button>
          <button class="file-list__dialog-btn file-list__dialog-btn--danger" @click="handleDeleteConfirm">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.file-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-family: 'Segoe UI', system-ui, sans-serif;
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
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
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
  background-color: rgba(59, 130, 246, 0.04);
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
  background: rgba(0, 0, 0, 0.5);
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
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.file-list__dialog-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--fg-title, #111);
  margin: 0 0 16px 0;
}

.file-list__dialog-text {
  font-size: 14px;
  color: var(--fg-label, #666);
  margin: 0 0 16px 0;
}

.file-list__dialog-warning {
  font-size: 14px;
  font-weight: 600;
  color: #ef4444;
  margin: 0 0 20px 0;
  padding: 10px;
  background: #fef2f2;
  border-radius: 6px;
  border: 1px solid #fecaca;
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
  border: 1px solid var(--border, #ddd);
  transition: all 0.15s;
}

.file-list__dialog-btn--cancel {
  background: var(--bg-card, #fff);
  color: var(--fg-title, #111);
}

.file-list__dialog-btn--cancel:hover {
  background: var(--bg-main, #f5f5f5);
}

.file-list__dialog-btn--danger {
  background: #ef4444;
  color: white;
  border-color: #ef4444;
}

.file-list__dialog-btn--danger:hover {
  background: #dc2626;
}
</style>
