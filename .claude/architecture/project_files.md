# SkillScan — Project Files

> Status as of 2026-06-18.

---

## Source — `src/skill_scan/`

### Entry point

| File | Status | Purpose |
|---|---|---|
| `__init__.py` | ✅ Current | `__version__ = "1.0.0"` |
| `__main__.py` | ✅ Current | `QApplication` entry; `python -m skill_scan` (launch) and `--scan <path>` (context-menu/CLI scan) |

### `core/`

| File | Status | Purpose |
|---|---|---|
| `config.py` | ✅ Current | JSON config `load()`/`save()` at `%APPDATA%\SkillScan\config.json`; per-provider credential storage (anthropic/openai/ollama/openai-local) + per-feature (`inapp`/`scanner`) active-provider selection; `get_llm_creds(cfg, feature)`, `_creds_for()`, `_migrate_llm()` (migrates legacy flat `llm_*` keys) |
| `llm.py` | ✅ Current | `LLMJob(QObject)` — non-blocking LiteLLM call on a `QThread`; reads `inapp` feature credentials via `get_llm_creds`; local providers (Ollama, OpenAI-local) get a dummy `api_key="local"` since LiteLLM's OpenAI client layer requires a non-empty key even when the server ignores it; falls back to `ANTHROPIC_API_KEY` env var |
| `scanner.py` | ✅ Current | `ScanJob(QObject)` — wraps `cisco-ai-skill-scanner` (skill/A2A) or `cisco-ai-mcp-scanner` (MCP manifests) via `QProcess`; routes by `router.detect_type()`; injects `scanner` feature LLM creds + VirusTotal/AI Defense keys as env vars; `_normalize_mcp_result()` flattens MCP scanner output to the shared findings shape |
| `router.py` | ✅ Current | `detect_type(path) -> SpecType` — `SKILL_MD` / `MCP_MANIFEST` / `A2A_CARD` / `UNKNOWN` |
| `skill_discovery.py` | ✅ Current | Walks folders, upserts `Skill` rows to DB, SHA-256 hash-check, trust invalidation on change |
| `db.py` | ✅ Current | SQLAlchemy models (`Folder`, `Skill`, `ScanResult`, `BomSnapshot`); `session()` context manager; `init_db()` |
| `result_store.py` | ✅ Current | Bounded JSON result history at `%APPDATA%\SkillScan\results.json`; `ScanResult.llm_skipped` property detects `LLM_ANALYSIS_FAILED` findings |
| `spec_compliance.py` | ✅ Current | Single source of truth for agentskills.io spec validation/scoring — used by both Skill Detail's Compliance tab and Skill Studio's live validator |
| `script_lint.py` | ✅ Current | Heuristic static checks for `scripts/` files per agentskills.io scripting guidance (interactive-prompt detection, `--help`/usage presence, exit codes) |
| `license_registry.py` | ✅ Current | Loads `data/license_registry.json`; backs the `LicensePicker` widget |
| `tool_detector.py` | ✅ Current | Detects installed AI dev tools from `data/tool_registry.json`; backs "Detect AI Tooling…" in Options → Watched Folders |
| `watcher.py` | ✅ Current | `FolderWatcher` — watchdog observer, filters to SKILL.md changes only, 60s debounce |
| `clipboard_watcher.py` | ✅ Current | `QTimer` clipboard poller; MD5 dedup; emits `scan_requested` above a configurable char threshold |
| `test_skills.py` | ✅ Current | Downloads/manages the `cisco-ai-defense/skill-scanner` eval fixtures into `evals/` |

### `data/`

| File | Purpose |
|---|---|
| `license_registry.json` | 14 SPDX licenses + No License + Custom, with category/description/source-disclosure/legal-link per entry |
| `tool_registry.json` | ~26 known AI tools with install-path glob hints, for AI tooling auto-detection |

### `ui/`

| File | Status | Purpose |
|---|---|---|
| `_palette.py` | ✅ Current | All colour tokens (`SYS_*` prefix) — no hardcoded hex in UI files |
| `_widgets.py` | ✅ Current | `RoundedCard`, `TitleBar`, `SCROLLBAR_STYLE` (single source of truth for 6px slim scrollbars), `_DarkMessageBox` + `msg_question/information/warning/critical()` wrappers, `round_corners()` (resize-tracked `QRegion` mask for scroll-area viewports and top-level frameless windows alike), `_Surface`/`_corner_rect_path` (cascade-immune background painter with independently-roundable corners; moved here from `options_view.py` so `help_window.py` could reuse it without duplication) |
| `_flow_layout.py` | ✅ Current | `FlowLayout` (wrap) + `FlowContainer` (responsive width fill); `reorder_by()` for in-place reorder without hide/show flashes |
| `_icons.py` | ✅ Current | Font Awesome 6 Free loader; `fa(size)`/`fa_reg(size)` + icon codepoint constants; replaces earlier Segoe Fluent Icons usage |
| `_license_picker.py` | ✅ Current | `LicensePicker` widget — combo + live info panel; shared by Options Skill Defaults and Skill Studio |
| `_status.py` | ✅ Current | `AiStatusRoutine` — named wrappers (`authenticating()`, `sending()`, `done()`, `error()`) around the taskbar status dot+text indicator |
| `main_window.py` | ✅ Current | Frameless main window; nav rail; `QStackedWidget` of 12 views (see Nav order below); resize event filter; dim overlay for floating Options window. `_NavPanel` (floating nav dropdown) uses `_widgets.round_corners()` so its `_NavItem` children's full-width hover/active highlight fills can't poke past its rounded card corners |
| `nav_rail.py` | ✅ Current | `NavRail`; burger hover menu (core/AI views + Options/About/Exit sections) |
| `options_window.py` | ✅ Current | Frameless floating window hosting `OptionsView` — no titlebar, no dragging, **no `round_corners()` mask**. Mirrors `main_window.py`'s `MainWindow`/`_MainPanel` split: `OptionsWindow` is a transparent shell carrying only window flags (incl. `NoDropShadowWindowHint`); `_OptionsPanel` paints the rounded background/border (same code as `_MainPanel`). `OptionsView` fills the panel so its nav sidebar spans full window height; the close button is injected into `OptionsView.add_header_widget()`'s thin column-2 header row rather than a full-width row above everything. Same mask-free principle as `help_window.py`: `OptionsView` no longer paints its own flat square background — nav and `content_col` are both `_Surface`s that paint correctly-nested rounded shapes and tile the whole view, so nothing square-edged ever reaches `_OptionsPanel`'s curve. Dim-overlays main window; `closeEvent` calls `OptionsView.save_now()` as a safety net (settings already autosave continuously, this just catches an uncommitted in-progress edit). Fixed size `self.resize(850, 650)` — confirmed seam-free on a real screen; the original 820×640 hit a fixed-size sub-pixel/DPI-rounding coincidence between independently-laid-out widgets (see change_history.md), not a structural bug. Re-check for the seam if this size ever changes |
| `test_window.py` | ⚠️ Temporary | Diagnostic-only, not part of the app — bisects the seam above one structural layer at a time by importing the real functions from `options_view.py` (not reimplementing them). Reachable via the burger menu's "Test Window" entry (`_TaskBar.test_window_requested`). All four bisection layers came back clean; the actual fix was the window-size change above, not anything in here. Left in place at the user's preference for further experiments — safe to delete along with its menu entry/signal wiring in `main_window.py` whenever it's no longer needed |
| `help_window.py` | ⚠️ Skeleton | Frameless floating help window, 700×500 — `HelpWindow`/`_HelpPanel` follow the same shell/panel split as `OptionsWindow`/`_OptionsPanel`, but with no `round_corners()` mask: `_HelpPanel` (radius `_OUTER_RADIUS=16`) and both columns (radius `_COL_RADIUS = _OUTER_RADIUS - _PANEL_MARGIN`, derived so it stays concentric whenever the margin changes) paint correctly-nested antialiased rounded shapes with adequate clearance, so nothing square-edged ever reaches the outer boundary — `setMask()`/`QRegion` can't antialias at all (hard binary pixel region) and only made the outer curve look rougher than the unmasked main window's, so it was removed entirely once the columns/panel were nesting properly. `_PANEL_MARGIN=1`: column 1 is 220×498 (fixed width, rounded outer-left corners only, empty), column 2 stretches to fill the rest (478×498, rounded outer-right corners only), split into row 1 (478×44, close button) + row 2 (empty). `0.5px` border, confirmed clean with the corner geometry settled. Wired to the taskbar's previously-unconnected `help_requested` signal. No help content yet — deliberately built content-free as a clean reference for the rounded-corner treatment, see `todo.md` → "Context-sensitive help content" |
| `detect_tooling_dialog.py` | ✅ Current | "Detect AI Tooling…" dialog — Select All/Detected/Clear, path-count summary, dedup on add |
| `scan_progress.py` | ✅ Current | Frameless scan progress dialog; "AI Security Evaluation" button appears when `result.llm_skipped` — runs an `LLMJob` security analysis and renders `<SEVERITY>/<FINDINGS>/<SUMMARY>` into the result view |
| `result_formatter.py` | ✅ Current | HTML findings report renderer — severity badges, findings table, remediation |
| `toggle_row.py` | ✅ Current | Pill toggle + label row, embeddable in `QMenu` via `QWidgetAction` |
| `tray.py` | ✅ Current | System tray satellite; scan triggers; notifications; opens main window / Options window |

### `ui/views/`

| File | Status | Purpose |
|---|---|---|
| `dashboard_view.py` | ✅ Current | Scrollable dashboard card grid; drag-and-drop reorder, edit mode, 60s auto-refresh, layout persisted to config |
| `dashboard/_base.py` | ✅ Current | `DashboardWidget` base class — `WIDGET_ID`, `SIZE` (`full`/`half`/`third`), `build_content()`, `refresh()`; drag handle + remove-from-layout chrome |
| `dashboard/_widgets.py` | ✅ Current | 14 widget classes (1226 lines) — see Dashboard Widgets table below |
| `dashboard/__init__.py` | ✅ Current | `REGISTRY` (ordered widget classes) + `DEFAULT_LAYOUT` (row/column arrangement) |
| `folders_view.py` | ✅ Current | Primary view: folder list pane + skill tile grid; FILTER/SORT `QComboBox`; SIZE icon buttons; compact mode; scan queue; discovery wiring; skill-count label lives here only (no longer duplicated on the taskbar) |
| `skill_tile.py` | ✅ Current | `SkillTile(QFrame)` — severity border, compact mode, badge layout, findings severity-count row, hover overlay, context menu |
| `skill_table.py` | ✅ Current | `QTableWidget`-based alternate list view for skill items |
| `skill_detail_view.py` | ✅ Current | Single skill deep-dive: Report / History / Raw Output / Compliance tabs; trust workflow with `QFileSystemWatcher` auto-revoke on file change; LLM-skipped badge |
| `skill_manager_view.py` | ✅ Current | **Skill Studio** — package/validate/remediate skill content against the agentskills.io spec. Metadata + Structure cards (left), SKILL.md body + AI Review + Compliance cards (right). Optimize Description / AI Review via `LLMJob`; Scan Now; Build Package; Save to Source; Script Lint wiring. All text-entry fields use shared `_FIELD_STYLE` (`SYS_BG_SECONDARY` background) |
| `inventory_view.py` | ⚠️ Stub | Phase 9 — full-library `QTableView`; not implemented |
| `testing_view.py` | ✅ Current | Eval test-skill download/management; migrated from legacy `settings_dialog` |
| `activity_log_view.py` | ✅ Current | Filterable scan/trust event history (All/Scans/Trust/Errors), severity colour coding, Clear Log with confirmation |
| `prompt_builder_view.py` | ⚠️ Stub | Nav placeholder — planned: compose/template/test prompts against the configured LLM |
| `amalgamator_view.py` | ⚠️ Stub | Nav placeholder — planned: merge multiple skills into one consolidated skill |
| `skill_competence_view.py` | ⚠️ Stub | Nav placeholder — planned: bundle skills, have Claude build a demo app using all of them |
| `options_view.py` | ✅ Current | `OptionsView(parent)` — search-filterable, icon-led nav sidebar (`_NavRow`, one Font-Awesome icon per page) over General/LLM/Analyzers/MCP/Clipboard/Watched Folders/Skill Defaults/Updates pages. No `paintEvent` of its own — nav and `content_col` are both `_Surface`s (`_CONTENT_RADIUS = 8`) that tile the entire view with their own correctly-nested rounded shapes, mirroring `help_window.py`'s column split, so the standalone host window never needs a `round_corners()` mask. `_content_stack`'s margins inside `content_col` are tied to `_CONTENT_RADIUS` on the right/bottom — anything less and its opaque square fill paints over (not just clips) the rounded corner instead of respecting it. No Save button — `_wire_autosave()` connects every control's discrete commit signal (toggled/currentIndexChanged/editingFinished/itemChanged) to `_save()`, wired only after the initial `_populate()` pass so opening the window never writes to disk. `save_now()` is the public alias the host window calls from its own close handler. LLM page: per-feature (Skill Studio / Scanner) provider selectors + one card per provider (Anthropic, OpenAI, Ollama, OpenAI Local, third-party) |
| `about_view.py` | ✅ Current | About page — shows both Skill Studio LLM and Scanner LLM rows via `get_llm_creds` |

### Dashboard Widgets (`dashboard/_widgets.py`)

| `WIDGET_ID` | Size | Purpose |
|---|---|---|
| `hero_metrics` | full | Top-line counts (skills, scans, trust, severity mix) |
| `integration_health` | full | Per-analyzer key/connectivity status, using `get_llm_creds(cfg, "scanner")` |
| `ai_module_map` | full | Which AI module uses which provider/model, status dot (Active/No key/Disabled) per Skill Studio + Scanner feature |
| `security_posture` | half | Severity distribution summary |
| `action_items` | half | Outstanding unscanned/untrusted/failed items |
| `ai_usage` | half | LLM call/usage summary |
| `updates` | half | App/dependency update status |
| `recent_activity` | half | Latest scan/trust events |
| `library_composition` | half | Breakdown by spec type (SKILL/MCP/A2A) |
| `scan_velocity` | third | Scan throughput over time |
| `ai_bom` | third | AI BOM snapshot summary |
| `trust_health` | third | Trust grant/revoke health |
| `system_setup` | full | Environment readiness checks, using `get_llm_creds(cfg, "inapp")` |
| `quick_actions` | full | Shortcut buttons to common actions |

### `windows/`

| File | Status | Purpose |
|---|---|---|
| `taskbar_dock.py` | ✅ Current | Drop strip docked flush against the Windows taskbar edge; drag-and-drop skill scan |
| `context_menu.py` | ✅ Current | HKCU Explorer right-click "Scan with SkillScan" installer (no admin required) |

---

## Nav order (`main_window._register_views()`)

`QStackedWidget` index → view: `0` Dashboard, `1` Folders, `2` Inventory, `3` Skill Studio (`SkillManagerView`), `4` Testing, `5` Activity Log, `6` Prompt Builder, `7` Amalgamator, `8` Skill Competence, `9` Options, `10` About, `11` Skill Detail.

---

## Documentation — `.claude/architecture/`

| File | Status | Purpose |
|---|---|---|
| `development.md` | ✅ Canonical roadmap | Phases 1–11+, planned feature areas, later phases, research TODOs |
| `architecture.md` | ✅ Current | Component architecture, DB schema, LLM/provider architecture, dashboard widget architecture, design patterns and decisions |
| `specification.md` | ✅ Current | Stack-agnostic product/technical spec — written so the same app could be rebuilt in any stack; describes behaviour and architecture *patterns* (e.g. "round by painting, not masking"), not this codebase's specific code. Meant to be used alongside `architecture.md`/`project_files.md` (which are codebase-specific) and any external design artefacts |
| `todo.md` | ✅ Current | Quick-reference view of outstanding work — Known Fixes + condensed roadmap pointers |
| `handover.md` | ✅ Current | Session handover — regenerated each session |
| `change_history.md` | ✅ Current | Chronological change log |
| `project_files.md` | ✅ Current | This file |
| `url.md` | ✅ Current | Reference URLs informing design/roadmap/research |
| `auditlog.md` | ✅ Current | Claude Code config/structure/doc-reorganisation change log |
| `assets/` | ✅ Current | Diagrams (`architecture-v2-pipeline.svg`, `main-window-layout.svg`), `screenshot.png` |

> `docs/` no longer exists — fully migrated into `.claude/architecture/` on 2026-06-14 (see `auditlog.md`). Any reference to `docs/DevelopmentV2.md` or `docs/ArchitectureV2.md` elsewhere is stale; the correct paths are `.claude/architecture/development.md` and `.claude/architecture/architecture.md`.

---

## Eval fixtures — `evals/`

Test fixtures for `core/test_skills.py` (downloaded from `cisco-ai-defense/skill-scanner`), **not** a hand-built skills library — there is no project-local `skills/` directory. The user's own working skills live globally at `~/.claude/skills/`.

| Path | Purpose |
|---|---|
| `evals/skills/` | SKILL.md eval fixtures by attack category (backdoor, command-injection, data-exfiltration, obfuscation, path-traversal, prompt-injection, resource-exhaustion, sql-injection, behavioral-analysis) + `safe-skills/`, `safe-skills-2/`; `GUIDE.md` |
| `evals/mcp/` | MCP manifest eval fixtures, incl. `behavioral-analysis/`, `remote/`; `README.md` |
| `evals/a2a/` | A2A agent card eval fixtures |

---

## Root

| File | Status | Purpose |
|---|---|---|
| `CLAUDE.md` | ✅ Current | Project guidance for Claude Code sessions across this directory's projects |
| `README.md` | ✅ Current | Project overview, features, setup |
| `requirements.txt` | ✅ Current | Runtime deps (PyQt6, SQLAlchemy, watchdog, litellm, pywin32, cisco-ai-skill-scanner, etc.) |
| `requirements-dev.txt` | ✅ Current | Dev-only deps (ruff, black, pytest, pip-audit) |
| `run.ps1` / `run.bat` | ✅ Current | Launch helpers |
| `.ai/project-context.md` | ✅ Current | AI-agent project context capsule |
| `.venv/` | ✅ Active | Python virtual environment |

---

## Runtime files (not in repo)

| Path | Purpose |
|---|---|
| `%APPDATA%\SkillScan\config.json` | User config — per-provider LLM credentials, per-feature provider selection, analyzer flags, watched folders, defaults |
| `%APPDATA%\SkillScan\skillscan.db` | SQLite database (folders, skills, scan results, BOM snapshots) |
| `%APPDATA%\SkillScan\activity.log` | Timestamped activity log (scan events, trust changes) |
| `%APPDATA%\SkillScan\results.json` | Bounded scan-result history |
| `%APPDATA%\SkillScan\Quarantine\` | (planned) Quarantine folder for suspicious skills |
| `%APPDATA%\SkillScan\spec_cache\` | (planned) Cached agentskills.io JSON Schema |
| `%APPDATA%\SkillScan\reports\` | (planned) Generated HTML reports |
