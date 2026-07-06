/**
 * Axios REST client for the SimpleETL API backend.
 *
 * Provides typed functions for CRUD operations on files and jobs.
 */

import axios, { type AxiosError } from 'axios'
import type { FileListResponse, FileUploadResponse } from '@/types/file'
import type { JobCreateRequest, JobResponse, JobListResponse, JobFilesResponse, JobLogsResponse, JobOutputsResponse } from '@/types/job'

// ── Axios instance ────────────────────────────────────────────────────────

const STORAGE_KEY = 'simpleetl_api_base_url'

function getBaseURL(): string {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) return stored
  return import.meta.env.VITE_API_BASE_URL || ''
}

function getApiKey(): string {
  return localStorage.getItem('simpleetl_api_server_key') || ''
}

const api = axios.create({
  baseURL: getBaseURL(),
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
})

// ── Request interceptor: attach API key ────────────────────────────────────
api.interceptors.request.use((config) => {
  const key = getApiKey()
  if (key) {
    config.headers['X-API-Key'] = key
  }
  return config
})

// ── Response interceptor (structured errors) ──────────────────────────────

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const structured = {
      status: error.response?.status,
      message: error.message,
      detail: error.response?.data?.detail,
    }
    throw structured as Error
  },
)

// ── File endpoints ────────────────────────────────────────────────────────

export async function uploadFiles(files: File[]): Promise<FileUploadResponse> {
  // Build FormData with 'files' field (required by the server)
  const formData = new FormData()
  files.forEach((file) => formData.append('files', file))

  // Override default JSON content-type for multipart uploads
  api.defaults.headers.common['Content-Type'] = undefined
  try {
    const res = await api.post<FileUploadResponse>('/api/v1/files/upload', formData, {
      headers: { 'Content-Type': undefined }, // axios will set multipart/form-data automatically
    })
    return res.data
  } finally {
    // Restore default JSON content-type for subsequent requests
    api.defaults.headers.common['Content-Type'] = 'application/json'
  }
}

export async function getFiles(): Promise<FileListResponse> {
  const res = await api.get<FileListResponse>('/api/v1/files')
  return res.data
}

export async function deleteFile(fileId: string): Promise<void> {
  // Server returns 204 No Content — no body to parse
  await api.delete(`/api/v1/files/${encodeURIComponent(fileId)}`)
}

// ── Job endpoints ────────────────────────────────────────────────────────

export async function createJob(request: JobCreateRequest): Promise<JobResponse> {
  const res = await api.post<JobResponse>('/api/v1/jobs', request)
  return res.data
}

export async function getJobs(): Promise<JobListResponse> {
  const res = await api.get<JobListResponse>('/api/v1/jobs')
  return res.data
}

export async function getJob(jobId: string): Promise<JobResponse> {
  const res = await api.get<JobResponse>(`/api/v1/jobs/${encodeURIComponent(jobId)}`)
  return res.data
}

export async function stopJob(jobId: string, deleteFiles: boolean = false): Promise<JobResponse> {
  const res = await api.delete<JobResponse>(`/api/v1/jobs/${encodeURIComponent(jobId)}`, {
    params: { delete_files: deleteFiles },
  })
  return res.data
}

export async function getJobFiles(jobId: string): Promise<JobFilesResponse> {
  const res = await api.get<JobFilesResponse>(`/api/v1/jobs/${encodeURIComponent(jobId)}/files`)
  return res.data
}

export async function downloadJobFile(jobId: string, filename: string): Promise<Blob> {
  const res = await api.get(`/api/v1/jobs/${encodeURIComponent(jobId)}/files/${encodeURIComponent(filename)}`, {
    responseType: 'blob',
  })
  return res.data as Blob
}

export async function downloadJobZip(jobId: string): Promise<Blob> {
  const res = await api.get(`/api/v1/jobs/${encodeURIComponent(jobId)}/download`, {
    responseType: 'blob',
  })
  return res.data as Blob
}

export async function getJobLogs(jobId: string): Promise<JobLogsResponse> {
  const res = await api.get<JobLogsResponse>(`/api/v1/jobs/${encodeURIComponent(jobId)}/logs`)
  return res.data
}

export async function getJobOutputs(jobId: string): Promise<JobOutputsResponse> {
  const res = await api.get<JobOutputsResponse>(`/api/v1/jobs/${encodeURIComponent(jobId)}/outputs`)
  return res.data
}

export async function cleanupJobs(maxAgeHours: number = 24): Promise<{ removed: number }> {
  const res = await api.post<{ removed: number }>(`/api/v1/jobs/cleanup?max_age_hours=${maxAgeHours}`)
  return res.data
}
