import type { LLMConfig, ProcessingConfig } from "./config"

/** Job status枚举. */
export type JobStatus = "queued" | "running" | "paused" | "stopped" | "completed" | "error"

/** Configuration for starting a new ETL job. */
export interface JobConfig {
  /** IDs of files to process. */
  file_ids: string[]
  /** LLM provider configuration. */
  llm: LLMConfig
  /** Processing parameters. */
  processing: ProcessingConfig
  /** System prompt text. */
  prompt_text: string
  /** Optional output directory. */
  output_dir?: string
}

/** Job response from the API. */
export interface JobResponse {
  /** Unique job identifier. */
  id: string
  /** Current job status. */
  status: JobStatus
  /** Job creation timestamp (ISO 8601). */
  created_at: string
  /** Number of files in the job. */
  file_count: number
}
