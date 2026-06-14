# SkillScan

PyQt6 Windows desktop app — scan, audit, and govern AI skill files (SKILL.md), MCP manifests, and A2A agent cards. Wraps the Cisco AI Skill Scanner CLI with a full windowed UI.

## Run

```powershell
cd C:\Users\stree\.claude\projects\skillscan
.\run.ps1
```

## Stack

- Python 3.13, PyQt6 6.6+, SQLAlchemy 2.0, watchdog, litellm, pywin32
- `cisco-ai-skill-scanner[all]` — core scanner CLI
- DB: `%APPDATA%\SkillScan\skillscan.db`
- Config: `%APPDATA%\SkillScan\config.json`
- Activity log: `%APPDATA%\SkillScan\activity.log`

## Project structure

```
src/skill_scan/
├── __main__.py
├── core/
│   ├── config.py            # load() / save() — JSON config
│   ├── db.py                # SQLAlchemy models: Folder, Skill, ScanResult, BomSnapshot
│   ├── scanner.py           # ScanJob — QProcess wrapper
│   ├── skill_discovery.py   # folder walk, SHA-256 hash, trust invalidation
│   ├── router.py            # detect_type() → SpecType enum
│   ├── watcher.py           # FolderWatcher
│   └── clipboard_watcher.py
├── ui/
│   ├── _palette.py          # colour tokens — always use these, never hardcode hex
│   ├── _widgets.py          # RoundedCard, TitleBar, SCROLLBAR_STYLE
│   ├── _flow_layout.py      # FlowLayout + reorder_by()
│   ├── main_window.py       # frameless QMainWindow, nav rail, QStackedWidget
│   ├── nav_rail.py          # NavRail, NavItem
│   └── views/
│       ├── folders_view.py       # folder pane + skill tile grid (Phase 3)
│       ├── skill_tile.py         # SkillTile, compact mode, severity badges
│       ├── skill_detail_view.py  # spec compliance, scan report, trust workflow (Phase 4)
│       ├── skill_creator_view.py # stub — Phase 5
│       ├── testing_view.py
│       ├── options_view.py
│       └── about_view.py
└── windows/
    ├── taskbar_dock.py
    └── context_menu.py
```

## Commands

```powershell
pytest tests/ -v                    # run tests
pytest --cov=src --cov-report=html  # with coverage
ruff check src/                     # lint
black src/                          # format
```

## Architecture reference

See `.claude/architecture/architecture.md` — component architecture, DB schema, design language, all PyQt6 patterns.
See `.claude/architecture/development.md` — full v2 roadmap (Phases 1–11), planned feature areas.
See `.claude/architecture/handover.md` — current build state, outstanding known fixes, next phase.
See `.claude/architecture/todo.md` — quick-reference checklist of all outstanding work.

## Current state

Phases 1–4 complete. Three known fixes before Phase 5 (Skill Creator):

1. Watched folders with `watch_enabled=True` don't appear in folder list pane
2. Activity Log nav item — backend writes to `activity.log`, no view yet
3. Options → Watched Folders: AI tooling detection

## PyQt6 gotchas

- **Scrollbar styles don't cascade** — call `.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)` directly; setting on a parent widget is silently ignored
- **Hidden widget + `stretch=1` still consumes space** — add `addStretch(1)` as a separate spacer; never pass `stretch` to the widget's `addWidget()` call
- **`reorder_by()` not hide/show** — `show()` on a widget without a parent causes an OS window flash; use `FlowLayout.reorder_by()` + `invalidate()` for in-place reorder
- **`update()` after `setStyleSheet()`** — stylesheet changes don't auto-repaint; always call `.update()` on the widget
- **Store `json.dumps(parsed)` not `result.stdout`** — scanner stdout has LiteLLM noise before the JSON payload; always store the already-parsed dict

## Colour tokens

Always use named tokens from `ui/_palette.py`. Never hardcode hex in UI files.
Key tokens: `ANCHOR` (window bg), `DEEP_SURFACE` (rail/toolbar), `ACCENT` `#0D9488` (CTA, active nav), `CRITICAL_ACCENT`, `HIGH_ACCENT`, `MEDIUM_ACCENT`, `SAFE_ACCENT`.

## Work-in-progress markers

```python
# TODO: pending work
# FIXME: known bug
# XXX: blocking — do not deploy
# SECURITY: requires security review
# HACK: temporary workaround
```

Resolve all XXX and SECURITY markers before marking any task complete.

## Before committing

1. `pytest tests/ -v` — all pass
2. `ruff check src/` — no errors
3. No XXX or SECURITY markers outstanding
4. Confirm `.gitignore` covers `.env`, `logs/`, `__pycache__/`

## Security

- Credentials via `.env` + `python-dotenv` — never hardcoded, never committed, never logged
- API keys injected via process environment, not CLI arguments
- No `eval()` or `subprocess(shell=True)` on external input
- No `pickle` for untrusted data
