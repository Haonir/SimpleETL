/**
 * Axios REST client for the SimpleETL API backend.
 *
 * Provides typed functions for all CRUD operations on config, prompts, and files.
 */

import axios, { type AxiosError } from 'axios'
import type { ConfigResponse, ConfigUpdateRequest } from '@/types/config'
import type { PromptLibraryResponse, PromptCreateRequest, PromptEntry, PromptDeleteResponse } from '@/types/config'
import type { FileListResponse, FileUploadResponse } from '@/types/file'

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
