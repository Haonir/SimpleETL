<script setup lang="ts">
import { onMounted } from 'vue'
import { useJobStore } from '@/stores/job'

const jobStore = useJobStore()

onMounted(() => { jobStore.fetchJobs() })

function formatDate(iso: string | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('ru-RU', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function statusClass(status: string): string {
  return `job-history__status--${status}`
}
</script>

<template>
  <div class="job-history">
    <h2 class="job-history__title">Job History</h2>

    <div v-if="jobStore.jobs.length === 0" class="job-history__empty">
      <p>No jobs yet.</p>
    </div>

    <table v-else class="job-history__table">
      <thead>
        <tr>
          <th>ID</th>
          <th>Status</th>
          <th>Files</th>
          <th>Created</th>
          <th>Completed</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="job in jobStore.jobs" :key="job.id" class="job-history__row" :class="{ 'job-history__row--selected': jobStore.selectedJobId === job.id }" @click="jobStore.selectJob(job.id)">
          <td class="job-history__cell-id">#{{ job.id.slice(0, 8) }}</td>
          <td>
            <span :class="['job-history__status', statusClass(job.status)]">{{ job.status }}</span>
          </td>
          <td>{{ job.file_count }}</td>
          <td>{{ formatDate(job.created_at) }}</td>
          <td>{{ formatDate(job.completed_at) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.job-history__title { font-size: 16px; font-weight: 600; color: var(--fg-title); margin: 0 0 1rem; }
.job-history__empty { padding: 2rem; text-align: center; color: var(--fg-label); }
.job-history__table { width: 100%; border-collapse: collapse; background: var(--bg-card); border-radius: 8px; overflow: hidden; }
.job-history__table th { padding: 10px 16px; text-align: left; font-size: 12px; font-weight: 600; color: var(--fg-header); border-bottom: 1px solid var(--border); background: var(--bg-main); }
.job-history__table td { padding: 10px 16px; font-size: 13px; border-bottom: 1px solid var(--border); }
.job-history__cell-id { font-family: monospace; font-size: 12px; }
.job-history__status { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 11px; font-weight: 500; }
.job-history__status--pending { background: #e5e7eb; color: #6b7280; }
.job-history__status--running { background: #dbeafe; color: #1d4ed8; }
.job-history__status--completed { background: #dcfce7; color: #166534; }
.job-history__status--stopped { background: #fef3c7; color: #92400e; }
.job-history__status--error { background: #fee2e2; color: #991b1b; }
.job-history__row { cursor: pointer; transition: background 0.15s; }
.job-history__row:hover { background: rgba(59, 130, 246, 0.05); }
.job-history__row--selected { background: rgba(59, 130, 246, 0.1); }
</style>
