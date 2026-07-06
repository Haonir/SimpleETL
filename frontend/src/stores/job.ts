import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { WSConnection } from '@/services/websocket'
import type { WSServerMessage, LogEntry } from '@/types/ws'
import type { JobStatus } from '@/types/job'
const JOB_STORAGE_KEY = 'simpleetl_current_job_id'

import { useFilesStore } from '@/stores/files'
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

  // ── Selected job from history ─────────────────────────────────────────────
  const selectedJobId = ref<string | null>(null)
  const selectedJobLogs = ref<LogEntry[]>([])

  const isRunning = computed(() => status.value === 'running')
  const isCompleted = computed(() => status.value === 'completed')
  const isActive = computed(
    () => status.value === 'running' || status.value === 'queued' || status.value === 'pending',
  )

  // ── Active view (current job or selected history job) ──────────────────────
  const activeLogs = computed(() => selectedJobId.value ? selectedJobLogs.value : logs.value)
  const activeFiles = computed(() => currentJobFiles.value)

  // ── Active job (selected from history or currently running) ───────────────
  const activeJobId = computed(() => selectedJobId.value || currentJobId.value)
  const activeJobFileIds = computed(() => {
    const id = activeJobId.value
    if (!id) return []
    // If it's the current running job, use stored file IDs
    if (id === currentJobId.value && currentJobFileIds.value.length > 0) return currentJobFileIds.value
    // Otherwise look up from jobs list
    const job = jobs.value.find(j => j.id === id)
    return job?.file_ids ?? []
  })
  const activeStatus = computed(() => {
    const id = activeJobId.value
    if (!id) return null
    if (id === currentJobId.value) return status.value
    const job = jobs.value.find(j => j.id === id)
    return job?.status ?? null
  })
  const activeProgress = computed(() => {
    const id = activeJobId.value
    if (!id) return 0
    if (id === currentJobId.value) return globalProgress.value
    const job = jobs.value.find(j => j.id === id)
    if (job?.status === 'completed') return 100
    return 0
  })

  const currentJobFileIds = ref<string[]>([])

  // ── REST API state ───────────────────────────────────────────────────────

  // ── REST API actions ──────────────────────────────────────────────────────

  async function createAndStartJob(fileIds: string[], config: Record<string, unknown>): Promise<string> {
    const response = await apiCreateJob({ file_ids: fileIds, config })
    startJob(response.job.id, fileIds)
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

  async function selectJob(jobId: string): Promise<void> {
    selectedJobId.value = jobId
    localStorage.setItem(JOB_STORAGE_KEY, jobId)
    // If selected job is running, connect to its WS
    disconnectWS()
    const selectedJob = jobs.value.find(j => j.id === jobId)
    if (selectedJob?.status === 'running' || selectedJob?.status === 'pending') {
      currentJobId.value = jobId
      connectWS(jobId)
    }
    // Set progress for completed jobs — map file_ids to store.files indices
    const job = jobs.value.find(j => j.id === jobId)
    if (job?.status === 'completed') {
      globalProgress.value = 100
      const prog: Record<number, number> = {}
      const filesStore = useFilesStore()
      job.file_ids?.forEach((fileId) => {
        const storeIdx = filesStore.files.findIndex(f => f.id === fileId)
        if (storeIdx !== -1) prog[storeIdx] = 100
      })
      progress.value = prog
    }
    // Fetch logs
    try {
      const logsResp = await apiGetJobLogs(jobId)
      selectedJobLogs.value = logsResp.logs.map((l) => ({
        timestamp: l.timestamp,
        level: l.level,
        message: l.message,
      }))
    } catch {
      selectedJobLogs.value = []
    }
    // Fetch outputs
    try {
      const outputsResp = await apiGetJobOutputs(jobId)
      currentJobFiles.value = outputsResp.outputs.map((o) => ({
        filename: o.filename,
        path: o.file_path,
        size_bytes: o.size_bytes,
      }))
    } catch {
      currentJobFiles.value = []
    }
  }

  async function deleteJob(jobId: string, keepSourceFiles: boolean = true): Promise<void> {
    await stopJobApi(jobId, !keepSourceFiles)
    // Remove from local list
    jobs.value = jobs.value.filter((j) => j.id !== jobId)
    // Clear selection if deleted job was selected
    if (selectedJobId.value === jobId) {
      selectedJobId.value = null
      selectedJobLogs.value = []
      currentJobFiles.value = []
    }
    // Refresh files list if source files were deleted
    if (!keepSourceFiles) {
      const filesStore = useFilesStore()
      await filesStore.fetchFiles()
    }
  }

  function clearSelection(): void {
    selectedJobId.value = null
    selectedJobLogs.value = []
  }

  // ── WebSocket actions (existing) ──────────────────────────────────────────

  function startJob(jobId: string, fileIds: string[] = []) {
    disconnectWS()  // Disconnect previous job's WS
    currentJobId.value = jobId
    currentJobFileIds.value = fileIds
    selectedJobId.value = null  // Clear history selection
    selectedJobLogs.value = []  // Clear history logs
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
    // Always fetch jobs list first
    await fetchJobs()

    const savedJobId = localStorage.getItem(JOB_STORAGE_KEY)
    if (savedJobId) {
      try {
        const response = await apiGetJob(savedJobId)
        const job = response.job

        currentJobId.value = job.id
        status.value = job.status
        currentJobFileIds.value = job.file_ids ?? []

        // Restore progress for completed jobs — map file_ids to store.files indices
        if (job.status === 'completed') {
          globalProgress.value = 100
          const prog: Record<number, number> = {}
          const filesStore = useFilesStore()
          job.file_ids?.forEach((fileId) => {
            const storeIdx = filesStore.files.findIndex(f => f.id === fileId)
            if (storeIdx !== -1) prog[storeIdx] = 100
          })
          progress.value = prog
        }

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
        return
      } catch {
        // Job not found — fall through to auto-select
      }
    }

    // No saved job or saved job not found — auto-select the most recent job
    if (jobs.value.length > 0) {
      const latestJob = jobs.value[0] // Already sorted by created_at DESC
      await selectJob(latestJob.id)
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
    // Only process messages for the currently tracked job
    if (msg.job_id !== currentJobId.value) return
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
    jobs, currentJobFiles, selectedJobId, selectedJobLogs, activeLogs, activeFiles,
    activeJobId, activeJobFileIds, activeStatus, activeProgress, currentJobFileIds,
    selectJob, clearSelection,
    isRunning, isCompleted, isActive,
    startJob, stopJob, restoreJob, connectWS, disconnectWS, addLog,
    createAndStartJob, fetchJobs, fetchJobFiles, deleteJob,
  }
})
