import type { ConfigResponse } from '@/types/config'

const STORAGE_KEY = 'simpleetl_config'

export async function loadConfigFile(): Promise<ConfigResponse> {
  const stored = localStorage.getItem(STORAGE_KEY)
  if (stored) {
    return JSON.parse(stored) as ConfigResponse
  }

  const response = await fetch('/config.json')
  if (!response.ok) throw new Error(`Failed to load config: ${response.statusText}`)
  const config = await response.json() as ConfigResponse
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config))
  return config
}

export function saveConfigFile(config: ConfigResponse): void {
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
