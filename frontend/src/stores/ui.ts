import { defineStore } from 'pinia'
import { ref } from 'vue'

interface Notification {
  type: 'success' | 'error' | 'info'
  message: string
}

interface Modal {
  type: string
  data?: unknown
}

export const useUiStore = defineStore('ui', () => {
  const notification = ref<Notification | null>(null)
  const modal = ref<Modal | null>(null)
  let notificationTimer: ReturnType<typeof setTimeout> | null = null

  // Layout navigation state
  type PanelId = 'files' | 'settings' | 'prompts' | 'logs' | 'output' | 'history'
  const activePanel = ref<PanelId>('files')
  const sidebarCollapsed = ref<boolean>(false)
  type LogFilter = 'all' | 'info' | 'warning' | 'error'
  const logFilter = ref<LogFilter>('all')

  function setPanel(id: PanelId) {
    activePanel.value = id
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setLogFilter(filter: LogFilter) {
    logFilter.value = filter
  }

  function showNotification(type: Notification['type'], message: string) {
    if (notificationTimer) clearTimeout(notificationTimer)
    notification.value = { type, message }
    notificationTimer = setTimeout(() => {
      notification.value = null
      notificationTimer = null
    }, 3000)
  }

  function clearNotification() {
    if (notificationTimer) {
      clearTimeout(notificationTimer)
      notificationTimer = null
    }
    notification.value = null
  }

  function openModal(type: string, data?: unknown) {
    modal.value = { type, data }
  }

  function closeModal() {
    modal.value = null
  }

  return {
    notification,
    modal,
    showNotification,
    clearNotification,
    openModal,
    closeModal,
    activePanel,
    sidebarCollapsed,
    logFilter,
    setPanel,
    toggleSidebar,
    setLogFilter,
  }
})
