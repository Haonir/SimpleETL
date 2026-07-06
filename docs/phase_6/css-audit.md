# CSS Color Audit — Phase 6 Theming Preparation

## Summary
- Total hardcoded colors: ~46 (excluding var() fallbacks)
- Components with hardcoded colors: 13 out of 24
- Clean components (0 hardcoded): 11

## Hardcoded Color Inventory

### Semantic Groups

#### 1. Status Colors (success/warning/error/info)
| Value | Components | Context | Proposed Variable |
|-------|-----------|---------|-------------------|
| `#22c55e` | App.vue, ConnectionStatus.vue, ServerSettings.vue | success bg/text | `--color-success` (exists) |
| `#ef4444` | Input.vue, FileList.vue, JobHistory.vue, App.vue | error/danger bg/text | `--color-error` (exists) |
| `#f59e0b` | ConnectionStatus.vue, FileDropZone.vue | warning bg/text | `--color-warning` (exists) |
| `#3b82f6` | App.vue | info bg | `--color-info` (exists) |

#### 2. Status Badge Colors (light backgrounds + dark text)
| Background | Text | Status | Components | Proposed Variables |
|-----------|------|--------|-----------|-------------------|
| `#e5e7eb` | `#6b7280` | pending/idle | JobHistory.vue, JobToolbar.vue | `--badge-bg-muted`, `--badge-fg-muted` |
| `#dbeafe` | `#1d4ed8` | running | JobHistory.vue, JobToolbar.vue | `--badge-bg-running`, `--badge-fg-running` |
| `#dcfce7` | `#166534` | completed | JobHistory.vue, JobToolbar.vue | `--badge-bg-success`, `--badge-fg-success` |
| `#fef3c7` | `#92400e` | partial/stopped | JobHistory.vue, JobToolbar.vue | `--badge-bg-warning`, `--badge-fg-warning` |
| `#fee2e2` | `#991b1b` | error | JobHistory.vue, JobToolbar.vue | `--badge-bg-error`, `--badge-fg-error` |

#### 3. Danger Button Colors
| Value | Context | Components | Proposed Variable |
|-------|---------|-----------|-------------------|
| `#ef4444` | danger button bg | FileList.vue, JobHistory.vue | `--btn-danger-bg` |
| `#dc2626` | danger button hover | FileList.vue, JobHistory.vue | `--btn-danger-hover` |
| `white` | danger button text | FileList.vue, JobHistory.vue | `--btn-danger-fg` |
| `#fecaca` | danger border | FileList.vue, JobHistory.vue | `--btn-danger-border` |
| `#fef2f2` | danger warning bg | FileList.vue, JobHistory.vue | `--btn-danger-bg-light` |

#### 4. Overlay/Backdrop Colors
| Value | Context | Components | Proposed Variable |
|-------|---------|-----------|-------------------|
| `rgba(0,0,0,0.4)` | modal backdrop | Modal.vue | `--backdrop-bg` |
| `rgba(0,0,0,0.5)` | dialog overlay | FileList.vue, JobHistory.vue | `--backdrop-bg` |
| `rgba(0,0,0,0.15)` | modal shadow | Modal.vue | `--shadow-modal` |
| `rgba(0,0,0,0.3)` | dialog shadow | FileList.vue, JobHistory.vue | `--shadow-dialog` |

#### 5. Hover Tints
| Value | Context | Components | Proposed Variable |
|-------|---------|-----------|-------------------|
| `rgba(59,130,246,0.08)` | hover bg | App.vue, LogPanel.vue | `--bg-hover-accent` |
| `rgba(59,130,246,0.05)` | row hover | FileList.vue, JobHistory.vue, JobOutput.vue | `--bg-hover-subtle` |
| `rgba(59,130,246,0.1)` | selected row | JobHistory.vue, JobOutput.vue | `--bg-active-subtle` |

#### 6. Muted/Gray Text
| Value | Context | Components | Proposed Variable |
|-------|---------|-----------|-------------------|
| `#6b7280` | muted text | JobHistory.vue, JobToolbar.vue | `--fg-muted` |
| `#9ca3af` | timestamp | LogEntry.vue | `--fg-muted` |
| `#999` | delete btn text | JobHistory.vue | `--fg-muted` |
| `#666` | dialog text | FileList.vue, JobHistory.vue | `--fg-subtle` |

#### 7. White/On-Accent Text
| Value | Context | Components | Proposed Variable |
|-------|---------|-----------|-------------------|
| `white` | primary btn text | Button.vue, Checkbox.vue | `--fg-on-accent` |
| `white` | active sidebar text | App.vue | `--fg-on-accent` |
| `white` | notification text | App.vue | `--fg-on-accent` |
| `white` | danger btn text | FileList.vue, JobHistory.vue | `--fg-on-accent` |

#### 8. Log Level Colors (JS-driven)
| Value | Level | Component | Proposed Variable |
|-------|-------|-----------|-------------------|
| `#3b82f6` | info | LogEntry.vue | `--log-info` |
| `#22c55e` | llm | LogEntry.vue | `--log-success` |
| `#f59e0b` | warning | LogEntry.vue | `--log-warning` |
| `#ef4444` | error | LogEntry.vue | `--log-error` |

#### 9. Misc
| Value | Context | Component | Proposed Variable |
|-------|---------|-----------|-------------------|
| `#d97706` | PDF warning text | FileDropZone.vue | `--warning-text` |
| `#f5740b` | stop hint text | JobToolbar.vue | `--warning-text` |

## Clean Components (0 hardcoded colors)
- Select.vue
- GeneralSettings.vue
- LLMSettings.vue
- ProcessingSettings.vue
- SettingsPanel.vue
- PromptEditor.vue
- PromptLibrary.vue
- FileProgressBar.vue
- GlobalProgressBar.vue
- ProgressBar.vue
- (11 total)

## Validation Results (Task 1.4)

### Variables Created
- **Light theme (`:root`)**: 55 color tokens + 12 non-color tokens (layout, typography, z-index, transitions)
- **Dark theme (`[data-theme="dark"]`)**: 55 color overrides

### Remaining Hardcoded Colors in Components (to be replaced in Phase 2)

| Category | Count | Components | Variable Available |
|----------|-------|-----------|-------------------|
| Hex status colors | ~15 | App, ConnectionStatus, ServerSettings, Input | ✅ `--color-*` |
| Hex badge colors | ~20 | JobHistory, JobToolbar | ✅ `--badge-*` |
| Hex danger colors | ~10 | FileList, JobHistory | ✅ `--btn-danger-*` |
| `rgba(59,130,246,...)` hover tints | 8 | App, FileList, JobHistory, JobOutput, LogPanel | ✅ `--bg-hover-*` |
| `rgba(0,0,0,...)` overlays | 8 | Modal, FileList, JobHistory | ✅ `--bg-overlay`, `--shadow-*` |
| `white` named color | 8 | App, FileList, JobHistory, LogEntry, LogPanel | ✅ `--fg-on-accent` |
| JS-level colorMap | 4 | LogEntry | ✅ `--log-*` |
| **Total** | **~73** | | **All mapped** |

### Coverage Status
- ✅ Every hardcoded color has a corresponding CSS variable
- ✅ Dark theme overrides exist for all color tokens
- ⏳ Component replacement pending (Phase 2)

## Notes
- Many `var(--x, #fallback)` patterns exist — fallbacks are acceptable
- LogEntry.vue uses JS-level colorMap — needs CSS variable approach
- Status badge colors are duplicated between JobHistory.vue and JobToolbar.vue

## Validation Results (Task 1.4)

### Variables Created
- **Light theme (`:root`)**: 55 color tokens + 12 non-color tokens (layout, typography, z-index, transitions)
- **Dark theme (`[data-theme="dark"]`)**: 55 color overrides

### Remaining Hardcoded Colors in Components (to be replaced in Phase 2)

| Category | Count | Components | Variable Available |
|----------|-------|-----------|-------------------|
| Hex status colors | ~15 | App, ConnectionStatus, ServerSettings, Input | ✅ `--color-*` |
| Hex badge colors | ~20 | JobHistory, JobToolbar | ✅ `--badge-*` |
| Hex danger colors | ~10 | FileList, JobHistory | ✅ `--btn-danger-*` |
| `rgba(59,130,246,...)` hover tints | 8 | App, FileList, JobHistory, JobOutput, LogPanel | ✅ `--bg-hover-*` |
| `rgba(0,0,0,...)` overlays | 8 | Modal, FileList, JobHistory | ✅ `--bg-overlay`, `--shadow-*` |
| `white` named color | 8 | App, FileList, JobHistory, LogEntry, LogPanel | ✅ `--fg-on-accent` |
| JS-level colorMap | 4 | LogEntry | ✅ `--log-*` |
| **Total** | **~73** | | **All mapped** |

### Coverage Status
- ✅ Every hardcoded color has a corresponding CSS variable
- ✅ Dark theme overrides exist for all color tokens
- ⏳ Component replacement pending (Phase 2)
