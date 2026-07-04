<script setup lang="ts">
import { useUiStore } from '@/stores/ui'
import { useJobStore } from '@/stores/job'
import { useFilesStore } from '@/stores/files'
import { useConfigStore } from '@/stores/config'
import { usePromptsStore } from '@/stores/prompts'
import SettingsPanel from '@/components/Settings/SettingsPanel.vue'
import PromptLibrary from '@/components/PromptLibrary/PromptLibrary.vue'
import LogPanel from '@/components/LogPanel/LogPanel.vue'
import FileList from '@/components/FileList/FileList.vue'
import GlobalProgressBar from '@/components/Progress/GlobalProgressBar.vue'
import JobOutput from '@/components/JobOutput/JobOutput.vue'
import JobHistory from '@/components/JobHistory/JobHistory.vue'
import ConnectionStatus from '@/components/ConnectionStatus/ConnectionStatus.vue'
import { onMounted } from 'vue'

const uiStore = useUiStore()
const jobStore = useJobStore()
const filesStore = useFilesStore()
const configStore = useConfigStore()
const promptsStore = usePromptsStore()

// ── Panel definitions ─────────────────────────────────────────────────────

interface PanelDef { id: string; label: string }
const panels: PanelDef[] = [
  { id: 'files', label: 'Files' },
  { id: 'settings', label: 'Settings' },
  { id: 'prompts', label: 'Prompts' },
  { id: 'logs', label: 'Logs' },
  { id: 'output', label: 'Output' },
  { id: 'history', label: 'History' },
]

// ── Helpers ───────────────────────────────────────────────────────────────

function statusBadgeText(status: string | null): string {
  switch (status) {
    case 'completed': return '✓ Completed'
    case 'running':   return '▶ Running'
    case 'error':     return '✗ Error'
    default:          return jobStore.currentJobId ? `#${jobStore.currentJobId.slice(0, 8)}…` : 'Idle'
  }
}

// ── Lifecycle ─────────────────────────────────────────────────────────────

onMounted(async () => {
  await configStore.loadConfig()
  await promptsStore.fetchPrompts()
  await filesStore.fetchFiles()
})
</script>

<template>
  <div class="app-layout">
    <!-- Notification bar (fixed bottom) -->
    <transition name="notification-fade">
      <div v-if="uiStore.notification" :class="['notification-bar', `notification-bar--${uiStore.notification.type}`]">
        <span>{{ uiStore.notification.message }}</span>
        <button class="notification-bar__close" @click="uiStore.clearNotification()">✕</button>
      </div>
    </transition>

    <!-- Header -->
    <header class="app-header">
      <h1 class="app-header__title">SimpleETL</h1>
      <ConnectionStatus />
      <span :class="['status-badge', `status-badge--${jobStore.status || 'idle'}`]">
        {{ statusBadgeText(jobStore.status) }}
      </span>
    </header>

    <!-- Main layout -->
    <div class="app-body">
      <!-- Sidebar -->
      <aside :class="['sidebar', { 'sidebar--collapsed': uiStore.sidebarCollapsed }]">
        <nav class="sidebar__nav">
          <button
            v-for="panel in panels"
            :key="panel.id"
            :class="['sidebar__item', { 'sidebar__item--active': uiStore.activePanel === panel.id }]"
            @click="uiStore.setPanel(panel.id)"
          >
            {{ panel.label }}
          </button>
        </nav>
      </aside>

      <!-- Sidebar toggle -->
      <button class="sidebar__toggle" @click="uiStore.toggleSidebar()">
        {{ uiStore.sidebarCollapsed ? '▸' : '◂' }}
      </button>

      <!-- Main content area -->
      <main class="app-main">
        <GlobalProgressBar />
        <FileList v-if="uiStore.activePanel === 'files'" />
        <SettingsPanel v-else-if="uiStore.activePanel === 'settings'" />
        <PromptLibrary v-else-if="uiStore.activePanel === 'prompts'" @select="promptsStore.setCurrentPrompt($event.name)" />
        <LogPanel v-else-if="uiStore.activePanel === 'logs'" />
        <JobOutput v-else-if="uiStore.activePanel === 'output'" />
        <JobHistory v-else-if="uiStore.activePanel === 'history'" />
      </main>
    </div>
  </div>
</template>

<style scoped>
/* ── Layout grid ─────────────────────────────────────────────── */
.app-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  font-family: 'Segoe UI', system-ui, sans-serif;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.75rem 1.25rem;
  background: var(--bg-main);
  border-bottom: 1px solid var(--border);
  min-height: 48px;
}

.app-header__title {
  font-size: 16px;
  font-weight: 700;
  color: var(--fg-title);
  margin: 0;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
}

.status-badge--idle    { background: #f3f4f6; color: #6b7280; }
.status-badge--pending { background: #e5e7eb; color: #6b7280; }
.status-badge--running { background: #dbeafe; color: #1d4ed8; }
.status-badge--completed { background: #dcfce7; color: #166534; }
.status-badge--error   { background: #fee2e2; color: #991b1b; }

/* ── Body grid ───────────────────────────────────────────────── */
.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.sidebar {
  width: 200px;
  min-width: 200px;
  background: var(--bg-card);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: min-width 0.2s ease, width 0.2s ease;
}

.sidebar--collapsed {
  width: 0;
  min-width: 0;
  border-right: none;
}

.sidebar__nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
}

.sidebar__item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  border: none;
  background: transparent;
  color: var(--fg-label);
  font-size: 13px;
  font-family: inherit;
  cursor: pointer;
  border-radius: 6px;
  transition: background-color 0.15s, color 0.15s;
}

.sidebar__item:hover {
  background: rgba(59, 130, 246, 0.08);
  color: var(--fg-title);
}

.sidebar__item--active {
  background: var(--accent);
  color: white;
}

.sidebar__toggle {
  flex-shrink: 0;
  width: 18px;
  align-self: center;
  height: 34px;
  border: 1px solid var(--border);
  border-radius: 0 6px 6px 0;
  background: var(--bg-card);
  color: var(--fg-label);
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: -1px;
}

.sidebar__toggle:hover {
  background: rgba(59, 130, 246, 0.08);
}

.app-main {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.panel-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
  color: var(--fg-label);
  font-size: 14px;
  opacity: 0.6;
}

/* ── Notification bar ────────────────────────────────────────── */
.notification-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 8px 1.5rem;
  font-size: 13px;
  color: white;
  z-index: 1000;
}

.notification-bar--success { background: #22c55e; }
.notification-bar--error   { background: #ef4444; }
.notification-bar--info     { background: #3b82f6; }

.notification-bar__close {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  font-size: 16px;
  padding: 0 4px;
}

/* ── Notification fade transition ────────────────────────────── */
.notification-fade-enter-active,
.notification-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.notification-fade-enter-from,
.notification-fade-leave-to {
  opacity: 0;
  transform: translateY(8px);
}
</style>
