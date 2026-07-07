/** Chunk processing progress update. */
export interface WSProgressMessage {
  type: "progress"
  job_id: string
  file_idx: number
  chunk_pct: number
  global_pct: number
}

/** Log line emitted during processing. */
export interface WSLogMessage {
  type: "log"
  job_id: string
  level: "info" | "llm" | "warning" | "error"
  message: string
}

/** Job status change (started, running, etc.). */
export interface WSStatusMessage {
  type: "status"
  job_id: string
  status: "pending" | "running" | "completed" | "partial" | "stopped" | "error"
}

/** Job completed successfully. */
export interface WSDoneMessage {
  type: "done"
  job_id: string
  output_dir: string
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

/** Single file processing complete — output files saved to DB. */
export interface WSFileDoneMessage {
  type: "file_done"
  job_id: string
  file_idx: number
  base_name: string
}

/** Union of all server-to-client WebSocket messages. */
export type WSServerMessage =
  | WSProgressMessage
  | WSLogMessage
  | WSStatusMessage
  | WSDoneMessage
  | WSErrorMessage
  | WSFileDoneMessage

/** Timestamped log entry for the UI log panel. */
export interface LogEntry {
  timestamp: string
  level: 'info' | 'llm' | 'warning' | 'error'
  message: string
}

/** Union of all client-to-server WebSocket messages. */
export type WSClientMessage = WSStopMessage
