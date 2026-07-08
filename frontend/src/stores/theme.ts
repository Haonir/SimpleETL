import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

export type ThemeMode = 'light' | 'dark' | 'system'

const STORAGE_KEY = 'theme'

export const useThemeStore = defineStore('theme', () => {
  const mode = ref<ThemeMode>((localStorage.getItem(STORAGE_KEY) as ThemeMode) || 'system')
  const systemDark = ref(false)

  // Detect system preference
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  systemDark.value = mediaQuery.matches

  // Effective theme: if 'system', follow system; otherwise use explicit choice
  const effectiveTheme = computed<'light' | 'dark'>(() => {
    if (mode.value === 'system') return systemDark.value ? 'dark' : 'light'
    return mode.value
  })

  // Apply to <html>
  function applyTheme() {
    document.documentElement.setAttribute('data-theme', effectiveTheme.value)
  }

  // Watch for system changes
  mediaQuery.addEventListener('change', (e) => {
    systemDark.value = e.matches
    if (mode.value === 'system') applyTheme()
  })

  // Watch for mode changes
  watch(mode, (val) => {
    localStorage.setItem(STORAGE_KEY, val)
    applyTheme()
  })

  // Initialize on store creation
  applyTheme()

  return { mode, effectiveTheme }
})
