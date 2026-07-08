const PROGRESS_KEY_PREFIX = 'simpleetl_progress_'

function getProgressStorageKey(jobId: string): string {
  return `${PROGRESS_KEY_PREFIX}${jobId}`
}

export function saveJobProgress(jobId: string, progress: Record<string, number>, globalProgress: number): void {
  try {
    localStorage.setItem(getProgressStorageKey(jobId), JSON.stringify({ progress, globalProgress }))
  } catch {}
}

export function loadJobProgress(jobId: string): { progress: Record<string, number>, globalProgress: number } | null {
  try {
    const cached = localStorage.getItem(getProgressStorageKey(jobId))
    if (!cached) return null
    const parsed = JSON.parse(cached)
    if (typeof parsed === 'object' && parsed !== null && 'progress' in parsed) {
      return { progress: parsed.progress ?? {}, globalProgress: parsed.globalProgress ?? 0 }
    }
    return null
  } catch {
    return null
  }
}

export function clearJobProgress(jobId: string): void {
  try {
    localStorage.removeItem(getProgressStorageKey(jobId))
  } catch {}
}
