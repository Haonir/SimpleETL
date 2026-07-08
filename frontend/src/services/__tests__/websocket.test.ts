import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { WSConnection } from '../websocket'

/** Track all MockWebSocket instances for test assertions. */
let instances: MockWebSocket[] = []

class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  readyState = MockWebSocket.CONNECTING
  url: string
  onopen?: (e: Event) => void
  onmessage?: (e: MessageEvent) => void
  onerror?: (e: Event) => void
  onclose?: (e: CloseEvent) => void

  constructor(url: string | URL) {
    this.url = url.toString()
    instances.push(this)
    // Simulate open asynchronously
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN
      this.onopen?.(new Event('open'))
    }, 0)
  }

  send(_data: string) {
    // no-op
  }

  close(code?: number, reason?: string) {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.(new CloseEvent('close', { code, reason }))
  }
}

describe('WSConnection', () => {
  let connection: WSConnection

  beforeEach(() => {
    instances = []
    vi.stubGlobal('WebSocket', MockWebSocket)
    vi.useFakeTimers()
    connection = new WSConnection()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('connects to the correct URL with jobId', async () => {
    const onMessage = vi.fn()
    connection.connect('job-123', onMessage)

    // Let MockWebSocket constructor fire onopen
    await vi.advanceTimersByTimeAsync(1)

    expect(instances).toHaveLength(1)
    expect(instances[0].url).toContain('/ws/job-123')
  })

  it('sends messages when connected', async () => {
    const sendSpy = vi.spyOn(MockWebSocket.prototype, 'send')
    connection.connect('job-123', vi.fn())

    await vi.advanceTimersByTimeAsync(1)
    expect(connection.isConnected).toBe(true)

    connection.send({ type: 'stop', job_id: 'job-123' })
    expect(sendSpy).toHaveBeenCalled()
  })

  it('disconnects and closes the socket', async () => {
    const closeSpy = vi.spyOn(MockWebSocket.prototype, 'close')
    connection.connect('job-123', vi.fn())

    await vi.advanceTimersByTimeAsync(1)
    connection.disconnect()

    expect(closeSpy).toHaveBeenCalled()
    expect(connection.isConnected).toBe(false)
  })

  it('calls onReconnect callback on unexpected close', async () => {
    const onReconnect = vi.fn()

    connection.connect('job-123', vi.fn(), undefined, undefined, onReconnect)

    await vi.advanceTimersByTimeAsync(1)
    // Simulate unexpected close (not from disconnect())
    instances[0].onclose?.(new CloseEvent('close', { code: 1006 }))

    // Wait for reconnect scheduling
    await vi.advanceTimersByTimeAsync(100)

    expect(onReconnect).toHaveBeenCalled()
  })

  it('does not reconnect when onClose is provided', async () => {
    const onClose = vi.fn()

    connection.connect('job-123', vi.fn(), undefined, onClose)

    await vi.advanceTimersByTimeAsync(1)
    instances[0].onclose?.(new CloseEvent('close', { code: 1006 }))

    await vi.advanceTimersByTimeAsync(100)

    // Only the initial connection, no reconnect
    expect(instances).toHaveLength(1)
  })

  it('isConnected returns false when no socket exists', () => {
    expect(connection.isConnected).toBe(false)
  })

  it('isConnected returns true when WebSocket is open', async () => {
    connection.connect('job-123', vi.fn())

    await vi.advanceTimersByTimeAsync(1)
    expect(connection.isConnected).toBe(true)
  })

  it('clearReconnectState resets retry counter', async () => {
    connection.connect('job-123', vi.fn())
    await vi.advanceTimersByTimeAsync(1)

    connection.clearReconnectState()
    expect((connection as any).reconnectAttempts).toBe(0)
  })
})
