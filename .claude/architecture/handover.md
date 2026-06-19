# SkillScan — Session Handover

> Generated: 2026-06-19
> Last commit: `4c6b314` ("feat: Phase 5 Skill Studio, dashboard, options redesign, and supporting infra")
> Branch: `chore/project-move-and-claude-config`
> Working tree: **dirty, and not entirely from this session — read "Concurrent work detected" below before doing anything else**

---

## ⚠️ Concurrent work detected — read this first

While this handover was being written, three new files appeared in the working tree that nobody in this session created: `src/skill_scan/core/skill_audit.py`, `src/skill_scan/ui/views/skill_audit_view.py`, `src/skill_scan/ui/_compliance_render.py` — plus modifications to `core/config.py` and a 111-line deletion from `ui/views/skill_detail_view.py`. This is clearly someone actively building the **Own-Skill Audit** feature (`skill_audit.py`'s docstring: "batch spec-compliance scoring for skills already on disk... targets Claude Code's own skill folders") — likely the user working directly in another terminal/session, possibly with another Claude Code instance, *simultaneously* with this session.

**Do not assume the working tree matches what this document describes for `core/config.py` or `ui/views/skill_detail_view.py`.** Re-check `git status` and `git diff` before touching either file. The new files are real, substantive, in-progress feature work — not noise — but this session has no knowledge of their actual implementation state (complete? tested? compiling?). Investigate before continuing or before assuming Own-Skill Audit is "not started" (todo.md still says that; it's now stale on this specific point).

---

## Project Summary

**SkillScan** — a PyQt6 Windows desktop app for scanning, auditing, and governing AI skill files (`SKILL.md`), MCP manifests, and A2A agent cards. Wraps the Cisco AI Skill Scanner / MCP Scanner CLIs with a full windowed UI (not just a tray utility). Phases 1–5 (frameless main window, DB/discovery, Folders tile grid, Skill Detail, Skill Studio builder, 14-widget Dashboard) are complete and were squashed into one commit this session.

## Architecture Summary

PyQt6 frameless-window app, MVC-separated (`core/` models, `ui/views/` views, signal/slot controllers). SQLite via SQLAlchemy (`core/db.py`: `Folder`/`Skill`/`ScanResult`/`BomSnapshot`). Multi-provider LLM abstraction (Anthropic/OpenAI/Ollama/OpenAI-local) selected independently per feature (`core/config.py` `get_llm_creds()`). Two external CLI scanners wrapped as subprocesses. Full detail: [architecture.md](architecture.md). Stack-agnostic product/behavior spec (new this session): [specification.md](specification.md).

---

## What Was Done This Session

This was a long session covering two distinct halves: documentation cleanup/skill-authoring, then an extended UI debugging arc on the Options window.

**Documentation & skills:**
- Reviewed the whole roadmap and updated `architecture.md`/`development.md`/`todo.md`/`project_files.md`/`change_history.md` comprehensively
- Wrote 7 Claude Code skills at `~/.claude/skills/`: `pyqt6-frameless-window`, `pyqt6-icons-buttons-text`, `pyqt6-scrollbars`, `pyqt6-menus`, `pyqt6-help-window`, `pyqt6-naming-conventions`, `pyqt6-options-pane` — distilled from the patterns established building this app's UI
- Diagnosed and deleted `ui-color-map.md` (root) — stale, zero code references, described the pre-frameless-rewrite UI
- Diagnosed and rewrote `README.md` — described the entire v2 app as "Coming in v1.1" future work and referenced a `## Skills Library` section pointing at a `skills/` directory that no longer exists (replaced by `evals/`)
- Wrote `specification.md` — a stack-agnostic product/technical spec, after asking the user 3 scoping questions (full technical depth, explicitly stack-agnostic despite "exactly what we built," saved alongside the codebase-specific docs rather than replacing them)
- Started, then explicitly paused, a notification-suppression feature — `core/config.py` gained `suppress_scan_windows`/`suppress_error_notifications`/`suppress_additional_notifications` keys, but a `tray.py` edit was rejected by the user mid-implementation; **do not resume without it being re-raised**

**Options window — rounding, then an extended seam investigation:**
- Applied the `pyqt6-frameless-window` skill's core principle to `OptionsWindow`: removed its `round_corners()` mask entirely. `OptionsView` no longer paints one flat square background — it now tiles itself with two `_Surface` children (`nav` rounded outer-left, `content_col` rounded outer-right), mirroring `help_window.py`'s proven column split
- User then reported a 1px seam (two lines meeting at 90° near the bottom-right corner) on the General page, present only on a real screen — `grab()`-based testing never reproduced it
- First hypothesis (redundant same-colour QSS layers stacked at the same boundary) was a real, worthwhile cleanup but **wasn't the actual cause** — the seam persisted after fixing it
- Built `test_window.py` (temporary, burger menu → "Test Window") and bisected the seam one structural layer at a time, importing the *real* functions from `options_view.py` rather than reimplementing them. All four layers — bare skeleton, container structure, real scroll/viewport machinery, real card content — came back clean on a real screen, ruling out every structural explanation
- **Actual root cause**, found via a cheaper parallel test the user suggested: resizing the window by a few percent made the seam vanish. It was a fixed-size sub-pixel/DPI-rounding coincidence specific to 820×640 — nothing structural was ever wrong
- Settled on 850×650 after the user chose to round a confirmed-clean 853×653 down, then re-confirmed *that exact value* clean on a real screen before keeping it
- Corrected the `pyqt6-frameless-window` skill's mistakes-table entry — check for this size coincidence (cheap: nudge `resize()`) before bisecting structure (expensive)
- Follow-up cosmetic request: halved the border stroke (`_BORDER_WIDTH` 1.5→0.75, now named/derived constants) and grew the window to 870×670 to compensate; quantified both with real pixel scans (geometry and border footprint both verified correct on the live class) rather than eyeballing
- Tightened the panel margin from 2px to 1px (verified safe against the concentric-radius ceiling)

---

## Current State

**Working and confirmed:**
- Phases 1–5 (main window, DB/discovery, Folders, Skill Detail, Skill Studio, Dashboard) — all squashed into commit `4c6b314`, confirmed working in earlier sessions
- `OptionsWindow`'s corner rounding (mask-free) and the seam fix at 850×650 — both confirmed on a real screen
- The 7 new `pyqt6-*` Claude Code skills, `specification.md`, README.md rewrite, `ui-color-map.md` deletion

**Not yet confirmed:**
- `OptionsWindow` is currently sized **870×670** with a halved border — this is a *different, untested* value than the 850×650 that was actually verified. The seam is proven size-sensitive; this needs its own real-screen check before being trusted.

**Known incomplete / paused (not broken, just not finished):**
- Notification suppression — config keys exist, no UI toggle, no `tray.py` wiring. Paused by explicit user action, not abandoned.
- `test_window.py` and its burger-menu entry are temporary diagnostic scaffolding, left in place at the user's preference. Safe to remove whenever, but ask first.
- **Own-Skill Audit** — see the concurrent-work warning above. Someone else appears to be actively building this right now; status unknown to this session.

---

## Next Actions (in priority order)

1. **Re-check `git status`/`git diff` for the Own-Skill Audit files** before doing anything else this repo touches `core/config.py` or `ui/views/skill_detail_view.py` for — see the warning at the top of this document.
2. **Confirm 870×670 is seam-free on a real screen.** If it isn't, the fix is the same as before: nudge the size and re-check, not a structural change.
3. Decide whether to remove `test_window.py` and its burger-menu entry, or keep it for further experiments.
4. If/when notification suppression is re-raised: add the missing Options UI toggle and wire `tray.py`'s `_notify_delayed()` (or equivalent) to check `suppress_error_notifications`/`suppress_additional_notifications`.
5. Commit the current uncommitted doc changes (`development.md`, `todo.md` from this handover pass) once the Own-Skill Audit situation above is sorted out — don't commit `config.py`/`skill_detail_view.py` changes without understanding what put them there first.

---

## Open Questions

- Who/what is building Own-Skill Audit concurrently, and is it safe to assume it'll be committed separately, or could it conflict with anything in this session's changes? (No file overlap currently exists, but worth confirming explicitly with the user.)
- Is 870×670 actually wanted, or should the window revert to the confirmed-clean 850×650 and the border/margin tweaks be reconsidered separately?
- `todo.md` D2 ("Window, Menu & Toolbar Specification" — icon inventory, palette tokens) is still open. Is the `ui-detailed-design` Claude skill (already available, not yet used on this project) the right tool for that, or does it warrant a dedicated doc?

---

## Important Context

- **Round by painting, not masking.** The single biggest UI lesson from this session: `setMask()`/`QRegion` cannot antialias, full stop — no amount of polygon refinement closes the gap with a `QPainterPath` + `Antialiasing` fill. Every window in this app should default to "every layer paints its own correctly-nested rounded shape," reaching for a mask only when something unavoidably square needs clipping.
- **A window's exact pixel size can itself cause a visible seam**, independent of anything structural — this cost most of this session's debugging time before the actual (cheap) test was tried. Next time a "weird artifact, can't find the cause in the code" bug shows up on a frameless window, try nudging the window's size *before* bisecting layout structure.
- **The user rejected a tool-use edit once this session** (the `tray.py` notification-suppression wiring) and explicitly said to stop and wait — that feature is paused, not a green light to keep iterating on it.
- **`grab()`-based screenshot testing has now failed to reproduce two different classes of real-screen-only bugs this session** (an unmasked-vs-masked render difference previously, and this session's DPI-rounding seam). Treat a clean offscreen render as inconclusive, not as proof, for anything involving window masking or exact pixel-size effects.
- **The user's CLAUDE.md and global rules (logging/security/python-style) apply throughout** — no hardcoded credentials, no logging secret values, no telemetry, local-only cache, never use `eval`/`exec`/`shell=True`/`pickle` on untrusted input. No violations introduced this session.

---

## Files Changed This Session

**Created:**
- `src/skill_scan/ui/help_window.py` — minimal frameless reference window (column split, no content)
- `src/skill_scan/ui/test_window.py` — ⚠️ temporary diagnostic, left in place per user preference
- `.claude/architecture/specification.md` — stack-agnostic product/technical spec
- 7 files under `~/.claude/skills/pyqt6-*/SKILL.md`

**Modified:**
- `src/skill_scan/ui/options_window.py` — de-masked, border halved, margin 2px→1px, resized 820×640 → 850×650 (confirmed) → 870×670 (unconfirmed)
- `src/skill_scan/ui/views/options_view.py` — `content_col` converted to a rounded `_Surface`, redundant QSS backgrounds removed from itself and `_section_scroll()`, `_CONTENT_RADIUS` constant added
- `src/skill_scan/ui/main_window.py` — wired `test_window_requested` signal, burger-menu "Test Window" entry, `_show_test_window()`/`_on_test_window_closed()`
- `src/skill_scan/core/config.py` — added (then paused) notification-suppression keys; also see the concurrent-work warning above for a *separate*, more recent modification to this same file
- `README.md` (project root) — full rewrite
- `.claude/architecture/architecture.md` — added the round-by-painting/DPI-seam patterns, 3 new Key Design Decisions rows, a new "Open Design Questions" section, `test_window.py` project-structure entry
- `.claude/architecture/development.md` — fixed the stale "Skills Library" section (described a deleted `skills/` concept; corrected to point at the real `pyqt6-*` Claude skills), updated sync date
- `.claude/architecture/todo.md` — same Skills Library fix, added Known Fixes rows 12/13, pending-verification/paused/temporary callouts, D3 documentation entry
- `.claude/architecture/project_files.md` — added `test_window.py` and `specification.md` rows
- `.claude/architecture/change_history.md` — extensive entries throughout, appended under "## Session: 2026-06-19"

**Deleted:**
- `ui-color-map.md` (project root) — stale, unreferenced

---

## References

- [architecture.md](architecture.md) — full system architecture
- [specification.md](specification.md) — stack-agnostic product/technical spec (new this session)
- [change_history.md](change_history.md) — session-by-session log, far more detail than this file's summary
- [development.md](development.md) — project plan and phase status
- [todo.md](todo.md) — quick-reference known fixes + outstanding work
- [url.md](url.md) — useful links and references (unchanged this session — nothing new to add)
