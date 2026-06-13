# SkillScan v1 — Architecture

> v1 is a PyQt6 Windows system tray utility wrapping the `cisco-ai-skill-scanner` CLI.
> For the v2 windowed application architecture see [ArchitectureV2.md](ArchitectureV2.md).

---

## Project Structure

```
SkillScan/
├── run.ps1                          # PowerShell launcher (prefers .venv\Scripts\python)
├── run.bat                          # Batch launcher
└── skill_scan/
    ├── __init__.py                  # __version__ = "1.0.0"
    ├── __main__.py                  # Entry point — argparse, QApplication, TrayApp
    ├── core/
    │   ├── config.py                # JSON config in %APPDATA%\SkillScan\config.json
    │   ├── scanner.py               # ScanJob — QProcess wrapper for skill-scanner CLI
    │   ├── clipboard_watcher.py     # QTimer-based clipboard poller with MD5 deduplication
    │   ├── result_store.py          # ScanResult dataclass; persists last 100 results
    │   └── watcher.py               # FolderWatcher — watchdog Observer + 5s debounce
    ├── ui/
    │   ├── _palette.py              # Colour tokens — single source of truth
    │   ├── _widgets.py              # Shared frameless components (RoundedCard, TitleBar)
    │   ├── tray.py                  # TrayApp, SkillScanMenu, menu construction
    │   ├── toggle_row.py            # ToggleSwitch, ToggleRow, ToggleAction (QWidgetAction)
    │   ├── settings_dialog.py       # Settings — LLM / Analyzers / Clipboard / Folders / Testing
    │   ├── about_dialog.py          # About dialog — frameless, rounded, two-colour wordmark
    │   ├── scan_progress.py         # ScanProgressDialog — live stream + structured findings
    │   ├── result_formatter.py      # HTML findings report with severity badges
    │   ├── results_window.py        # Results window — scan history (stub in v1)
    │   └── drop_zone.py             # Legacy floating drop zone (superseded by TaskbarDock)
    └── windows/
        ├── taskbar_dock.py          # TaskbarDock — slim strip docked to Windows taskbar edge
        └── context_menu.py          # HKCU Explorer context menu install / uninstall
```

---

## Configuration

Settings live at `%APPDATA%\SkillScan\config.json` — never committed to git.

```json
{
  "llm_provider": "anthropic",
  "llm_api_key": "",
  "llm_model": "anthropic/claude-sonnet-4-20250514",
  "virustotal_api_key": "",
  "ai_defense_api_key": "",
  "use_behavioral": true,
  "use_llm": true,
  "use_trigger": false,
  "use_aidefense": false,
  "use_virustotal": false,
  "policy": "permissive",
  "detailed": true,
  "fail_on_severity": "",
  "watched_folders": [],
  "clipboard_watch_enabled": false,
  "clipboard_watch_interval_secs": 30,
  "clipboard_min_chars": 200
}
```

`config.py` exposes `load() -> dict` and `save(cfg: dict)`. No module-level singleton — hot-reload after Settings is just `self._cfg = cfg.load()`.

---

## Core Data Model

### ScanResult (dataclass — `result_store.py`)

| Field | Type | Description |
|---|---|---|
| `path` | `str` | Folder that was scanned |
| `returncode` | `int` | Exit code from `skill-scanner` |
| `stdout` | `str` | Raw stdout (JSON from `--format json`) |
| `stderr` | `str` | Raw stderr |
| `timestamp` | `str` | ISO 8601 timestamp |
| `parsed` | `dict \| None` | Extracted JSON object from stdout |

`severity_label` property: parses `parsed` JSON for the worst `severity` across findings; falls back to `"unknown"`.

Results persist at `%APPDATA%\SkillScan\results.json`, capped at 100 entries.

### ScanJob (QObject — `scanner.py`)

| Attribute | Type | Description |
|---|---|---|
| `_path` | `str` | Folder being scanned |
| `_cfg` | `dict` | Config snapshot at job creation time |
| `_proc` | `QProcess` | The running `skill-scanner` process |

Signals: `output_line(str)`, `finished(ScanResult)`, `error(str)`.

Executable resolved as `Path(sys.executable).parent / "skill-scanner.exe"` — venv-aware, not PATH-dependent.

---

## UI Layout

### Tray Menu (`SkillScanMenu`)

```
  SkillScan
  ─────────────────────
  Scan Skill Folder…
  Scan Clipboard
  ─────────────────────
  FEATURES
  [label]  Drop Zone            ●○
  [label]  Clipboard Auto-Scan  ●○
  [label]  Folder Watching      ●○
  ─────────────────────
  View Results
  ─────────────────────
  Settings…
  About…
  ─────────────────────
  Exit
```

Toggle rows embedded via `QWidgetAction` (`ToggleAction`). `SkillScanMenu` overrides `mouseReleaseEvent` with `actionAt(event.pos())` to prevent menu closure on toggle clicks.

### TaskbarDock

```
┌── Screen width, flush against taskbar ──────────────────┐
│  [6px accent strip — idle / collapsed]                   │
│  ↕ expands to 56px on drag-enter                         │
│  "Drop Skill Folder" shown when fully expanded           │
└──────────────────────────────────────────────────────────┘
```

Edge detected via Win32 `SHAppBarMessage(ABM_GETTASKBARPOS)`. Rounded corners on inward-facing side only.

---

## PyQt6 Patterns

### 1. Subprocess Scanning (`QProcess`)

`QProcess` instead of `subprocess` — stdout delivered asynchronously to the Qt event loop. API keys injected via `QProcess.setProcessEnvironment()`, never as CLI args.

### 2. Animated Pill Toggle (`toggle_row.py`)

`QPropertyAnimation` on `pyqtProperty(float)` named `knob_pos` (0.0–1.0). `toggle()` delegates to `setChecked()` — never pre-sets `self._checked`, which would trigger the early-return guard and abort the animation.

### 3. Frameless Dialogs (`_widgets.py`)

`FramelessWindowHint` + `WA_TranslucentBackground`. `QPainterPath.addRoundedRect` in `paintEvent`. `QGraphicsDropShadowEffect` (blur=28, offset=(0,6)). Drag via `mousePressEvent` / `mouseMoveEvent` tracking `globalPosition().toPoint()`.

### 4. Structured Findings (`result_formatter.py`)

`json.JSONDecoder().raw_decode(text, i)` extracts JSON from mixed LiteLLM output. `format_result_html()` generates Qt-compatible HTML: severity badges, LLM-failure callout, findings table sorted by severity. Displayed in `QTextBrowser` on scan completion.

### 5. Clipboard Watcher (`clipboard_watcher.py`)

`QTimer` poller. Emits `scan_requested(str)` only when text length ≥ `min_chars` AND MD5 differs from last emitted hash.

### 6. Folder Watcher (`watcher.py`)

`watchdog.Observer` on its own thread. Walks up from changed file path (up to 5 levels) to find `SKILL.md` root. 5-second per-skill debounce prevents burst re-scans.

### 7. Taskbar Dock Geometry (`taskbar_dock.py`)

`thickness` is `pyqtProperty(float)`. `QPropertyAnimation` animates 6px → 56px. Setter calls `_apply_geometry()` each frame, keeping the strip flush to the taskbar edge.

---

## Key Design Decisions

| Decision | Rationale |
|---|---|
| Config via `load()`/`save()` (no singleton) | Settings hot-reload without restart |
| `QProcess` instead of `subprocess` | Async stdout keeps UI event loop alive |
| `skill-scanner.exe` from `sys.executable` parent | Venv-aware, no PATH dependency |
| API keys via process environment | Keys hidden from process listings |
| MD5 deduplication in clipboard watcher | No re-scan on rapid timer ticks |
| `actionAt(event.pos())` not `activeAction()` | `activeAction()` returns None for `QWidgetAction` items |
| `toggle()` delegates to `setChecked()` | Single source of animation logic |
| Taskbar dock via `SHAppBarMessage` (read-only) | No AppBar registration, no work-area modification |

---

## Common Workflows

### Manual Scan

```
TrayApp._pick_and_scan()
  → QFileDialog → launch_scan(path)
      → ScanJob.start() → QProcess → skill-scanner
      → ScanProgressDialog streams output_line signals
  → _on_job_done(result) → tray.showMessage(severity)
```

### Clipboard Auto-Scan

```
ClipboardWatcher._check()   [QTimer tick]
  → len >= min_chars, MD5 changed
  → scan_requested.emit(text)
TrayApp._on_clipboard_content(text)
  → write to temp/SKILL.md → launch_scan(temp, silent=True)
```

### Folder Watch Auto-Scan

```
FolderWatcher (watchdog thread)
  → file event → walk up → find SKILL.md root → debounce 5s
  → skill_changed.emit(skill_path)
TrayApp → tray.showMessage("Auto-scanning") → launch_scan(skill_path)
```

### Drop to Taskbar Strip

```
TaskbarDock.dragEnterEvent() → _expand()
TaskbarDock.dropEvent() → scan_requested.emit(path)
TrayApp.launch_scan(path)
```
