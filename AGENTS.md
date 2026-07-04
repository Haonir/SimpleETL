# AGENTS.md — SimpleETL Development Guide

## Project Overview
**SimpleETL** — Desktop ETL app (CustomTkinter GUI) for text chunking + LLM SPR generation → Markdown + YAML Front Matter output for RAG pipelines.

**Stack**: Python 3.10+, CustomTkinter, OpenAI-compatible API (Ollama/LM Studio/vLLM), LangChain text splitters, PyMuPDF, python-docx, python-frontmatter, pytesseract (optional OCR).

**Entry point**: `python -m core.main_ui` (requires activated `.venv-core`)

> **Note**: A migration to **Vue 3 + FastAPI (web app)** is planned. See `PLAN.md` for details.

---

## Commands

```bash
# Setup
python3 -m venv .venv-core
source .venv-core/bin/activate  # Windows: .venv-core\Scripts\Activate.ps1
pip install -r core/requirements.txt

# Run (with core venv)
python -m core.main_ui

# Build (PyInstaller)
pyinstaller --onefile --windowed --name SimpleETL core/main_ui.py
```

> **Note**: For PDF OCR, install system Tesseract-OCR separately (`apt install tesseract-ocr` / `brew install tesseract` / Windows installer).

---

## Architecture

```
core/main_ui.py        → GUI (CustomTkinter), thread orchestration, config UI
core/etl_pipeline.py   → Оркестратор: process_batch() + process_pipeline()
core/extract/extractor.py  → Извлечение текста из файлов (.txt/.md/.docx/.pdf)
core/chunk/splitter.py     → Нарезка на чанки (RecursiveCharacterTextSplitter)
core/llm/analyzer.py       → LLM-анализ через OpenAI-compatible API
core/pack/packer.py        → Упаковка в итоговые .md файлы (3 формата)
core/cleanup/cleaner.py    → Автоочистка временных папок
core/config_manager.py     → JSON config persistence (config.json, Frozen/non-frozen aware)
```

**ETL Pipeline** (per file, parallelized via `ThreadPoolExecutor`):
1. **Extract** (`core/extract/extractor.py`) → text from `.txt/.md/.docx/.pdf` (PyMuPDF + optional Tesseract OCR)
2. **Chunk** (`core/chunk/splitter.py`) → `RecursiveCharacterTextSplitter(chunk_size, chunk_overlap)` → `raw/*.txt`
3. **LLM** (optional, `core/llm/analyzer.py`) → OpenAI-compatible API → `processed/*.txt` (SPR/YAML)
4. **Pack** (`core/pack/packer.py`) → parse YAML Front Matter → 3 output formats → `final/*.md`
5. **Cleanup** (optional, `core/cleanup/cleaner.py`) → remove `raw/`, `processed/`

---

## Key Files & Conventions

| File | Purpose | Notes |
|------|---------|-------|
| `core/main_ui.py:145` | `SimpleETLApp` — main GUI class | Single-threaded GUI; heavy work in `threading.Thread` |
| `core/etl_pipeline.py` | `process_batch()` + `process_pipeline()` — оркестратор ETL | Coordinates all stages via ThreadPoolExecutor |
| `core/extract/extractor.py` | `extract_text_from_file()` — извлечение текста | Supports TXT/MD/DOCX/PDF with optional OCR (PyMuPDF + Tesseract) |
| `core/chunk/splitter.py` | `split_and_save()` — нарезка и сохранение чанков | Uses RecursiveCharacterTextSplitter, saves to raw/*.txt |
| `core/llm/analyzer.py` | `analyze_chunk()` — LLM-запрос + SPR генерация | OpenAI-compatible API call with temperature 0.2 |
| `core/pack/packer.py` | `pack_outputs()` — упаковка в 3 формата | Parses YAML Front Matter → spr/frontmatter/markdown |
| `core/cleanup/cleaner.py` | `clean_temp_dirs()` — автоочистка | Removes raw/ and processed/ dirs after processing |
| `core/config_manager.py:10` | `CONFIG_FILE` path | Handles PyInstaller `--onefile` via `sys.frozen` |

---

## Running / Testing

**No automated tests exist.** Manual verification only:

```bash
# 1. Activate venv
source .venv/bin/activate

# 2. Run GUI
python -m core.main_ui

# 3. Manual test flow:
#    - Add .txt/.md/.docx/.pdf files
#    - Set LLM endpoint (Ollama default: http://localhost:11434/v1, key: ollama)
#    - Choose chunk size / overlap / workers / output format
#    - Select/Edit prompt
#    - Click "▶ Начать обработку"
#    - Verify output in `<filename>/` folder with numbered `.md` files
```

**Requirements for full test**: Running OpenAI-compatible LLM server (Ollama/LM Studio/vLLM).

---

## Config & Secrets

- **`config.json` is in `.gitignore`** — contains API keys. Never commit.
- `core/config_manager.py` handles frozen (PyInstaller) vs dev paths via `sys.frozen`.
- Settings persist on "💾 Сохранить настройки" button click (`core/main_ui.py:685`).

---

## Key Implementation Details

**Parallel processing** (`core/etl_pipeline.py:300`):
- `ThreadPoolExecutor(max_workers=cfg["max_workers"])` per file
- Per-file progress tracked via `file_progress` array + callbacks
- Global progress = mean of per-file chunk progress

**Callback-based progress system** (`core/etl_pipeline.py:310-318`, `core/main_ui.py:812-823`):
- `make_progress_cb(file_idx)` creates isolated callback per file
- Callback signature: `progress_callback(chunk_pct, global_pct, file_idx)`
- UI updates via `root.after(0, callback, ...)` from background thread

**LLM call** (`core/etl_pipeline.py:170`):
- Uses `openai.OpenAI(base_url, api_key).chat.completions.create()`
- Temperature fixed at 0.2, system prompt from UI/config

**Output formats** (`core/etl_pipeline.py:196-270`):
- `spr` — Custom markdown with YAML-style meta block + "SPR" sections
- `frontmatter` — Valid YAML Front Matter via `frontmatter.dumps()`
- `markdown` — Raw LLM output or chunk text

**PDF OCR** (`core/etl_pipeline.py:30-35`):
- Optional, requires `pytesseract` + system Tesseract
- `OCR_AVAILABLE` checked at import time (`core/etl_pipeline.py:24`)
- Falls back gracefully if unavailable (logs warning)

**GUI threading** (`core/main_ui.py:784`):
- Pipeline runs in `threading.Thread(daemon=True)`
- UI callbacks via `root.after(0, callback, ...)`
- Stop flag: `self.stop_requested` checked via callback

---

## Common Tasks

| Task | Location |
|------|----------|
| Add output format | `core/etl_pipeline.py:196` + UI combo box `core/main_ui.py` |
| Add input format | `core/etl_pipeline.py:37` `extract_text_from_file()` |
| Change chunking strategy | `core/etl_pipeline.py:115` `RecursiveCharacterTextSplitter` |
| Modify LLM request | `core/etl_pipeline.py:170` `client.chat.completions.create()` |
| Add config key | `core/config_manager.py:12` `save_config()` + `core/main_ui.py:685` save + `load_settings()` |

---

## Gotchas

- **config.json has secrets** — in `.gitignore`, don't commit
- **PyInstaller frozen mode** — `core/config_manager.py:5-8` handles `sys._MEIPASS` / `sys.executable`
- **Tkinter context menu** — right-click bindings on text widgets (`core/main_ui.py:252`)
- **Progress callbacks** — per-file progress via closure factory `make_progress_cb()` (`core/etl_pipeline.py:310`)
- **Stop button** — sets flag, checked at chunk boundaries (`core/etl_pipeline.py:143`), not immediate
- **Russian UI labels** — code comments/messages in Russian; keep consistent if editing
- **OCR availability** — checked at import (`core.etl_pipeline.OCR_AVAILABLE`), UI shows hint if PDF added without Tesseract (`core/main_ui.py:583`)

---

## Dependencies (from README)

```
customtkinter
openai
langchain-text-splitters
python-frontmatter
python-docx
PyMuPDF
pytesseract
Pillow
```

Optional system deps: **Tesseract-OCR** (for scanned PDF OCR).

---

## Global Variables

**File**: `docs/global_variables.json`

**Rules:**

1. **All global variables must be registered in `docs/global_variables.json`**
2. When adding a new global variable, you **must** update the file
3. The `modules_used_in` field indicates where the variable is used
4. Variables with `type: "secret"` are not stored in this file — only in `.env`
5. When changing a value, update `value` and leave a comment in the PR

**Variable Structure:**

```jsonc
{
  "variables": [
    {
      "name": "VARIABLE_NAME",
      "type": "string|integer|boolean|array|secret",
      "value": "...",
      "file": "src/path/to/file.py:line",
      "description": "Description of the purpose.",
      "modules_used_in": ["module1", "module2"]
    }
  ]
}
```

**Secrets (API keys, tokens):**

* Store **only** in the `.env` file
* In `docs/global_variables.json`, specify `type: "secret"` and `value: "SEE .env"`
* Example:
```jsonc
{
  "LLM_API_KEY": {
    "name": "LLM_API_KEY",
    "type": "secret",
    "value": "SEE .env",
    "file": ".env",
    "description": "API key for the LLM provider.",
    "modules_used_in": ["config_manager"]
  }
}
```

**Workflow:**

| Stage | Action |
|-------|--------|
| **Development** | After adding code — check if new global variables were introduced → update `docs/global_variables.json` |
| **Testing** | Before running tests — verify all used variables are registered in the file |
| **Review** | Check that all variables are registered and up-to-date; remove dead entries or mark with `@deprecated` |

---

## Phase Lifecycle

The phase status is tracked in the registry `docs/state.json` → `phases[].status`. It is updated at specific milestones:

| Event | phases[].status |
|-------|-----------------|
| Plan approved, execution starts | `executing` |
| A task completes (coder_iterations >= 5) AND other tasks remain pending | `testing` |
| All tasks completed AND all tests passed | `reviewing` |
| Global review passes | `completed` |
| Strategic error detected | `blocked` |

**Important:** Never set phase status to a value that is not one of: `executing`, `testing`, `reviewing`, `blocked`, `completed`.

---

## Verification command:
```bash
# Find all variables used in source code
grep -rh "VARIABLE_NAME\|config_key" src/ --include="*.py" \| sort -u > /tmp/used_vars.txt

# Extract registered variables from global_variables.json
jq -r '.variables[].name' docs/global_variables.json > /tmp/registered_vars.txt

# Compare — differences indicate missing or dead registrations
diff /tmp/used_vars.txt /tmp/registered_vars.txt
```

## Concise Reasoning

1. **Be brief.** Answer directly — no unnecessary explanations, tables, or lists when a short answer suffices.
2. **Don't repeat context.** Don't restate what's already in per-phase state.json, AGENTS.md, or PLAN.md.
3. **Skip obvious steps.** If you checked a file and it's fine, say "checked" — don't dump its contents.
4. **One sentence > three paragraphs.** Prefer compact answers over verbose ones.