/**
 * WebSocket connection manager for real-time job progress.
 *
 * Connects to the backend WS endpoint and dispatches typed server messages
 * to registered callbacks. Includes automatic reconnection with exponential backoff.
 */

import type { WSServerMessage, WSClientMessage } from '@/types/ws'
import { logger } from '@/utils/logger'

export class WSConnection {
  private ws: WebSocket | null = null

  /** Whether a connection is currently open. */
  get isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }

  /** Current retry count for reconnection attempts. */
  private reconnectAttempts = 0

  /** Maximum number of reconnection retries before giving up. */
  private readonly maxRetries = 5

  /** Exponential backoff delay in ms: 1s, 2s, 4s, 8s, 16s (capped at 30s). */
  private getBackoffDelay(): number {
    const base = Math.min(this.reconnectAttempts * 1000, 30_000)
    return base
  }

  /** Clear reconnection state. Call when the connection is intentionally closed. */
  clearReconnectState(): void {
    this.reconnectAttempts = 0
  }

  /**
   * Open a new WebSocket to the job-specific endpoint.
   *
   * URL format: `${wsBase}/ws/${jobId}`
   * where wsBase = VITE_WS_BASE_URL or `ws://${location.host}` (dev fallback).
   *
   * @param jobId — unique job identifier for the WS path
   * @param onMessage — callback for incoming server messages
   * @param onError — optional error handler
   * @param onClose — optional close handler; if provided, reconnection is suppressed
   * @param onReconnect — optional callback invoked when a reconnect attempt starts
   */
  connect(
    jobId: string,
    onMessage: (msg: WSServerMessage) => void,
    onError?: (e: Event) => void,
    onClose?: (e: CloseEvent) => void,
    onReconnect?: () => void,
  ): void {
    this.reconnectAttempts = 0

    const wsBase = import.meta.env.VITE_WS_BASE_URL || `ws://${location.host}`
    const url = `${wsBase}/ws/${jobId}`

    this.ws = new WebSocket(url)

    this.ws.onopen = () => {
      logger.info('[WS] Connected to', url)
    }

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data) as WSServerMessage
        onMessage(msg)
      } catch {
        // Silently ignore malformed messages — server should always send valid JSON.
      }
    }

    this.ws.onerror = (e) => {
      logger.error('[WS] Error:', e)
      if (onError) onError(e)
    }

    this.ws.onclose = (event: CloseEvent) => {
      logger.info('[WS] Closed: code=' + event.code, 'reason=' + event.reason)
      if (onClose) {
        onClose(event)
        return
      }

      // Not an intentional disconnect — attempt reconnection
      this.attemptReconnect(jobId, onMessage, onError, onReconnect)
    }
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
    // Clear reconnect state since the user intentionally disconnected
    this.reconnectAttempts = 0
  }

  /** Schedule a reconnection attempt with exponential backoff. */
  private attemptReconnect(
    jobId: string,
    onMessage: (msg: WSServerMessage) => void,
    onError?: (e: Event) => void,
    onReconnect?: () => void,
  ): void {
    if (this.reconnectAttempts >= this.maxRetries) {
      logger.warn('[WSConnection] Max reconnection attempts reached. Giving up.')
      return
    }

    this.reconnectAttempts++
    const delay = this.getBackoffDelay()

    if (onReconnect) onReconnect()

    setTimeout(() => {
      try {
        this.connect(jobId, onMessage, onError)
      } catch {
        logger.error('[WSConnection] Failed to reconnect after', delay, 'ms')
      }
    }, delay)
  }
}
