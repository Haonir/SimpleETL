<script setup lang="ts">
interface Option {
  value: string
  label: string
}

interface Props {
  modelValue: string
  options: Option[]
  disabled?: boolean
}

withDefaults(defineProps<Props>(), {
  disabled: false,
})

defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<template>
  <div class="select-wrapper">
    <select
      :value="modelValue"
      :disabled="disabled"
      class="select"
      @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
    >
      <option v-for="opt in options" :key="opt.value" :value="opt.value">
        {{ opt.label }}
      </option>
    </select>
    <span class="select__arrow" />
  </div>
</template>

<style scoped>
.select-wrapper {
  position: relative;
  display: inline-flex;
}
.select {
  appearance: none;
  height: 34px;
  padding: 0 30px 0 10px;
  background: var(--bg-input);
  border: 1px solid var(--border);
  border-radius: 6px;
  font-family: 'Segoe UI', system-ui, sans-serif;
  font-size: 12px;
  color: var(--fg-title);
  cursor: pointer;
  outline: none;
  transition: border-color 0.15s;
}
.select:focus { border-color: var(--accent); }
.select:disabled { opacity: 0.5; cursor: not-allowed; }
.select__arrow {
  position: absolute;
  right: 10px;
  top: 50%;
  transform: translateY(-50%);
  width: 0; height: 0;
  border-left: 4px solid transparent;
  border-right: 4px solid transparent;
  border-top: 5px solid var(--fg-label);
  pointer-events: none;
}
</style>
