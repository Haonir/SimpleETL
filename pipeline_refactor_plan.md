# Pipeline Refactor Plan: Parallel LLM + Persistence

**Цель**: Переработать ETL-пайплайн для параллельной LLM-обработки, обеспечить персистентность логов (JSON) и структурированных данных (SQLite).

**Дата**: 2026-07-05

---

## Архитектура до/после

### До (всё последовательно)
```
Job → for file in files:
        extract → split → [for chunk: LLM (один за раз)] → pack
        ↓
      следующий файл...
```

### После (три параллельных фазы с barriers)
```
Job → ┌─ Фаза 1: ThreadPool → extract + split ВСЕХ файлов параллельно
      │              ↓ barrier (все файлы нарезаны)
      ├─ Фаза 2: ThreadPool → LLM ВСЕХ чанков параллельно
      │              ↓ barrier (все чанки обработаны)
      └─ Фаза 3: ThreadPool → pack ВСЕХ файлов параллельно

      Логи:   threading-safe FileHandler → {job_dir}/logs.json
      Status: SQLite: jobs, files, job_outputs
```

---

## Схема БД

```sql
CREATE TABLE IF NOT EXISTS files (
    id            TEXT PRIMARY KEY,
    filename      TEXT NOT NULL,
    size_bytes    INTEGER NOT NULL,
    content_type  TEXT NOT NULL DEFAULT '',
    uploaded_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id              TEXT PRIMARY KEY,
    status          TEXT NOT NULL DEFAULT 'pending',
    file_ids        TEXT NOT NULL DEFAULT '[]',
    config          TEXT NOT NULL DEFAULT '{}',
    output_dir      TEXT,
    log_path        TEXT,
    file_count      INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL,
    started_at      TEXT,
    completed_at    TEXT,
    error_message   TEXT
);

CREATE TABLE IF NOT EXISTS job_outputs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id      TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    filename    TEXT NOT NULL,
    file_path   TEXT NOT NULL,
    size_bytes  INTEGER NOT NULL DEFAULT 0,
    format      TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_job_outputs_job_id ON job_outputs(job_id);
```

**Логи** — не в SQLite, а в `{job_dir}/logs.json` через Python `logging`.

---

## Структура каталогов

```
/tmp/SimpleETL/
├── uploads/                          # загруженные файлы (FileService)
│   ├── {uuid}.docx
│   └── {uuid}.pdf
├── jobs/
│   └── {job_id}/
│       ├── logs.json                 # ← логи (logging.FileHandler)
│       └── output/
│           └── {file_base}/
│               ├── chunks/           # промежуточные (cleanup удаляет)
│               ├── processed/        # промежуточные (cleanup удаляет)
│               └── final/            # результаты (остаются)
│                   ├── file.spr.md
│                   ├── file.frontmatter.md
│                   └── file.html
└── simpleetl.db                      # SQLite (jobs, files, job_outputs)
```

---

## Файлы для изменения

### Создать
| Файл | Назначение |
|------|-----------|
| `backend/app/db.py` | SQLite: init, get_db, get_cursor, schema creation |
| `backend/app/services/log_manager.py` | Logging: создание FileHandler per job, thread-safe |

### Переработать
| Файл | Что меняется |
|------|-------------|
| `backend/app/etl/runner.py` | Двухфазный пайплайн: extract/split → parallel LLM → pack |
| `backend/app/etl/llm_processor.py` | Новая функция `process_chunk()` для одного чанка (для ThreadPool) |
| `backend/app/services/file_service.py` | `_files` dict → SQLite (`files` таблица) |
| `backend/app/services/job_service.py` | `_jobs` dict → SQLite (`jobs` таблица) + `add_log`/`get_logs` → JSON-файл |
| `backend/app/api/v1/jobs.py` | Новый эндпоинт `GET /jobs/{id}/logs` |
| `backend/app/api/v1/files.py` | Адаптация под SQLite backend |
| `backend/app/etl/callbacks.py` | `make_log_cb` пишет в JSON-файл через logging |
| `backend/app/main.py` | Инициализация БД + recovery interrupted jobs |
| `backend/app/schemas/job.py` | Новые схемы: `JobLogEntry`, `JobLogsResponse`, `JobOutputItem` |
| `frontend/src/stores/job.ts` | `restoreJob()` + загрузка логов из API |
| `frontend/src/App.vue` | `onMounted`: `jobStore.restoreJob()` |
| `frontend/src/components/Settings/ProcessingSettings.vue` | Настройки cleanup retention |
| `frontend/src/components/Settings/LLMSettings.vue` | Настройка `max_workers` (уже есть) |

### Не трогать
| Файл | Почему |
|------|--------|
| `etl/extractor.py` | Чистая ETL-логика, без state |
| `etl/splitter.py` | Чистая ETL-логика, без state |
| `etl/packer.py` | Чистая ETL-логика, без state |
| `etl/image_utils.py` | Утилита |
| `services/websocket_manager.py` | Runtime-only |
| `services/config_service.py` | Уже удалён или не используется |
| Frontend: Prompts, Config stores | Чисто фронт |

---

## Пошаговый план

### Фаза 1: SQLite ядро

**Создать `backend/app/db.py`**:
```python
import sqlite3
import threading
from pathlib import Path
from contextlib import contextmanager

_local = threading.local()
_db_path: Path | None = None

def init_db(db_path: str = "simpleetl.db"):
    global _db_path
    _db_path = Path(db_path)
    conn = _get_connection()
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _create_tables(conn)
    _recover_interrupted_jobs(conn)

def _get_connection() -> sqlite3.Connection:
    if not hasattr(_local, "conn") or _local.conn is None:
        _local.conn = sqlite3.connect(str(_db_path), check_same_thread=False)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn

@contextmanager
def get_cursor():
    conn = _get_connection()
    cur = conn.cursor()
    try:
        yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise

def _create_tables(conn): ...
def _recover_interrupted_jobs(conn): ...
```

**Инициализация в `main.py`**:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.db import init_db
    init_db()
    yield
```

### Фаза 2: FileService → SQLite

**`services/file_service.py`** — заменить `_files: dict` на SQLite:

| Метод | Было (dict) | Стало (SQLite) |
|-------|-------------|----------------|
| `upload()` | `_files[id] = item` | `INSERT INTO files (...)` |
| `list_files()` | `list(_files.values())` | `SELECT * FROM files ORDER BY uploaded_at` |
| `get_file(id)` | `_files.get(id)` | `SELECT * FROM files WHERE id = ?` |
| `delete(id)` | `del _files[id]` | `DELETE FROM files WHERE id = ?` |

**Оставить в RAM**:
- `_upload_dir` — путь к диск-файлам
- `_file_data` — bytes при загрузке (временно)

### Фаза 3: JobService → SQLite

**`services/job_service.py`** — заменить `_jobs: dict` на SQLite:

| Метод | Было | Стало |
|-------|------|-------|
| `create()` | `_jobs[id] = job` | `INSERT INTO jobs (...)` |
| `get(id)` | `_jobs.get(id)` | `SELECT * FROM jobs WHERE id = ?` |
| `list_all()` | `list(_jobs.values())` | `SELECT * FROM jobs ORDER BY created_at DESC` |
| `update_status()` | `job.status = ...` | `UPDATE jobs SET status=?, ... WHERE id=?` |
| `delete()` | `del _jobs[id]` | `DELETE FROM jobs WHERE id = ?` |

**Новые методы**:
```python
def get_logs(self, job_id: str) -> list[dict]:
    """Read logs.json from job_dir."""
    log_path = self._get_log_path(job_id)
    if not log_path.exists():
        return []
    entries = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            entries.append(json.loads(line))
    return entries

def delete_job_files(self, job_id: str) -> None:
    """Delete job directory from disk + DB records."""
    job = self.get(job_id)
    if job and job.output_dir:
        shutil.rmtree(job.output_dir, ignore_errors=True)
    # delete from job_outputs, jobs (CASCADE)
    with get_cursor() as cur:
        cur.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
```

**Оставить в RAM**:
- `_stop_flags` — проверяется из ETL-потока, performance-critical

### Фаза 4: Логирование через JSON-файл

**Создать `backend/app/services/log_manager.py`**:
```python
import json
import logging
import threading
from pathlib import Path

_lock = threading.Lock()

def create_job_logger(job_id: str, job_dir: Path) -> logging.Logger:
    """Create a thread-safe logger that writes JSON lines to {job_dir}/logs.json."""
    logger = logging.getLogger(f"etl.{job_id}")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    log_path = job_dir / "logs.json"
    handler = logging.FileHandler(log_path, encoding="utf-8")
    formatter = logging.Formatter('{"timestamp":"%(asctime)s","level":"%(levelname)s","message":"%(message)s"}', datefmt='%Y-%m-%dT%H:%M:%S')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def make_log_cb(logger: logging.Logger) -> callable:
    """Create a thread-safe log callback for ETL pipeline."""
    def cb(message: str) -> None:
        with _lock:
            logger.info(message)
    return cb
```

**Изменения в `callbacks.py`**:
```python
def create_callbacks(ws_manager, job_id, loop, job_service, job_logger):
    log_cb = make_log_cb(job_logger)  # ← пишет в файл
    # ... остальное без изменений
```

### Фаза 5: Трёхфазный параллельный пайплайн

**`etl/runner.py`** — общая структура:

```python
async def run_etl_job(job_id, file_paths, config, job_service, ws_manager, log_cb):
    max_workers = flat_config.get("max_workers", 2)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        # ── Фаза 1: extract + split (параллельно) ──
        log_cb("--- Phase 1: Extract & Split ---")
        registry = await _phase_prepare(pool, file_paths, flat_config, log_cb, stop_cb)

        if stop_cb(): return

        # ── Фаза 2: LLM (параллельно) ──
        log_cb("--- Phase 2: LLM Processing ---")
        success = await _phase_llm(pool, registry, flat_config, log_cb, stop_cb, progress_cb)

        if stop_cb(): return

        # ── Фаза 3: pack (параллельно) ──
        log_cb("--- Phase 3: Packing ---")
        await _phase_pack(pool, registry, flat_config, log_cb)

        log_cb("🎉 ETL job completed!")
```

**Фаза 1 — extract + split**:
```python
async def _phase_prepare(pool, file_paths, flat_config, log_cb, stop_cb):
    """Параллельно extract + split для всех файлов."""
    loop = asyncio.get_event_loop()
    registry = {}  # {base_name: {chunks_dir, processed_dir, final_dir, chunk_paths}}

    futures = {}
    for file_path in file_paths:
        future = loop.run_in_executor(pool, _extract_and_split, file_path, flat_config, log_cb)
        futures[future] = file_path

    for future in as_completed(futures):
        if stop_cb():
            for f in futures: f.cancel()
            return None
        base_name, chunk_paths, dirs = future.result()
        registry[base_name] = {"chunk_paths": chunk_paths, **dirs}

    return registry

def _extract_and_split(file_path, flat_config, log_cb):
    """Extract text + split into chunks (sync, runs in thread)."""
    text = extract_text(file_path, log_cb)
    chunk_files = split_to_chunks(text, chunks_dir, base_name, ...)
    return base_name, chunk_files, {"chunks_dir": ..., "processed_dir": ..., "final_dir": ...}
```

**Фаза 2 — LLM**:
```python
async def _phase_llm(pool, registry, flat_config, log_cb, stop_cb, progress_cb):
    """Параллельно LLM-обработка всех чанков."""
    loop = asyncio.get_event_loop()
    total = sum(len(r["chunk_paths"]) for r in registry.values())
    counter = {"done": 0}
    lock = threading.Lock()

    def process_chunk(chunk_path, processed_path, config):
        """Обработка одного чанка (sync, runs in thread)."""
        if processed_path.exists():
            return "skip"
        client = OpenAI(base_url=config["base_url"], api_key=config["api_key"])
        response = client.chat.completions.create(...)
        with open(processed_path, "w") as f:
            f.write(response.choices[0].message.content)
        with lock:
            counter["done"] += 1
            progress_cb(counter["done"] / total * 100, 0, 0)

    futures = []
    for base_name, info in registry.items():
        for chunk_path in info["chunk_paths"]:
            processed_path = info["processed_dir"] / chunk_path.name
            future = pool.submit(process_chunk, chunk_path, processed_path, flat_config)
            futures.append(future)

    for future in as_completed(futures):
        if stop_cb():
            for f in futures: f.cancel()
            return False
        try:
            future.result()
        except Exception as e:
            log_cb(f"⚠️ LLM error: {e}")  # fail-continue

    return True
```

**Фаза 3 — pack**:
```python
async def _phase_pack(pool, registry, flat_config, log_cb):
    """Параллельно pack для всех файлов."""
    loop = asyncio.get_event_loop()
    output_format = flat_config.get("output_format", "spr")

    futures = []
    for base_name, info in registry.items():
        future = loop.run_in_executor(
            pool, pack_outputs,
            info["processed_dir"], info["final_dir"], base_name, output_format, log_cb,
        )
        futures.append(future)

    for future in as_completed(futures):
        future.result()  # propagate exceptions
```

### Фаза 6: API — логи + job outputs

**`api/v1/jobs.py`** — новые эндпоинты:

```python
@router.get("/jobs/{job_id}/logs", response_model=JobLogsResponse)
async def get_job_logs(job_id: str):
    service = get_job_service()
    logs = service.get_logs(job_id)
    return JobLogsResponse(logs=logs, total=len(logs))

@router.get("/jobs/{job_id}/outputs", response_model=JobOutputsResponse)
async def get_job_outputs(job_id: str):
    service = get_job_service()
    outputs = service.get_outputs(job_id)
    return JobOutputsResponse(outputs=outputs, total=len(outputs))
```

**Новые Pydantic-схемы**:
```python
class JobLogEntry(BaseModel):
    timestamp: str
    level: str
    message: str

class JobLogsResponse(BaseModel):
    logs: list[JobLogEntry]
    total: int

class JobOutputItem(BaseModel):
    filename: str
    file_path: str
    size_bytes: int
    format: str

class JobOutputsResponse(BaseModel):
    outputs: list[JobOutputItem]
    total: int
```

### Фаза 7: Фронтенд — восстановление

**`stores/job.ts`**:
```typescript
function startJob(jobId: string) {
    currentJobId.value = jobId
    localStorage.setItem('simpleetl_current_job_id', jobId)
    // ...
}

async function restoreJob() {
    const savedId = localStorage.getItem('simpleetl_current_job_id')
    if (!savedId) return
    try {
        const response = await getJob(savedId)
        currentJobId.value = savedId
        status.value = response.job.status
        const logsResponse = await getJobLogs(savedId)
        logs.value = logsResponse.logs
    } catch {
        localStorage.removeItem('simpleetl_current_job_id')
    }
}
```

**`App.vue`** — в `onMounted`:
```typescript
onMounted(async () => {
    await configStore.loadConfig()
    await promptsStore.fetchPrompts()
    await filesStore.fetchFiles()
    await jobStore.restoreJob()
})
```

### Фаза 8: Cleanup + Retention

**Настройки в UI** (Processing tab):
- Auto-cleanup: `24h / 7d / 30d / Never`
- Кнопка «Очистить историю» в JobHistory

**Логика**:
- Cleanup удаляет `chunks/` и `processed/` (промежуточные)
- `output/` и `logs.json` остаются
- При новом job: проверяем старые completed jobs, удаляем если старше retention
- Ручная очистка: удалить все completed jobs + их файлы

---

## Порядок выполнения

| # | Фаза | Сложность | Ожидаемый результат |
|---|------|-----------|---------------------|
| 1 | `db.py` + init в `main.py` | 🟢 | БД создаётся, recovery работает |
| 2 | `log_manager.py` + callbacks | 🟢 | Логи пишутся в JSON, thread-safe |
| 3 | FileService → SQLite | 🟡 | Файлы переживают рестарт |
| 4 | JobService → SQLite | 🟡 | Jobs + outputs переживают рестарт |
| 5 | **3-фазный параллельный пайплайн** | 🔴 | Extract/split → LLM → pack, все параллельно |
| 6 | API: /jobs/{id}/logs + outputs | 🟢 | Фронт может запрашивать логи |
| 7 | Фронт: restoreJob + logs | 🟢 | UI восстанавливается после рефреша |
| 8 | Cleanup + retention | 🟢 | Настройки + автоочистка |

**Общая оценка**: ~3-5 часов (упрощённый пайплайн компенсирует добавление SQLite)

---

## Риски и митигация

| Риск | Митигация |
|------|-----------|
| SQLite concurrent writes | WAL mode + текущая нагрузка минимальна (~50 записей/job) |
| LLM concurrency > server limit | `max_workers` дефолт 2, adaptive retry на 429 |
| Один чанк падает → остальные продолжают | Fail-continue, помечаем в логах |
| Stop → активные LLM-запросы ещё работают | Ждём до 30с через `pool.shutdown(wait=True, cancel_futures=True)` |
| Бэк упал mid-job | Recovery: `UPDATE jobs SET status='error'` при старте |
| Лог-файл обрезан при crash | Append-only JSON lines, одна обрезанная строка — норма |
| `_file_data` в RAM при большом объёме | MVP: принимаем. Потом — shutil.copy2 на диск |
| OpenAI client threading | `openai>=1.0` 使用 httpx с connection pool — работает в threads |

---

## Recovery при старте

```python
def _recover_interrupted_jobs():
    """Mark any 'running'/'pending' jobs as 'error' on startup."""
    with get_cursor() as cur:
        cur.execute(
            "UPDATE jobs SET status='error', error_message='Interrupted by server restart' "
            "WHERE status IN ('running', 'pending')"
        )
```
