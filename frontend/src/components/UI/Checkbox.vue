<script setup lang="ts">
interface Props {
  modelValue: boolean
  label?: string
  disabled?: boolean
}

withDefaults(defineProps<Props>(), {
  label: '',
  disabled: false,
})

defineEmits<{
  'update:modelValue': [value: boolean]
}>()
</script>

<template>
  <label class="checkbox" :class="{ 'checkbox--disabled': disabled }">
    <input
      type="checkbox"
      :checked="modelValue"
      :disabled="disabled"
      class="checkbox__input"
      @change="$emit('update:modelValue', ($event.target as HTMLInputElement).checked)"
    />
    <span class="checkbox__box" />
    <span v-if="label" class="checkbox__label">{{ label }}</span>
  </label>
</template>

<style scoped>
.checkbox {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 12px;
  color: var(--fg-title);
  user-select: none;
}
.checkbox--disabled { opacity: 0.5; cursor: not-allowed; }
.checkbox__input {
  position: absolute;
  opacity: 0;
  width: 0; height: 0;
}
.checkbox__box {
  width: 16px; height: 16px;
  border: 1px solid var(--border);
  border-radius: 4px;
  background: var(--bg-input);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.15s, border-color 0.15s;
  flex-shrink: 0;
}
.checkbox__input:checked + .checkbox__box {
  background: var(--accent);
  border-color: var(--accent);
}
.checkbox__input:checked + .checkbox__box::after {
  content: '';
  width: 4px; height: 8px;
  border: solid white;
  border-width: 0 2px 2px 0;
  transform: rotate(45deg);
  margin-bottom: 2px;
}
.checkbox__input:focus + .checkbox__box {
  box-shadow: 0 0 0 2px var(--accent-disabled);
}
.checkbox__label { line-height: 1; }
</style>
