# Migration Plan: SimpleETL → Vue 3 + FastAPI (Web App, Electron-Ready)

## Status Update

The **backend scaffold (`backend/app/`)** has already been created with the full structure described in this plan. The project is ready for development work following the phases outlined below.

> **Note:** The `.venv-core` virtual environment for the desktop app (`core/`) is now located at `core/.venv-core/`, not at the project root.

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (Vue 3 SPA)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ FileList │  │Settings  │  │PromptLib │  │ Progress/Logs  │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬────────┘  │
│       │             │             │                 │           │
│       ▼             ▼             ▼                 ▼           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              Pinia Store (State + WebSocket)             │   │
│  └─────────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────────┘
                           │ WebSocket (progress, logs, status)
                           │ REST (config, file upload, job control)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ /api/v1  │  │  WS /ws  │  │  ETL     │  │  Config        │  │
│  │ routes   │  │  manager │  │  runner  │  │  manager       │  │
│  └──────────┘  └──────────┘  └────┬─────┘  └────────────────┘  │
│                                    │                              │
│                           ┌────────▼────────┐                     │
│                           │ core/etl_pipeline.py │ (async-adapted)     │
│                           └─────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
```

**Future Electron**: Wrap the same Vue build (`dist/`) with Electron main process pointing to `http://localhost:8000` or served via `file://` protocol.

---

## 2. Backend (FastAPI) — Implementation Plan

### 2.1 Project Structure
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI app, lifespan, CORS, static files
│   ├── config.py            # Pydantic Settings (env + config.json)
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── config.py        # Config schemas (request/response)
│   │   ├── job.py           # Job status, progress, log schemas
│   │   └── file.py          # File upload, file list schemas
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── config.py    # GET/POST /config
│   │   │   ├── files.py     # POST /files/upload, GET /files, DELETE
│   │   │   ├── jobs.py      # POST /jobs, GET /jobs/{id}, DELETE
│   │   │   └── prompts.py   # CRUD for prompt library
│   │   └── websocket.py     # WebSocket endpoint /ws/{job_id}
│   ├── services/
│   │   ├── __init__.py
│   │   ├── config_service.py    # Load/save config.json (reuse config_manager)
│   │   ├── file_service.py      # Handle uploads, temp storage
│   │   ├── job_service.py       # Job lifecycle, background tasks
│   │   └── websocket_manager.py # Connection manager for WS
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── runner.py      # Async wrapper around process_batch
│   │   └── callbacks.py   # Progress/log callbacks → WS broadcast
│   └── static/            # Vue build output (served in prod)
├── config.json            # Runtime config (same location)
├── requirements.txt
├── pyproject.toml
└── Dockerfile (optional)
```

### 2.2 Key Backend Components

| Component | Responsibility | Migration Notes |
|-----------|---------------|-----------------|
| `config_service.py` | Load/save `config.json` | **Reuse** `core/config_manager.py` logic; add Pydantic validation |
| `file_service.py` | Save uploads to temp dir, cleanup | New: `tempfile` + background cleanup task |
| `job_service.py` | Create/manage ETL jobs, track status | New: job registry (in-memory + persistence optional) |
| `websocket_manager.py` | Broadcast progress/logs to clients | New: `ConnectionManager` class with `job_id` rooms |
| `etl/runner.py` | Run `process_batch` in thread pool, emit callbacks | **Adapt** `etl_pipeline.process_batch` to async + callbacks |
| `etl/callbacks.py` | Convert pipeline callbacks → WS messages | New: `ProgressCallback`, `LogCallback`, `StopCheckCallback` |

### 2.3 API Contract (REST)

```
GET    /api/v1/config              → ConfigResponse
POST   /api/v1/config              → ConfigResponse (save)
GET    /api/v1/prompts             → PromptLibraryResponse
POST   /api/v1/prompts             → PromptResponse (create)
DELETE /api/v1/prompts/{name}      → 204
POST   /api/v1/files/upload        → FileListResponse (multipart)
GET    /api/v1/files               → FileListResponse
DELETE /api/v1/files/{id}          → 204
POST   /api/v1/jobs                → JobResponse (start ETL)
GET    /api/v1/jobs                → JobListResponse
GET    /api/v1/jobs/{id}           → JobResponse
DELETE /api/v1/jobs/{id}           → 204 (stop job)
WS     /api/v1/ws/{job_id}         → WebSocket (progress, logs, done)
```

### 2.4 WebSocket Message Types

```python
# Server → Client
{"type": "progress", "job_id": "...", "file_idx": 0, "chunk_pct": 45, "global_pct": 12}
{"type": "log", "job_id": "...", "level": "info", "message": "Processing chunk 3..."}
{"type": "status", "job_id": "...", "status": "running|completed|stopped|error"}
{"type": "error", "job_id": "...", "message": "LLM connection failed"}
{"type": "done", "job_id": "...", "output_dir": "/path/to/output"}

# Client → Server
{"type": "stop", "job_id": "..."}
```

### 2.5 ETL Pipeline Adaptation

Current `process_batch` is synchronous with threading. Need async wrapper:

```python
# etl/runner.py
async def run_etl_job(job_id: str, file_paths: list[str], cfg: dict, ws_manager: WSManager):
    loop = asyncio.get_event_loop()
    
    def progress_cb(chunk_pct, global_pct, file_idx):
        asyncio.run_coroutine_threadsafe(
            ws_manager.broadcast(job_id, {"type": "progress", ...}), loop
        ).result()
    
    def log_cb(msg):
        asyncio.run_coroutine_threadsafe(
            ws_manager.broadcast(job_id, {"type": "log", "message": msg}), loop
        ).result()
    
    def stop_cb():
        return job_service.is_stopped(job_id)
    
    # Run sync process_batch in thread pool
    await loop.run_in_executor(
        None, 
        lambda: process_batch(file_paths, cfg, progress_cb, log_cb, stop_cb, cfg["max_workers"])
    )
```

---

## 3. Frontend (Vue 3 + TypeScript) — Implementation Plan

### 3.1 Project Structure
```
frontend/
├── src/
│   ├── main.ts                    # App entry, Pinia, Router, WS plugin
│   ├── App.vue                    # Root layout
│   ├── components/
│   │   ├── FileList/
│   │   │   ├── FileList.vue       # Main list with drag-drop, tooltips
│   │   │   ├── FileItem.vue       # Single row (name, progress, actions)
│   │   │   └── FileDropZone.vue   # Drag-drop area
│   │   ├── Settings/
│   │   │   ├── ProcessingParams.vue   # chunk_size, overlap, workers, format
│   │   │   ├── LLMProvider.vue        # model, base_url, api_key
│   │   │   └── OutputOptions.vue      # cleanup, skip_llm
│   │   ├── PromptLibrary/
│   │   │   ├── PromptSelector.vue     # Dropdown + save/delete buttons
│   │   │   ├── PromptEditor.vue       # Textarea with context menu
│   │   │   └── SavePromptDialog.vue   # Modal for new prompt name
│   │   ├── Progress/
│   │   │   ├── FileProgressBar.vue    # Per-file progress
│   │   │   └── GlobalProgressBar.vue  # Overall progress
│   │   ├── LogPanel/
│   │   │   └── LogPanel.vue           # Timestamped log with auto-scroll
│   │   └── UI/
│   │       ├── Button.vue
│   │       ├── Input.vue
│   │       ├── Select.vue
│   │       ├── Checkbox.vue
│   │       └── Modal.vue
│   ├── views/
│   │   └── Dashboard.vue           # Main view (single page app)
│   ├── stores/
│   │   ├── config.ts               # Config state + persistence
│   │   ├── files.ts                # File list, upload, selection
│   │   ├── prompts.ts              # Prompt library CRUD
│   │   ├── job.ts                  # Job state, WS connection
│   │   └── ui.ts                   # Tooltips, modals, notifications
│   ├── services/
│   │   ├── api.ts                  # Axios/Fetch wrapper for REST
│   │   ├── websocket.ts            # WS connection manager
│   │   └── file.ts                 # File upload helpers
│   ├── types/
│   │   ├── config.ts
│   │   ├── job.ts
│   │   ├── file.ts
│   │   └── prompt.ts
│   ├── composables/
│   │   ├── useWebSocket.ts         # WS connection + message handling
│   │   ├── useFileUpload.ts        # Drag-drop + upload logic
│   │   └── useContextMenu.ts       # Right-click menu (cut/copy/paste)
│   ├── styles/
│   │   ├── variables.css           # CSS custom properties (colors, spacing)
│   │   ├── global.css              # Reset, base styles
│   │   └── scoped/                 # Component-scoped styles (auto via `<style scoped>`)
│   └── utils/
│       ├── format.ts               # Date, bytes, duration formatting
│       └── validation.ts           # Form validators
├── index.html
├── vite.config.ts
├── tsconfig.json
├── package.json
└── .env.example
```

### 3.2 Key Frontend Features Mapping

| Current Feature | Vue Component(s) | Notes |
|----------------|------------------|-------|
| File list + tooltips | `FileList`, `FileItem` | `<style scoped>` for hover tooltip; `@mouseenter`/`@mouseleave` |
| Drag-drop upload | `FileDropZone`, `useFileUpload` | `DataTransfer` API + `FormData` |
| Progress bars (2) | `FileProgressBar`, `GlobalProgressBar` | Reactive from Pinia store |
| Settings panels | `ProcessingParams`, `LLMProvider`, `OutputOptions` | Bound to `config` store |
| Prompt library | `PromptSelector`, `PromptEditor`, `SavePromptDialog` | `prompts` store + REST sync |
| Context menu | `useContextMenu` composable | Replicates Tkinter right-click menu |
| Log panel | `LogPanel` | Virtualized list for performance |
| Start/Stop button | `Dashboard` toolbar | Job store controls |
| OCR hint | `FileList` banner | Conditional render from `files` store |

### 3.3 State Management (Pinia)

```typescript
// stores/job.ts
export const useJobStore = defineStore('job', () => {
  const currentJob = ref<Job | null>(null)
  const ws = ref<WebSocket | null>(null)
  const progress = ref<Record<number, number>>({}) // file_idx → chunk_pct
  const globalProgress = ref(0)
  const logs = ref<LogEntry[]>([])
  const isRunning = computed(() => currentJob.value?.status === 'running')
  
  function connect(jobId: string) { /* WS setup */ }
  function handleMessage(msg: WSMessage) { /* update progress/logs */ }
  function startJob(config: JobConfig) { /* POST /jobs → connect WS */ }
  function stopJob() { /* send WS stop → update status */ }
  
  return { currentJob, progress, globalProgress, logs, isRunning, connect, startJob, stopJob }
})
```

---

## 4. Development Workflow

### 4.1 Dev Mode (Hot Reload)
```bash
# Terminal 1: Backend
cd backend && uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev  # Vite on :5173, proxy /api → :8000
```

### 4.2 Production Build
```bash
# Frontend builds to backend/app/static/
cd frontend && npm run build

# Backend serves SPA + API
cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 4.3 Electron Wrapper (Future)
```javascript
// electron/main.js
const { app, BrowserWindow } = require('electron')
const path = require('path')

function createWindow() {
  const win = new BrowserWindow({ width: 1200, height: 800 })
  if (process.env.NODE_ENV === 'development') {
    win.loadURL('http://localhost:5173')
  } else {
    // Serve via FastAPI or static files
    win.loadFile(path.join(__dirname, '../backend/app/static/index.html'))
  }
}
```

---

## 5. Migration Phases

### Phase 1: Backend Foundation (Week 1)
- [ ] FastAPI project setup with `pyproject.toml`, `uvicorn`, `pydantic-settings`
- [ ] Config service (reuse `core/config_manager.py` + Pydantic schemas)
- [ ] REST endpoints: `/config`, `/prompts` CRUD
- [ ] WebSocket manager + `/ws/{job_id}` endpoint
- [ ] File upload endpoint (multipart → temp dir)
- [ ] Job service with in-memory registry
- [ ] ETL runner: async wrapper around `process_batch` with WS callbacks

### Phase 2: Frontend Core (Week 2)
- [ ] Vue 3 + TypeScript + Pinia + Vite setup
- [ ] Component library (Button, Input, Select, Checkbox, Modal, ProgressBar)
- [ ] Layout: Dashboard with left panel (scrollable) + right panel
- [ ] Config store + REST sync (load/save settings)
- [ ] Prompt library store + UI (selector, editor, save/delete dialogs)
- [ ] File list with drag-drop, tooltips, selection
- [ ] Log panel with auto-scroll

### Phase 3: Integration & Real-time (Week 3)
- [ ] WebSocket connection in `job` store
- [ ] Start job flow: POST `/jobs` → connect WS → update UI from messages
- [ ] Progress bars (per-file + global) driven by WS `progress` messages
- [ ] Log panel driven by WS `log` messages
- [ ] Stop button → WS `stop` message → job cancellation
- [ ] Error handling + toast notifications

### Phase 4: Polish & Electron Prep (Week 4)
- [ ] Scoped CSS refinement (design system variables)
- [ ] Responsive layout (mobile-friendly for future)
- [ ] Keyboard shortcuts (Ctrl+C/V/X/A/Z + context menu)
- [ ] OCR availability detection + hint banner
- [ ] Config persistence (localStorage backup + config.json sync)
- [ ] Electron main process + build script
- [ ] Dockerfile for containerized deployment

---

## 6. Critical Decisions & Tradeoffs

| Decision | Recommendation | Rationale |
|----------|----------------|-----------|
| **State sync** | Pinia + WS (server-authoritative) | Single source of truth; WS pushes updates |
| **File storage** | Temp dir + cleanup job | Avoid DB for files; simple `tempfile` + TTL |
| **Job persistence** | In-memory (MVP) → SQLite later | Keep simple; add persistence if needed |
| **Auth** | None (local dev) → optional API key | Add later if multi-user needed |
| **PDF/OCR** | Backend-only (system deps) | Frontend never handles binary processing |
| **Output files** | ZIP download endpoint | `/api/v1/jobs/{id}/download` → `FileResponse` |

---

## 7. Reuse vs Rewrite Checklist

| Module | Action |
|--------|--------|
| `core/config_manager.py` | **Reuse** → `services/config_service.py` with Pydantic |
| `core/etl_pipeline.py` | **Reuse** logic; wrap in `services/etl/runner.py` |
| `core/main_ui.py` GUI | **Rewrite** as Vue components |
| `FileListBox` | **Rewrite** → `FileList` + `FileItem` (Vue) |
| Prompt library UI | **Rewrite** → `PromptLibrary` components |
| Context menu | **Rewrite** → `useContextMenu` composable |
| Progress/log callbacks | **Adapt** → `etl/callbacks.py` → WS broadcast |

---

## 8. Open Questions

1. **Output file access**: Should completed job results be downloadable as ZIP via API, or served from a static output directory?
2. **Concurrent jobs**: Allow multiple simultaneous ETL jobs, or queue sequentially?
3. **Config persistence**: Keep `config.json` as single source, or also mirror to frontend `localStorage` for offline resilience?
4. **LLM streaming**: Current pipeline waits for full response. Want token-by-token streaming to UI (requires OpenAI `stream=True` + WS chunks)?
5. **Testing**: Add minimal backend tests (pytest + httpx) and frontend component tests (Vitest + Vue Test Utils)?