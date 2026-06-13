# SkillScan v2 — Development Roadmap

> Canonical roadmap for SkillScan v2 — the Skill Security Environment.
> Supersedes `Development.md` (v1 tray app phases).
> Architecture reference: [ArchitectureV2.md](ArchitectureV2.md)

---

## Skills Library

Skills live in `skills/`. Each skill is a subdirectory containing `SKILL.md` + `_expected.json`. Scan any skill folder with SkillScan to verify it remains clean after edits.

| Skill | Status | Description |
|---|---|---|
| `pyqt6-ui-designer` | ✅ Created | PyQt6 UI engineering — frameless windows, palette, layouts, threading |
| `color-palette-builder` | ✅ Created | Generate a full `_palette.py` from a single base colour with WCAG checks |
| `cisco-ai-defense-integrator` | ✅ Created | Integrate skill-scanner, DefenseClaw, AI BOM, and agentskills.io validation |
| `environment-setup` | ✅ Created | Optimal Python + AI dev environment — venv, API keys, toolchain, secrets |

---

## What Carries Forward from v1

All of the following v1 work is **retained unchanged** in v2:

| Module | Status |
|---|---|
| `core/config.py` — `load()` / `save()` | ✅ Retained |
| `core/scanner.py` — `ScanJob` / `QProcess` | ✅ Retained |
| `core/result_store.py` — JSON history (migrates to DB) | ✅ Retained, then superseded |
| `core/clipboard_watcher.py` | ✅ Retained |
| `core/watcher.py` — `FolderWatcher` | ✅ Retained |
| `core/test_skills.py` + Testing Guide | ✅ Retained |
| `ui/_palette.py` — colour tokens | ✅ Retained |
| `ui/_widgets.py` — `RoundedCard`, `TitleBar` | ✅ Retained |
| `ui/scan_progress.py` — frameless scan dialog | ✅ Retained |
| `ui/result_formatter.py` — HTML findings report | ✅ Retained |
| `ui/toggle_row.py` — pill toggle | ✅ Retained |
| `ui/tray.py` — simplified to satellite | ✅ Retained (simplified) |
| `windows/taskbar_dock.py` | ✅ Retained |
| `windows/context_menu.py` | ✅ Retained (optional install) |
| `resources/logo_no_bg.png` | ✅ Retained |

---

## Open Carries (from v1 Known Fixes)

Items from v1 that are resolved by v2 architecture, or must be fixed before/during migration:

- [x] **Scan output is raw JSON** — resolved by `result_formatter.py` (v1 Phase 5)
- [ ] **`skill-scanner` not installed** — startup check + install-hint dialog; carry into Phase 1
- [ ] **`fail_on_severity` not wired** — pass `--fail-on-severity` CLI flag; carry into Phase 1
- [ ] **Drop Zone toggle not persisted** — carry into Phase 1 (add to config)
- [ ] **`drop_zone.py` still present** — delete in Phase 1 cleanup
- [ ] **Results window empty stub** — superseded by v2 Inventory view (Phase 3)
- [ ] **No startup registration** — add to Options view (Phase 2)

---

## Phase 1 — Main Window Shell

*Goal: replace the tray-first entry point with a primary windowed application. All existing functionality continues to work; no features removed.*

### 1.1 Window infrastructure

- [ ] `ui/main_window.py` — `MainWindow(QMainWindow)` with `FramelessWindowHint` + `WA_TranslucentBackground`
- [ ] Custom title bar: SKILLSCAN wordmark, draggable, minimise + close only (Segoe Fluent Icons)
- [ ] `QPainterPath` rounded rect `paintEvent`, `QGraphicsDropShadowEffect` (blur=28, offset=0,6)
- [ ] `mousePressEvent` / `mouseMoveEvent` drag on title bar
- [ ] Window minimum size 1000×640; resizable
- [ ] Status bar: scanner state dot, unscanned count, LLM model name, version string

### 1.2 Nav rail

- [ ] `ui/nav_rail.py` — `NavRail(QWidget)` with `NavItem` buttons
- [ ] Items: Folders, Inventory, Create, (spacer), Options, About, Exit
- [ ] Active item: `ACCENT` colour, 3px left border, `rgba(ACCENT, 0.12)` bg
- [ ] Hover state: `DEEP_SURFACE` bg, `MUTED_TEXT` → `LIGHT_CANVAS` transition
- [ ] `page_changed(int)` signal wired to `QStackedWidget.setCurrentIndex()`
- [ ] Back button in title bar area: hidden by default, shown when `_history` stack non-empty

### 1.3 View stubs

- [ ] `ui/views/folders_view.py` — stub (populated Phase 3)
- [ ] `ui/views/inventory_view.py` — stub (populated Phase 4)
- [ ] `ui/views/skill_creator_view.py` — stub (populated Phase 5)
- [ ] `ui/views/testing_view.py` — **migrated** from `settings_dialog._make_testing_tab()`
- [ ] `ui/views/options_view.py` — **migrated** from `SettingsDialog` (all tabs)
- [ ] `ui/views/about_view.py` — **migrated** from `AboutDialog`

### 1.4 Entry point + tray simplification

- [ ] `__main__.py` updated: create `MainWindow` as primary; `TrayApp` as satellite
- [ ] Tray menu simplified: keep scan triggers, feature toggles, notifications; remove Settings/About (→ main window)
- [ ] `MainWindow.show()` on tray double-click or "Open SkillScan" menu item
- [ ] Window close hides to tray (does not quit); Exit nav item quits

### 1.5 Carry-forward fixes

- [ ] Startup check for `cisco-ai-skill-scanner` — show install-hint dialog if not found
- [ ] Wire `fail_on_severity` → `--fail-on-severity <level>` CLI arg in `scanner.py`
- [ ] Persist Drop Zone toggle state to `config.json`
- [ ] Delete `ui/drop_zone.py`

---

## Phase 2 — SQLite Database + Skill Discovery

*Goal: replace flat JSON result store with a relational database; populate it by scanning watched folders on startup.*

### 2.1 Database layer (`core/db.py`)

- [ ] SQLAlchemy declarative models: `Folder`, `Skill`, `ScanResult`, `BomSnapshot`
- [ ] Schema as defined in `ArchitectureV2.md` §Database Schema
- [ ] `session()` context manager for short-lived reads
- [ ] Migration on startup: import existing `results.json` into `scan_results` (one-time, then delete JSON)
- [ ] Database at `%APPDATA%\SkillScan\skillscan.db`

### 2.2 Skill discovery (`core/skill_discovery.py`)

- [ ] `discover(folder: Folder, session) -> DiscoveryResult` — walks folder tree, finds SKILL.md, MCP manifests, A2A cards
- [ ] File type detection: `core/router.py` — `detect_type(path) -> SpecType`
- [ ] SHA-256 hash each file; compare to DB; insert new, update changed, mark missing as deleted
- [ ] Trust invalidation: if `file_hash` changed and `skill.trusted`, set `trusted=False`, clear `trust_signed_at`
- [ ] `DiscoveryWorker(QThread)` — runs discovery without blocking UI; emits `progress(int, int)` and `finished()`
- [ ] Auto-discovery on startup for all `watch_enabled` folders
- [ ] Manual "Refresh" per folder in Folders view toolbar

### 2.3 Windows integration — startup at login

- [ ] "Launch at login" checkbox in Options → General
- [ ] Writes/removes `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\SkillScan`

---

## Phase 3 — Folders View + Skill Tile Grid

*Goal: the primary working view — browse folders, see all skills as tiles with severity badges, trigger scans.*

### 3.1 Folder pane (`views/folders_view.py` — FolderPane)

- [ ] `QListWidget` of tracked folders loaded from DB
- [ ] Each row: folder name, skill count badge, issues count badge (amber if any non-clean)
- [ ] "Add Folder…" button — `QFileDialog`, inserts into DB, runs discovery
- [ ] Right-click context menu: Remove Folder, Scan All, Open in Explorer
- [ ] Selection emits `folder_selected(folder_id)` → loads tile grid

### 3.2 Skill tile grid (`views/folders_view.py` — SkillTileGrid)

- [ ] `QScrollArea` with `QFlowLayout` of `SkillTile` widgets
- [ ] `SkillTile(QFrame)`: skill name, description (truncated), spec type icon, severity badge, trust badge, last-scanned age
- [ ] Tile border colour reflects severity (`CRITICAL_ACCENT`, `HIGH_ACCENT`, `MEDIUM_ACCENT`, `SAFE_ACCENT`, `DIVIDER` for unscanned)
- [ ] Unscanned tiles: dashed border; hover shows "▶ Scan now" overlay
- [ ] Trusted skills: secondary `✓ TRUST` badge in `ACCENT`
- [ ] Click tile → push `SkillDetailView` onto stack, show back button
- [ ] Right-click tile: Scan, Open Folder, Copy Path, Trust / Revoke Trust
- [ ] Toolbar: path breadcrumb, skill count, Filter dropdown (by severity / type / trust), "Scan All" button

### 3.3 Scan integration

- [ ] "Scan All" queues all unscanned (or all) skills in folder; runs `ScanJob` sequentially
- [ ] Progress shown in status bar: "Scanning 3 / 8…"
- [ ] On completion: tile badges refresh from DB; tray notification summarises worst severity
- [ ] Single tile scan: right-click → Scan, opens `ScanProgressDialog`

---

## Phase 4 — Skill Detail View

*Goal: single-skill deep-dive — spec compliance, full scan report, history sparkline.*

### 4.1 Layout (`views/skill_detail_view.py`)

- [ ] Back button in title bar (uses `_history` stack from Phase 1)
- [ ] Header: skill name + type badge + path; severity badge + trust badge
- [ ] Spec compliance section: score bar (0–100), list of missing required fields, warnings
- [ ] Scan report section: reuses `result_formatter.py` HTML output in `QTextBrowser`
- [ ] "Show Raw Output" toggle
- [ ] Scan history section: table of past scans (timestamp, severity, duration, analyzers used)
- [ ] History sparkline: small `QPainter`-drawn severity timeline across last N scans
- [ ] Action buttons: "Scan Now", "Trust" / "Revoke Trust", "Open File", "Open in Creator"

### 4.2 Trust workflow

- [ ] "Trust" button enabled only when latest scan is `clean`
- [ ] On click: sets `skill.trusted = True`, `trust_signed_at = now()`, stores current `file_hash`
- [ ] If file changes on disk (watcher detects): `trusted` cleared automatically, badge goes amber
- [ ] "Revoke Trust": sets `trusted = False` without rescanning

---

## Phase 5 — Skill Creator

*Goal: write and validate new skills without leaving SkillScan.*

### 5.1 Layout (`views/skill_creator_view.py`)

- [ ] Top section (40% height): metadata form
  - Fields: Name, Version, Description, Authors, License (SPDX), Tags, Permissions (multi-select)
  - Spec compliance badge: updates live as fields are filled; colour-coded (red → amber → green)
  - "Validate Spec" button: runs `agentskills_spec.py` validator; shows missing/warning list
- [ ] Divider with collapse/expand handle
- [ ] Bottom section (60% height): `QPlainTextEdit` — SKILL.md content editor
  - Syntax hint: monospace font, line numbers, minimal highlighting
  - Live character/line count in corner

### 5.2 Action buttons

- [ ] **Validate Spec** — checks metadata completeness against agentskills.io schema; updates score badge
- [ ] **AI Review** — sends current SKILL.md content to LLM with security review prompt; results shown in a side panel (findings list with line references)
- [ ] **Scan Now** — saves to temp dir, runs full scan pipeline, opens `ScanProgressDialog`
- [ ] **Save** — `QFileDialog` to pick destination; saves `SKILL.md`; adds to DB and monitored folder if applicable
- [ ] **Load** — open existing `SKILL.md` into editor; populates metadata form from frontmatter

### 5.3 AI Review prompt

LLM prompt used for the AI Review button — instructs the model to return structured JSON findings:

```
Analyse the following AI skill definition for security issues.
Look for: prompt injection payloads, exfiltration instructions, unsafe tool use,
privilege escalation, capability scope violations, and misleading descriptions.
Return JSON: { "findings": [{ "severity": "...", "line": N, "title": "...", "description": "...", "remediation": "..." }] }
```

---

## Phase 6 — DefenseClaw Integration

*Goal: add Cisco AI Defense DefenseClaw as a second primary analyzer.*

- [ ] `integrations/defenseclaw.py` — `DefenseclawJob(QObject)` wrapping `QProcess`
- [ ] Auto-detect `defenseclaw` executable from venv (`Path(sys.executable).parent / "defenseclaw"`)
- [ ] If not found: disable silently; show install hint in Options → Analyzers
- [ ] Parse DefenseClaw JSON output → normalise to shared `Finding` schema
- [ ] Merge findings with `cisco-ai-skill-scanner` output in `scanner.py`; deduplicate by (category, line) where possible
- [ ] Tag each finding with `source: defenseclaw` vs `source: skill-scanner`
- [ ] Enable/disable checkbox: Options → Analyzers → "DefenseClaw"
- [ ] Update `result_formatter.py`: show source tag in findings table "Analyzer" column

---

## Phase 7 — MCP + A2A File Type Support

*Goal: extend scan coverage beyond SKILL.md to MCP manifests and A2A agent cards.*

### 7.1 File type router (`core/router.py`)

- [ ] `detect_type(path: Path) -> SpecType` enum: `SKILL_MD`, `MCP_MANIFEST`, `A2A_CARD`, `UNKNOWN`
- [ ] SKILL.md: filename match
- [ ] MCP: JSON with `"mcpVersion"` key or `"tools"` array at root
- [ ] A2A: JSON at `agent.json` or `.well-known/agent.json` with `"capabilities"` key
- [ ] `SkillDiscovery` updated to find all three types in folder walks

### 7.2 MCP / A2A scan adapter (`integrations/mcp_a2a.py`)

- [ ] Extract tool descriptions / capability declarations as text
- [ ] Assemble synthetic skill context string
- [ ] Route to LLM Analyzer + Trigger Detector only (not `cisco-ai-skill-scanner`)
- [ ] Tag all findings with `source: mcp` or `source: a2a`
- [ ] Return standard `ScanResult`

### 7.3 UI changes

- [ ] Tile type icon: `SKILL.md` = skill icon, `MCP` = plug icon, `A2A` = agent icon
- [ ] Filter dropdown in tile grid: filter by spec type
- [ ] Skill detail header: show spec type badge

---

## Phase 8 — AI BOM Generation + Export

*Goal: generate machine-readable AI Bills of Materials from the skill inventory.*

### 8.1 BOM generator (`integrations/aibom.py`)

- [ ] `generate_component(skill: Skill, latest_result: ScanResult) -> dict` — single CycloneDX component
- [ ] `generate_bom(skills: list[Skill], ...) -> dict` — full CycloneDX 1.6 document
- [ ] Properties per component: `skillscan:spec_type`, `skillscan:scan_severity`, `skillscan:scan_timestamp`, `skillscan:trusted`, `skillscan:spec_score`
- [ ] Export formats: `cyclonedx-json`, `cyclonedx-xml` (via `json` + `xml.etree`; no external library required for initial pass)
- [ ] Save snapshot to `bom_snapshots` table after each export

### 8.2 BOM export UI

- [ ] "Export AI BOM" button in Folders view toolbar (folder-scoped)
- [ ] "Export Library BOM" button in Inventory view (all tracked skills)
- [ ] `QFileDialog.getSaveFileName()` — defaults to `SkillScan-BOM-{date}.cdx.json`
- [ ] Success toast notification via tray `showMessage`

### 8.3 BOM diff

- [ ] "Compare Snapshots…" in Inventory view — picker for two `bom_snapshots` by date
- [ ] `diff_bom(snap_a, snap_b) -> BomDiff(added, removed, changed)` — compare by component name+version
- [ ] Diff shown in modal dialog: three sections (added green, removed red, changed amber) as tables

---

## Phase 9 — agentskills.io Spec Compliance + Inventory View

*Goal: validate skills against the agentskills.io specification and surface compliance across the full library.*

### 9.1 Spec validator (`integrations/agentskills_spec.py`)

- [ ] Download JSON Schema from agentskills.io on first use; cache to `%APPDATA%\SkillScan\spec_cache\`
- [ ] `validate(skill_path: Path) -> SpecResult(score: int, missing: list[str], warnings: list[str])`
- [ ] Score: 100 minus deductions per missing required field (−10) and warning (−3)
- [ ] `SpecWorker(QThread)` — runs validation without blocking UI
- [ ] Store `spec_score` in `skills` table; refresh on each scan

### 9.2 Inventory view (`views/inventory_view.py`)

- [ ] `QTableView` backed by `SkillTableModel(QAbstractTableModel)`
- [ ] Columns: Name, Type, Folder, Severity, Spec Score, Trusted, Last Scanned, Version, Authors
- [ ] Sortable by any column
- [ ] Filter bar: severity, type, trusted state, folder
- [ ] Row click → navigate to Skill Detail view
- [ ] "Export AI BOM" button (library-scoped)
- [ ] "Compare Snapshots…" button
- [ ] Spec Score shown as a coloured bar (red 0–40, amber 41–74, green 75–100)

---

## Phase 10 — Registry Browser + Trust Store

*Goal: discover and import community skills; formalise the trust workflow.*

### 10.1 Registry Browser (new nav item between Inventory and Create)

- [ ] Browse agentskills.io registry (or GitHub search fallback) for published skills
- [ ] Results shown as tiles: name, author, version, description, published date
- [ ] "Import" button: downloads SKILL.md to chosen folder → auto-runs Phase 7 discovery → opens Skill Detail
- [ ] "Scan before import": scan is triggered immediately; import only completes after result shown
- [ ] Community vs Local label on tiles

### 10.2 Trust Store enhancements

- [ ] Trust history: log each grant/revoke with timestamp and scan_result_id
- [ ] "Trust All Clean" bulk action in Inventory view
- [ ] Export trusted skill list as signed manifest (JSON with SHA-256 hashes) for team sharing
- [ ] Import trust manifest: marks matching skills as trusted if hashes match

---

## Phase 11 — Advanced Features

*Goal: power-user and team features that round out the environment.*

### 11.1 Batch reports

- [ ] "Generate Report" in Folders view toolbar — produces a timestamped HTML report for all skills in folder
- [ ] Report template: summary table (counts by severity), then per-skill findings sections
- [ ] Opens in default browser after generation; also saved to `%APPDATA%\SkillScan\reports\`

### 11.2 Multiple concurrent scans

- [ ] `ScanQueue` — manages a list of active `ScanJob` instances
- [ ] Status bar shows: "Scanning 2 / 5…" with a progress indicator
- [ ] Each queued scan is a row in a compact "Scan Queue" panel that slides up from the status bar

### 11.3 Scan scheduling

- [ ] Per-folder option: "Auto-scan on change" (existing) + "Scheduled: daily / weekly"
- [ ] Uses `QTimer` with persisted next-run timestamp in config
- [ ] Silent mode: no progress dialog; tray notification on completion

### 11.4 Policy profiles

- [ ] Named presets: "Strict" (all analyzers, fail on medium+), "Quick" (static + trigger only), "Offline" (no LLM/VT)
- [ ] Selectable per-scan in `ScanProgressDialog` override, or set as default in Options

### 11.5 Portable mode

- [ ] Config and DB stored adjacent to the executable when `--portable` flag passed
- [ ] Allows USB/shared-drive deployment without `%APPDATA%` dependency

---

## Future / Ideas

- **GitHub Actions integration** — `skillscan-action` that scans SKILL.md in a PR and posts findings as review comments
- **VS Code companion extension** — trigger scans from the editor sidebar; inline severity annotations
- **Team config sync** — shared `config.json` fetched from a URL for org-wide defaults (API keys, policy, analyzer flags)
- **Webhook on finding** — POST scan result JSON to a configured URL (Slack, Teams, Splunk, SIEM)
- **SKILL.md syntax highlighting** — VS Code / Notepad++ language extension for frontmatter + body sections
- **Dependency graph** — visualise skill-to-skill dependencies (if declared in metadata) as a DAG
- **A2A live scan** — connect to a running A2A agent endpoint and scan the live agent card from the network
- **MCP server live scan** — connect to a running MCP server and introspect tool descriptions at runtime
