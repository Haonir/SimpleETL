/** Chunk processing progress update. */
export interface WSProgressMessage {
  type: "progress"
  job_id: string
  file_name: string
  chunk_index: number
  total_chunks: number
  percent: number
}

/** Log line emitted during processing. */
export interface WSLogMessage {
  type: "log"
  job_id: string
  level: "info" | "warning" | "error"
  message: string
}

/** Job status change (started, running, etc.). */
export interface WSStatusMessage {
  type: "status"
  job_id: string
  status: "queued" | "running" | "paused" | "stopped"
  file_name?: string
}

/** Job completed successfully. */
export interface WSDoneMessage {
  type: "done"
  job_id: string
  file_name: string
  total_chunks: number
  processed_chunks: number
  error_count: number
}

/** Job failed with an error. */
export interface WSErrorMessage {
  type: "error"
  job_id: string
  file_name?: string
  message: string
}

/** Client request to stop processing. */
export interface WSStopMessage {
  type: "stop"
  job_id: string
}

/** Union of all server-to-client WebSocket messages. */
export type WSServerMessage =
  | WSProgressMessage
  | WSLogMessage
  | WSStatusMessage
  | WSDoneMessage
  | WSErrorMessage

/** Union of all client-to-server WebSocket messages. */
export type WSClientMessage = WSStopMessage
