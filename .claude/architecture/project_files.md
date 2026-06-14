# SkillScan — Project Files

> Status as of 2026-06-13. Last commit: `0794a43`.

---

## Source — `skill_scan/`

### Entry point

| File | Status | Purpose |
|---|---|---|
| `__init__.py` | ✅ Current | `__version__ = "2.0.0"` |
| `__main__.py` | ✅ Current | `QApplication`, `MainWindow`, `TrayApp` satellite |

### `core/`

| File | Status | Purpose |
|---|---|---|
| `db.py` | ✅ Current | SQLAlchemy models (Folder, Skill, ScanResult, BomSnapshot); `session()` context manager; `init_db()`; `get_or_create_folder()` |
| `scanner.py` | ✅ Current | `ScanJob(QObject)` — wraps `cisco-ai-skill-scanner` via `QProcess`; injects API keys via env |
| `router.py` | ✅ Current | `detect_type(path)` → `"skill"` / `"mcp"` / `"a2a"` / `"unknown"` |
| `skill_discovery.py` | ✅ Current | `DiscoveryWorker(QThread)` — walks folder, upserts skills to DB, SHA-256 hash-check, trust invalidation |
| `config.py` | ✅ Current | JSON config `load()` / `save()` at `%APPDATA%\SkillScan\config.json` |
| `watcher.py` | ✅ Current | `FolderWatcher` — watchdog observer, 5s debounce re-scan |
| `clipboard_watcher.py` | ✅ Current | QTimer clipboard poller; MD5 dedup |
| `result_store.py` | ✅ Current | Last-100 results JSON at `%APPDATA%\SkillScan\results.json` (v1 bridge; migrates to DB) |
| `test_skills.py` | ✅ Current | Test runner; evaluates skills against `_expected.json` |

### `ui/`

| File | Status | Purpose |
|---|---|---|
| `_palette.py` | ✅ Current | All colour tokens (`ACCENT`, `ANCHOR`, `DEEP_SURFACE`, `CRITICAL_ACCENT`, etc.) |
| `_widgets.py` | ✅ Current | `RoundedCard`, `TitleBar`, `card_divider`; `SCROLLBAR_STYLE` (single source of truth for 6px slim scrollbars) |
| `_flow_layout.py` | ✅ Current | `FlowLayout` (left-to-right wrap); `FlowContainer` (responsive width fill, forced column count); `reorder_by()` added 2026-06-13 |
| `main_window.py` | ✅ Current | Frameless `QMainWindow`; custom title bar; drag; `QGraphicsDropShadowEffect`; `QStackedWidget` view routing; back navigation history stack |
| `nav_rail.py` | ✅ Current | `NavRail`; `NavItem` buttons; active item: `ACCENT` left-border; separator before Options/About |
| `result_formatter.py` | ✅ Current | HTML findings report renderer; severity badges; findings table; remediation |
| `scan_progress.py` | ✅ Current | Frameless scan progress dialog |
| `toggle_row.py` | ✅ Current | Animated pill toggle switch |
| `tray.py` | ✅ Current | System tray satellite; scan triggers; notifications; opens main window |
| `about_dialog.py` | ⚠️ Legacy | Superseded by `about_view.py`; kept for tray fallback |
| `settings_dialog.py` | ⚠️ Legacy | Superseded by `options_view.py` + `testing_view.py`; kept for tray fallback |
| `results_window.py` | ⚠️ Legacy | Original scan results popup; superseded by `skill_detail_view.py` |

### `ui/views/`

| File | Status | Purpose |
|---|---|---|
| `folders_view.py` | ✅ Current | Primary view: folder list pane + skill tile grid; FILTER/SORT `QComboBox`; SIZE icon buttons; compact mode wiring; scan queue; discovery wiring |
| `skill_tile.py` | ✅ Current | `SkillTile(QFrame)`: severity border, compact mode, badge layout, findings severity-count row, hover overlay, context menu; `SkillInfo` dataclass |
| `skill_detail_view.py` | ✅ Current | Single skill deep-dive: spec compliance tab, HTML scan report, Raw Output tab, history table + sparkline, trust workflow, `QFileSystemWatcher` auto-revoke |
| `testing_view.py` | ✅ Current | Testing guide; migrated from `settings_dialog` |
| `options_view.py` | ✅ Current | LLM provider, analyzers, clipboard, watched folders; migrated from `SettingsDialog` |
| `about_view.py` | ✅ Current | About page |
| `inventory_view.py` | ⚠️ Stub | Phase 9 — `QTableView` over all tracked skills; not implemented |
| `skill_creator_view.py` | ⚠️ Stub | Phase 5 — metadata form + SKILL.md editor + AI Review; not implemented |

### `windows/`

| File | Status | Purpose |
|---|---|---|
| `taskbar_dock.py` | ✅ Current | 6px → 56px taskbar drop strip; drag-and-drop skill scan |
| `context_menu.py` | ✅ Current | HKCU Explorer right-click "Scan with SkillScan" installer (no admin required) |

---

## Documentation — `docs/`

| File | Status | Purpose |
|---|---|---|
| `DevelopmentV2.md` | ✅ Canonical | Full roadmap: phases 1–11, known fixes, planned feature areas (Actions, Governance, System Setup, CLI, Skill Source Classification, Claude Plugin Format, Integration Reviews) |
| `ArchitectureV2.md` | ✅ Current | Component architecture, DB schema, design patterns, design decisions; updated 2026-06-13 with tile/toolbar patterns |
| `Development.md` | ⚠️ Legacy | v1 tray app roadmap — historical reference |
| `Architecture.md` | ⚠️ Legacy | v1 architecture — historical reference |
| `handover.md` | ✅ Current | Session handover document |
| `change_history.md` | ✅ Current | Chronological change log |
| `project_files.md` | ✅ Current | This file |
| `todo.md` | ✅ Current | Outstanding todos and research items |
| `url.md` | ✅ Current | Reference URLs |
| `assets/screenshot.png` | ✅ Current | App screenshot (embedded in README) |
| `assets/architecture-v2-pipeline.svg` | ✅ Current | Scan pipeline diagram |
| `assets/main-window-layout.svg` | ✅ Current | Main window layout diagram |

---

## Skills Library — `skills/`

### Test skills (SKILL.md format)

| Folder | Status | Purpose |
|---|---|---|
| `pyqt6-ui-designer/` | ✅ Created | PyQt6 UI patterns — frameless windows, palette, layouts, threading |
| `color-palette-builder/` | ✅ Created | WCAG palette generation from a base colour |
| `cisco-ai-defense-integrator/` | ✅ Created | Cisco tool integration patterns |
| `environment-setup/` | ✅ Created | Python + AI dev environment setup |

Each has `SKILL.md` + `_expected.json` for scanner evaluation.

### MCP evals (`skills/mcp-evals/`)

| Folder | Purpose |
|---|---|
| `clean-calculator-mcp/` | Baseline clean MCP manifest |
| `suspicious-unrestricted-fs-mcp/` | Unrestricted filesystem access pattern |
| `malicious-data-exfil-mcp/` | Data exfiltration payload |
| `malicious-prompt-injection-mcp/` | Prompt injection payload |

Each has `mcp.json` + `_expected.json`.

---

## Root

| File | Status | Purpose |
|---|---|---|
| `README.md` | ✅ Current | Project overview, features, setup, skills library, docs table |
| `run.ps1` | ✅ Current | PowerShell launch helper |
| `run.bat` | ✅ Current | Command Prompt launch helper |
| `.venv/` | ✅ Active | Python virtual environment (PyQt6, SQLAlchemy, LiteLLM, watchdog, etc.) |

---

## Runtime files (not in repo)

| Path | Purpose |
|---|---|
| `%APPDATA%\SkillScan\config.json` | User config (API keys, analyzer flags, watched folders) |
| `%APPDATA%\SkillScan\skillscan.db` | SQLite database (folders, skills, scan results, BOM snapshots) |
| `%APPDATA%\SkillScan\activity.log` | Timestamped activity log (scan events, trust changes) |
| `%APPDATA%\SkillScan\results.json` | v1 legacy result store (migrates to DB on first v2 run) |
| `%APPDATA%\SkillScan\Quarantine\` | (planned) Quarantine folder for suspicious skills |
| `%APPDATA%\SkillScan\spec_cache\` | (planned) Cached agentskills.io JSON Schema |
| `%APPDATA%\SkillScan\reports\` | (planned) Generated HTML reports |
