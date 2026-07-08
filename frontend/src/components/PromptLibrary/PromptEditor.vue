<script setup lang="ts">
import { ref, watch } from 'vue'
import type { PromptEntry } from '@/types/config'
import Modal from '@/components/UI/Modal.vue'
import Input from '@/components/UI/Input.vue'
import Button from '@/components/UI/Button.vue'

interface Props {
  show: boolean
  prompt: PromptEntry | null
}

const props = withDefaults(defineProps<Props>(), {})

const emit = defineEmits<{
  save: [payload: { name: string; text: string }]
  cancel: []
}>()

const name = ref(props.prompt?.name || '')
const text = ref(props.prompt?.text || '')
const isEditing = !!props.prompt

watch(() => props.show, (visible) => {
  if (!visible) {
    emit('cancel')
  }
})

function handleSave() {
  const trimmedName = name.value.trim()
  const trimmedText = text.value.trim()
  if (!trimmedName || !trimmedText) return
  emit('save', { name: trimmedName, text: trimmedText })
}

function handleCancel() {
  emit('cancel')
}
</script>

<template>
  <Modal :show="show" :title="$t('promptEditor.title')" @close="handleCancel">
    <div class="prompt-editor">
      <label class="field-label">{{ $t('promptEditor.name') }}</label>
      <Input
        v-model="name"
        type="text"
        :placeholder="$t('promptEditor.namePlaceholder')"
        :disabled="isEditing"
      />

      <label class="field-label">{{ $t('promptEditor.text') }}</label>
      <textarea
        v-model="text"
        rows="6"
        class="prompt-textarea"
        :placeholder="$t('promptEditor.textPlaceholder')"
      />
    </div>

    <template #footer>
      <Button variant="secondary" size="sm" @click="handleCancel">{{ $t('common.cancel') }}</Button>
      <Button variant="primary" size="sm" @click="handleSave">{{ $t('common.save') }}</Button>
    </template>
  </Modal>
</template>

<style scoped>
.prompt-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--fg-label);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.prompt-textarea {
  width: 100%;
  min-height: 120px;
  padding: 8px 10px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 12px;
  color: var(--fg-title);
  resize: vertical;
  outline: none;
  transition: border-color 0.15s;
}

.prompt-textarea:focus {
  border-color: var(--accent);
}
</style>
