# Config Migration Plan: Backend → Frontend

**Цель**: Перенести хранение конфигурации (LLM, Processing, Prompts) из `config.json` на бэкенде в JSON-файл на фронте. Бэкенд станет stateless в отношении настроек — будет получать весь конфиг из тела запроса.

**Дата**: 2026-07-04

---

## Текущая архитектура

```
Frontend                          Backend                     Disk
───────                          ───────                     ────
SettingsPanel
  ├─ loadConfig() ─────→ GET /config ──→ ConfigService.load()
  │                                           └─ config.json
  ├─ save() ──────────→ POST /config ─→ ConfigService.save()
  │                                           └─ config.json
  └─ updateLLM/Processing()  (local only)

PromptLibrary
  ├─ fetchPrompts() ───→ GET /prompts ─→ ConfigService.get_prompts()
  ├─ addPrompt() ──────→ POST /prompts → ConfigService.add_prompt()
  ├─ removePrompt() ───→ DELETE /prompts/{name}
  └─ setCurrentPrompt() → POST /config → ConfigService.save()
```

## Целевая архитектура

```
Frontend                          Backend
───────                          ───────
configStore (Pinia)
  ├─ loadConfig() ────→ GET /config.json (static file)
  ├─ save() ──────────→ local file write (no API)
  └─ all CRUD locally

PromptLibrary
  ├─ fetchPrompts() ──→ local (from store)
  ├─ addPrompt() ─────→ local + save to file
  ├─ removePrompt() ──→ local + save to file
  └─ setCurrentPrompt() → local

Start Job ────────────→ POST /api/v1/jobs { config: {...} }
                         (конфиг в теле запроса — уже работает)
```

---

## Фаза 1: Фронтенд — локальный конфиг-файл

### 1.1 Создать `frontend/public/config.json`

Стартовый файл с дефолтами:

```json
{
  "llm": {
    "model": "llama3",
    "base_url": "http://localhost:11434/v1",
    "api_key": "ollama"
  },
  "processing": {
    "chunk_size": 10000,
    "chunk_overlap": 1500,
    "max_workers": 1,
    "output_format": "spr",
    "skip_llm": false
  },
  "prompts": [],
  "current_prompt_name": ""
}
```

### 1.2 Создать `frontend/src/services/configFile.ts`

Новый модуль для чтения/записи конфига:

```ts
// Чтение — fetch из public/config.json (статический файл)
export async function loadConfigFile(): Promise<ConfigResponse>

// Запись — через download blob (браузер не может писать на диск напрямую)
// Вариант A: возвращаем JSON и пользователь сохраняет вручную
// Вариант B: используем File System Access API (Chrome/Edge)
export function downloadConfigFile(config: ConfigResponse): void
```

> **Примечание**: Браузер не может напрямую записать файл в `public/`. Есть два подхода:
>
> - **Вариант A (простой)**: При сохранении — скачивать `config.json` через `<a download>`. Пользователь кладёт его обратно в `public/`. Подходит для dev, неудобно для прода.
> - **Вариант B (File System Access API)**: Пользователь выбирает файл один раз (`showOpenFilePicker`), дальше читаем/пишем через `FileSystemFileHandle`. Работает в Chrome/Edge, не в Firefox.
> - **Вариант C (рекомендуемый)**: Хранить в `localStorage` +提供 кнопку «Export / Import JSON». Пользователь может экспортировать конфиг в файл и импортировать на другой машине. При этом всё работает автоматически без ручных операций.

### 1.3 Обновить `frontend/src/stores/config.ts`

| Было | Стало |
|------|-------|
| `loadConfig()` → `getConfig()` (REST) | `loadConfig()` → `loadConfigFile()` (fetch static JSON) |
| `save()` → `saveConfig()` (REST) | `save()` → сохранение в `localStorage` + offer download |
| `loaded` flag | Аналогично |

### 1.4 Обновить `frontend/src/stores/prompts.ts`

| Было | Стало |
|------|-------|
| `fetchPrompts()` → `getPrompts()` (REST) | `fetchPrompts()` → читает из `configStore` |
| `addPrompt()` → `createPrompt()` (REST) | `addPrompt()` → добавляет в store + сохраняет |
| `removePrompt()` → `deletePrompt()` (REST) | `removePrompt()` → удаляет из store + сохраняет |
| `setCurrentPrompt()` → `saveConfig()` (REST) | `setCurrentPrompt()` → локально + сохраняет |

### 1.5 Обновить `frontend/src/services/api.ts`

**Удалить** функции:
- `getConfig()`
- `saveConfig()`
- `getPrompts()`
- `createPrompt()`
- `deletePrompt()`

Оставить только: `uploadFiles`, `getFiles`, `deleteFile`, `createJob`, `getJobs`, `getJob`, `stopJob`, `getJobFiles`, `downloadJobFile`, `downloadJobZip`.

### 1.6 Обновить `frontend/src/components/Settings/ServerSettings.vue`

Убрать подсказку «Saved to browser storage» — это теперь стандартное поведение. Добавить «Export / Import» кнопки:

```html
<Button @click="exportConfig">Export Config</Button>
<Button @click="importConfig">Import Config</Button>
```

### 1.7 Обновить `frontend/src/components/Settings/SettingsPanel.vue`

- Убрать `serverSettingsRef` — save() теперь просто сохраняет в localStorage
- Save кнопка вызывает `configStore.save()` (который пишет в localStorage)

### 1.8 Обновить `frontend/src/App.vue`

- `onMounted`: `loadConfigFile()` вместо `configStore.loadConfig()`
- `handleStart`: уже отправляет конфиг в job request — без изменений

### 1.9 Обновить типы `frontend/src/types/config.ts`

- Добавить `skip_llm` в `ProcessingConfig` (уже есть)
- Добавить `ConfigResponse.skip_llm` если нужно
- Убрать `ConfigUpdateRequest` (больше не нужен — PATCH через REST)

---

## Фаза 2: Бэкенд — удаление config CRUD

### 2.1 Удалить файлы

| Файл | Действие |
|------|----------|
| `backend/app/api/v1/config.py` | ❌ Удалить |
| `backend/app/services/config_service.py` | ❌ Удалить |
| `backend/config.json` | ❌ Удалить (переносится на фронт) |

### 2.2 Обновить `backend/app/main.py`

Убрать импорт и регистрацию config router:

```python
# Было:
from app.api.v1 import config_router, files_router, jobs_router, ws_router
app.include_router(config_router)

# Стало:
from app.api.v1 import files_router, jobs_router, ws_router
# (config_router удалён)
```

### 2.3 Обновить `backend/app/api/v1/__init__.py`

Убрать экспорт `config_router`.

### 2.4 Проверить `backend/app/etl/runner.py`

Уже получает конфиг из `config` dict — **без изменений**.

### 2.5 Удалить тесты

| Файл | Действие |
|------|----------|
| `backend/tests/test_config_service.py` | ❌ Удалить |
| `backend/tests/test_api_v1_config.py` | ❌ Удалить |
| `backend/tests/test_schemas_config.py` | ❌ Удалить (схемы Pydantic больше не нужны для REST) |
| `backend/tests/conftest.py` | Убрать `isolated_config` fixture |

### 2.6 Обновить `backend/app/schemas/config.py`

**Вариант A**: Удалить полностью — бэкенд больше не валидирует конфиг через Pydantic.

**Вариант B (рекомендуемый)**: Оставить как утилиту для валидации конфига при старте job. Добавить `skip_llm: bool = False` в `ProcessingConfig`. Раннер может валидировать входящий конфиг через эту схему.

### 2.7 Обновить `backend/app/schemas/job.py`

`JobCreateRequest.config` — оставить как `dict`. Раннер уже работает с dict. Можно добавить optional валидацию через `ConfigResponse` из schemas.

---

## Фаза 3: Тестирование

### 3.1 Фронтенд

- [ ] Загрузка конфига при старте (из `public/config.json` или `localStorage`)
- [ ] Сохранение настроек LLM → перезагрузка → настройки сохранены
- [ ] CRUD промптов (добавить / удалить / выбрать)
- [ ] Выбор промпта → `current_prompt_name` сохраняется
- [ ] Запуск job с правильным конфигом (проверить в логах бэкенда)
- [ ] No LLM режим (skip_llm) → job пропускает LLM шаг
- [ ] Export / Import конфига
- [ ] Server URL сохраняется и используется
- [ ] ConnectionStatus показывает Connected

### 3.2 Бэкенд

- [ ] `GET /api/v1/files` — работает
- [ ] `POST /api/v1/files/upload` — работает
- [ ] `POST /api/v1/jobs` — работает с конфигом в теле
- [ ] `GET /api/v1/config` — **404** (ожидаемо)
- [ ] `GET /api/v1/prompts` — **404** (ожидаемо)
- [ ] Единый тест: upload file → start job → проверить output

---

## Файлы для изменения (сводка)

### Удалить
- `backend/app/api/v1/config.py`
- `backend/app/services/config_service.py`
- `backend/config.json`
- `backend/tests/test_config_service.py`
- `backend/tests/test_api_v1_config.py`
- `backend/tests/test_schemas_config.py`

### Создать
- `frontend/public/config.json` (дефолтный конфиг)
- `frontend/src/services/configFile.ts` (read/write/download)

### Изменить
- `frontend/src/stores/config.ts` — localStorage вместо REST
- `frontend/src/stores/prompts.ts` — localStorage вместо REST
- `frontend/src/services/api.ts` — удалить config/prompt функции
- `frontend/src/types/config.ts` — добавить `skip_llm` (если нужно), удалить `ConfigUpdateRequest`
- `frontend/src/components/Settings/SettingsPanel.vue` — упростить save()
- `frontend/src/components/Settings/ServerSettings.vue` — добавить Export/Import
- `frontend/src/App.vue` — обновить `onMounted`
- `backend/app/main.py` — удалить config router
- `backend/app/api/v1/__init__.py` — удалить config_router
- `backend/app/schemas/config.py` — добавить `skip_llm` в `ProcessingConfig`
- `backend/tests/conftest.py` — убрать `isolated_config`

---

## Порядок выполнения

1. **Фронт: создать `public/config.json` + `configFile.ts`** — ядро новой логики
2. **Фронт: обновить `config.ts` store** — переключить на локальный файл
3. **Фронт: обновить `prompts.ts` store** — убрать REST-вызовы
4. **Фронт: обновить `api.ts`** — удалить config/prompt функции
5. **Фронт: обновить компоненты** — SettingsPanel, ServerSettings, App.vue
6. **Фронт: тестирование** — проверить всё
7. **Бэк: удалить config CRUD** — файлы, роутер, тесты
8. **Бэк: обновить схемы** — добавить `skip_llm`
9. **Бэк: тестирование** — проверить job API
10. **Общее тестирование** — полный цикл
