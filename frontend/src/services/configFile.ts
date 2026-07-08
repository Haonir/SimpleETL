import type { ConfigResponse } from '@/types/config'

const STORAGE_KEY = 'simpleetl_config'

export async function loadConfigFile(): Promise<ConfigResponse> {
  // Try API endpoint first
  try {
    const apiResponse = await fetch('/api/v1/config')
    if (apiResponse.ok) {
      const config = await apiResponse.json() as ConfigResponse
      localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
      return config
    }
  } catch {
    // API unavailable
  }

  // Fall back to static file
  try {
    const response = await fetch('/config.json')
    if (response.ok) {
      const config = await response.json() as ConfigResponse
      localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
      return config
    }
  } catch {
    // Static file unavailable
  }

  // Fall back to localStorage
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) {
    return JSON.parse(stored) as ConfigResponse
  }

  throw new Error('Failed to load config from server and localStorage')
}

export async function saveConfigFile(config: ConfigResponse): Promise<void> {
  // Save to server
  try {
    await fetch('/api/v1/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    })
  } catch (e) {
    console.warn('Failed to save config to server:', e)
  }
  // Also save to localStorage as cache
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
}

export function downloadConfigFile(config: ConfigResponse): void {
  const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'config.json'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export async function importConfigFile(file: File): Promise<ConfigResponse> {
  const text = await file.text()
  return JSON.parse(text) as ConfigResponse
}

export function clearConfigFile(): void {
  localStorage.removeItem(STORAGE_KEY)
}
