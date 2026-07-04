import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUiStore } from '@/stores/ui'

describe('ui store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('showNotification auto-clears after 3s', () => {
    const store = useUiStore()
    store.showNotification('success', 'Done!')

    expect(store.notification).toEqual({ type: 'success', message: 'Done!' })

    vi.advanceTimersByTime(3000)

    expect(store.notification).toBeNull()
  })

  it('openModal/closeModal toggle modal state', () => {
    const store = useUiStore()

    store.openModal('save-prompt', { name: 'test' })
    expect(store.modal).toEqual({ type: 'save-prompt', data: { name: 'test' } })

    store.closeModal()
    expect(store.modal).toBeNull()
  })
})
