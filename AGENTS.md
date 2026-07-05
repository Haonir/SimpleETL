# AGENTS.md — SimpleETL

## What This Is

Vue 3 + FastAPI web app for text chunking + LLM SPR generation → Markdown/YAML output for RAG pipelines.

**Stack**: Python 3.10+, FastAPI, Vue 3, TypeScript, Pinia, Vite, OpenAI-compatible API (Ollama/LM Studio/vLLM), LangChain text splitters, PyMuPDF, python-docx, python-frontmatter.

---

## Commands

```bash
# Backend (from project root)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev  # Vite on :5173, proxies /api → :8000

# Tests
cd backend && pytest                    # Backend tests
cd frontend && npm test                 # Frontend tests (Vitest)
cd frontend && npm run test:watch       # Watch mode

# Build
cd frontend && npm run build            # → backend/app/static/
```

---

## Architecture

```
backend/app/
├── main.py              # FastAPI app, CORS, API key middleware
├── settings.py          # Pydantic Settings (env vars + config.json fallback)
├── api/v1/              # REST endpoints: files, jobs, websocket
├── etl/                 # ETL pipeline modules (extractor, splitter, llm_processor, packer)
├── services/            # Business logic (file_service, job_service, websocket_manager)
└── schemas/             # Pydantic v2 models

frontend/src/
├── stores/              # Pinia stores (config, files, job, prompts, ui)
├── services/            # API client (axios), WebSocket, configFile
├── components/          # Vue components (FileList, Settings, PromptLibrary, etc.)
└── types/               # TypeScript interfaces
```

**ETL Pipeline**: extract → chunks → (optional LLM) → pack → final/{spr|frontmatter|markdown|html}

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/main.py` | FastAPI app, API key middleware, router registration |
| `backend/app/settings.py` | AppSettings singleton, env vars with `APP_` prefix |
| `backend/app/etl/runner.py` | `run_etl_job()` — async entry point, runs sync pipeline in thread pool |
| `backend/app/services/job_service.py` | In-memory job registry (SQLite planned) |
| `backend/app/services/file_service.py` | File upload/list/delete, temp storage |
| `backend/app/services/websocket_manager.py` | WS connection rooms per job_id |
| `frontend/src/stores/config.ts` | Config store — localStorage persistence |
| `frontend/src/stores/job.ts` | Job state, WebSocket connection, progress tracking |
| `frontend/src/services/api.ts` | Axios REST client with API key interceptor |

---

## Config & Secrets

- **Config storage**: Frontend localStorage (not backend). Backend is stateless for config.
- **`config.json`**: Legacy file, not used by web app. Frontend loads from `public/config.json` defaults + localStorage.
- **API key auth**: Optional `APP_API_KEY` env var → `X-API-Key` header required.
- **`.env`**: Backend reads `APP_*` env vars. Frontend reads `VITE_*` vars.

---

## Gotchas

1. **`run_etl.py` is test-only** — manual integration test script, not part of production.
2. **In-memory registry** — JobService and FileService use dicts, not SQLite. Data lost on restart.
3. **Config is frontend-managed** — backend receives full config in job request body, doesn't store it.
4. **WebSocket per job** — connect to `/ws/{job_id}` after creating job. Client sends `{"type": "stop"}` to cancel.
5. **Russian UI labels** — some code comments and UI text in Russian. Keep consistent if editing.
6. **OCR optional** — `pytesseract` + system Tesseract required for scanned PDFs. Gracefully falls back.
7. **Singleton services** — `get_settings()`, `get_file_service()`, `get_job_service()`, `get_ws_manager()` return global instances.
8. **Pydantic v2** — all schemas use `BaseModel` from pydantic v2. `model_config` not `class Config`.
9.  **Vite proxy** — dev mode proxies `/api`, `/health`, `/ws` to `:8000`. No CORS issues in dev.

---

## Testing Patterns

**Backend** (pytest):
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
response = client.get("/health")
```

**Frontend** (Vitest + Vue Test Utils):
```typescript
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

beforeEach(() => { setActivePinia(createPinia()) })
```

- Mock `@/services/api` and `@/services/websocket` in component tests
- Store tests: test actions directly, mock API calls

---

## API Endpoints

```
POST   /api/v1/files/upload        # multipart file upload
GET    /api/v1/files               # list uploaded files
DELETE /api/v1/files/{id}          # delete file

POST   /api/v1/jobs                # create + start ETL job
GET    /api/v1/jobs                # list all jobs
GET    /api/v1/jobs/{id}           # get job status
DELETE /api/v1/jobs/{id}           # stop/delete job
GET    /api/v1/jobs/{id}/files     # list output files
GET    /api/v1/jobs/{id}/download  # ZIP download

WS     /ws/{job_id}                # real-time progress/logs
```

---

## Common Tasks

| Task | Where |
|------|-------|
| Add output format | `backend/app/etl/packer.py` + frontend Settings |
| Add input format | `backend/app/etl/extractor.py` `extract_text()` |
| Change chunking | `backend/app/etl/splitter.py` `split_to_chunks()` |
| Modify LLM request | `backend/app/etl/llm_processor.py` `process_with_llm()` |
| Add config field | Frontend: `stores/config.ts` + `types/config.ts` + Settings component |
| Add API endpoint | `backend/app/api/v1/` + Pydantic schema in `schemas/` |

---

## Planned (Not Yet Implemented)

- **SQLite persistence** — see `pipeline_refactor_plan.md`
- **3-phase parallel pipeline** — extract/split → LLM → pack with ThreadPoolExecutor
- **Job logs API** — `GET /jobs/{id}/logs` with JSON file storage
- **Job restore on refresh** — localStorage + API restore

---

## References

- `PLAN.md` — Full migration plan (Vue 3 + FastAPI)
- `config_migration.md` — Config storage migration details
- `pipeline_refactor_plan.md` — SQLite + parallel pipeline plan
- `docs/global_variables.json` — Global variable registry
- `docs/state.json` — Phase execution state
