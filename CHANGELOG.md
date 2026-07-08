# Changelog

## [1.0.1] - 2026-07-08

### Fixed
- **Language switching** — vue-i18n locale now updates correctly via `.value` assignment

---

## [1.0.0] - 2026-07-08

### 🎉 Initial Web Release

Complete rewrite from desktop CustomTkinter application to web application (Vue 3 + FastAPI).

### Added

#### Backend (FastAPI)
- **REST API** — file upload, job creation/status, result download
- **WebSocket** — real-time progress and logs for each job
- **ETL pipeline** — extract → split → LLM → pack with parallel processing via ThreadPoolExecutor
- **Four output formats** — `spr`, `frontmatter`, `markdown`, `html`
- **Server-side caps** — limit `max_workers` and `chunk_size` via environment variables
- **API authorization** — optional `X-API-Key` header authentication
- **Pydantic Settings** — configuration via `APP_*` environment variables

#### Frontend (Vue 3)
- **Web interface** — modern UI with settings, progress, and logs
- **Pinia stores** — state management (config, files, job, prompts)
- **WebSocket integration** — real-time updates
- **Prompt library** — create, save, switch templates
- **Localization** — i18n support via vue-i18n
- **Server settings** — set backend URL directly in UI (localStorage)

#### DevOps
- **Docker** — multi-stage Dockerfile, docker-compose for monolith and split deployment
- **Makefile** — commands for development, testing, building, deployment
- **Tests** — pytest for backend, Vitest for frontend
- **Documentation** — README in English and Russian

### Changed
- **Architecture** — migration from desktop (CustomTkinter) to web (Vue 3 + FastAPI)
- **Configuration** — from config.json to env vars + localStorage
- **ETL pipeline** — synchronous → asynchronous with thread pool

### Removed
- **Desktop UI** — CustomTkinter GUI replaced with web interface
- **core/ module** — deprecated, kept for reference only

### Dependencies
- Backend: FastAPI, uvicorn, pydantic-settings, openai, langchain-text-splitters, python-frontmatter, python-docx, PyMuPDF, markdown, Pillow
- Frontend: Vue 3, Pinia, Axios, vue-i18n, marked, Lucide icons, Vite, TypeScript

---

## [0.4.0] - 2026-06-28

### Added
- **Dynamic frontmatter fields** — YAML Front Matter parsing now handles **any** fields from LLM response, not just hardcoded ones (`concept`, `algorithm`, etc.). Supports any prompts.
- **Three output formats** — new "Output Format" dropdown in processing settings:
  - `spr` — markdown representation with SPR sections (default)
  - `frontmatter` — real YAML Front Matter between `---` (standard for Obsidian/RAG)
  - `markdown` — raw text without processing
- **Real YAML Front Matter** — `frontmatter` format generates correct YAML block with automatic escaping and list serialization via `frontmatter.dumps()`.
- **Scrollable left panel** — `CTkScrollableFrame` instead of regular `CTkFrame`: left panel scrolls vertically when window is resized.

### Changed
- **Panel order** — "Control and Progress" moved above "LLM Provider Settings" for more logical UX.
- **Output format is saved** — new `output_format` setting is saved in `config.json` and loaded on startup.
- **"Save Settings" button** — moved to a separate card at the bottom of the left panel.

---

## [0.3.0] - 2026-06-28

### Added
- **PDF file support** — reading PDF documents via `PyMuPDF` (`fitz`) with page-by-page text extraction.
- **OCR recognition of scans** — optional `pytesseract` + `Pillow` support for recognizing text on scanned PDF pages. Requires Tesseract-OCR installed on the system.
- **OCR notification** — centered hint below file list buttons, displayed when PDF files are present and Tesseract is missing.
- **"Only chunking and conversion" checkbox** — allows skipping the LLM processing step: file is chunked and immediately packed into `.md` without calling the model.
- **Selected file progress bar** — clicking a file in the list shows its progress in real-time.
- **"Delete Prompt" button** — delete selected prompt template from the library with confirmation. Cannot delete the last prompt.

### Changed
- **Left panel** — fixed width 400px, cards expand to full width.
- **File list buttons** — "Add", "Delete", "Clear" are centered.
- **File dialog filter** — added `*.pdf` format.
- **Progress bar label** — changed from "Current file progress" to "Progress: <filename>".

### Dependencies
- Added: `PyMuPDF`, `pytesseract`, `Pillow`

---

## [0.2.0] - 2026-06-28

### Added
- **Migration to CustomTkinter** — complete replacement of `tkinter`/`ttk` with `customtkinter` featuring rounded corners, cards, and modern widgets.
- **Custom `FileListBox`** — custom file list widget based on `CTkScrollableFrame` with selection and Ctrl+Click support.
- **File tooltips** — hovering over a file in the list displays its full path in a tooltip.
- **Parallel threads** — selection of parallel thread count (1–8) via `CTkOptionMenu` with `max_workers` configuration in the pipeline.

### Changed
- **All widgets migrated to CTk** — `CTkButton`, `CTkEntry`, `CTkLabel`, `CTkTextbox`, `CTkProgressBar`, `CTkCheckBox`, `CTkOptionMenu`, `CTkToplevel`.
- **Color palette** — updated for modern minimalist style (`BG_MAIN`, `BG_CARD`, `FG_LABEL`, `FG_HEADER`, etc.).
- **README.md** — updated for CustomTkinter, added `customtkinter` and `max_workers` to dependencies/configuration, updated mermaid diagram for parallel threads.
