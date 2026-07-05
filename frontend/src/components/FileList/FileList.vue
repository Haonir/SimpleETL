<script setup lang="ts">
import { computed } from 'vue'
import { useFilesStore } from '@/stores/files'
import { useJobStore } from '@/stores/job'
import Button from '@/components/UI/Button.vue'
import Checkbox from '@/components/UI/Checkbox.vue'
import FileProgressBar from '@/components/Progress/FileProgressBar.vue'
import FileDropZone from '@/components/FileList/FileDropZone.vue'
import JobToolbar from '@/components/FileList/JobToolbar.vue'

const store = useFilesStore()
const jobStore = useJobStore()

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
    return new Date(iso).toLocaleString('ru-RU', {
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

function handleDelete(id: string) {
  const confirmed = window.confirm('Удалить этот файл?')
  if (!confirmed) return
  store.removeFile(id)
}

const allSelected = computed(() => store.files.length > 0 && store.selectedIds.length === store.files.length)
</script>

<template>
  <div class="file-list">
    <!-- Drop zone (always visible) -->
    <FileDropZone :disabled="jobStore.isRunning.value" />

    <!-- Job toolbar (Start, prompt, format, skip LLM) -->
    <JobToolbar />

    <!-- Empty state -->
    <div v-if="!store.hasFiles" class="file-list__empty">
      <p class="file-list__empty-text">Нет загруженных файлов</p>
      <p class="file-list__empty-hint">Перетащите файлы сюда или используйте зону загрузки</p>
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
          <th class="file-list__header-cell">Имя файла</th>
          <th class="file-list__header-cell file-list__header-cell--size">Размер</th>
          <th class="file-list__header-cell file-list__header-cell--date">Загружен</th>
          <th class="file-list__header-cell" />
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
          <td class="file-list__cell file-list__cell--name" :title="file.filename">{{ file.filename }}</td>
          <td class="file-list__cell file-list__cell--size">{{ formatSize(file.size_bytes) }}</td>
          <td class="file-list__cell file-list__cell--date">{{ formatDate(file.uploaded_at) }}</td>
          <td class="file-list__cell file-list__cell--actions">
            <Button variant="secondary" size="sm" @click="handleDelete(file.id)">Удалить</Button>
          </td>
        </tr>
        <tr v-if="jobStore.isRunning.value" class="file-list__progress-row">
          <td colspan="5">
            <FileProgressBar :fileIdx="fileIndex" :fileName="file.filename" />
          </td>
        </tr>
      </tbody>
    </table>

    <!-- Footer -->
    <div v-if="store.hasFiles" class="file-list__footer">
      <span>{{ store.selectedCount }} из {{ store.files.length }} выбрано</span>
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

/* Footer */
.file-list__footer {
  padding: 8px 16px;
  font-size: 12px;
  color: var(--fg-label);
  opacity: 0.7;
}
</style>
