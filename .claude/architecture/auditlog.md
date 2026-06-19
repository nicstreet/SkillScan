# SkillScan — Configuration Audit Log

> Records changes to Claude Code configuration files, project structure migrations, and documentation reorganisation.
> Most recent entry first.

---

## 2026-06-18 — Documentation sync pass

Full review of all 7 files in `.claude/architecture/` against the actual current codebase, requested after several sessions of feature work (LLM provider refactor, dashboard widgets, Skill Studio) had drifted ahead of the docs.

### Stale path references fixed

The 2026-06-14 `docs/` → `.claude/architecture/` migration (below) renamed `DevelopmentV2.md` → `development.md` and `ArchitectureV2.md` → `architecture.md`, but left several internal cross-references pointing at the old deleted `docs/...` paths:

| File | Old reference | Fixed to |
|---|---|---|
| `todo.md` line 3 | `docs/DevelopmentV2.md` | `development.md` |
| `development.md` (Phase 2 DB schema note) | `ArchitectureV2.md` | `architecture.md` |
| `handover.md` | `docs/DevelopmentV2.md`, `docs/ArchitectureV2.md` | regenerated in place with current paths |

`auditlog.md`'s own historical entries (below) were left untouched — they describe what those filenames were called *at the time*, which is accurate as a record.

### Content corrections

- `project_files.md` — full rewrite; was dated 2026-06-13 and missing every file added since (dashboard package, `skill_manager_view.py`, `core/llm.py`, `spec_compliance.py`, `script_lint.py`, `tool_detector.py`, `license_registry.py`, `_icons.py`, `_license_picker.py`, `_status.py`, `options_window.py`, `detect_tooling_dialog.py`, and the rest of the AI-feature view stubs); also corrected a wrong claim that `about_dialog.py`/`settings_dialog.py`/`results_window.py` are "kept for tray fallback" — grepped the codebase and confirmed the tray menu no longer references any of them; relabelled as orphaned/deletion candidates
- `architecture.md` — nav rail table and Project Structure tree updated to the current 12-view layout; added "LLM Provider Architecture" and "Dashboard Widget Architecture" sections, neither of which had been documented anywhere
- `development.md` — Phase 1–4 checkboxes were still unchecked despite being confirmed complete (cross-checked against `todo.md` and the live codebase before bulk-toggling); Phase 5 section rewritten to match the as-built Skill Studio (left/right panel layout, XML-tagged AI Review response) instead of the original "Skill Creator" plan (top/bottom layout, JSON findings); duplicate/stale "Known Fixes" section replaced with a pointer to `todo.md`, which is kept live every session
- `handover.md` — regenerated; was frozen at 2026-06-13, predating the dashboard and LLM refactor entirely
- `change_history.md` — appended a 2026-06-16 → 2026-06-18 session entry

### Scope note

This was a documentation-only pass — no application code was changed. Flagged for follow-up, not acted on here: `ui/about_dialog.py`, `ui/settings_dialog.py`, `ui/results_window.py` appear to be dead code (no remaining import path); and the working tree has ~66 uncommitted changes including an apparent `skills/` → `evals/` directory restructure that predates this session (see `handover.md` → "Uncommitted changes" for detail) — flagged to the user rather than committed or altered.

---

## 2026-06-14 — Claude Code hooks added

### `.claude/hooks/` — created

Two hooks added after auditing the existing `.git/hooks/pre-commit` (which already runs ruff, black, pytest, pip-audit, and .env staging check at commit time). Claude Code hooks add in-session enforcement that fires during Claude's work, not just at commit.

| File | Trigger | Behaviour |
|---|---|---|
| `post-edit-lint.ps1` | `PostToolUse` on `Edit\|Write` matching `src/**/*.py` | Runs `ruff check src/`; exits 2 (blocking) on lint errors so Claude fixes them in the same turn |
| `stop-markers.ps1` | `Stop` (every turn end) | Scans `src/` for `# XXX:` and `# SECURITY:` markers; feeds found markers back to Claude as `additionalContext` (non-blocking) |

**Why these two:**
- `post-edit-lint.ps1` — closes the lint feedback loop immediately rather than waiting for `git commit`; aligns with the best-practice "give Claude a way to verify its work"
- `stop-markers.ps1` — ensures Claude is always aware of outstanding blocking markers before declaring a task done; non-blocking so it doesn't prevent Claude stopping when markers are intentional in-progress TODOs

**What was not hooked (and why):**
- `black` — formatter; auto-fixing on every write would interfere with edits in progress
- `pytest` — unit test suite too slow to run on every file edit; pre-commit hook is the right gate
- `pip-audit` — only relevant when `requirements.txt` changes; not worth running every turn

### `.claude/settings.json` — hooks section added

Wired `PostToolUse` and `Stop` hooks into project settings. The `if` filter on PostToolUse (`Edit(src/**/*.py)|Write(src/**/*.py)`) ensures the lint hook only fires on Python source edits, not documentation or config file changes.

---

## 2026-06-14 — CLAUDE.md rewrite + docs migration

### CLAUDE.md rewritten (project root)

**Removed:**
- Entire stale project structure describing `src/main.py`, `src/models/`, `src/scanners/`, `src/utils/` — none of these exist in the v2 codebase
- Old `skillscanner/` directory layout
- 7-phase development process description (belongs in architecture docs, not CLAUDE.md)
- Verbose "Reducing Hallucinations" section
- Verbose "Debugging" section
- References section pointing to old `.claude/rules/` files
- Redundant Python conventions already covered by global `~/.claude/rules/python-style.md`

**Added:**
- Correct run command (`.\run.ps1` from new project location)
- Actual `src/skill_scan/` project structure with real file paths
- Runtime locations (`%APPDATA%\SkillScan\` — DB, config, activity log)
- Real stack with actual package names from `requirements.txt`
- References to `.claude/architecture/` docs (architecture.md, development.md, handover.md, todo.md)
- Current state summary (Phases 1–4 complete, 3 known fixes)
- 5 PyQt6 gotchas distilled from session handover notes
- Colour token reminder (use `_palette.py` tokens, never hardcode hex)
- Condensed "Before committing" checklist

**Rationale:** Old CLAUDE.md was a v1 template that described a project structure that no longer exists. Every Claude session was loading incorrect context. Rewrite targets ~100 lines (well under the 200-line best practice limit).

---

### `.claude/architecture/` — files added

| File | Source | Action |
|---|---|---|
| `ArchitectureV2.md` | `docs/ArchitectureV2.md` | Copied — then deleted (duplicate of `architecture.md`) |
| `DevelopmentV2.md` | `docs/DevelopmentV2.md` | Copied — then deleted (duplicate of `development.md`) |
| `assets/main-window-layout.svg` | `docs/assets/main-window-layout.svg` | Copied — fixes broken `assets/` relative links in `architecture.md` |
| `assets/architecture-v2-pipeline.svg` | `docs/assets/architecture-v2-pipeline.svg` | Copied — fixes broken `assets/` relative links in `architecture.md` |
| `assets/screenshot.png` | `docs/assets/screenshot.png` | Copied — README.md link updated to new path |
| `auditlog.md` | New | This file |

### `.claude/architecture/` — files deleted

| File | Reason |
|---|---|
| `ArchitectureV2.md` | Duplicate — `architecture.md` already contains full v2 content |
| `DevelopmentV2.md` | Duplicate — `development.md` already contains full v2 content |

---

### `docs/` folder — deleted entirely

All content had been migrated to `.claude/architecture/` in previous sessions. Files removed:

| File | Status before deletion |
|---|---|
| `docs/Architecture.md` | v1 stub — one-liner redirect to V2, no unique content |
| `docs/Development.md` | v1 stub — one-liner redirect to V2, no unique content |
| `docs/ArchitectureV2.md` | Migrated to `.claude/architecture/architecture.md` |
| `docs/DevelopmentV2.md` | Migrated to `.claude/architecture/development.md` |
| `docs/handover.md` | Already existed in `.claude/architecture/handover.md` |
| `docs/change_history.md` | Already existed in `.claude/architecture/change_history.md` |
| `docs/project_files.md` | Already existed in `.claude/architecture/project_files.md` |
| `docs/todo.md` | Already existed in `.claude/architecture/todo.md` |
| `docs/url.md` | Already existed in `.claude/architecture/url.md` |
| `docs/assets/architecture-v2-pipeline.svg` | Migrated to `.claude/architecture/assets/` |
| `docs/assets/main-window-layout.svg` | Migrated to `.claude/architecture/assets/` |
| `docs/assets/screenshot.png` | Migrated to `.claude/architecture/assets/` |

---

### `README.md` — links updated

| Location | Old path | New path |
|---|---|---|
| Line 7 (screenshot) | `docs/assets/screenshot.png` | `.claude/architecture/assets/screenshot.png` |
| Roadmap link | `docs/DevelopmentV2.md` | `.claude/architecture/development.md` |
| Architecture link | `docs/ArchitectureV2.md` | `.claude/architecture/architecture.md` |
| Documentation table | 4 rows pointing to `docs/` | 2 rows pointing to `.claude/architecture/` (v1 stub rows removed) |

---

### `.gitignore` — Claude Code entries added

Added under new `# Claude Code` section:

- `.claude/settings.local.json` — personal settings overrides must not be committed
- `CLAUDE.local.md` — personal project notes must not be committed

---

### `.claude/settings.json` — created

New project-level settings file. Permission allowlists covering routine dev commands so Claude does not prompt for approval on every invocation:

**Allowed:**
- `pytest *`, `python -m pytest *` — test runner
- `ruff check *`, `ruff format *` — linting
- `black *` — formatting
- `pip-audit *` — dependency vulnerability scan
- `git status`, `git diff *`, `git log *`, `git show *` — read-only git
- `git add *`, `git commit *`, `git branch *` — staging and committing
- `python -m skill_scan *` — run the app
- `powershell *run.ps1*` — launch script

**Denied:**
- `Read(.env)`, `Read(.env.*)` — secrets files
- `Read(./secrets/**)` — secrets directory
- `git push *`, `git reset *`, `git clean *` — destructive / external git actions (always require explicit approval)

---

## Canonical docs location

All architecture, roadmap, and session documentation now lives in `.claude/architecture/`. The `docs/` folder has been removed. README.md links updated accordingly.
