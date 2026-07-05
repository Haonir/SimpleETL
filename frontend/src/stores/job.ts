import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { WSConnection } from '@/services/websocket'
import type { WSServerMessage, LogEntry } from '@/types/ws'
import type { JobStatus } from '@/types/job'
import { createJob as apiCreateJob, getJobs as apiGetJobs, getJobFiles as apiGetJobFiles, stopJob as stopJobApi } from '@/services/api'
import type { JobCreateRequest, JobItem, JobFileItem } from '@/types/job'

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
        break
      case 'error':
        status.value = 'error'
        addLog({ timestamp: new Date().toISOString(), level: 'error', message: msg.message })
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
    startJob, stopJob, connectWS, disconnectWS, addLog,
    createAndStartJob, fetchJobs, fetchJobFiles,
  }
})
