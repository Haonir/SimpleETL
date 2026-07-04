import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { WSConnection } from '@/services/websocket'
import type { WSServerMessage, LogEntry } from '@/types/ws'
import type { JobStatus } from '@/types/job'

export const useJobStore = defineStore('job', () => {
  const currentJobId = ref<string | null>(null)
  const status = ref<JobStatus | null>(null)
  const progress = ref<Record<string, number>>({})
  const globalProgress = ref(0)
  const logs = ref<LogEntry[]>([])
  const ws = ref<WSConnection | null>(null)

  const isRunning = computed(() => status.value === 'running')
  const isCompleted = computed(() => status.value === 'completed')

  function startJob(jobId: string) {
    currentJobId.value = jobId
    status.value = 'queued'
    progress.value = {}
    globalProgress.value = 0
    logs.value = []
    connectWS(jobId)
  }

  function stopJob() {
    if (ws.value && ws.value.isConnected) {
      ws.value.send({ type: 'stop', job_id: currentJobId.value! })
    }
    disconnectWS()
    status.value = 'stopped'
  }

  function connectWS(jobId: string) {
    ws.value = new WSConnection()
    ws.value.connect(jobId, handleMessage)
  }

  function disconnectWS() {
    ws.value?.disconnect()
    ws.value = null
  }

  function handleMessage(msg: WSServerMessage) {
    switch (msg.type) {
      case 'progress':
        progress.value[msg.file_name] = msg.percent
        {
          const values = Object.values(progress.value)
          globalProgress.value = values.length
            ? values.reduce((a, b) => a + b, 0) / values.length
            : 0
        }
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
    isRunning, isCompleted,
    startJob, stopJob, connectWS, disconnectWS, addLog,
  }
})
