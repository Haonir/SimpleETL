/**
 * Axios REST client for the SimpleETL API backend.
 *
 * Provides typed functions for all CRUD operations on config, prompts, files, and jobs.
 */

import axios, { type AxiosError } from 'axios'
import type { ConfigResponse, ConfigUpdateRequest } from '@/types/config'
import type { PromptLibraryResponse, PromptCreateRequest, PromptEntry, PromptDeleteResponse } from '@/types/config'
import type { FileListResponse, FileUploadResponse } from '@/types/file'
import type { JobCreateRequest, JobResponse, JobListResponse, JobFilesResponse } from '@/types/job'

// ── Axios instance ────────────────────────────────────────────────────────

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '', // empty string → dev proxy handles /api/*
  timeout: 30_000,
  headers: { 'Content-Type': 'application/json' },
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

// ── Config endpoints ──────────────────────────────────────────────────────

export async function getConfig(): Promise<ConfigResponse> {
  const res = await api.get<ConfigResponse>('/api/v1/config')
  return res.data
}

export async function saveConfig(update: ConfigUpdateRequest): Promise<ConfigResponse> {
  const res = await api.post<ConfigResponse>('/api/v1/config', update)
  return res.data
}

// ── Prompt library endpoints ──────────────────────────────────────────────

export async function getPrompts(): Promise<PromptLibraryResponse> {
  const res = await api.get<PromptLibraryResponse>('/api/v1/prompts')
  return res.data
}

export async function createPrompt(req: PromptCreateRequest): Promise<PromptEntry> {
  const res = await api.post<PromptEntry>('/api/v1/prompts', req)
  return res.data
}

export async function deletePrompt(name: string): Promise<PromptDeleteResponse> {
  const res = await api.delete<PromptDeleteResponse>(`/api/v1/prompts/${encodeURIComponent(name)}`)
  return res.data
}

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

export async function stopJob(jobId: string): Promise<JobResponse> {
  const res = await api.delete<JobResponse>(`/api/v1/jobs/${encodeURIComponent(jobId)}`)
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
