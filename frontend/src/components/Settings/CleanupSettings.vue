<script setup lang="ts">
import { ref, watch } from 'vue'
import type { CleanupConfig } from '@/types/config'

const props = defineProps<{ modelValue: CleanupConfig }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: CleanupConfig): void }>()

const enabled = ref(props.modelValue.enabled)
const maxAgeHours = ref(props.modelValue.max_age_hours)

watch(enabled, (val) => {
  emit('update:modelValue', { ...props.modelValue, enabled: val })
})

watch(maxAgeHours, (val) => {
  emit('update:modelValue', { ...props.modelValue, max_age_hours: val })
})
</script>

<template>
  <div class="cleanup-settings">
    <!-- Toggle -->
    <label class="toggle-label">
      <input type="checkbox" v-model="enabled" />
      <span class="toggle-text">Auto-cleanup old jobs</span>
    </label>

    <!-- Max age input (shown when enabled) -->
    <div v-if="enabled" class="max-age-group">
      <label for="cleanup-max-age-hours" class="field-label">Max age (hours)</label>
      <input
        id="cleanup-max-age-hours"
        type="number"
        min="1"
        max="720"
        :value="maxAgeHours"
        @input="maxAgeHours = Number((($event.target as HTMLInputElement).value) || 24)"
      />
      <span class="field-hint">Range: 1–720 hours. Default: 24</span>
    </div>

    <!-- Run button -->
    <button type="button" class="btn btn--secondary btn--sm" @click="$emit('run-cleanup')">
      Run Cleanup Now
    </button>
  </div>
</template>

<style scoped>
.cleanup-settings {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.toggle-label {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 13px;
  color: var(--fg-title);
}

.toggle-text {
  user-select: none;
}

.max-age-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field-label {
  font-size: 12px;
  color: var(--fg-label);
  font-weight: 500;
}

#cleanup-max-age-hours {
  height: 30px;
  padding: 0 8px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg-main);
  color: var(--fg-title);
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 13px;
}

.field-hint {
  font-size: 11px;
  color: var(--fg-label);
  opacity: 0.7;
}

.btn--sm {
  height: 28px;
  padding: 0 12px;
  font-size: 11px;
}
</style>
