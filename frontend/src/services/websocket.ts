/**
 * WebSocket connection manager for real-time job progress.
 *
 * Connects to the backend WS endpoint and dispatches typed server messages
 * to registered callbacks.
 */

import type { WSServerMessage, WSClientMessage } from '@/types/ws'

export class WSConnection {
  private ws: WebSocket | null = null

  /** Whether a connection is currently open. */
  get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  /**
   * Open a new WebSocket to the job-specific endpoint.
   *
   * URL format: `${wsBase}/ws/${jobId}`
   * where wsBase = VITE_WS_BASE_URL or `ws://${location.host}` (dev fallback).
   */
  connect(
    jobId: string,
    onMessage: (msg: WSServerMessage) => void,
    onError?: (e: Event) => void,
    onClose?: (e: CloseEvent) => void,
  ): void {
    const wsBase = import.meta.env.VITE_WS_BASE_URL || `ws://${location.host}`
    const url = `${wsBase}/ws/${jobId}`

    this.ws = new WebSocket(url)

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data) as WSServerMessage
        onMessage(msg)
      } catch {
        // Silently ignore malformed messages — server should always send valid JSON.
      }
    }

    this.ws.onerror = onError || (() => {})
    this.ws.onclose = onClose || (() => {})
  }

  /** Send a client message as JSON. */
  send(msg: WSClientMessage): void {
    if (this.ws && this.isConnected) {
      this.ws.send(JSON.stringify(msg))
    }
  }

  /** Close the connection and nullify the socket reference. */
  disconnect(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }
}
