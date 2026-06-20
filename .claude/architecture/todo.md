# SkillScan — TODO

> Canonical roadmap: [`development.md`](development.md)  
> This file is a quick-reference view of all outstanding work.  
> Last updated: 2026-06-19

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
| 12 | **OptionsWindow rounded corners looked rougher than the main window** | `options_window.py`, `views/options_view.py` | ✅ Fixed 2026-06-19 — removed the `round_corners()` mask entirely; `OptionsView` no longer paints one flat square `fillRect()`, instead tiles itself with two `_Surface` children (nav rounded outer-left, `content_col` rounded outer-right), mirroring `help_window.py`. See `change_history.md` for the full saga. |
| 13 | **1px seam on the Options General page, ~10px from the right/bottom edges** | `options_window.py` | ✅ Fixed 2026-06-19 — turned out to be a fixed-size DPI-rounding coincidence at 820×640, not structural (confirmed via `test_window.py` bisection — every layer came back clean). Fixed by resizing to 850×650, confirmed seam-free on a real screen. |

> ⚠️ **Pending verification (not yet a confirmed fix):** a follow-up cosmetic request right after #13 (halve the border, grow the window to compensate, then tighten the panel margin) moved `options_window.py` to **870×670** — a different, untested value than the 850×650 actually confirmed above. The seam is proven size-sensitive, so this needs its own real-screen check before being added to the table above as fixed.

> ⏸️ **Paused, not abandoned: notification suppression.** `core/config.py` has `suppress_scan_windows`, `suppress_error_notifications`, `suppress_additional_notifications` keys (added in response to "still getting a load of windows messages for skills") but no Options UI toggle exists for any of them, and `tray.py` doesn't check `suppress_error_notifications`/`suppress_additional_notifications` anywhere yet. The user rejected a tool-use edit to `tray.py` mid-implementation and pivoted to a different topic — explicitly paused, don't resume without it being re-raised.

> 🗑️ **`test_window.py` is temporary diagnostic scaffolding**, not a real feature — see Skills Library note above and `change_history.md`. Left in place (burger menu → "Test Window") at the user's preference. No timeline for removal; ask before deleting it.

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

### Own-skill audit (merged from former separate phase) — ✅ built 2026-06-20
- [x] Batch-scan `~/.claude/skills/` and any project `.claude/skills/` folders against `core/spec_compliance.py` — `core/skill_audit.py` + `views/skill_audit_view.py`, new "Skill Audit" nav item
- [x] Surface findings per-skill in a dedicated view (severity-coded, same finding model as main scanner) — table + detail pane reusing the shared `_compliance_render.py` renderer
- [x] Batch mode — scan all skills at once, summary dashboard — healthy/needs-attention/at-risk counts in the toolbar
- [x] **Description-length / `available_skills` budget risk check** — `core/skill_budget.py`, surfaced in both the audit table ("Desc. Chars" column) and the shared compliance renderer (per-skill "DESCRIPTION LENGTH" section). Informational only, deliberately not factored into `spec_compliance.score()` since the thresholds are community-reverse-engineered and already changed once (250→1536 char per-skill cap) — see [url.md](url.md) for sources. Real finding on the user's own 33 installed skills: ~14,200 chars total against the documented ~8,000-char fallback shared budget (≈177%), 21 skills over the legacy 250-char cap (`claude-api` at 1068, `xlsx` at 941, `docx` at 785, several `pyqt6-*` skills in the 300s).
- [x] **Remediate** action — ✅ built 2026-06-20. Scoped deliberately to `name`+`description` only (the two fields `spec_compliance.py` actually scores, plus the new budget-cap check) — not a general body rewrite, which Skill Studio's existing AI Review already covers. `_REMEDIATE_SYSTEM` prompt sends the issues list (missing required fields, name/description validation errors, budget-cap overage with target length) + body for context only; `<REVISED_NAME>`/`<REVISED_DESCRIPTION>`/`<CHANGES_MADE>` response parsed the same way AI Review parses its tags. `_RemediateDialog` shows a before/after diff (mirrors `_DarkMessageBox`'s frameless chrome); Accept writes a timestamped `.bak-` backup before overwriting the real file, logs to the activity log (`core/activity_log.py`, extracted from `skill_detail_view.py` once a second view needed it), and re-runs the audit scan to refresh scores. Verified end-to-end against a disposable scratch skill (never a real one): backup/rewrite/rescan all confirmed correct (score 50→100 after a real fix). Caught a genuine quality limitation while testing, not a plumbing bug: the configured local model (`llama3.1:8b`) sometimes claims in `CHANGES_MADE` that it shortened a description when the `REVISED_DESCRIPTION` content is actually unchanged — same reliability caveat that already applies to Optimize Description/AI Review with smaller models.
- [x] **Domain-crowding check** — ✅ built 2026-06-20, `core/skill_crowding.py`. Lexical-overlap heuristic (overlap coefficient on description keywords, not Jaccard — Jaccard washes out when one description is much shorter, exactly the vague/clear shape this targets). Two distinct word-exclusion lists, not one — they guard against two distinct calibration bugs caught and fixed the same day: (1) the skill's own *name* is excluded from extraction entirely, since generic naming suffixes like "-builder"/"-helper" both diluted real overlap and created false matches between unrelated same-suffix skills; (2) `_GENERIC_SKILL_WORDS` (create/edit/build/trigger/whenever/helper/tool/etc.) filters generic skill-description *prose style*, derived from word-frequency analysis across the real + benchmark corpora, not guessed — without it, "Create and edit Word documents" vs. "Create and edit Excel spreadsheets" falsely flagged as crowded purely from templated phrasing. Validated against the real twin-pair finding: correctly flags `pdf-builder`↔`pdf-helper`. Surfaced in Skill Audit's toolbar summary (pair count) and per-skill in the detail pane ("DOMAIN CROWDING" section). Informational only, same as `core/skill_budget.py` — not factored into `spec_compliance.score()`.
  - [x] **Regression tests (2026-06-20)** — `tests/core/test_skill_crowding.py`, 7 cases covering both calibration bugs above plus baseline sanity checks (unrelated skills stay unflagged, empty descriptions skipped, custom threshold respected, sort order). **First test file in this project** — `tests/` didn't exist before this; added a root `conftest.py` (`sys.path` insert, same pattern already used by every ad-hoc verification script in this repo) since there's no `pyproject.toml`/installable package layout yet for pytest to resolve `skill_scan` imports otherwise. `pytest tests/ -v` → 7 passed.
- [ ] Anthropic-best-practices checks beyond raw spec compliance instruction specificity, example coverage, no hallucinated tool names — trigger clarity and domain crowding are now covered (above + the skill-selection benchmark below); these three are still unaddressed.
- [ ] **Keep skill-budget constants current** — the 250/1536/8000/109 numbers in `core/skill_budget.py` are a moving target (Anthropic already changed the per-skill cap once, undocumented officially). Write a routine — run as part of SkillScan's own update/release process — that checks for newer values (re-scan the tracked GitHub issues/gist, or a maintained source if Anthropic ever documents this officially) and flags when `core/skill_budget.py`'s constants are stale. Likely lives alongside the planned System Setup module (see below) rather than as a one-off script.
- [x] **Skill-selection benchmark** (validates the trigger-clarity hypothesis empirically, not part of the SkillScan app itself) — `evals/skill_selection/`: 18-skill corpus (15 well-differentiated + 2 deliberately vague controls + 1 vague/clear twin), 16 hand-labeled tasks, `run_selection_benchmark.py` calls the configured LLM N times per task and computes precision/false-positive rate. Baseline result against `llama3.1:8b` (local): 100% accuracy, 0% false-positive rate across 75 trials (15 tasks × 5 runs).
  - [x] **Vague/clear twin-pair test (2026-06-20)** — added `pdf-helper` ("Helps with PDF stuff.") alongside the existing clear `pdf-builder`, plus a task ("redact SSNs from this PDF") where `pdf-helper` is the genuinely-correct answer despite its thin description. Result, 16 tasks × 5 runs (80 trials): **97.5% overall accuracy** — but the interesting finding isn't where it was expected. `pdf-helper` won its own task 5/5 (vagueness alone didn't stop it being found). Instead, **`pdf-builder`'s accuracy dropped from 100% to 60%** purely from `pdf-helper` existing in the corpus — the vague entry got picked for 2/5 runs of the original "combine these PDF files" task, which has nothing to do with redaction. Conclusion: the real risk of a vague description isn't just "this skill won't be found" — it's **cross-contamination that degrades selection reliability for well-written neighbors in the same domain**. Reframes the still-unbuilt "Anthropic-best-practices checks beyond raw spec compliance" item below: a useful check isn't just per-skill description clarity in isolation, it's **domain crowding** — flagging multiple similarly-scoped, under-differentiated skills competing for the same task space.

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

## Open Question: Rebrand (raised 2026-06-20, deliberately not decided)

"SkillScan" fits the already-built core (Folders, Inventory, Skill Detail, Skill Audit, Remediate) — still fundamentally about looking at skill files and reporting on them. It fits less well against where the session's discussion has been heading: Project Setup, Skill Supply Chain (sourcing/vetting/provisioning from outside), task→skillset swapping, agent delegation — all more active/generative than "scan" implies. **User's call: maybe rebrand once the bigger feature set is actually built out, not now.** Capturing candidates so they aren't lost, not to decide between them yet:

- **GUAIRD** (user's own idea) — GU-**AI**-RD, AI embedded mid-word. More original than the now-cliché "-AI" suffix pattern (SentinelAI, VigilAI, etc.), but asks more of the reader — risk that people read "gwaird" before spotting the wordplay.
- **SAIFE** — s-**AI**-fe, reads cleanly as "safe" with AI plainly visible, lower pronunciation risk than GUAIRD, also less original.
- **ChAIn** — "chain" already contains AI as a real word, no forcing needed; ties to the *supply chain* framing (sourcing/provisioning) rather than just security — covers ground GUAIRD's "guard" framing doesn't reach.
- **SkillOps** — mirrors DevOps/MLOps/SecOps; names the category (ops layer for AI skills) rather than picking one pillar, so scan/audit/remediate/govern/provision all sit underneath it instead of competing for the one word.
- **SkillGuard** — keeps security as the primary identity (matches the Cisco AI Defense roots) with the broader lifecycle secondary.

## Documentation Tasks

| # | Document | Notes |
|---|---|---|
| D1 | **SDD — SkillScan Software Design Document** | Full SDD covering architecture, data model, component interactions, DB schema, scan pipeline, threading model, config store. |
| D2 | **Window, Menu & Toolbar Specification** | Document the current frameless window build: panel structure, taskbar layout, hover menus (nav + about), Options window, dim overlay, resize event filter, icon inventory, palette tokens in use. Useful as a reference for adding new chrome elements consistently. Partially satisfied by D3 below (the conceptual patterns), but the icon-inventory/palette-token catalogue this describes still isn't written anywhere — `ui-detailed-design` (see Claude's available skills) may be the right tool for that, not a new doc. |
| D3 | **Stack-agnostic product/technical specification** | ✅ Done 2026-06-19 — `specification.md`. Deliberately excludes pixel/colour-level detail (that's D2's job, still open) in favour of behaviour and architecture *patterns*, so it can pair with external design artefacts or a rebuild in a different stack. |

---

## Planned Feature Areas

> **Roadmap housekeeping (flagged 2026-06-20, not yet done):** this section and "Later Phases" below now have real cross-dependencies that aren't reflected in any ordering — Project Setup needs System Setup's checklist; Skill Supply Chain needs Phase 12 + the crowding check + Own-skill audit; Prompt Builder is a dependency of Project Setup, not just a sibling feature. Worth a dependency-ordering pass (what unblocks what) before picking the next big build — but explicitly **not** a full renumbering of every phase; half of what's listed below is still speculative, and this file is meant to stay a live scratchpad, not a waterfall plan.

### AI Features

- [ ] **AI Prompt Builder** — nav stub added 2026-06-18 (index 6, `prompt_builder_view.py`). Full build: UI for composing, templating, and testing prompts against the configured LLM. Variable substitution, system/user role split, token count preview, copy-to-clipboard. Entry point from Skill Manager and right-click context menu.
- [ ] **Task → skillset swapping** (idea raised 2026-06-20, not yet scoped) — a table mapping declared task types to the skills relevant to each, feeding both the Prompt Builder above (task selection drives the question scaffold) and a live skillset swap. Confirmed technically viable, not just a wish: Claude Code's skill hot-reload (CLI 2.1.0+) means files added/removed under an *already-watched* `.claude/skills/` directory take effect within the live session, no restart — see [url.md](url.md) for sources. No native "Claude requests a skill" protocol exists, so the swap has to be enacted externally (a hook, or a small always-visible "router" skill that runs a script via Claude's own Bash tool) — there's nothing for SkillScan to wait on from Anthropic. The eviction side connects directly to `core/skill_budget.py` (what to swap *out* when budget's tight); the task table is the same lookup the Prompt Builder needs for question-scaffold selection, so these two planned features should share one data source rather than duplicating "what task is this" logic. Open design questions before scoping: where does the inactive skill library live (a staging folder SkillScan manages?), and is task detection explicit (user declares it) or inferred (an LLM call reading the conversation — would need its own accuracy check, same pattern as the skill-selection benchmark in `evals/skill_selection/`).
- [ ] **AI Usage Dashboard Widget** — new dashboard panel showing LLM call counts, token usage, estimated cost, and per-feature breakdown (scans vs. reviews vs. builder calls). Requires in-process call logging in `core/llm.py`.
- [ ] **Skill Competence Builder** — nav stub added 2026-06-18 (index 8, `skill_competence_view.py`). Full build: select an assortment of installed skills, bundle them, prompt Claude to build a basic app using all of them with full documentation. Compare scan results across bundles to surface quality and compliance differences.
- [ ] **Skill Amalgamator** — nav stub added 2026-06-18 (index 7, `amalgamator_view.py`). Full build: analyse several skills covering related topics and generate a single consolidated skill with the best content from each. Diff view showing what was merged/dropped. Entry point from multi-select in Folders view.
- [ ] **Context-sensitive right-click** — `QMenu` on right-click throughout the app: tile right-click (Scan, Trust, View Detail, Open Folder, Delete), folder right-click (Add to Watch, Scan All, Remove), activity log right-click (Copy, Filter to This). Actions vary by selection context.
- [x] **Help window shell** — `help_window.py` built 2026-06-19: frameless `HelpWindow`/`_HelpPanel` (mirrors `OptionsWindow`/`_OptionsPanel`), 2-column layout (column 1 rounded-left, column 2 rounded-right, square inner seam), column 2 split into a close-button row + an empty row, wired to the taskbar's `help_requested` signal (`ICON_CIRCLE_QUESTION`, previously unconnected). Deliberately no content yet — built as a clean reference for the rounded-corner treatment after several rounds of Options-window corner issues.
- [ ] **Context-sensitive help content** — row 2 of `help_window.py`'s column 2 is currently empty; needs a topic nav list (column 1, currently also empty) + rendered HTML/CSS content (likely `QTextBrowser`, same approach already used for scan reports). F1 or ? button should open it pre-navigated to the page matching wherever it was invoked from (Dashboard, Folders, Skill Detail, Skill Studio, Options, Activity Log, etc.) — the window itself isn't context-sensitive, the *entry point into it* is, so each view needs to pass its own help-page identifier when launching the window.
- [ ] **Ollama help page (setup guide)** — one of the help pages above: requirements, download, install, and configuration walkthrough for running a local Ollama server as an LLM provider. Entry point: a help/link button on the Software Updates page in Options (`_make_updates_page()` in `options_view.py`), in addition to being reachable from the general help window once that's built.
- [ ] **Articles section in the help window** — a dedicated topic-nav category (alongside per-view help pages) surfacing longer-form write-ups from `docs/articles/` rather than just short reference pages. First candidate already written: `docs/articles/skill-discoverability-and-the-character-budget.md` (the skill-selection benchmark + the Claude Code `available_skills` character-budget finding). Needs the same Markdown→HTML rendering decision as the rest of "Context-sensitive help content" above (`QTextBrowser` likely needs a Markdown-to-HTML step, since these articles are authored as plain `.md`, not hand-written HTML/CSS like the other help pages) — design that conversion once, reuse for every future article rather than hand-converting each one.

### Storage & Discovery

- [ ] **System scan for SKILL.md on attached storage** — scan all mounted drives and network shares for `SKILL.md` files not yet in the SkillScan DB. Results shown in a discovery dialog with add-to-watched option. Progress via background `QThread`; cancellable.
- [ ] **Skills Browser** — connect to one or more external URLs (GitHub repos, agentskills.io registry, org-internal feeds) and browse available skills without downloading them first. Tile or list view of remote skills; click to preview SKILL.md content inline; scan before import; one-click add to watched folders. URL list configurable in Options. See also Phase 12 for the fuller safe-preview pipeline, and "Project Setup & Skill Supply Chain" below — gap detection from a project's process file is the trigger that gives this feature an automatic reason to fire, not just manual browsing.
- [ ] **Hash-before-scan (skip unchanged content)** — store a content hash per scanned path and check it before invoking the scanner; skip the scan entirely if unchanged. For a file: SHA-256 of its content (same approach `_sha256_file()` already uses for trust invalidation in `skill_detail_view.py`). For a folder: hash a manifest (sorted `(relpath, mtime_ns, size)` tuples, or per-file content hashes) rather than raw bytes of every file — cheaper, and still catches adds/removes/renames. Store as a new column (or reuse the existing `file_hash` on `Skill`, since it's the same underlying question: "has this changed since I last looked?"). Wire into `core/watcher.py`'s change-triggered flow so a watcher event on an unchanged file never reaches `launch_scan()` — directly reduces redundant scans and the resulting notification spam from repeated auto-scans of unchanged files.

### Actions
- [ ] Permanent Delete (with confirmation; update DB + Folders view; log to activity)
- [ ] Quarantine (move to configurable path; read-only lock; quarantine section in Folders view)
- [ ] Options: quarantine folder path (default `%APPDATA%\SkillScan\Quarantine\`)

### System Setup (new nav item "Setup") — likely host for a broader "system testing module"
> User intent (2026-06-20): the description-length/budget check built into Own-skill audit is the first piece of a planned broader system-testing module — checking the live, operational state of the Claude Code environment, not just individual skill files. The checks below (CLAUDE.md, `.claude/` structure, tooling detection) are the same kind of "is the environment actually healthy" question. When this nav item gets built, fold the skill-budget check (and its periodic "keep constants current" routine, see Own-skill audit above) into it rather than leaving it siloed in Skill Audit only.
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

### Project Setup & Skill Supply Chain (new nav item — idea raised 2026-06-20)

> **Process flow drafted 2026-06-20:** [project-setup-flow.md](project-setup-flow.md) — swimlane + timing diagrams for the actual entry-point flow (rough idea → instant local scaffold → background async sourcing/vetting → non-blocking notification), drafted to drive the UI design before this gets built. Key finding from drafting it: the *hard* part (vetting) is already 100% built (scanner + spec_compliance + skill_budget + skill_crowding) — what's missing is almost entirely orchestration, not new detection logic.

**Framing.** System Setup (above) is diagnostic — it audits an existing project and scores it. Project Setup is its generative sibling — it builds a new project's starting state rather than grading one that already exists. Both should share the same checklist definitions (e.g. "does CLAUDE.md have a Stack section") rather than duplicate them: System Setup uses a check to *flag* a gap, Project Setup uses the same check to *generate* what's missing.

The bigger shape this grew into during discussion: SkillScan stops being only a scanner that judges skills someone else already installed, and becomes the thing that actively **sources, vets, and provisions** the skills a project needs — using its own existing scan pipeline as the trust gate for anything pulled in from outside. Concretely, four pieces that click together:

**1. Project Setup module (scaffolding)**
- New nav item (parallel to Skill Studio, but project-level instead of skill-level), or launched as a guided "New Project" flow. Decided 2026-06-20: **not** a Prompt Builder extension — Prompt Builder stays focused on prompt composition; Project Setup *calls into* it for the AI-instructions step, same as Skill Studio calls into `core/llm.py` without being merged into another view.
- Must handle two distinct cases with different UX: **greenfield** (empty folder, generate from scratch) vs. **retrofit** (existing project missing structure — diff against what's there and propose a patch, don't overwrite blindly). Retrofit reuses the Remediate dialog's exact pattern (`_RemediateDialog` — before/after diff, Accept/Reject, backup before write) rather than inventing a second diff-and-accept flow.
- Scaffolding scope (confirmed 2026-06-20, "open to suggestions" → CI config, test suite, skills, config amendments):
  - Skeleton: `src/`, `tests/`, `docs/`, `.claude/{skills,commands,rules}/`, `.gitignore`/`.gitattributes`, `README.md` stub, `LICENSE` (reuse `ui/_license_picker.py` + `data/license_registry.json` — already built for Skill Studio's Default Info, don't build a second picker)
  - `CLAUDE.md` generated from the System Setup checklist + a short Q&A (stack, conventions, commands) instead of starting blank
  - AI instructions / system prompt via Prompt Builder, scoped to "project bootstrap" intent
  - `.claude/settings.json` stub with sensible default hooks — this repo's own `.claude/settings.json` (lint-on-save, etc.) is a real, working template to offer directly
  - CI: GitHub Actions workflow from the declared stack; this repo's own pre-commit hook (ruff/black/pip-audit) is a battle-tested template; Dependabot/Renovate config (ties to the pip-audit-blocked-commit lesson from 2026-06-20)
  - Test suite skeleton matching stack convention + one real smoke test ("does it launch"), mirroring the `/run` skill's own philosophy
  - Security defaults from day one, not retrofitted later: `.gitignore` covering secrets/logs/cache, least-privilege tool grants in `.claude/settings.json`, `.env.example` (never a real `.env`) , `.claudeignore` with sensible defaults
  - Named templates ("PyQt6 Desktop App," "Web API," "CLI Tool") pre-answering most of the wizard so a Beginner-tier user only answers 2-3 deltas — same tiering instinct as the original Prompt Builder idea

**2. Process file / gap detection**
- A staged plan (Setup → Core Build → Testing → Polish, each stage listing the skills it needs) doubling as the manifest the dynamic skill-swapping idea (above, "Task → skillset swapping") needs to actually work — building this gives that earlier idea concrete shape instead of staying abstract.
- The gap is the difference between what a stage's row says it needs and what Own-skill audit reports is actually installed. That gap is the trigger for (3) below — not a generic "browse a registry" feature with no reason to fire, but something that activates automatically when a real gap is detected.
- **Third column, idea raised 2026-06-20: stage → recommended agent, not just stage → skills.** Claude Code plugins already support an `agents/` folder for custom subagent definitions, the same place `commands/`/`skills/` live — Project Setup scaffolding a project-specific subagent (e.g. a tuned test-writer, a security-reviewer) alongside the skills it provisions is the same mechanism, not a new one. Caution worth keeping attached to this idea, not lost: a subagent starts cold with no memory of the parent conversation, so splitting work across agents only pays off when a stage genuinely benefits from an isolated, unbiased pass (security review, focused test-writing) — not a blanket "every stage gets its own agent" policy. The real design question per stage is "does this benefit from isolation," not "should we use agents at all."

**3. Skill supply chain (reframes existing "Skills Browser" / Phase 12 entries — see Storage & Discovery above and Later Phases below — rather than replacing them)**
- Discovery sources, safe preview, and quarantine-first are already specified under Phase 12; what changes is the trigger (gap detection, not manual browsing) and the vetting bar before anything scraped is trusted.
- Every candidate sourced to fill a gap goes through the full existing pipeline before touching disk: scanner + `core/spec_compliance.py` + `core/skill_budget.py` + — genuinely new from the twin-pair test (2026-06-20) — a **domain-crowding check** against skills already installed, since that test proved empirically that a redundant/overlapping skill measurably degrades a good neighbor's selection accuracy even when nobody asked for the redundant one.

**4. Reference exemplars as packaged skill assets**
- "UI design screenshots, palettes, report formats, diagram formats... good examples, bad examples" don't need a new content type — the agentskills.io spec already supports a `references/` subfolder for supplementary material loaded on demand, and Skill Studio's Structure card already has a UI for exactly that. A scraped palette or report-format example is `references/` content inside a skill whose body says "check here for examples."
- **Keep this distinct from `evals/skills/`** — that's a labeled good/bad corpus for testing the *scanner* (security eval fixtures). This is a labeled good/bad corpus for Claude to *reference while doing project work* (design/quality exemplars). Same shape (labeled corpus), different purpose — don't let the two collide in one folder.

**5. SkillScan is the front door, not the work surface (decided 2026-06-20)**
- SkillScan's own UI should **not** become a chat/coding surface. Claude Code and [Claude Cowork](https://www.testingcatalog.com/anthropic-launches-claude-cowork-in-general-availability/) (Anthropic's agentic Desktop-app mode, GA April 2026 — Claude Code's power extended to non-engineers) already have full file access, execution, the skill-invocation mechanism, subagents, and hooks. Rebuilding any of that would be duplicating something already excellent. SkillScan's job ends at correctly preparing the directory, then handing off — launching the real tool as its own process (same established pattern as VS Code's "Open in Terminal"), not embedding a console widget inside SkillScan's own frame. Engineering-shaped projects hand off to Claude Code; less code-centric ones may hand off to Cowork instead — decide per project, not once globally.
- **Concrete requirement this surfaces, not just a preference:** [setting `ANTHROPIC_API_KEY` makes Claude Code silently switch from subscription billing to pay-as-you-go API billing](https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan) — it takes precedence over subscription auth. `core/llm.py`'s `_env_fallback_key()` reads that same env var for SkillScan's own small internal calls (Optimize Description, Remediate, the future Intent Parser), which is fine today since those go straight to litellm, not a subprocess. The moment Project Setup launches Claude Code as a subprocess, that key must be **stripped from the subprocess environment** unless the user explicitly opts into API billing for the handoff — otherwise a key configured for SkillScan's own tiny calls silently hijacks the user's whole session onto metered billing.
- **This simplifies the UI a lot, not just the architecture.** If almost everything in [project-setup-flow.md](project-setup-flow.md) is background, the *visible* surface is genuinely three screens: the prompt entry box; an approvals interface for anything the background vetting flags — which already exists, it's `_RemediateDialog`'s exact before/after diff + Accept/Reject pattern, just triggered by the supply-chain worker instead of Skill Audit; and a new "handoff summary" screen (what got built, which skills were auto-approved vs. flagged, then the launch-to-Claude-Code/Cowork action). Only the third is genuinely new UI.

**Open design questions before this is buildable, not just discussable:**
- Where does the inactive/staged skill library live when not in use (a SkillScan-managed staging folder, separate from `.claude/skills/`)?
- Is gap/task detection explicit (user declares the current stage) or inferred (an LLM call reading the conversation) — inferred detection needs its own accuracy check, same pattern as `evals/skill_selection/`.
- Does the crowding check run only at import time, or periodically against the full installed set (tying back to System Setup's "Re-scan Environment")?
- Who decides whether a given stage actually warrants its own subagent vs. staying in the main conversation — a fixed rule per stage type, or a judgment call surfaced to the user at scaffold time?
- Does Cowork have an equivalent CLI/deep-link launcher to Claude Code's? Unconfirmed — needs checking before designing the handoff around it.

**Intent Parser — ✅ built and tested 2026-06-20, `core/intent_parser.py`**

Built first and in isolation, deliberately, before any scaffolding/UI — it's the one genuinely unproven assumption the whole vision rests on; everything downstream is mechanical. Two LLM calls (not one combined, not N per-stage — serves the token-efficiency goal in the Validation protocol below): `parse_intent()` infers project type/stack/summary/staged plan from a rough idea; `match_local_skills()` matches every stage's capability needs against the local skill corpus in one combined call, reusing `evals/skill_selection/`'s exact name+description matching mechanism rather than inventing a new approach.

Tested manually against 3 realistic rough prompts ("I want something that helps me track my photo collection and find duplicates", "need a tool to manage my todo list with reminders, nothing fancy", "build me something that watches a folder and warns me if any skill files have security issues") against the real 32-skill local corpus, on the local `llama3.1:8b` model:

- **Plan inference (call 1): genuinely good.** All three plans were sensible, correctly staged (3-4 stages), and showed real contextual judgment — e.g. inferred Tkinter rather than defaulting to PyQt6 for "nothing fancy". The riskiest assumption holds up even on a small local model.
- **Local matching (call 2): found and fixed two real bugs before trusting it.**
  1. `template-skill` (a generic skill-authoring template with the literal unfilled placeholder description "Replace with description of the skill and when Claude should use it.") matched against nearly every unrelated capability need — same domain-crowding failure mode as the twin-pair test, different mechanism. Fixed by excluding thin-description skills from the candidate pool entirely, reusing `core/skill_crowding.py`'s keyword logic (`is_thin_description()`, new). First attempt at the threshold (`< 3` keywords) missed `template-skill` by exactly one keyword — caught by re-testing against the real description, not reasoned out in advance; raised to `< 5`.
  2. **The local model hallucinated a skill name** — returned `pyqt6-layout-management` as a match, a plausible-sounding name that does not exist anywhere in the real 32-skill corpus, despite the prompt explicitly saying "exact names as given". Fixed with a defensive validation step: every returned name is checked against the actual candidate pool offered, not trusted blindly — smaller/local models will do this regardless of how the prompt is worded, so the code has to check, not just ask nicely.
- **Known remaining limitation, not fixed, mitigated by design instead:** semantic domain confusion that neither fix above can catch — "Tkinter GUI design" matched all the installed `pyqt6-*` skills (different, unrelated GUI frameworks, false match from the shared word "GUI"); `skill-creator`'s genuinely rich description (mentions "test", "benchmark", "evals") falsely matched "writing pytest tests" and "TDD" despite being about creating *other* skills, not general Python testing. Both candidate skills have substantive, non-thin descriptions, so neither fix applies — this is a real LLM reasoning limitation, not a filterable pattern. Mitigation is the existing design, not a new filter: the Handoff Summary screen's Accept/Reject step (project-setup-flow.md) is exactly the cheap human-review checkpoint this class of error needs, rather than chasing perfect automated matching against 3 anecdotal test prompts (the same overfitting risk avoided when calibrating the crowding check against real frequency data instead of guesses).
- **Tests:** `tests/core/test_intent_parser.py` (6 cases, LLM calls mocked per testing.md's "mock external dependencies" rule) + 3 more added to `tests/core/test_skill_crowding.py` for `is_thin_description()` — 16 total, all passing. Both real bugs above are regression-tested directly (the exact hallucinated name, the exact template-skill description that slipped through once already).

**Validation protocol (planned, blocked on the rest of the build existing first — 2026-06-20)**

The thesis driving this whole feature area, stated plainly so it can be tested rather than assumed: people will actually adopt this **only if it beats three things people already get for free from firing a raw prompt at an LLM** —
1. **Minimum interruption** — little to no back-and-forth from the user; the scaffolded project folder should need little to no intervention to be ready to hand off.
2. **Token efficiency** — the structured approach should cost no more (ideally less) than letting an LLM figure everything out unguided.
3. **Output quality** — the final project should land closer to what the user actually wanted, not just faster/cheaper.

Tick those three and adoption follows; miss any one and the "fire a prompt at raw Claude" baseline stays the rational choice. Test design, once Project Setup exists to test:
- [ ] Multiple test subjects, not one — a handful of representative prompts spanning different domains/complexity. A single comparison run once proves nothing; same lesson as the skill-selection benchmark needing 15+ tasks, not 1.
- [ ] Two arms per subject: (a) conventional — the raw idea fired straight at an LLM/Claude Code with no SkillScan involvement; (b) via SkillScan — the same raw idea through the full Project Setup flow.
- [ ] **Build time** — wall-clock, needs a shared "done" criterion (e.g. a smoke test passing) so both arms stop at the same bar, not whenever the tester feels satisfied.
- [ ] **Token usage** — litellm responses already expose usage data for SkillScan's side; the conventional-LLM baseline needs the same capture wired up or the comparison is unmeasured.
- [ ] **Interference (extra prompts)** — the trap: if the tester intervenes more freely on one arm, the result is meaningless. Needs a fixed intervention policy decided *before* running it (e.g. "only intervene when something is objectively broken, never for style/preference").
- [ ] **Output quality / closeness to stated intent** — the most subjective metric and the one with no proposed measure yet. Same shape as the LLM-as-judge idea from earlier this session (objective step + subjective judged step) — a rubric or judge LLM scoring the final result against the original prompt, with the same bias caveats (position bias, verbosity bias, self-preference bias) already documented from that discussion.
- [ ] Deliverables: a reusable test harness/script (mirrors `evals/skill_selection/`'s shape), a written report of findings, and at least one real built app per arm as the evidence backing it — not just numbers with nothing to inspect.

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

Scan skills sourced from public marketplaces and repositories before they touch the filesystem. See "Project Setup & Skill Supply Chain" (Planned Feature Areas, above) for the trigger that makes this worth building now — automatic gap detection from a project's process file, not manual browsing — and the additional domain-crowding vetting step it adds on top of scan-before-import.

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

## Skills Library — built 2026-06-19 (superseded the rows below)

The "Planned" rows that used to live here were built — as Claude Code skills at `~/.claude/skills/`, not inside this repo. They cover the same ground under different names, scoped to what was actually learned building this app's UI rather than guessed in advance:

| Skill | Status | Covers |
|---|---|---|
| `pyqt6-frameless-window` | ✅ Built | Window creation/sectioning/rounding — supersedes the planned `ui-window-elements` and `pyqt-window-panes-toolbar-menus` |
| `pyqt6-icons-buttons-text` | ✅ Built | FA icon loading, button variants, toggle switch, label hierarchy — supersedes the planned `ui-text`/`ui-design-elements` overlap |
| `pyqt6-scrollbars` | ✅ Built | `SCROLLBAR_STYLE`, viewport-rounding gotcha |
| `pyqt6-menus` | ✅ Built | Hover `QMenu` pattern, `QWidgetAction` toggle rows |
| `pyqt6-help-window` | ✅ Built | Dialog lifecycle — lazy singleton, dim overlay, centering |
| `pyqt6-naming-conventions` | ✅ Built | Casual-term → formal-term glossary — supersedes the planned `ui-about-dialog`/`ui-options-dialog` naming overlap |
| `pyqt6-options-pane` | ✅ Built (rewritten 2026-06-19 to match the current autosave/no-Save-button design) | Settings-pane structure — supersedes the planned `ui-options-dialog` |

`features-md-generator` (diagram + table doc generator) was **not** built — no equivalent exists yet. The `ui-detailed-design` skill (listed in Claude's available-skills, see system context) may already cover this need; worth checking before building a new one.
