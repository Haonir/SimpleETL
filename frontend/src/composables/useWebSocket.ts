import { ref, onUnmounted } from 'vue'
import { WSConnection } from '@/services/websocket'
import type { WSServerMessage } from '@/types/ws'

export function useWebSocket() {
  const ws = ref<WSConnection | null>(null)
  const isConnected = ref(false)

  function connect(jobId: string, onMessage: (msg: WSServerMessage) => void) {
    ws.value = new WSConnection()
    ws.value.connect(jobId, onMessage)
    isConnected.value = true
  }

  function disconnect() {
    ws.value?.disconnect()
    ws.value = null
    isConnected.value = false
  }

  function send(msg: Record<string, unknown>) {
    ws.value?.send(msg as any)
  }

  onUnmounted(disconnect)

  return { ws, isConnected, connect, disconnect, send }
}
