/** Job status enum matching backend Pydantic schema. */
export type JobStatus = "pending" | "running" | "completed" | "stopped" | "error"

/** Full job metadata stored in the registry. */
export interface JobItem {
  /** Unique job identifier (UUID4). */
  id: string
  /** Current job status. */
  status: JobStatus
  /** IDs of files to process. */
  file_ids: string[]
  /** ETL config snapshot (llm + processing + prompt_text). */
  config: Record<string, unknown>
  /** Job creation timestamp (ISO 8601 UTC). */
  created_at: string
  /** Optional start time of the job. */
  started_at?: string
  /** Optional completion time of the job. */
  completed_at?: string
  /** Optional path to output directory. */
  output_dir?: string
  /** Optional error message if the job failed. */
  error_message?: string
  /** Number of files in the job. */
  file_count: number
}

/** Request body for POST /jobs. */
export interface JobCreateRequest {
  /** IDs of files to process. */
  file_ids: string[]
  /** Full ETL config (llm + processing + prompt_text). */
  config: Record<string, unknown>
}

/** Single job response wrapper. */
export interface JobResponse {
  /** The processed job object. */
  job: JobItem
}

/** List of jobs with total count. */
export interface JobListResponse {
  /** Array of job objects. */
  jobs: JobItem[]
  /** Total number of jobs. */
  total: number
}

/** Represents a single output file from a completed job. */
export interface JobFileItem {
  /** Output filename. */
  filename: string
  /** Relative path from job output dir. */
  path: string
  /** File size in bytes. */
  size_bytes: number
}

/** List of output files for a job. */
export interface JobFilesResponse {
  /** Job identifier. */
  job_id: string
  /** Array of output file objects. */
  files: JobFileItem[]
  /** Total number of output files. */
  total: number
}
