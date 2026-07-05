import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { WSConnection } from '@/services/websocket'
import type { WSServerMessage, LogEntry } from '@/types/ws'
import type { JobStatus } from '@/types/job'
const JOB_STORAGE_KEY = 'simpleetl_current_job_id'

import { createJob as apiCreateJob, getJobs as apiGetJobs, getJobFiles as apiGetJobFiles, stopJob as stopJobApi, getJob as apiGetJob, getJobLogs as apiGetJobLogs, getJobOutputs as apiGetJobOutputs } from '@/services/api'
import type { JobCreateRequest, JobItem, JobFileItem, JobResponse } from '@/types/job'

export const useJobStore = defineStore('job', () => {
  const currentJobId = ref<string | null>(null)
  const status = ref<JobStatus | null>(null)
  const progress = ref<Record<number, number>>({})
  const globalProgress = ref(0)
  const logs = ref<LogEntry[]>([])
  const ws = ref<WSConnection | null>(null)
  const stopRequested = ref(false)

  // ── REST API state ───────────────────────────────────────────────────────
  const jobs = ref<JobItem[]>([])
  const currentJobFiles = ref<JobFileItem[]>([])

  const isRunning = computed(() => status.value === 'running')
  const isCompleted = computed(() => status.value === 'completed')
  const isActive = computed(
    () => status.value === 'running' || status.value === 'queued' || status.value === 'pending',
  )

  // ── REST API actions ──────────────────────────────────────────────────────

  async function createAndStartJob(fileIds: string[], config: Record<string, unknown>): Promise<string> {
    const response = await apiCreateJob({ file_ids: fileIds, config })
    startJob(response.job.id)
    return response.job.id
  }

  async function fetchJobs(): Promise<void> {
    const response = await apiGetJobs()
    jobs.value = response.jobs
  }

  async function fetchJobFiles(jobId: string): Promise<void> {
    const response = await apiGetJobOutputs(jobId)
    currentJobFiles.value = response.outputs.map((o) => ({
      filename: o.filename,
      path: o.file_path,
      size_bytes: o.size_bytes,
    }))
  }

  // ── WebSocket actions (existing) ──────────────────────────────────────────

  function startJob(jobId: string) {
    currentJobId.value = jobId
    status.value = 'queued'
    progress.value = {}
    globalProgress.value = 0
    logs.value = []
    stopRequested.value = false
    localStorage.setItem(JOB_STORAGE_KEY, jobId)
    connectWS(jobId)
  }

  async function stopJob() {
    stopRequested.value = true
    addLog({ timestamp: new Date().toISOString(), level: 'info', message: 'User requested stop' })
    if (currentJobId.value) {
      try {
        await stopJobApi(currentJobId.value)
      } catch {
        // Ignore REST errors
      }
    }
    // Keep JOB_STORAGE_KEY so restoreJob() can restore logs/outputs on refresh
  }

  async function restoreJob(): Promise<void> {
    const savedJobId = localStorage.getItem(JOB_STORAGE_KEY)
    if (!savedJobId) return

    try {
      const response = await apiGetJob(savedJobId)
      const job = response.job

      currentJobId.value = job.id
      status.value = job.status

      // Restore logs
      try {
        const logsResp = await apiGetJobLogs(savedJobId)
        logs.value = logsResp.logs.map((l) => ({
          timestamp: l.timestamp,
          level: l.level,
          message: l.message,
        }))
      } catch {
        // Logs not available yet
      }

      // Restore output files
      try {
        const outputsResp = await apiGetJobOutputs(savedJobId)
        currentJobFiles.value = outputsResp.outputs.map((o) => ({
          filename: o.filename,
          path: o.file_path,
          size_bytes: o.size_bytes,
        }))
      } catch {
        // Outputs not available yet
      }

      if (job.status === 'running' || job.status === 'pending') {
        // Job still running — reconnect WebSocket
        connectWS(job.id)
      }
      // Finished job: keep in localStorage so logs/outputs persist across refreshes
    } catch {
      // Backend unreachable or job not found — keep localStorage so data restores when backend is back
    }
  }

  function connectWS(jobId: string) {
    ws.value = new WSConnection()
    ws.value.connect(jobId, handleMessage, undefined, undefined)
  }

  function disconnectWS() {
    ws.value?.disconnect()
    ws.value = null
  }

  function handleMessage(msg: WSServerMessage) {
    console.log('[JobStore] handleMessage:', msg.type, msg)
    switch (msg.type) {
      case 'progress':
        progress.value[msg.file_idx] = msg.chunk_pct
        globalProgress.value = msg.global_pct
        break
      case 'log':
        addLog({ timestamp: new Date().toISOString(), level: msg.level, message: msg.message })
        break
      case 'status':
        status.value = msg.status
        if (msg.status === 'stopped' || msg.status === 'completed' || msg.status === 'error') {
          stopRequested.value = false
        }
        break
      case 'done':
        status.value = 'completed'
        globalProgress.value = 100
        stopRequested.value = false
        // Keep JOB_STORAGE_KEY so restoreJob() can restore logs/outputs on refresh
        break
      case 'error':
        status.value = 'error'
        addLog({ timestamp: new Date().toISOString(), level: 'error', message: msg.message })
        stopRequested.value = false
        // Keep JOB_STORAGE_KEY so restoreJob() can restore logs/outputs on refresh
        break
    }
  }

  function addLog(entry: LogEntry) {
    logs.value.push(entry)
  }

  return {
    currentJobId, status, progress, globalProgress, logs, stopRequested,
    jobs, currentJobFiles,
    isRunning, isCompleted, isActive,
    startJob, stopJob, restoreJob, connectWS, disconnectWS, addLog,
    createAndStartJob, fetchJobs, fetchJobFiles,
  }
})
