# SkillScan — TODO

> Canonical roadmap: [`development.md`](development.md)  
> This file is a quick-reference view of all outstanding work.  
> Last updated: 2026-06-18

---

## Known Fixes (do first)

These are confirmed bugs in the current v2 build. Address before marking any new phase complete.

| # | Issue | File(s) | Notes |
|---|---|---|---|
| 1 | **Nav rail top gap** | `nav_rail.py` | ✅ Fixed 2026-06-15 — `vbox.setContentsMargins(0, 8, 0, 8)` → `(0, 0, 0, 8)` |
| 2 | **Watched folders not in folder list** | `folders_view.py` | ✅ Fixed 2026-06-15 — extracted `sync_watched_folders()`, called from `_on_settings_changed()` in `main_window.py` |
| 3 | **Activity Log nav item** | `nav_rail.py`, new `views/activity_log_view.py` | ✅ Fixed 2026-06-15 — `activity_log_view.py` created; Activity nav item at index 4; Options→5, About→6, SkillDetail→7; filter buttons All/Scans/Trust/Errors; severity colour coding; Clear Log with confirmation. |
| 4 | **Auto-popup window polish** | `ui/scan_progress.py` | ✅ Fixed 2026-06-15 — SKILLSCAN wordmark title bar (32 px, matches main window), two-tone `_ScanCard` (SYS_BG_PRIMARY title / SYS_BG_SECONDARY body), `_ContentBlock` rounded card, full path in meta row, severity badge tag after path, table headers SYS_TXT_MUTED bg / SYS_TXT_PRIMARY 12 px, window −20 % height / +20 % width |
| 5 | **Options → Watched Folders: AI tooling detection** | `options_view.py` | ✅ Fixed 2026-06-16 — tool registry JSON (26 tools), `core/tool_detector.py`, `ui/detect_tooling_dialog.py`; "Detect AI Tooling…" button in Watched Folders page; glob hint detection, file→parent path resolution, Select All/Detected/Clear, path count summary, deduplication on add. |
| 7 | **Options → Watched Folders: suppress Windows notifications** | `options_view.py`, `core/config.py`, `ui/tray.py` | ✅ Fixed 2026-06-16 — `watched_folder_notify` config flag (default True); toggle added to Watched Folders page; `tray.py _on_watched_change()` gates `self._tray.showMessage()` on it. Scan still runs regardless of the toggle. |
| 8 | **Options → Clipboard: Check Interval as dropdown** | `options_view.py` | ✅ Fixed 2026-06-16 — `QSpinBox` replaced with `QComboBox` (3/5/10/15/30 s), values stored via `addItem(text, data)` + `currentData()`. |
| 9 | **Options → Clipboard: Minimum Characters as dropdown** | `options_view.py`, `core/config.py` | ✅ Fixed 2026-06-16 — `QSpinBox` replaced with `QComboBox` (250/500/1000 chars); default config value updated 200→250 to match. |
| 6 | **Folder watcher triggering repeated scans** | `core/watcher.py` | ✅ Fixed 2026-06-15 — filter to SKILL.md changes only (was firing on any file in the tree incl. scan output/DB writes); debounce raised from 5s to 60s |
| 10 | **Error message box colours** | `ui/_widgets.py` | ✅ Fixed 2026-06-18 — `_DarkMessageBox(QDialog)` in `_widgets.py`: frameless, no OS chrome, FA icon (teal/amber/red per type), rounded dark card, palette-styled buttons. `msg_question/information/warning/critical()` wrappers replace all `QMessageBox.static()` calls in `activity_log_view`, `dashboard_view`, `skill_manager_view`. |
| 11 | **Remove title bar on SkillDetail** | `ui/views/skill_detail_view.py` | ✅ Fixed 2026-06-18 — `_make_header()` background changed from `SYS_BG_SECONDARY` to `SYS_BG_PRIMARY`; the contrasting band that read as a title bar is gone. |

---

## Phase 5 — Skill Manager (next major phase, renamed/merged 2026-06-16)

Renamed from "Skill Creator" — skills are drafted by an AI agent, not hand-authored from
a blank form. SkillScan's job is to package, validate, and remediate that content against
the [agentskills.io specification](https://agentskills.io/specification), and to audit
skills already on disk. Absorbs the former "Own-Skill Audit & Remediation" planned area
(same validation engine, two entry points: new content vs. existing files).

`views/skill_creator_view.py` stub replaced by `views/skill_manager_view.py` (✅ 2026-06-16).

Source guidance:
- [Specification](https://agentskills.io/specification) — frontmatter fields, folder layout, progressive disclosure budget (SKILL.md <500 lines / 5000 tokens)
- [Best practices](https://agentskills.io/skill-creation/best-practices) — gotchas sections, templates, checklists, validate-before-execute loops
- [Optimizing descriptions](https://agentskills.io/skill-creation/optimizing-descriptions) — imperative phrasing, user-intent focus, trigger-eval rubric
- [Using scripts](https://agentskills.io/skill-creation/using-scripts) — non-interactive scripts, `--help`, structured stdout/stderr, exit codes

### Builder UI — v1 ✅ built 2026-06-16
- [x] **Load AI-generated skill** — "Load SKILL.md…" (file) and "Paste from Clipboard" buttons, parses frontmatter + body into the form
- [x] Metadata form: Name (live-validated — lowercase/hyphen/length/must-match-folder-name via `core/spec_compliance.py`), Description (live char counter, ≤1024 chars)
- [x] `QPlainTextEdit` SKILL.md body editor (monospace) with live line/token count against the 500-line / 5000-token budget
- [x] Live spec-compliance score panel — **reuses** `core/spec_compliance.py`, the same engine as the Skill Detail Compliance tab (no duplicated logic)
- [x] Folder scaffolding: `scripts/`/`references/`/`assets/` via `_FileListBox` — Add/Remove files, copied into the package on build
- [x] **Script Lint** (`core/script_lint.py`) — static checks on anything in `scripts/`: interactive-prompt detection (`input()`/`getpass()`/bash `read`), `--help`/usage presence, exit-code presence
- [x] **Build Package** button → writes `{name}/SKILL.md` (+ subfolders) to a chosen destination, folder name forced to match `name`, Default Info fields pre-filled and overridable, blocked until required-field validation passes
- [x] **Scan Now** button → stages the package to a temp dir, runs the existing `core.scanner.ScanJob` against it, renders via the existing `result_formatter.format_result_html`
- [x] **Optimize Description** button — ✅ 2026-06-18 confirmed working. `core/llm.py` `LLMJob(QObject)` moves to `QThread`, calls `litellm.completion()`. `_optimize_description()` in `skill_manager_view.py` builds prompt from name+description+body, emits result to `_on_optimize_done()` which writes back to the description field. API key from Options → Scanning or `ANTHROPIC_API_KEY` env var. Model defaults to `anthropic/claude-sonnet-4-6`.
- [x] **AI Review** button — ✅ 2026-06-18 confirmed working. `_ai_review()` sends full SKILL.md content, `_on_review_done()` parses structured response (ISSUES / CHANGES_MADE / REVISED_DESCRIPTION / REVISED_BODY sections), enters review mode with diff viewer, Accept/Revert actions, and Save Review to markdown.
- [ ] **Validate Spec** as a standalone button — currently validation is always-live (every keystroke), no separate manual trigger needed; revisit if that proves noisy
- [ ] Save/Load *draft* (incomplete/invalid state) — deferred; v1 treats "Build Package" as the only persistence point, blocked until the package is actually valid

### Own-skill audit (merged from former separate phase) — not started
- [ ] Batch-scan `~/.claude/skills/` and any project `.claude/skills/` folders against `core/spec_compliance.py`
- [ ] Surface findings per-skill in a dedicated view (severity-coded, same finding model as main scanner)
- [ ] **Remediate** action — AI-assisted rewrite of non-compliant sections with diff preview before applying. LLM wiring now exists (`core/llm.py`); needs own-skill audit view to be built first.
- [ ] Batch mode — scan all skills at once, summary dashboard
- [ ] Anthropic-best-practices checks beyond raw spec compliance: trigger clarity, instruction specificity, example coverage, no hallucinated tool names

### Options → Default Info — ✅ built 2026-06-16
- [x] **License** — `ui/_license_picker.py` `LicensePicker` widget: curated combo (`data/license_registry.json`, 14 SPDX licenses + No License + Custom free-text), shows category/description/source-disclosure obligation/legal-text link per selection. Shared with Skill Manager's per-skill License field — not a duplicated control.
- [x] **Compatibility** — free text, blank by default (spec: "most skills do not need this field")
- [x] **Metadata** — key/value table editor (string→string map per spec, e.g. author/version)
- [x] **Allowed-tools** — free text, space-separated, labelled experimental per spec
- [x] Pre-fills new packages built in Skill Manager; per-skill override always available
- [x] Changes logged to the config audit trail (`_log_config_changes`)

### Foundational refactor (done alongside the above)
- [x] Extracted `core/spec_compliance.py` as the single validation/scoring engine; `skill_detail_view.py`'s Compliance tab now calls into it instead of a local copy
- [x] **Corrected the field list while extracting it** — the old inline `_REQUIRED_FIELDS` (`name, version, description, authors, license, tags, permissions`) didn't match the real agentskills.io spec at all (only `name`+`description` are actually required). Every skill scanned before this fix was scored against invented rules.

---

## Window Chrome & Nav (completed 2026-06-17/18)

These were done across the previous and current sessions — recorded here for the D2 spec document.

- [x] **Burger nav menu** — hover-triggered `QMenu` (non-blocking `popup()`), 80ms close timer polling cursor position. Three sections: core views / AI views / Options+About+Exit. Left-aligned to icon. Left margin 6px.
- [x] **About menu** — centered `QMenu` under About button, same dark stylesheet, 80ms auto-close. Shows model + version + separator + About SkillScan action.
- [x] **Options as floating window** — `OptionsWindow(QWidget)` frameless window with draggable header, close button, hosts `OptionsView`. Separate from main window stack.
- [x] **Dim overlay** — `_DimOverlay(QWidget)` child of `_panel`, clips to rounded rect, `WA_TransparentForMouseEvents`. Shows when Options window is open, hides on close.
- [x] **Window resizable** — app-level `eventFilter` on `QApplication.instance()` intercepts child widget mouse events for edge/corner resize. `QApplication.setOverrideCursor` for resize cursors.
- [x] **Startup size** — 1920×1024, centered on primary screen.
- [x] **AI nav items** — Prompt Builder (6), Amalgamator (7), Skill Builder (8) added to burger menu and `_NavPanel._TOP`; Options→9, About→10, SkillDetail→11.

---

## Documentation Tasks

| # | Document | Notes |
|---|---|---|
| D1 | **SDD — SkillScan Software Design Document** | Full SDD covering architecture, data model, component interactions, DB schema, scan pipeline, threading model, config store. |
| D2 | **Window, Menu & Toolbar Specification** | Document the current frameless window build: panel structure, taskbar layout, hover menus (nav + about), Options window, dim overlay, resize event filter, icon inventory, palette tokens in use. Useful as a reference for adding new chrome elements consistently. |

---

## Planned Feature Areas

### AI Features

- [ ] **AI Prompt Builder** — nav stub added 2026-06-18 (index 6, `prompt_builder_view.py`). Full build: UI for composing, templating, and testing prompts against the configured LLM. Variable substitution, system/user role split, token count preview, copy-to-clipboard. Entry point from Skill Manager and right-click context menu.
- [ ] **AI Usage Dashboard Widget** — new dashboard panel showing LLM call counts, token usage, estimated cost, and per-feature breakdown (scans vs. reviews vs. builder calls). Requires in-process call logging in `core/llm.py`.
- [ ] **Skill Competence Builder** — nav stub added 2026-06-18 (index 8, `skill_competence_view.py`). Full build: select an assortment of installed skills, bundle them, prompt Claude to build a basic app using all of them with full documentation. Compare scan results across bundles to surface quality and compliance differences.
- [ ] **Skill Amalgamator** — nav stub added 2026-06-18 (index 7, `amalgamator_view.py`). Full build: analyse several skills covering related topics and generate a single consolidated skill with the best content from each. Diff view showing what was merged/dropped. Entry point from multi-select in Folders view.
- [ ] **Context-sensitive right-click** — `QMenu` on right-click throughout the app: tile right-click (Scan, Trust, View Detail, Open Folder, Delete), folder right-click (Add to Watch, Scan All, Remove), activity log right-click (Copy, Filter to This). Actions vary by selection context.
- [x] **Help window shell** — `help_window.py` built 2026-06-19: frameless `HelpWindow`/`_HelpPanel` (mirrors `OptionsWindow`/`_OptionsPanel`), 2-column layout (column 1 rounded-left, column 2 rounded-right, square inner seam), column 2 split into a close-button row + an empty row, wired to the taskbar's `help_requested` signal (`ICON_CIRCLE_QUESTION`, previously unconnected). Deliberately no content yet — built as a clean reference for the rounded-corner treatment after several rounds of Options-window corner issues.
- [ ] **Context-sensitive help content** — row 2 of `help_window.py`'s column 2 is currently empty; needs a topic nav list (column 1, currently also empty) + rendered HTML/CSS content (likely `QTextBrowser`, same approach already used for scan reports). F1 or ? button should open it pre-navigated to the page matching wherever it was invoked from (Dashboard, Folders, Skill Detail, Skill Studio, Options, Activity Log, etc.) — the window itself isn't context-sensitive, the *entry point into it* is, so each view needs to pass its own help-page identifier when launching the window.
- [ ] **Ollama help page (setup guide)** — one of the help pages above: requirements, download, install, and configuration walkthrough for running a local Ollama server as an LLM provider. Entry point: a help/link button on the Software Updates page in Options (`_make_updates_page()` in `options_view.py`), in addition to being reachable from the general help window once that's built.

### Storage & Discovery

- [ ] **System scan for SKILL.md on attached storage** — scan all mounted drives and network shares for `SKILL.md` files not yet in the SkillScan DB. Results shown in a discovery dialog with add-to-watched option. Progress via background `QThread`; cancellable.
- [ ] **Skills Browser** — connect to one or more external URLs (GitHub repos, agentskills.io registry, org-internal feeds) and browse available skills without downloading them first. Tile or list view of remote skills; click to preview SKILL.md content inline; scan before import; one-click add to watched folders. URL list configurable in Options. See also Phase 12 for the fuller safe-preview pipeline.
- [ ] **Hash-before-scan (skip unchanged content)** — store a content hash per scanned path and check it before invoking the scanner; skip the scan entirely if unchanged. For a file: SHA-256 of its content (same approach `_sha256_file()` already uses for trust invalidation in `skill_detail_view.py`). For a folder: hash a manifest (sorted `(relpath, mtime_ns, size)` tuples, or per-file content hashes) rather than raw bytes of every file — cheaper, and still catches adds/removes/renames. Store as a new column (or reuse the existing `file_hash` on `Skill`, since it's the same underlying question: "has this changed since I last looked?"). Wire into `core/watcher.py`'s change-triggered flow so a watcher event on an unchanged file never reaches `launch_scan()` — directly reduces redundant scans and the resulting notification spam from repeated auto-scans of unchanged files.

### Actions
- [ ] Permanent Delete (with confirmation; update DB + Folders view; log to activity)
- [ ] Quarantine (move to configurable path; read-only lock; quarantine section in Folders view)
- [ ] Options: quarantine folder path (default `%APPDATA%\SkillScan\Quarantine\`)

### System Setup (new nav item "Setup")
- [ ] `CLAUDE.md` completeness check
- [ ] `.claude/` directory structure check
- [ ] `.claudeignore` presence check
- [ ] `settings.json` quality check
- [ ] MCP server config detection
- [ ] Stack / directory / commands / conventions declaration checks
- [ ] Installed AI tooling detection (Claude Desktop, Cursor, Copilot, Continue)
- [ ] Secrets files not in `.gitignore` / `.claudeignore`
- [ ] Scoring model: 0–100 per category; weighted overall; colour-coded gauge
- [ ] "Re-scan Environment" button
- [ ] "Export Report" (markdown)
- [ ] Nav: insert "Setup" between Testing and separator before Options

> **Memory reminder:** When System Setup work begins, ask user to share ChatGPT / Gemini / Copilot platform-specific config outputs they have ready.

### Governance (research first — see Research TODOs below)
- [ ] Governance profile selector (Personal / Enterprise / Regulated)
- [ ] Framework mapping in Compliance tab (NIST / NCSC controls)
- [ ] Policy enforcement rules
- [ ] Governance report export (JSON / PDF)

### CLI
- [ ] `scan <path>` — print findings, exit code reflects severity
- [ ] `discover <folder>` — walk + register in DB
- [ ] `list` — all tracked skills (json/table)
- [ ] `trust <path>` — grant/revoke
- [ ] `report <path>` — last scan result
- [ ] `setup` — headless env analysis
- [ ] Design: shared DB or independent? exit code conventions? stdout/stderr separation?

### Skill Source Classification
- [ ] `[P1]` Skill `source` DB field (anthropic / custom / org / partner / unknown)
- [ ] `[P1]` Source badge in Skill Detail header
- [ ] `[P1]` Executable attachment detection (`SUSPICIOUS_EXECUTABLE_ATTACHMENT` finding)
- [ ] `[P1]` Anthropic skill name spoofing detection (`ANTHROPIC_NAME_SPOOF` finding)
- [ ] `[P2]` Auto-invoke flag detection
- [ ] `[P2]` Org-provisioned supply chain finding (`ORG_SCOPE_DISTRIBUTION`)

### Claude Plugin Format (5th spec type)
- [ ] Plugin detection (`spec_type = "plugin"` via `.claude-plugin/plugin.json`)
- [ ] `plugin.json` schema validation
- [ ] `strict: false` finding (`PLUGIN_STRICT_MODE_DISABLED`)
- [ ] External `source.url` finding (`PLUGIN_EXTERNAL_GIT_SOURCE`)
- [ ] Bundle scope score
- [ ] Known-good corpus from `anthropics/skills` + `anthropics/claude-plugins-official`
- [ ] Community plugin cross-reference (`anthropics/claude-plugins-community`)

---

## Later Phases

### Phase 6 — DefenseClaw Integration
- [ ] `integrations/defenseclaw.py` — subprocess wrapper + result parser
- [ ] Merge findings with cisco-ai-skill-scanner output; deduplicate; tag by source
- [ ] Options toggle; result_formatter source column

### Phase 7 — MCP + A2A File Type Support
- [ ] `integrations/mcp_a2a.py` — synthetic SKILL.md context adapter
- [ ] Router updates for MCP/A2A file detection
- [ ] Tile type icons; filter for spec type
- [ ] **Mixed-folder handling** — folders containing both SKILL.md files and MCP/A2A manifests must be handled gracefully: (1) `file_type` discriminator on each tile so SKILL and MCP tiles are visually distinct; (2) folder-level severity stats split by spec type rather than blended (a mixed folder showing one combined severity number is meaningless); (3) detail view / spec compliance tab must dispatch to the correct parser per file — loading an MCP manifest into the SKILL.md compliance parser will produce garbage findings

### Phase 8 — AI BOM Generation + Export
- [ ] `integrations/aibom.py` — CycloneDX 1.6 ML BOM
- [ ] Export button (folder-scoped + library-scoped)
- [ ] BOM diff (two snapshot comparison)

### Phase 9 — agentskills.io Spec + Inventory View
- [ ] `integrations/agentskills_spec.py` — download/cache JSON Schema; validator; `SpecWorker`
- [ ] `inventory_view.py` — full `QTableView` with sort/filter, spec score bar, BOM export

### Phase 10 — Registry Browser + Trust Store
- [ ] Registry browser (agentskills.io / GitHub search fallback)
- [ ] Scan-before-import flow
- [ ] Trust history log; "Trust All Clean" bulk action; export/import trust manifest

### Phase 12 — Online Skill Discovery & Safe Preview

Scan skills sourced from public marketplaces and repositories before they touch the filesystem.

#### Discovery sources
- [ ] GitHub search — query `filename:SKILL.md` via GitHub Search API; filter by stars/forks/recency
- [ ] agentskills.io registry (when public API available)
- [ ] Claude plugin marketplace (if/when launched)
- [ ] Configurable custom source URLs (organisation-internal registries)

#### Safe preview (no unzip required)
- [ ] Stream-read `.zip` / `.tar.gz` archives directly from URL — extract and display `SKILL.md` content without writing to disk
- [ ] Inline skill viewer — render SKILL.md in the existing skill detail layout (spec compliance, findings) against the streamed content
- [ ] Full scan pipeline runs against in-memory content; no file written until user explicitly approves import
- [ ] "Import" action copies to a user-selected local folder and registers in DB; "Discard" leaves no trace

#### Trust & provenance
- [ ] Source badge on tiles/detail: GitHub / Marketplace / Custom / Unknown
- [ ] Verified publisher badge (matched against known-good org list)
- [ ] Download signature check (if publisher provides `.sig` or checksum file)
- [ ] Quarantine-first option — imported skills go to quarantine folder pending manual trust grant

### Phase 11 — Advanced
- [ ] Batch HTML reports
- [ ] Multiple concurrent scans with `ScanQueue`
- [ ] Per-folder scan scheduling
- [ ] Policy profiles (Strict / Quick / Offline)
- [ ] Portable mode (`--portable`)

---

## Research TODOs

| Item | Priority | Notes |
|---|---|---|
| OWASP Agentic Skills Top 10 — scanner integration review | P1 | Cross-reference vs cisco-ai-skill-scanner; identify gap categories |
| agentskills.io specification — workflow integration review | P1 | How to feed into Compliance tab, Skill Creator validator, Inventory spec score |
| Landscape research — what are others building? | P1 | Starting point: HutCh1E/Skills-check; identify complementary tools and detection techniques |
| NIST AI RMF — map SkillScan findings to AI RMF controls | P1 | Four functions: GOVERN, MAP, MEASURE, MANAGE |
| NCSC LLM / AI security guidance review | P1 | Identify controls translating to SkillScan detection rules |
| EU AI Act risk classification — applicability to skills | P2 | High-risk domain detection? |
| Third-party supplier governance mechanisms | P2 | Provenance attestation, SBOMs, supplier questionnaires |
| Jurisdiction detection feasibility | P2 | UK/US/EU jurisdiction-aware compliance mode |
| ISO/IEC 42001 — evidence trail feasibility | P2 | Can SkillScan output contribute to ISO 42001 audit trail? |
| Anthropic name spoofing — detection approach | P1 | Compile known Anthropic skill names; evaluate fuzzy-match thresholds |
| Skill source detection — file-system signatures | P1 | What distinguishes Anthropic / org / partner / custom at the filesystem level? |
| Executable attachment risk — legitimate patterns | P1 | Anthropic skills repo is 84% Python; define `SUSPICIOUS_EXECUTABLE_ATTACHMENT` boundary |
| Auto-invoke detection — frontmatter or implicit? | P2 | Is it declared in SKILL.md / plugin.json or inferred from description? |
| Org-provisioned skills — delivery mechanism | P2 | Known install paths? Config file? Registry entry? |
| Anthropic GitHub — remaining 87 repos | P2 | Browse /orgs/anthropics/repositories; focus on knowledge-work-plugins, agent SDKs |

---

## Skills Library (planned additions)

| Skill | Status | Description |
|---|---|---|
| `ui-text` | Planned | UI copy conventions |
| `ui-design-elements` | Planned | Colour tokens, typography, spacing, iconography |
| `ui-window-elements` | Planned | Window chrome patterns |
| `ui-about-dialog` | Planned | About dialog conventions |
| `ui-options-dialog` | Planned | Options dialog structure |
| `pyqt-window-panes-toolbar-menus` | Planned | PyQt6 frameless window construction: panel/pane layout, toolbar build pattern, hover menus, signal wiring, resize event filter, dim overlay. Based on the SkillScan main window implementation. |
| `features-md-generator` | Planned | Skill that produces a `features.md` for a built UI component: full-size annotated diagram with numbered callouts, plus a companion table listing each component's size, colour token, padding, font, and role. Used to document UI builds for handover and spec reference. |
