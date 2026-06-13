# SkillScan v1 — Development Roadmap

> v1 roadmap for the PyQt6 system tray app.
> For the v2 windowed application roadmap see [DevelopmentV2.md](DevelopmentV2.md).
> Run: `.venv\Scripts\python -m skill_scan`

---

## Known Fixes

### Core / Scanner
- [ ] **`skill-scanner` not installed** — app silently fails with a cryptic `QProcess` error; add a startup check and install-hint dialog
- [ ] **`fail_on_severity` not wired** — config field exists but is never passed as `--fail-on-severity <level>` CLI flag
- [x] **Scan output is raw JSON** — replaced with structured HTML findings view; raw output accessible via "Show Raw Output" toggle

### UI / Tray
- [ ] **Drop Zone toggle resets on restart** — toggle state not persisted to config; always starts hidden
- [ ] **Results window is empty stub** — `ResultsWindow` exists but does not render stored scan entries
- [ ] **`drop_zone.py` still present** — legacy file superseded by `TaskbarDock`; remove once confirmed unused

---

## Phase 1 — Core Tray App (complete)

- [x] System tray icon with right-click `SkillScanMenu`
- [x] Manual scan via folder picker (`QFileDialog`)
- [x] Manual scan clipboard action
- [x] `ScanJob` / `QProcess` wrapper for `skill-scanner` CLI
- [x] `ScanProgressDialog` — live streaming output during scan
- [x] Tray notification on scan completion (severity label)
- [x] `ScanResult` dataclass with `severity_label` property
- [x] `result_store.py` — persist last 100 results to `%APPDATA%\SkillScan\results.json`
- [x] `config.py` — JSON config at `%APPDATA%\SkillScan\config.json`
- [x] `SettingsDialog` — LLM, Analyzers, Clipboard, Watched Folders, Testing tabs
- [x] `AboutDialog` — frameless, rounded, two-colour SKILLSCAN wordmark

---

## Phase 2 — Windows Integration (complete)

- [x] `TaskbarDock` — slim accent strip docked flush to Windows taskbar edge
- [x] Win32 `SHAppBarMessage(ABM_GETTASKBARPOS)` for edge/position detection
- [x] Animated expand (6px → 56px) on drag-enter; collapse on drag-leave or drop
- [x] `--scan <PATH>` CLI flag in `__main__.py`
- [x] HKCU Explorer context menu (optional install, no admin required)

---

## Phase 3 — Background Features (complete)

- [x] `ClipboardWatcher` — QTimer poller with configurable interval and min-chars threshold
- [x] MD5 deduplication — only scans when clipboard content actually changes
- [x] `FolderWatcher` — `watchdog.Observer` with 5-second per-skill debounce
- [x] Walk-up logic to identify skill root from a changed file path
- [x] Animated pill toggle switches embedded in tray menu via `QWidgetAction`
- [x] `SkillScanMenu` override to keep menu open on toggle clicks
- [x] 10-second deferred tray notifications

---

## Phase 4 — UI Polish (complete)

- [x] `_palette.py` — colour token system, 60-30-10 rule, semantic severity colours
- [x] `_widgets.py` — shared `RoundedCard`, `TitleBar`, Segoe Fluent Icons chrome
- [x] Frameless `ScanProgressDialog` with X button
- [x] Frameless `AboutDialog` — logo, two-colour wordmark, info rows
- [x] `logo_no_bg.png` as tray icon (transparent background)
- [x] All UI colours migrated to `_palette.py` tokens

---

## Phase 5 — Enhanced Scan UX (complete)

- [x] `result_formatter.py` — HTML findings report: header summary, LLM-failure callout, severity-sorted findings table
- [x] "Show Raw Output" / "Show Results" toggle in `ScanProgressDialog`
- [x] Severity badges with colour-coded backgrounds (CRITICAL / HIGH / MEDIUM / CLEAN)
- [x] Processing Report status replacing raw "Findings detected" label

---

## Superseded by v2

The following planned v1 items are addressed by the v2 architecture instead:

| Item | v2 resolution |
|---|---|
| Results window table view | Inventory view (Phase 3 v2) |
| Startup registration | Options view → General tab (Phase 2 v2) |
| Scan badge on tray icon | Status bar in main window (Phase 1 v2) |
| Re-scan from results | Skill detail view action button (Phase 4 v2) |
| Severity filter in results | Inventory view filter bar (Phase 9 v2) |
| Export results to CSV/JSON | AI BOM export (Phase 8 v2) |
