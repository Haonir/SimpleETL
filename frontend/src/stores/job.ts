import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { WSConnection } from '@/services/websocket'
import type { WSServerMessage, LogEntry } from '@/types/ws'
import type { JobStatus } from '@/types/job'
const JOB_STORAGE_KEY = 'simpleetl_current_job_id'

interface JobItem { id: string; status: string; file_ids: string[]; config?: Record<string, unknown>; [key: string]: any }
interface JobFileItem { filename: string; [key: string]: any }

import { logger } from '@/utils/logger'
import { loadJobProgress, saveJobProgress as saveProgress, clearJobProgress as clearProgress } from '@/utils/progressCache'
import { useFilesStore } from '@/stores/files'
import { createJob as apiCreateJob, getJobs as apiGetJobs, stopJob as stopJobApi, getJob as apiGetJob, getJobLogs as apiGetJobLogs, getJobOutputs as apiGetJobOutputs } from '@/services/api'
import { useConfigStore } from '@/stores/config'

export const useJobStore = defineStore('job', () => {
  const currentJobId = ref<string | null>(null)
  const status = ref<JobStatus | null>(null)
  const stopRequested = ref(false)

  // Per-job state — stores progress/logs/WS for ALL running jobs simultaneously
  const jobProgress = ref<Record<string, Record<string, number>>>({})
  const jobGlobalProgress = ref<Record<string, number>>({})
  const jobLogs = ref<Record<string, LogEntry[]>>({})
  const wsConnections = ref<Record<string, WSConnection>>({})

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
  const activeLogs = computed(() => {
    const id = activeJobId.value
    if (!id) return []
    return jobLogs.value[id] ?? []
  })
  const activeFiles = computed(() => currentJobFiles.value)

  // ── Active job (selected from history or currently running) ───────────────
  const activeJobId = computed(() => selectedJobId.value || currentJobId.value)
  const activeJobFileIds = computed(() => {
    const id = activeJobId.value
    if (!id) return []
    return getJobFileIds(id)
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
    const job = jobs.value.find(j => j.id === id)
    if (job?.status === 'completed') return 100
    return jobGlobalProgress.value[id] ?? 0
  })

  const progress = computed(() => {
    const id = activeJobId.value
    if (!id) return {}
    const job = jobs.value.find(j => j.id === id)
    if (job?.status === 'completed') {
      const prog: Record<string, number> = {}
      job.file_ids?.forEach((fid: string) => { prog[fid] = 100 })
      return prog
    }
    return jobProgress.value[id] ?? {}
  })

  const globalProgress = computed(() => {
    const id = activeJobId.value
    if (!id) return 0
    const job = jobs.value.find(j => j.id === id)
    if (job?.status === 'completed') return 100
    return jobGlobalProgress.value[id] ?? 0
  })

  const logs = computed(() => {
    const id = activeJobId.value
    if (!id) return []
    return jobLogs.value[id] ?? []
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

    const selectedJob = jobs.value.find(j => j.id === jobId)
    if (!selectedJob) return

    if (selectedJob.status === 'running' || selectedJob.status === 'pending') {
      currentJobId.value = jobId
      currentJobFileIds.value = selectedJob.file_ids ?? []
      status.value = selectedJob.status
      connectJobWS(jobId)
    }

    // Fetch logs and outputs for the selected job
    try {
      const logsResp = await apiGetJobLogs(jobId)
      jobLogs.value[jobId] = logsResp.logs.map((l) => ({
        timestamp: l.timestamp,
        level: l.level as 'error' | 'info' | 'warning' | 'llm',
        message: l.message,
      }))
    } catch (err) {
      logger.warn('[JobStore] Failed to fetch logs for job', jobId, err)
      jobLogs.value[jobId] = []
    }
    try {
      const outputsResp = await apiGetJobOutputs(jobId)
      currentJobFiles.value = outputsResp.outputs.map((o) => ({
        filename: o.filename,
        path: o.file_path,
        size_bytes: o.size_bytes,
      }))
    } catch (err) {
      logger.warn('[JobStore] Failed to fetch outputs for job', jobId, err)
      currentJobFiles.value = []
    }
  }

  async function deleteJob(jobId: string, keepSourceFiles: boolean = true): Promise<boolean> {
    try {
      await stopJobApi(jobId, !keepSourceFiles)
    } catch (err) {
      logger.error('[JobStore] Failed to delete job', jobId, err)
      return false
    }
    disconnectJobWS(jobId)
    // Clean up per-job data
    delete jobProgress.value[jobId]
    delete jobGlobalProgress.value[jobId]
    delete jobLogs.value[jobId]
    clearProgress(jobId)
    // Remove from local list
    jobs.value = jobs.value.filter((j) => j.id !== jobId)
    // Clear selection if deleted job was selected
    if (selectedJobId.value === jobId) {
      selectedJobId.value = null
      selectedJobLogs.value = []
      currentJobFiles.value = []
    }
    // Clear current job if it was the deleted one
    if (currentJobId.value === jobId) {
      currentJobId.value = null
      status.value = null
      currentJobFileIds.value = []
      localStorage.removeItem(JOB_STORAGE_KEY)
    }
    currentJobFiles.value = []
    // Refresh files list if source files were deleted
    if (!keepSourceFiles) {
      const filesStore = useFilesStore()
      await filesStore.fetchFiles()
    }
    return true
  }

  function clearActiveJob(): void {
    disconnectAllWS()
    currentJobId.value = null
    selectedJobId.value = null
    selectedJobLogs.value = []
    currentJobFiles.value = []
    currentJobFileIds.value = []
    status.value = null
    stopRequested.value = false
    // Clear all cached progress from localStorage (before resetting in-memory)
    const cachedIds = Object.keys(jobProgress.value)
    for (const id of cachedIds) {
      clearProgress(id)
    }
    jobProgress.value = {}
    jobGlobalProgress.value = {}
    jobLogs.value = {}
    localStorage.removeItem(JOB_STORAGE_KEY)
  }

  function clearSelection(): void {
    selectedJobId.value = null
    selectedJobLogs.value = []
  }

  // ── WebSocket actions (existing) ──────────────────────────────────────────

  function startJob(jobId: string, fileIds: string[] = []) {
    currentJobId.value = jobId
    currentJobFileIds.value = fileIds
    selectedJobId.value = null
    selectedJobLogs.value = []
    status.value = 'queued'
    stopRequested.value = false
    // Initialize per-job state
    jobProgress.value[jobId] = {}
    jobGlobalProgress.value[jobId] = 0
    jobLogs.value[jobId] = []
    localStorage.setItem(JOB_STORAGE_KEY, jobId)
    connectJobWS(jobId)
    // Backfill logs sent before WS was connected — merge then deduplicate by timestamp+message
    apiGetJobLogs(jobId).then(resp => {
      const backfill = resp.logs.map((l: any) => ({
        timestamp: l.timestamp, level: l.level, message: l.message,
      }))
      const merged = [...backfill, ...(jobLogs.value[jobId] ?? [])]
      const seen = new Set<string>()
      jobLogs.value[jobId] = merged.filter(l => {
        const key = `${l.timestamp}|${l.message}`
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
    }).catch(() => {})
  }

  async function stopJob() {
    stopRequested.value = true
    if (currentJobId.value) {
      // Log stop request to per-job logs
      if (!jobLogs.value[currentJobId.value]) jobLogs.value[currentJobId.value] = []
      jobLogs.value[currentJobId.value].push({ timestamp: new Date().toISOString(), level: 'info', message: 'User requested stop' })
      try {
        await stopJobApi(currentJobId.value)
      } catch {
        // Ignore REST errors
      }
    }
  }

  async function restoreJob(): Promise<void> {
    await fetchJobs()

    // Connect WS for ALL running/pending jobs
    for (const job of jobs.value) {
      if (job.status === 'running' || job.status === 'pending') {
        jobProgress.value[job.id] = {}
        jobGlobalProgress.value[job.id] = 0
        jobLogs.value[job.id] = []
        connectJobWS(job.id)
      }
    }

    const savedJobId = localStorage.getItem(JOB_STORAGE_KEY)
    if (savedJobId) {
      try {
        const response = await apiGetJob(savedJobId)
        const job = response.job

        currentJobId.value = job.id
        status.value = job.status
        currentJobFileIds.value = job.file_ids ?? []

        // Restore logs
        try {
          const logsResp = await apiGetJobLogs(savedJobId)
          jobLogs.value[savedJobId] = logsResp.logs.map((l) => ({
            timestamp: l.timestamp,
            level: l.level as 'error' | 'info' | 'warning' | 'llm',
            message: l.message,
          }))
        } catch {}

        // Restore output files
        try {
          const outputsResp = await apiGetJobOutputs(savedJobId)
          currentJobFiles.value = outputsResp.outputs.map((o) => ({
            filename: o.filename,
            path: o.file_path,
            size_bytes: o.size_bytes,
          }))
        } catch {}

        // Initialize per-job progress
        jobProgress.value[savedJobId] = {}
        jobGlobalProgress.value[savedJobId] = 0

        // Restore cached progress from localStorage (survives page refresh)
        const cached = loadJobProgress(savedJobId)
        if (cached) {
          jobProgress.value[savedJobId] = cached.progress
          jobGlobalProgress.value[savedJobId] = cached.globalProgress
        }

        return
      } catch {}
    }
  }

  function connectJobWS(jobId: string) {
    if (wsConnections.value[jobId]) return
    const conn = new WSConnection()
    conn.connect(jobId, handleMessage, undefined, undefined)
    wsConnections.value[jobId] = conn
  }

  function disconnectJobWS(jobId: string) {
    const conn = wsConnections.value[jobId]
    if (conn) {
      conn.disconnect()
      delete wsConnections.value[jobId]
    }
  }

  function disconnectAllWS() {
    for (const id of Object.keys(wsConnections.value)) {
      wsConnections.value[id].disconnect()
    }
    wsConnections.value = {}
  }

  function updateJobInList(jobId: string, newStatus: string) {
    const job = jobs.value.find((j: JobItem) => j.id === jobId)
    if (job) {
      job.status = newStatus as JobStatus
      if (newStatus === 'completed' || newStatus === 'error' || newStatus === 'stopped') {
        job.completed_at = new Date().toISOString()
      }
    }
  }

  function getJobFileIds(jobId: string): string[] {
    if (jobId === currentJobId.value && currentJobFileIds.value.length > 0) return currentJobFileIds.value
    return jobs.value.find(j => j.id === jobId)?.file_ids ?? []
  }

  function playNotificationSound() {
    try {
      const ctx = new AudioContext()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.type = 'sine'
      osc.frequency.value = 880
      gain.gain.value = 0.3
      osc.start()
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.5)
      osc.stop(ctx.currentTime + 0.5)
    } catch {
      // Audio not available
    }
  }

  function handleProgress(jobId: string, msg: Extract<WSServerMessage, { type: 'progress' }>) {
    const fileIds = getJobFileIds(jobId)
    const fileId = fileIds[msg.file_idx]
    if (fileId) {
      if (!jobProgress.value[jobId]) jobProgress.value[jobId] = {}
      jobProgress.value[jobId][fileId] = msg.chunk_pct
    }
    jobGlobalProgress.value[jobId] = msg.global_pct
    saveProgress(jobId, jobProgress.value[jobId] ?? {}, jobGlobalProgress.value[jobId] ?? 0)
  }

  function handleLog(jobId: string, msg: Extract<WSServerMessage, { type: 'log' }>) {
    if (!jobLogs.value[jobId]) jobLogs.value[jobId] = []
    jobLogs.value[jobId].push({ timestamp: new Date().toISOString(), level: msg.level, message: msg.message })
  }

  function handleStatus(jobId: string, msg: Extract<WSServerMessage, { type: 'status' }>) {
    updateJobInList(jobId, msg.status)
    if (jobId === currentJobId.value) {
      status.value = msg.status
      if (msg.status === 'stopped' || msg.status === 'completed' || msg.status === 'error') {
        stopRequested.value = false
      }
    }
  }

  function handleFileDone(jobId: string) {
    if (activeJobId.value === jobId) {
      fetchJobFiles(jobId)
    }
  }

  function handleDone(jobId: string) {
    const fileIds = getJobFileIds(jobId)
    if (!jobProgress.value[jobId]) jobProgress.value[jobId] = {}
    for (const fid of fileIds) {
      jobProgress.value[jobId][fid] = 100
    }
    jobGlobalProgress.value[jobId] = 100
    saveProgress(jobId, jobProgress.value[jobId] ?? {}, jobGlobalProgress.value[jobId] ?? 0)
    updateJobInList(jobId, 'completed')
    if (jobId === currentJobId.value) {
      if (status.value !== 'stopped' && status.value !== 'error' && status.value !== 'partial') {
        status.value = 'completed'
      }
      stopRequested.value = false
    }
    if (activeJobId.value === jobId) {
      fetchJobFiles(jobId)
    }
    // Notification
    try {
      const configStore = useConfigStore()
      if (configStore.notifications.enabled) {
        if ('Notification' in window && Notification.permission === 'granted') {
          new Notification('SimpleETL', { body: `Job completed: ${jobId.slice(0, 8)}` })
        } else if ('Notification' in window && Notification.permission !== 'denied') {
          Notification.requestPermission().then(permission => {
            if (permission === 'granted') {
              new Notification('SimpleETL', { body: `Job completed: ${jobId.slice(0, 8)}` })
            }
          })
        }
        if (configStore.notifications.sound) {
          playNotificationSound()
        }
      }
    } catch {}
    disconnectJobWS(jobId)
  }

  function handleError(jobId: string) {
    updateJobInList(jobId, 'error')
    if (jobId === currentJobId.value) {
      status.value = 'error'
      stopRequested.value = false
    }
    disconnectJobWS(jobId)
  }

  function handleMessage(msg: WSServerMessage) {
    const jobId = msg.job_id
    logger.debug('[JobStore] handleMessage:', msg.type, msg)
    switch (msg.type) {
      case 'progress': handleProgress(jobId, msg); break
      case 'log': handleLog(jobId, msg); break
      case 'status': handleStatus(jobId, msg); break
      case 'file_done': handleFileDone(jobId); break
      case 'done': handleDone(jobId); break
      case 'error': handleError(jobId); break
    }
  }

  return {
    currentJobId, status, progress, globalProgress, logs, stopRequested,
    jobs, currentJobFiles, selectedJobId, selectedJobLogs, activeLogs, activeFiles,
    activeJobId, activeJobFileIds, activeStatus, activeProgress, currentJobFileIds,
    selectJob, clearSelection, clearActiveJob,
    isRunning, isCompleted, isActive,
    startJob, stopJob, restoreJob,
    createAndStartJob, fetchJobs, fetchJobFiles, deleteJob,
  }
})
