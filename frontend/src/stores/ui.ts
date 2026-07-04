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

  return { notification, modal, showNotification, clearNotification, openModal, closeModal }
})
