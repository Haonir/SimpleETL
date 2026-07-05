import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { WSConnection } from '@/services/websocket'
import type { WSServerMessage, LogEntry } from '@/types/ws'
import type { JobStatus } from '@/types/job'
const JOB_STORAGE_KEY = 'simpleetl_current_job_id'

import { createJob as apiCreateJob, getJobs as apiGetJobs, getJobFiles as apiGetJobFiles, stopJob as stopJobApi } from '@/services/api'
import type { JobCreateRequest, JobItem, JobFileItem, JobResponse } from '@/types/job'

export const useJobStore = defineStore('job', () => {
  const currentJobId = ref<string | null>(null)
  const status = ref<JobStatus | null>(null)
  const progress = ref<Record<number, number>>({})
  const globalProgress = ref(0)
  const logs = ref<LogEntry[]>([])
  const ws = ref<WSConnection | null>(null)

  // ── REST API state ───────────────────────────────────────────────────────
  const jobs = ref<JobItem[]>([])
  const currentJobFiles = ref<JobFileItem[]>([])

  const isRunning = computed(() => status.value === 'running')
  const isCompleted = computed(() => status.value === 'completed')

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
    const response = await apiGetJobFiles(jobId)
    currentJobFiles.value = response.files
  }

  // ── WebSocket actions (existing) ──────────────────────────────────────────

  function startJob(jobId: string) {
    currentJobId.value = jobId
    status.value = 'queued'
    progress.value = {}
    globalProgress.value = 0
    logs.value = []
    localStorage.setItem(JOB_STORAGE_KEY, jobId)
    connectWS(jobId)
  }

  async function stopJob() {
    if (currentJobId.value) {
      try {
        await stopJobApi(currentJobId.value)
      } catch {
        // Ignore REST errors — WS stop signal is still sent below
      }
    }
    if (ws.value && ws.value.isConnected) {
      ws.value.send({ type: 'stop', job_id: currentJobId.value! })
    }
    disconnectWS()
    status.value = 'stopped'
    localStorage.removeItem(JOB_STORAGE_KEY)
  }

  async function restoreJob(): Promise<void> {
    const savedJobId = localStorage.getItem(JOB_STORAGE_KEY)
    if (!savedJobId) return

    try {
      const response = await apiGetJob(savedJobId)
      const job = response.job

      currentJobId.value = job.id
      status.value = job.status

      if (job.status === 'running' || job.status === 'pending') {
        // Job still running — reconnect WebSocket
        connectWS(job.id)
      } else {
        // Job finished — clean up localStorage
        localStorage.removeItem(JOB_STORAGE_KEY)
      }
    } catch {
      // Job not found (404) or API error — clean up
      localStorage.removeItem(JOB_STORAGE_KEY)
    }
  }

  function connectWS(jobId: string) {
    ws.value = new WSConnection()
    ws.value.connect(jobId, handleMessage, undefined, () => {
      // On close: do NOT auto-reconnect — job may no longer exist
      ws.value?.clearReconnectState()
    })
  }

  function disconnectWS() {
    ws.value?.disconnect()
    ws.value = null
  }

  function handleMessage(msg: WSServerMessage) {
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
        break
      case 'done':
        status.value = 'completed'
        globalProgress.value = 100
        localStorage.removeItem(JOB_STORAGE_KEY)
        break
      case 'error':
        status.value = 'error'
        addLog({ timestamp: new Date().toISOString(), level: 'error', message: msg.message })
        localStorage.removeItem(JOB_STORAGE_KEY)
        break
    }
  }

  function addLog(entry: LogEntry) {
    logs.value.push(entry)
  }

  return {
    currentJobId, status, progress, globalProgress, logs,
    jobs, currentJobFiles,
    isRunning, isCompleted,
    startJob, stopJob, restoreJob, connectWS, disconnectWS, addLog,
    createAndStartJob, fetchJobs, fetchJobFiles,
  }
})
