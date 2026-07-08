<script setup lang="ts">
interface Props {
  value?: number
  color?: string
  height?: number
  indeterminate?: boolean
}

withDefaults(defineProps<Props>(), {
  value: 0,
  color: 'var(--accent)',
  height: 8,
  indeterminate: false,
})
</script>

<template>
  <div class="progress-track" :style="{ height: height + 'px' }">
    <div
      v-if="!indeterminate"
      class="progress-fill"
      :style="{ width: Math.min(100, Math.max(0, value)) + '%', background: color }"
    />
    <div v-else class="progress-fill progress-fill--indeterminate" :style="{ background: color }" />
  </div>
</template>

<style scoped>
.progress-track {
  width: 100%;
  background: var(--btn-bg);
  border-radius: 4px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}
.progress-fill--indeterminate {
  width: 40%;
  animation: indeterminate 1.5s ease-in-out infinite;
}
@keyframes indeterminate {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(350%); }
}
</style>
