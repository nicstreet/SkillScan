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
- [ ] **Task → skillset swapping** (idea raised 2026-06-20, **concrete enactment mechanism proposed 2026-06-21, not yet built**) — a table mapping declared task types to the skills relevant to each, feeding both the Prompt Builder above (task selection drives the question scaffold) and a live skillset swap. Confirmed technically viable, not just a wish: Claude Code's skill hot-reload (CLI 2.1.0+) means files added/removed under an *already-watched* `.claude/skills/` directory take effect within the live session, no restart — see [url.md](url.md) for sources. No native "Claude requests a skill" protocol exists, so the swap has to be enacted externally - **2026-06-21 proposal for that enactment**: a small, self-dropping "build-planner" skill, wired in alongside the real capability skills, whose only job is to *operationalize* the plan already sitting in `CLAUDE.md` (not re-plan from scratch - `parse_intent()` already does that cheaply, before any code exists) into a concrete per-stage swap structure, then remove itself once done so it isn't permanently consuming budget. The swap instructions themselves should live in plain **project files** (e.g. a `/path` the planner skill writes to), not as additional skills - confirmed via research that the `available_skills` character budget applies only to the skill *listing*, not to ordinary files Claude Code can read with its own tools, so this sidesteps the budget constraint entirely for stage-transition metadata. Connects to `core/project_scaffolder.py`'s existing skill-copying mechanism - instead of copying every matched skill directly into `.claude/skills/` at scaffold time, it could stage them in a project-local staging folder instead, with the planner skill drawing from that staging area stage by stage rather than from SkillScan's library directly.
  - **Important mechanics nuance, confirmed via research 2026-06-21**: removing a skill's files does *not* retroactively free tokens already spent on that skill's full content if it was already invoked/read earlier in the same session - it only prevents future re-listing and re-invocation. There's no documented "forget this skill" command in Claude Code, only `/compact` (which can be focused on a topic) and automatic compaction when the context window fills. So the swap mechanism's real value is **prevention** (keep each stage's `available_skills` listing lean and relevant, so the shared budget never overflows and irrelevant options don't compete for space before they're needed), not memory reclamation - a meaningfully different framing than "freeing up memory," worth keeping straight when explaining or building this.
  - **The budget arithmetic, corrected 2026-06-21** (a user estimate of "~60 skills at 150 chars each" was checked against the actual code in `core/skill_budget.py`): the real fallback shared budget is **8,000 chars, not 9k**, and the 109-char `OVERHEAD_PER_SKILL` is *additive* to description length, not included within it - so a skill with a 150-char description actually costs ~259 chars total, giving roughly 31 skills that fit comfortably, not 60. This budget figure is itself a fallback used when the real context window size is unknown - treat it as a conservative default, not a fixed constant, consistent with `skill_budget.py`'s own "worth checking, not certain" framing.
  - The task table is the same lookup the Prompt Builder needs for question-scaffold selection, so these two planned features should share one data source rather than duplicating "what task is this" logic. Open design questions before scoping: is task detection explicit (user declares it) or inferred (an LLM call reading the conversation — would need its own accuracy check, same pattern as the skill-selection benchmark in `evals/skill_selection/`), and the exact file format/location for the `/path` swap-instruction files.
- [ ] **AI Usage Dashboard Widget** — new dashboard panel showing LLM call counts, token usage, estimated cost, and per-feature breakdown (scans vs. reviews vs. builder calls). Requires in-process call logging in `core/llm.py`.
- [ ] **Skill Competence Builder** — nav stub added 2026-06-18 (index 8, `skill_competence_view.py`). Full build: select an assortment of installed skills, bundle them, prompt Claude to build a basic app using all of them with full documentation. Compare scan results across bundles to surface quality and compliance differences.
- [ ] **Skill Amalgamator** — nav stub added 2026-06-18 (index 7, `amalgamator_view.py`). Full build: analyse several skills covering related topics and generate a single consolidated skill with the best content from each. Diff view showing what was merged/dropped. Entry point from multi-select in Folders view.
- [ ] **Context-sensitive right-click** — `QMenu` on right-click throughout the app: tile right-click (Scan, Trust, View Detail, Open Folder, Delete), folder right-click (Add to Watch, Scan All, Remove), activity log right-click (Copy, Filter to This). Actions vary by selection context.
- [x] **Help window shell** — `help_window.py` built 2026-06-19: frameless `HelpWindow`/`_HelpPanel` (mirrors `OptionsWindow`/`_OptionsPanel`), 2-column layout (column 1 rounded-left, column 2 rounded-right, square inner seam), column 2 split into a close-button row + an empty row, wired to the taskbar's `help_requested` signal (`ICON_CIRCLE_QUESTION`, previously unconnected). Deliberately no content yet — built as a clean reference for the rounded-corner treatment after several rounds of Options-window corner issues.
- [ ] **Context-sensitive help content** (queued 2026-06-20, set aside mid-session for the process-chain build — not started) — row 2 of `help_window.py`'s column 2 is currently empty; needs a topic nav list (column 1, currently also empty) + rendered HTML/CSS content (likely `QTextBrowser`, same approach already used for scan reports). F1 or ? button should open it pre-navigated to the page matching wherever it was invoked from (Dashboard, Folders, Skill Detail, Skill Studio, Options, Activity Log, etc.) — the window itself isn't context-sensitive, the *entry point into it* is, so each view needs to pass its own help-page identifier when launching the window. **One buildable unit with the two items below** — the nav list + rendering infrastructure built here is what unblocks both.
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
  - **A second, separate axis from skill tier - project purpose (proof-of-concept/feasibility check vs. a durable build to maintain and extend)**, surfaced by the SEMG/LSE comparison test (2026-06-20): the SkillScan arm's plan defaulted to full rigor (tests, retry logic, venv isolation, MVC structure) costing ~87% more than a baseline that shipped a bare-but-correct script - neither was wrong, they just answered a question the original vague prompt never asked. Skill tier affects *wizard friction* (how many questions get asked); project purpose affects *plan rigor* (whether the generated stages include a testing/tooling stage at all). Don't conflate them - a Pro user might still want a throwaway weekend PoC, and a Beginner might benefit most from the *more* structured build.
  - **Both axes above are already solved, more precisely, in `Notes_Vault/.../SkillScan - AI Skill Scanning Tool/Prompt Analysis.pdf`** (the "AI Work Package Builder" framework, read 2026-06-20) - the actual design research behind the existing `PromptBuilderView` nav stub. "Project purpose" maps onto its **Analysis Depth** dimension (Fast / Standard / Thorough / Expert - a spectrum, not the binary I'd derived from a single test); skill tier maps onto its **Audience → Experience Level** (Beginner/Intermediate/Advanced/Expert). The document also recommends a tiered UX (Tier 1 Standard: Task Definition + Audience + Context + Output Spec; Tier 2 Power: + Identity + Examples + Execution Framework + Governance; Tier 3 Enterprise: + Validation + Refinement + Template Engine) - directly reusable for deciding which controls show by default on Project Setup's entry screen vs. behind an "Advanced options" disclosure, rather than exposing the full 11-component framework and violating minimum-interruption. **Naming note from the same document, worth its own decision later**: "don't call it a Prompt Builder, call it an AI Work Package Builder" - a direct critique of the existing nav item's framing, separate from anything Project-Setup-specific.
  - **Concrete toggle proposal for `ui/views/project_setup_view.py`'s entry screen** (not yet built): two dropdowns next to the rough-idea box - **Experience Level** (Beginner→Expert) and **Depth** (Fast→Expert) - matching the PDF's own Tier-1 minimalism, not the full framework. Depth would need to flow into `core/intent_parser.py`'s `_PLAN_SYSTEM`, letting it decide whether to include a testing/tooling stage at all, directly fixing the over-engineering risk the SEMG/LSE test surfaced.

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
- ~~Where does the inactive/staged skill library live when not in use~~ — **proposal raised 2026-06-20, prompted directly by the SEMG/LSE comparison test**: split into two tiers. **Essentials** - a small, deliberately curated set that stays in the real global `.claude/skills/` (low noise, low crowding risk, what's active for everyday Claude Code use outside any specific project). **Library** - a larger pool living elsewhere (a SkillScan-managed staging folder, not globally active, not loaded by Claude Code day-to-day), searched by `match_local_skills()` *instead of* whatever happens to be globally installed, with only the matched results copied into a given project's `.claude/skills/` - the exact same `_wire_skills()` mechanism already built, just pointed at a different, purpose-built source instead of the organic global folder. Directly motivated by today's test: the local-matching call drew from whatever 32 skills happened to already be installed globally, which is an organic, accumulated mix, not a curated catalogue meant for project-matching - a real library would likely both match better (richer, more specific candidates) and cost less per call (no need to keep the global set large just so Project Setup has enough to match against). Not built - this is the proposal, not an implementation; still needs deciding where the staging folder actually lives, how skills get added to the library (manually curated, or auto-demoted from global when the crowding check flags them as too generic/overlapping for everyday use), and whether `core/skill_audit.py`'s `audit_roots()` needs a second root-type to scan library skills separately from active ones.
- **A more useful test, once the essentials/library split exists**: re-run the SEMG/LSE comparison (or a fresh subject) with a deliberately small global essentials set and a richer, purpose-built library behind it, and see whether match quality and cost per build actually improve over today's result - which drew from an untuned, organically-grown global folder that was never designed for this.

**Library design refinements, raised 2026-06-20/21 during the invoice-tracker test - none built yet:**
- **Many small, atomic library skills instead of fewer broad ones** - directly motivated by today's evidence: the invoice tracker's "PyQt6 QTableView with QSortFilterProxyModel" need went unmatched because nothing in the corpus narrowly covers it - broad skills like `pyqt6-naming-conventions` don't compete for that need, nothing does. A library of hundreds of small, precisely-scoped skills (PyQt-Window, PyQt-Menu, PyQt-Table-Filter-Sort, PDF-Report, CSV-Report, SQLAlchemy-Setup, ...) raises the odds of a precise hit per need. Justified by a 90/10 argument: most projects use a small common core, but the long tail of niche skills is what makes a large library worth having, even though any single project only touches a fraction of it - same intuition as why package registries work.
- **Wishlist-and-lookup instead of full bipartite LLM matching, to keep this affordable at library scale** - have the LLM generate a short list (~20) of needed capabilities directly (no library content needed as input at all, cheap, bounded), then do a *non-LLM* lookup against the library afterward - avoids ever sending hundreds of skill descriptions through an LLM call, which would otherwise multiply the local-matching call's cost in proportion to library size. Real risk: naive name/keyword lookup can miss genuine matches purely on wording ("PyQt6 table with sorting" vs. a skill named `pyqt6-filterable-grid`). Mitigation: reuse `core/skill_crowding.py`'s existing keyword-overlap logic as the cheap lookup layer (already built, already tested) rather than exact-string matching or a second expensive LLM pass.
- **Per-skill synonyms/tags to improve that lookup's hit rate** - e.g. `pyqt6_table` tagged with synonyms like "table," "formatted," "grid" alongside its name+description, all fed through the same keyword-overlap matching. Must reuse the existing generic-word filtering (`_GENERIC_SKILL_WORDS`/`_STOPWORDS`) - "GUI" as a synonym would match nearly every PyQt6 skill indiscriminately, the same false-positive pattern the crowding checker already exists to catch, just arriving via a curated tag instead of a verbose description this time. Synonyms should be generated by a **one-time LLM call when a skill is added to the library**, not regenerated per build - keeps the recurring per-build cost (the whole point of this design) intact while still getting LLM-quality tag suggestions.
- **A feedback skill that writes performance signal back to SkillScan, to improve the library/synonym data over time from real outcomes** rather than only static authored content. Genuinely separate, bigger feature from the above, not a small addition. The hard part is measurement, not mechanism - an LLM self-reporting "was this skill helpful" mid-task is a soft signal with the same judgment-reliability caveats already documented for LLM-as-judge approaches elsewhere in this doc, and any single build's feedback is noise until a skill has accumulated enough uses to mean anything (same "n=1 proves nothing" lesson as the validation protocol, applied to skill-quality tracking instead of build comparisons). Must stay strictly local (write to a local file/DB SkillScan watches, never phone home) - consistent with this project's existing no-auto-upload, no-telemetry-without-opt-in stance, not a new exception to it.
  - **Extended 2026-06-21**: this feedback shouldn't be limited to individual skills - it could also rank/rate the *pre-drawn plan stages* `parse_intent()` produced (was this stage's scope right, was the staging order sensible, did the build actually follow it or deviate significantly). This formalizes something that's so far only been tracked manually, by asking the tester directly after each comparison-test build ("did any assumption need correcting mid-build") - turning that ad-hoc check into a structured signal feeds back into improving `_PLAN_SYSTEM` itself, not just the library/synonym data. Same measurement-reliability and local-only caveats apply.
- **An automated, LLM-driven library-bootstrapping tool, to solve the "hundreds of skills" authoring burden at scale** rather than hand-writing each one: generate hundreds of synthetic rough-idea scenarios (same shape as `evals/skill_selection/`'s corpus generation, just for this purpose instead), run each through `core/intent_parser.py`'s `parse_intent()` to get `skills_needed` per scenario (the exact existing mechanism, no new code needed for this step), cluster/deduplicate the resulting need-phrases across all scenarios (could reuse `skill_crowding.py`'s keyword-overlap to detect near-duplicate needs, same code as the lookup-layer idea above), then author an actual skill for each frequently-recurring cluster (the existing `skill-creator` skill already in this corpus is built for exactly this task) plus its synonym list (the one-time-LLM-call idea above). Ties together five separate pieces already built or proposed today into one pipeline - not yet built, not yet scoped in detail.
- **Near-term, smaller-scale precursor to all of the above**: manually adding a handful of small library skills (the four named earlier - PyQt-Window, PyQt-Menu, PDF-Report, CSV-Report) and re-testing SkillScan's matching performance against them - planned for 2026-06-22, ahead of any of the automated/larger-scale ideas above.
- **Reactive, on-demand skill-authoring for unmatched needs, raised 2026-06-21** - if no library skill matches an identified need (the wishlist-and-lookup step above returns empty for it), make one additional LLM call to author a brand-new skill for that specific gap, reusing the existing `skill-creator` skill already in this corpus rather than building new authoring logic. Sharper and better-targeted than the proactive bulk-generation idea above, since it grows the library exactly where real, proven demand exists (a genuine project genuinely needed this), not speculative demand from synthetic scenarios - the two ideas aren't mutually exclusive, but this one is cheaper to start with. **Decided 2026-06-21: a newly-authored skill goes to *both* the project's local `.claude/skills/` (immediately usable for the current build) and the persistent library (so future projects benefit too)** - not an either/or. Still needs, separately: a distinct "auto-generated for a gap, not vetted" flag in the Handoff Summary, rather than being presented with the same confidence as an established library skill - same instinct as the existing Remediate/Accept-Reject pattern, applied to skill provenance instead of skill edits. The "pays for itself in token savings" intuition behind this is a hypothesis, not yet confirmed by any test run - worth checking once built, not assumed going in.
- **Visualisor overlay, raised 2026-06-21 - meaning still unclarified.** Could be: an updated architecture diagram extending the existing Mermaid diagrams in `project-setup-flow.md` to show how the swap mechanism fits in; an actual in-app UI feature visualising build progress/stages within SkillScan itself; or something else. Not yet resolved - ask before building anything here.
- **Stated proof criterion for this whole thread of ideas, 2026-06-21**: "asking for a big app to be built with many facets and how the build is structured" - i.e. a deliberately large, multi-stage test subject (bigger than the SEMG or invoice-tracker subjects so far) is the actual test of whether the swap mechanism, the library, and reactive skill-authoring are worth their added complexity, not just discussion. None of the ideas above should be considered validated until checked against a build at that scale - same "don't assume, test it" discipline as the rest of the validation protocol.
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

**Project Scaffolder — ✅ built and tested 2026-06-20, `core/project_scaffolder.py`**

Second link in the chain, built right after Intent Parser proved trustworthy. Greenfield only in this v1 (refuses to scaffold over a directory that already looks like a project — retrofit is a meaningfully bigger feature with its own UX, deliberately deferred). Deliberately not included either: CI config, a real test suite (just the skeleton dir), LICENSE selection (reuse `ui/_license_picker.py` from the eventual UI, don't duplicate it here), named templates, and AI instructions via Prompt Builder — `CLAUDE.md` generation already produces a real, useful first version directly from the `IntentResult` with zero extra LLM calls, covering a reasonable amount of that need without Prompt Builder existing yet.

Writes: skeleton dirs (`src/`, `tests/`, `docs/`, `.claude/{skills,commands,rules}/`), `.gitignore` (stack-agnostic security-conscious core + a Python section only when the stack says Python — trimmed from this repo's own `.gitignore`), `.claudeignore`, `.env.example`, `.claude/settings.json` (a stack-agnostic permission denylist trimmed from this repo's own settings.json — dropped the PostToolUse/Stop hooks since those call SkillScan-specific PowerShell scripts, not generically reusable), `README.md`, and a real generated `CLAUDE.md` (summary, stack, full staged build plan, and which local skills got wired in). Matched local skills get their entire real folder (`SKILL.md` + any `scripts/references/assets`) copied into `.claude/skills/` via `shutil.copytree`.

One real bug caught by testing, not foreseen: `_wire_skills()` computed the wired-skill list correctly and used it for `CLAUDE.md` generation, but never actually assigned it onto `ScaffoldResult.wired_skills` — that field silently stayed at its empty default forever. Caught by a test asserting on the result object, not just inspecting the generated file (`test_scaffold_project_wires_in_matched_local_skills`) — exactly the kind of bug that looks fine if you only eyeball the output.

8 tests, `tmp_path`-based (per testing.md — this module's whole job is file I/O, so the filesystem is the thing under test, not an external dependency to mock).

**Full end-to-end smoke test, real LLM + real local corpus + real disposable directory:** "I want something that helps me track my photo collection and find duplicates" → produced a 4-stage plan, correctly matched 7 real `pyqt6-*` skills (zero hallucinations, zero `template-skill` pollution this run) plus one borderline-but-defensible match (`auditprojectfolder` for a setup-related need — not wrong, just a stretch, exactly the class of call the Handoff Summary review step exists for) — all wired in with their real `SKILL.md` content intact, plus a genuinely good generated `CLAUDE.md`. First two links of the chain now work end-to-end.

**Handoff Summary + Launch — ✅ framework built 2026-06-20, `ui/views/handoff_summary_view.py` + `core/launch.py`**

Deliberately scoped as "framework, will grow" rather than the finished screen — built now so there's something real to pass the chain's output *to*, rather than waiting for the full Project Setup wizard (prompt-entry screen, gap detection, background Supply Chain) to exist first. **Not wired into `main_window.py`'s nav stack** — there's no prompt-entry screen to reach it from yet, so it's directly testable/driveable standalone for now, same pattern as every other piece of this chain so far.

`core/launch.py` — the safety-critical piece flagged earlier in this section: `launch_claude_code()` strips `ANTHROPIC_API_KEY` from the subprocess environment by default (`allow_api_billing=True` opts back in explicitly), spawns `claude` as its own process via `shutil.which`-resolved path, and returns immediately - SkillScan does not wait on or embed the launched process. Cowork launching is **not implemented** - still unconfirmed whether it has an equivalent CLI/deep-link launcher (see open design questions above) - guessing at one would be worse than not having it. 4 tests, `subprocess.Popen`/`shutil.which` mocked (per testing.md - a real launch would spawn an actual Claude Code session as a side effect, which a test must never do), including a direct regression test confirming a real `ANTHROPIC_API_KEY` set in the environment does not leak into the launched process by default.

`ui/views/handoff_summary_view.py` — renders project type/summary/stack/location/full build plan/wired-skills list from an `IntentResult` + `ScaffoldResult`, with a Launch button gated on `claude_code_available()`. Visually verified by rendering with real scaffolded data and screenshotting it (not just unit-tested) — per this project's own UI-testing rule, and because the Launch button's click handler was deliberately *not* exercised in that verification (clicking it for real would have spawned an actual Claude Code session as a side effect of testing, the same reason `core/launch.py`'s tests mock the subprocess call rather than invoking it). No automated test for the view itself - consistent with this project's existing convention that PyQt6 views are visually/manually verified, only `core/` logic gets pytest coverage.

Still deferred, explicitly not in this pass: the Cowork launch option, gap-detection results display, a richer file-tree preview, and the approval-dialog step for anything the background Supply Chain eventually flags.

**Prompt-entry screen + full wiring — ✅ built and tested 2026-06-20, `ui/views/project_setup_view.py` + `core/project_build_worker.py`**

The last piece needed for a fully runnable v1 loop - closes the gap the day's earlier updates both flagged. `ProjectSetupView` is a `QStackedWidget` of two pages: an entry form (rough-idea text box, a parent-directory picker reusing the same `QFileDialog.getExistingDirectory` pattern used everywhere else in this app, "Build It" button) and the existing `HandoffSummaryView` as page 2 - swaps to it automatically once a build finishes. Still **not wired into `main_window.py`'s nav stack** - same reasoning as the rest of this chain, real and directly testable without needing the larger nav decision made first.

`core/project_build_worker.py` - new `ProjectBuildWorker(QThread)`, living in `core/` alongside the other QThread workers that wrap core logic (`DiscoveryWorker`, `SkillAuditWorker`), not in `ui/`. Runs `parse_intent()` -> resolves local skill name->path via `core/skill_audit.py`'s `audit_roots()` -> `match_local_skills()` -> `scaffold_project()` off the UI thread, emitting progress text between each step. Also added: `slugify_project_name()` in `core/project_scaffolder.py` (e.g. "Photo Collection Organizer" -> "photo-collection-organizer") - lets the user pick a parent directory upfront without inventing a project folder name before they know what's actually being built; 3 tests covering the normal case, punctuation stripping, and the empty-input fallback.

**Name-collision fix — ✅ done 2026-06-20**, found by real use during the invoice-tracker comparison test: two similarly-vague prompts ("stock price tracker," "invoice tracker") both got inferred as a generic project type that slugified to the same folder name, hard-failing the second build with `ScaffoldError`. Added `resolve_target_dir()` in `core/project_scaffolder.py` - tries `slug`, `slug-2`, `slug-3`, ... rather than failing outright, since the user never typed this name themselves (it's auto-derived from an LLM guess), so a clash shouldn't need their intervention to resolve - same instinct as how Windows/macOS handle "this name already exists" when creating a new folder. `project_build_worker.py` now calls this instead of computing the path inline. 4 new tests, including a direct regression test reproducing the exact collision. `scaffold_project()` itself is unchanged and still fails loudly if handed a colliding path directly - the new function only changes how the *worker* picks a path in the first place.

**Full real end-to-end smoke test through the actual GUI widget** (not just the underlying core/ functions) - typed the photo-organizer rough idea into the real `QPlainTextEdit`, clicked the real "Build It" button, let the real background worker run two real LLM calls against the real local corpus, and watched it correctly auto-transition to the summary page after 99 seconds (cold local model). Result: correctly slugified target folder, 5 real skills matched (no hallucinations, though a couple are generic/borderline matches - `pdf` and `application-solution-design-document` for a photo-duplicate-finder needs explanation rather than being clearly wrong - exactly the class of call the still-unbuilt Accept/Reject review step exists for), Launch button genuinely enabled since `claude` resolves on PATH. First time all three pieces have run together as one flow rather than three separately-tested pieces.

**The v1 chain is now fully runnable, not wired into the main app.** What's left before this is reachable from the actual SkillScan UI: a `main_window.py` nav decision (new top-level item, or reachable some other way), plus everything already listed as deferred across this whole section (Gap Detection, background Supply Chain, Cowork launch, named templates, retrofit, CI/test-suite generation, LICENSE picker integration). The validation protocol below can technically run against this chain as it stands today.

**Wired into the nav — ✅ done 2026-06-20, `main_window.py`.** `ProjectSetupView` is now a real nav item ("Project Setup", wand-magic icon), reachable from both the floating nav panel and the burger menu. Added as `_register_views()`'s 13th entry (stack index 12), inserted *before* `SkillDetailView` rather than appended after it - `SkillDetailView` isn't nav-reachable itself (only via `navigate_to()` from a tile click) and was already at the position the floating nav panel's automatic `_BOTTOM` offset math would otherwise land the new item on, so inserting before it and bumping `SkillDetailView` to index 13 was the only one-line-change option; appending after it would have collided two views onto the same stack slot. Verified for real: launched the actual `MainWindow`, called the exact same handler a real nav click invokes, confirmed the taskbar title updates to "Project Setup" and the correct view renders (screenshotted), and confirmed the pre-existing Folders -> tile -> Skill Detail flow still lands on the right view after the index shift. The v1 chain is now reachable from the real app, not just test scripts - what's left is exactly what was already listed as deferred above, nothing new.

**Real-world end-to-end confirmation, by the user, not a script — 2026-06-20.** Typed a real idea into the live wired-in nav item, the chain scaffolded a real project (a PKI logical architecture diagrams tool), and clicking Launch correctly spawned `claude` in that new folder via `core/launch.py`. The only friction: Claude Code's own standard one-time "trust this folder" prompt for a workspace it had never seen, which looked like a hang because nothing in the app warned it was coming, compounded by a terminal keyboard-focus issue unrelated to SkillScan. **Fix:** `handoff_summary_view.py` now shows a persistent hint above the Launch button - "First time opening this folder, Claude Code will ask you to confirm you trust it — that's expected, not an error." This is the first time the *complete* chain - including the real subprocess launch, not just a screenshot stopping short of it - has been confirmed working by an actual user typing an actual idea.

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

**First real data point, "via SkillScan" arm only — 2026-06-20.** Subject: "I need an app to provide the current price of SEMG on the LSE" (deliberately vague, no stack specified — see discussion above on why vague is the right test input). SkillScan prep (Intent Parser + Scaffolder, Sonnet): ~3,500 tokens, ~$0.014, a few seconds. The actual build, done by the user driving a real Claude Code session against the SkillScan-prepared `CLAUDE.md`: **$1.70, 5m50s API duration (21m33s wall-clock - the gap is human response latency to clarifying questions, not system speed; use API duration for fair time comparisons, or enable Auto mode on both arms next time), 477 lines added, 4 removed, two clarifying questions** (one was the interface choice - rich-CLI vs tkinter vs both; recommended rich-CLI as the better fit for a single-purpose lookup tool, rejecting "both" as unrequested scope). Usage breakdown: 582 fresh input tokens, 30.5k output, 2.3m cache read, 92.7k cache write - the prep's ~3,500 tokens is roughly 0.8% of the build's total cost, negligible overhead if the prep meaningfully reduces build-phase waste.

**Baseline arm, same subject, same day.** Same prompt, cold Claude Code session, empty folder, no SkillScan involvement: **$0.91, 3m20s API duration (13m38s wall), 130 lines added, 3 removed, two clarifying questions** (same count as the SkillScan arm). Usage: a mix of claude-haiku-4-5 (11.8k input, 436 output, 1 web search - delegated cheap-model research, presumably to find the actual LSE price data source) and claude-sonnet-4-6 (554 input, 14.3k output, 1.2m cache read, 50.9k cache write).

**Honest read of the comparison, not a clean win either way:**
- **Interference: tied.** Both arms asked exactly 2 clarifying questions. No advantage to the structured approach on this metric, at least in this n=1 test.
- **Cost/time: baseline arm was cheaper and faster** ($0.91 vs $1.70, 3m20s vs 5m50s API) - on the surface, against the thesis.
- **But it's not a clean efficiency loss - it's a scope difference, confirmed by checking the actual output.** The SkillScan arm's `requirements.txt` includes `pytest`, `ruff`, `black` as dev dependencies; the baseline arm's does not. The SkillScan arm almost certainly built tests and lint-compliant code because its `CLAUDE.md`-supplied plan included a "Testing / Polish" stage with "writing pytest tests" as a listed need - every Intent Parser plan generated this session, across every test subject, included that same generic stage regardless of project complexity. The baseline arm, with no plan at all, made its own (unprompted) judgment call to skip all of that and ship a bare script.
- **The actually important open question this surfaces:** did the original prompt - "an app to provide the current price of SEMG on the LSE" - want test/lint tooling at all? It never asked for it. If the baseline's bare script works just as correctly, Claude Code's cold judgment to skip ceremony for a trivial personal utility may be the *better-calibrated* call, not a worse one. This points at a real, actionable refinement for `core/intent_parser.py`'s `_PLAN_SYSTEM`: **plan generation should probably scale stage-richness (and whether to include a testing/tooling stage at all) to the apparent complexity of the request, rather than always inserting the same generic "Testing / Polish" stage regardless of scale.** Not fixed yet - flagging it here as a finding from real comparative testing, the same way every other calibration bug this session was caught by testing against real data rather than guessed at in advance.
- **Output quality is still the genuinely unmeasured piece.** Neither app's actual correctness (does it really fetch and display the real SEMG/LSE price) has been checked yet. Without that, "which arm did better" can't be answered from cost/time alone - a cheaper app that doesn't work isn't a win, and a more expensive one that's needlessly over-tooled isn't necessarily a loss either.
- **n=1.** The validation protocol always called for multiple test subjects spanning different domains/complexity precisely because a single comparison proves nothing on its own - this is a real, useful first signal, not a verdict.

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
