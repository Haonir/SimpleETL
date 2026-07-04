<script setup lang="ts">
import { ref, computed } from 'vue'
import { useFilesStore } from '@/stores/files'
import { useUiStore } from '@/stores/ui'
import Button from '@/components/UI/Button.vue'

const filesStore = useFilesStore()
const uiStore = useUiStore()

const ALLOWED_EXTENSIONS = ['.txt', '.md', '.docx', '.doc', '.pdf'] as const
type AllowedExtension = (typeof ALLOWED_EXTENSIONS)[number]

interface Props {
  /** Whether the drop zone is disabled. */
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
})

const fileInput = ref<HTMLInputElement | null>(null)
const dragOver = ref(false)

const hasPdf = computed(() => filesStore.hasPdf)

function isAllowed(file: File): boolean {
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  return ALLOWED_EXTENSIONS.includes(ext as AllowedExtension)
}

function handleDragOver(e: DragEvent) {
  e.preventDefault()
  if (props.disabled) return
  dragOver.value = true
}

function handleDragLeave(e: DragEvent) {
  e.preventDefault()
  dragOver.value = false
}

async function handleDrop(e: DragEvent) {
  e.preventDefault()
  dragOver.value = false
  if (props.disabled || !e.dataTransfer?.files.length) return

  const droppedFiles = Array.from(e.dataTransfer.files).filter(isAllowed)
  await uploadFiles(droppedFiles)
}

function handleBrowse() {
  fileInput.value?.click()
}

async function uploadFiles(fileList: File[]) {
  if (fileList.length === 0) return

  filesStore.uploading = true
  try {
    await filesStore.upload(fileList)
    // refresh store after upload completes
    await filesStore.fetchFiles()
  } catch (err) {
    uiStore.showNotification('error', `Upload failed: ${err instanceof Error ? err.message : String(err)}`)
  } finally {
    filesStore.uploading = false
  }
}

function handleFileSelected(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return
  const selectedFilesList = Array.from(input.files).filter(isAllowed)
  uploadFiles(selectedFilesList)
}
</script>

<template>
  <div class="file-drop-zone">
    <!-- Drop zone area -->
    <div
      :class="[
        'drop-area',
        { 'drag-over': dragOver },
        { 'disabled': disabled },
      ]"
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
    >
      <div class="drop-area__content">
        <svg class="drop-area__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="17 8 12 3 7 8" />
          <line x1="12" y1="3" x2="12" y2="15" />
        </svg>
        <p class="drop-area__text">Drag files here or</p>
      </div>

      <!-- Browse button -->
      <Button variant="primary" size="sm" @click="handleBrowse">
        Browse
      </Button>

      <!-- Hidden file input -->
      <input
        ref="fileInput"
        type="file"
        class="drop-area__input"
        accept=".txt,.md,.docx,.doc,.pdf"
        multiple
        @change="handleFileSelected"
      />
    </div>

    <!-- PDF warning hint -->
    <p v-if="hasPdf && !disabled" class="drop-area__warning">
      PDF OCR requires Tesseract-OCR installed on the system
    </p>
  </div>
</template>

<style scoped>
.file-drop-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
}

.drop-area {
  width: 100%;
  min-height: 120px;
  border: 2px dashed var(--border);
  border-radius: 8px;
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  transition: border-color 0.2s, background-color 0.2s;
}

.drop-area.drag-over {
  border-color: var(--accent);
  background-color: color-mix(in srgb, var(--accent) 8%, transparent);
}

.drop-area.disabled {
  opacity: 0.6;
  pointer-events: none;
}

.drop-area__content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.drop-area__icon {
  width: 48px;
  height: 48px;
  color: var(--fg-label);
}

.drop-area__text {
  font-size: 14px;
  color: var(--fg-label);
  margin: 0;
}

.drop-area__input {
  display: none;
}

.drop-area__warning {
  font-size: 12px;
  color: #d97706;
  text-align: center;
  max-width: 400px;
}
</style>
