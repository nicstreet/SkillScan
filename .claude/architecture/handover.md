# SkillScan — Session Handover

> Generated: 2026-06-19
> Last commit: `4b17dba` (chore: add requirements-dev.txt for dev tooling)
> Branch: `chore/project-move-and-claude-config`
> Working tree: **dirty** — see "Uncommitted changes" below before starting new work

---

## Project

**SkillScan** — PyQt6 Windows desktop app for scanning, auditing, and governing AI skill files (SKILL.md), MCP manifests, and A2A agent cards. Wraps the Cisco AI Skill Scanner / MCP Scanner CLIs with a full windowed UI.

**Run:**
```powershell
cd C:\Users\stree\.claude\projects\skillscan
.\run.ps1
```

**Canonical roadmap:** [`development.md`](development.md)
**Architecture reference:** [`architecture.md`](architecture.md)
**Quick-reference Known Fixes:** [`todo.md`](todo.md)

---

## Uncommitted changes on this branch

`git status --short` shows 66 changed paths, not yet staged/committed:

- **`skills/` → `evals/` restructure** — the old hand-built "Skills Library" (`pyqt6-ui-designer/`, `color-palette-builder/`, `cisco-ai-defense-integrator/`, `environment-setup/`, `mcp-evals/`) is deleted from the working tree; `evals/skills/`, `evals/mcp/`, `evals/a2a/` (eval fixtures for `core/test_skills.py`) are new/untracked in its place
- `src/skill_scan/ui/views/skill_creator_view.py` deleted — renamed to `skill_manager_view.py` (Skill Studio)
- `requirements.txt` — 3 lines added
- This session's `.claude/architecture/` doc updates (`architecture.md`, `development.md`, `project_files.md`, `todo.md`, this file, `change_history.md`, `auditlog.md`)
- `src/`, `evals/` show as untracked (`??`)
- `ui-color-map.md` (root) deleted — stale colour-token doc from the pre-frameless-rewrite UI (old title bar, 56px icon nav rail), superseded by `_palette.py`'s current `SYS_*` tokens; was never referenced by any code

None of this has been committed — flag to the user before assuming a clean baseline.

---

## What was completed across recent sessions

### LLM provider architecture refactor

Per-provider credential storage (Anthropic / OpenAI / Ollama / OpenAI-local) + independent per-feature active-provider selection, so Skill Studio and the scanner subprocess can each point at a different provider simultaneously (e.g. Ollama for Skill Studio, Anthropic for scans). `core/config.py` `get_llm_creds(cfg, feature)` / `_creds_for()` / `_migrate_llm()` (upgrades legacy flat `llm_*` keys in place). Full detail in [architecture.md](architecture.md) → "LLM Provider Architecture".

### Local LLM support (Ollama / OpenAI-compatible local servers)

Options → LLM gained OLLAMA and OPENAI (LOCAL) provider cards (base URL + model, no key required). Hit and fixed a LiteLLM `AuthenticationError` — LiteLLM routes local providers through its OpenAI client layer, which requires a non-empty `api_key` even though the local server ignores it. Fixed in `core/llm.py` and both env-builders in `core/scanner.py` by passing a dummy `"local"` key when none is set.

### AI Module Map dashboard widget

New `AiModuleMapWidget` (`ui/views/dashboard/_widgets.py`) — one row per AI-touching module, showing active provider/model and a status dot (Active / No key / Disabled) for both the `inapp` and `scanner` features independently.

### AI Security Evaluation for LLM-skipped scans

`ScanProgressDialog` shows an "AI Security Evaluation" button when `ScanResult.llm_skipped` is true (detects `LLM_ANALYSIS_FAILED` in findings); runs an ad-hoc `LLMJob` security review and renders `<SEVERITY>/<FINDINGS>/<SUMMARY>` into the result view.

### Smaller fixes this session

- Removed the duplicate "N Skills" count label from the taskbar (folders view toolbar already owns this count — `tile_counts_changed` was redundantly wired to both)
- Skill Studio (`skill_manager_view.py`) — Name, Description, Compatibility, Allowed Tools, and Additional Metadata fields now use `_FIELD_STYLE` with `SYS_BG_SECONDARY` background (was `SYS_BG_PRIMARY`), giving them a recessed look against the metadata card
- Options window redesign (2026-06-19): `options_window.py` lost its 38px titlebar and drag handling entirely (no dragging, just a floating close button). `options_view.py`'s manual Save button is gone — `_wire_autosave()` connects every control's discrete commit signal to `_save()` (connected only after the initial `_populate()` pass, so opening the window writes nothing). `OptionsWindow.closeEvent` calls the new public `OptionsView.save_now()` as a safety net for an in-progress edit that hasn't committed yet (e.g. a text field still focused when the window closes). The old `standalone` constructor flag is gone — there's no longer any behavioural difference between the embedded nav-page instance and the floating window instance. Nav sidebar gained a live search-filter box and a Font-Awesome icon per page (`_NavRow`, `_NAV_PAGES`), each icon chosen to match that page's content (robot for LLM, shield for Analyzers, plug for MCP, etc.)

---

## Current application state

Phases 1–5 (builder UI) complete and working — see [development.md](development.md) for the phase-by-phase breakdown:

- **Phase 1** — Frameless main window, nav rail, `QStackedWidget` view routing (12 views), tray satellite
- **Phase 2** — SQLite DB (`%APPDATA%\SkillScan\skillscan.db`), skill discovery worker, SHA-256 trust invalidation
- **Phase 3** — Folders view: tile grid, compact/large modes, FILTER/SORT/SIZE toolbar, scan queue
- **Phase 4** — Skill Detail view: Report/History/Raw Output/Compliance tabs, trust workflow
- **Phase 5** — Skill Studio (renamed from "Skill Creator"): builder UI, Script Lint, Optimize Description, AI Review, Scan Now, Build Package, Save to Source — all confirmed working
- **Dashboard** — 14-widget card grid, drag-and-drop reorder, edit mode, 60s auto-refresh

`ui/about_dialog.py`, `ui/settings_dialog.py`, `ui/results_window.py` — confirmed dead/orphaned (superseded by `views/*_view.py` equivalents; tray menu no longer referenced them) and deleted 2026-06-18.

---

## Outstanding known fixes

None currently open — every item in [todo.md](todo.md) → "Known Fixes (do first)" is checked off as of 2026-06-18 (most recent: Skill Detail title-bar band removal).

---

## Next phase candidates

Based on [development.md](development.md) and [todo.md](todo.md):

1. **Own-skill audit** (Phase 5 sub-area) — batch-scan `~/.claude/skills/` against `spec_compliance.py`; not started
2. **System Setup** — new "Setup" nav item; env analysis + scoring; user has ChatGPT/Gemini/Copilot platform outputs ready to feed in when this starts *(memory reminder)*
3. **AI Prompt Builder / Amalgamator / Skill Competence Builder** — nav stubs exist (`prompt_builder_view.py`, `amalgamator_view.py`, `skill_competence_view.py`); none built out yet
4. **Actions** — Permanent Delete, Quarantine, Options quarantine path
5. **Governance** — research-first; NIST AI RMF, NCSC, EU AI Act, ISO 42001
6. Decide whether to delete the three orphaned legacy UI files noted above

---

## Key file locations

| What | Where |
|---|---|
| Main window | `src/skill_scan/ui/main_window.py` |
| Folders view | `src/skill_scan/ui/views/folders_view.py` |
| Skill Studio | `src/skill_scan/ui/views/skill_manager_view.py` |
| Skill detail | `src/skill_scan/ui/views/skill_detail_view.py` |
| Dashboard | `src/skill_scan/ui/views/dashboard_view.py`, `dashboard/_widgets.py`, `dashboard/_base.py` |
| LLM config | `src/skill_scan/core/config.py` (`get_llm_creds`), `src/skill_scan/core/llm.py` (`LLMJob`) |
| Scanner | `src/skill_scan/core/scanner.py` |
| DB models | `src/skill_scan/core/db.py` |
| Colour palette | `src/skill_scan/ui/_palette.py` |
| Roadmap | `.claude/architecture/development.md` |
| Architecture | `.claude/architecture/architecture.md` |
| Config (runtime) | `%APPDATA%\SkillScan\config.json` |
| Database (runtime) | `%APPDATA%\SkillScan\skillscan.db` |
| Activity log (runtime) | `%APPDATA%\SkillScan\activity.log` |

---

## PyQt6 / design gotchas established recently

- **Local LLM providers need a non-empty dummy `api_key`** — LiteLLM's OpenAI client layer raises `AuthenticationError` on Ollama/local calls if `api_key` is empty, even though the server ignores it. Pass `api_key or "local"`.
- **Separate "persist state" from "close the window"** — a settings view used both standalone (its own window) and embedded (a page in another window) should never decide for itself whether to close anything; `self.window()` resolves to whatever ancestor happens to be a top-level window, which is the *wrong* one in the embedded case. Make persistence (`_save()`) idempotent and side-effect-free, expose a public alias (`save_now()`), and let the host window's own `closeEvent` decide when to call it. Superseded the earlier `OptionsView(standalone=...)` flag approach entirely.
- **Wire autosave signals only after the initial populate pass** — connecting `toggled`/`currentIndexChanged`/`editingFinished` to a save handler *before* programmatically setting initial widget values (`setChecked`, `setCurrentIndex`, etc. all fire their change signals regardless of whether the change was user- or code-initiated) causes a save on every value the populate step sets. Build the UI, populate it, *then* wire autosave.
- **QSS `border-radius` does not clip a `QAbstractScrollArea` viewport** — `QTableWidget`/`QListWidget`/`QTextBrowser`/`QPlainTextEdit` all render their viewport as a plain rectangle regardless of the widget's own border-radius, so corners look square whenever the background contrasts with whatever sits behind it. Fixed widget-by-widget with `_widgets.round_corners(widget, radius)` — a resize-tracked `QRegion` mask, not a stylesheet fix.
- **`QWidget.grab()` does not apply `setMask()`.** Debugging a masked frameless window by screenshotting it with `.grab()` shows the *unmasked* render — square corners and all — which looks like the mask isn't working even when it is. To see what the real on-screen (compositor-applied) result will look like, manually composite it: `p = QPainter(target); p.setClipRegion(widget.mask()); p.drawPixmap(0, 0, widget.grab()); p.end()`. Trusted the wrong screenshot once during this debugging session before catching it.
- **A widget's own rounded pill/card can still get sliced by an ancestor's `round_corners()` mask** if it doesn't sit far enough from the masked ancestor's edge — clearance needs to exceed (ancestor's corner radius − this widget's own inset), not just be "a few pixels." Don't assume a small fixed margin is automatically safe; check it against the actual outer radius.
- **Frameless top-level widgets get a default OS drop shadow on Windows** unless `Qt.WindowType.NoDropShadowWindowHint` is in the window flags — easy to mistake for a `QGraphicsDropShadowEffect` left in the code when there isn't one. `round_corners()`'s mask should also be applied to the actual top-level widget, not a child panel that merely happens to fill it — masking a child only changes how *it* paints, not the native window region Windows uses for the shadow/click area.
- **`setMask()`/`QRegion` cannot antialias, ever — no amount of polygon sampling fixes that.** It's a hard binary per-pixel region (Win32 `SetWindowRgn` underneath), fundamentally different from `_Surface`'s `QPainterPath` + `Antialiasing` fill, which blends sub-pixel. A masked outer window edge will *always* look rougher than a child widget's own painted curve, no matter how smooth the mask's polygon is. The fix isn't a better mask — it's not needing one: if every layer (panel + content) paints its own correctly-nested, antialiased rounded shape with adequate clearance, nothing square-edged ever reaches the outer boundary, and the window doesn't need `setMask()` at all (`_MainPanel`/`MainWindow` works this way already; `help_window.py` was changed to match after `OptionsWindow`'s masked edge looked visibly rougher than the unmasked main window). Reach for `round_corners()` only when something *unavoidably* square (no rounding of its own) needs clipping — not as a default applied to every frameless window.
- **Hidden widget with stretch** still consumes space. Separate the `addStretch(1)` from `addWidget(section)` — the widget gets no stretch.
- **`reorder_by()` instead of hide/show** — calling `show()` on a widget that still has no parent causes a top-level OS window flash. Reorder `_items` in-place, call `invalidate()`.
- **`update()` after stylesheet change** — `setStyleSheet()` does not force a repaint; call `update()` on the widget for immediate colour change.
- **`raw_json` must be `json.dumps(parsed)`** — scanner stdout contains LiteLLM noise before the JSON; always store the already-parsed dict.
