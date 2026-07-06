<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useUiStore } from '@/stores/ui'
import { useJobStore } from '@/stores/job'
import { useFilesStore } from '@/stores/files'
import { useConfigStore } from '@/stores/config'
import { usePromptsStore } from '@/stores/prompts'
import SettingsPanel from '@/components/Settings/SettingsPanel.vue'
import PromptLibrary from '@/components/PromptLibrary/PromptLibrary.vue'
import LogPanel from '@/components/LogPanel/LogPanel.vue'
import FileList from '@/components/FileList/FileList.vue'
import JobOutput from '@/components/JobOutput/JobOutput.vue'
import JobHistory from '@/components/JobHistory/JobHistory.vue'
import ConnectionStatus from '@/components/ConnectionStatus/ConnectionStatus.vue'
import { cleanupJobs } from '@/services/api'
import {
  FileStack, Settings, MessageSquare, ScrollText, Package, History,
  PanelLeftClose, PanelLeftOpen
} from '@lucide/vue'

const uiStore = useUiStore()
const jobStore = useJobStore()
const filesStore = useFilesStore()
const configStore = useConfigStore()
const promptsStore = usePromptsStore()

// ── Panel definitions ─────────────────────────────────────────────────────

interface PanelDef { id: string; label: string; icon: any }
const panels: PanelDef[] = [
  { id: 'files', label: 'Files', icon: FileStack },
  { id: 'settings', label: 'Settings', icon: Settings },
  { id: 'prompts', label: 'Prompts', icon: MessageSquare },
  { id: 'logs', label: 'Logs', icon: ScrollText },
  { id: 'output', label: 'Output', icon: Package },
  { id: 'history', label: 'History', icon: History },
]

// ── Helpers ───────────────────────────────────────────────────────────────

const activeJobsCount = computed(() => {
  return jobStore.jobs.filter(j => j.status === 'running' || j.status === 'pending').length
})

// ── Lifecycle ─────────────────────────────────────────────────────────────

onMounted(async () => {
  await configStore.loadConfig()
  await promptsStore.fetchPrompts()
  await filesStore.fetchFiles()
  await jobStore.restoreJob()

  // Auto-cleanup if enabled
  if (configStore.cleanup?.enabled) {
    try {
      await cleanupJobs(configStore.cleanup.max_age_hours)
    } catch {
      // Ignore cleanup errors on startup
    }
  }
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

    <!-- Main layout -->
    <div class="app-body">
      <!-- Sidebar -->
      <aside :class="['sidebar', { 'sidebar--collapsed': uiStore.sidebarCollapsed }]">
        <!-- Sidebar header: title + toggle -->
        <div class="sidebar__header">
          <h1 v-if="!uiStore.sidebarCollapsed" class="sidebar__title">SimpleETL</h1>
          <button class="sidebar__toggle" @click="uiStore.toggleSidebar()">
            <PanelLeftOpen v-if="uiStore.sidebarCollapsed" :size="18" />
            <PanelLeftClose v-else :size="18" />
          </button>
        </div>

        <!-- Navigation -->
        <nav class="sidebar__nav">
          <button
            v-for="panel in panels"
            :key="panel.id"
            :class="['sidebar__item', { 'sidebar__item--active': uiStore.activePanel === panel.id }]"
            :title="panel.label"
            @click="uiStore.setPanel(panel.id)"
          >
            <component :is="panel.icon" :size="18" />
            <span v-if="!uiStore.sidebarCollapsed" class="sidebar__item-label">{{ panel.label }}</span>
          </button>
        </nav>

        <!-- Spacer to push status to bottom -->
        <div class="sidebar__spacer" />

        <!-- Sidebar footer: active jobs + connection -->
        <div class="sidebar__footer">
          <div v-if="!uiStore.sidebarCollapsed" class="sidebar__active-jobs">
            Active jobs: {{ activeJobsCount }}
          </div>
          <div class="sidebar__connection">
            <ConnectionStatus :compact="uiStore.sidebarCollapsed" />
          </div>
        </div>
      </aside>

      <!-- Main content area -->
      <main class="app-main">
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

/* ── Body grid ───────────────────────────────────────────────── */
.app-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── Sidebar ─────────────────────────────────────────────────── */
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
  width: 52px;
  min-width: 52px;
}

.sidebar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid var(--border);
  min-height: 48px;
}

.sidebar__title {
  font-size: 16px;
  font-weight: 700;
  color: var(--fg-title);
  margin: 0;
  white-space: nowrap;
}

.sidebar__toggle {
  background: none;
  border: none;
  color: var(--fg-label);
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.sidebar__toggle:hover {
  background: rgba(59, 130, 246, 0.08);
  color: var(--fg-title);
}

.sidebar__nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px;
}

.sidebar__item {
  display: flex;
  align-items: center;
  gap: 10px;
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
  white-space: nowrap;
}

.sidebar__item:hover {
  background: rgba(59, 130, 246, 0.08);
  color: var(--fg-title);
}

.sidebar__item--active {
  background: var(--accent);
  color: white;
}

.sidebar__item-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar__spacer {
  flex: 1;
}

.sidebar__footer {
  border-top: 1px solid var(--border);
  padding: 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sidebar__active-jobs {
  font-size: 11px;
  color: var(--fg-label);
  white-space: nowrap;
}

.sidebar__connection {
  display: flex;
  align-items: center;
}

/* ── Main content ────────────────────────────────────────────── */
.app-main {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
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
