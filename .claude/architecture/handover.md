# SkillScan — Session Handover

> Generated: 2026-06-13  
> Last commit: `0794a43` (docs: add screenshot and update README)  
> Branch: main, up to date with origin

---

## Project

**SkillScan** — PyQt6 Windows desktop app for scanning, auditing, and governing AI skill files (SKILL.md), MCP manifests, and A2A agent cards. Wraps the Cisco AI Skill Scanner CLI with a full windowed UI.

**Run:**
```powershell
cd C:\Users\stree\PythonProjects\SkillScan
.venv\Scripts\python -m skill_scan
```

**Canonical roadmap:** `docs/DevelopmentV2.md`  
**Architecture reference:** `docs/ArchitectureV2.md`

---

## What was completed in this session

### Tile UI overhaul (`skill_scan/ui/views/skill_tile.py`)

- `TILE_H = 192` (reduced from 320px — 60%)
- **Compact mode** — `set_compact(bool)` public method; `_compact` flag; `_nb` property returns 25%-smaller badge CSS when compact; `_refresh_labels()` centralises all badge stylesheet application so compact switching requires no layout rebuild
- **Findings redesign** — replaced 4-column findings layout with a compact severity count row: `CRITICAL(x) - HIGH(x) - MEDIUM(x) - LOW(x)` rendered as inline RichText in `_sev_row_lbl`; hidden when no findings
- **Whitespace fix** — removed `stretch=1` from `_findings_section`; added `addStretch(1)` before the section (no stretch on section itself); name label aligned `AlignTop`
- **Badge vertical spacing** — both columns (left: results/analyzers, right: unsafe/severity) use `QVBoxLayout(spacing=8)` for consistent 8px gap between all badges

### Toolbar redesign (`skill_scan/ui/views/folders_view.py`)

- **FILTER** — replaced button group with `QComboBox` (`_filter_combo`); options: All / Skill / MCP / A2A (proper-case); `currentIndexChanged` wired to `_set_filter()`
- **SORT** — new toolbar section between FILTER and SIZE; `QComboBox` (`_sort_combo`); options: Name / Severity / Results; separator between SORT and SIZE
- **SIZE** — removed "Small" option; text buttons replaced with Segoe Fluent Icons `QPushButton` (30×30); Medium icon ``, Large icon ``; SIZE label restored to left of icons
- **Sort implementation** — `_sorted_infos()` returns infos ordered by key; `_reorder_tiles()` calls `FlowLayout.reorder_by()` for in-place reorder (no hide/show, no parent change)
- **Compact mode wiring** — `_set_tile_size()` sets `compact = key == "medium"` and calls `tile.set_compact(compact)` on all tiles; tile creation passes `compact=self._active_tile_size == "medium"`

### FlowLayout `reorder_by()` (`skill_scan/ui/_flow_layout.py`)

New method on `FlowLayout`:
```python
def reorder_by(self, widgets: list) -> None:
    item_map = {item.widget(): item for item in self._items if item.widget()}
    self._items = [item_map[w] for w in widgets if w in item_map]
    self.invalidate()
```
Rearranges `_items` in-place without hide/show, avoiding OS-level window flashes.

### Persistence fix (`skill_scan/ui/views/folders_view.py` — `_on_scan_finished`)

- `raw_json=json.dumps(parsed)` (was `result.stdout` which contained LiteLLM noise before the JSON)
- `analyzers_used=json.dumps(parsed.get("analyzers_used", []))` (was hardcoded `"[]"`)

### Ghost / artifact fixes

- Sort ghost: `self._tile_container.update()` called after `updateGeometry()` to force repaint of vacated tile positions
- Toolbar button ghost: `btn.update()` called after each `btn.setStyleSheet()` in `_update_size_styles()`

### Documentation

- `docs/assets/screenshot.png` — app screenshot added
- `README.md` — screenshot embedded after first paragraph

---

## Current application state

Phases 1–4 complete and working:
- **Phase 1** — Frameless main window, nav rail, QStackedWidget view routing, tray satellite
- **Phase 2** — SQLite DB (`%APPDATA%\SkillScan\skillscan.db`), skill discovery worker, SHA-256 trust invalidation
- **Phase 3** — Folders view with tile grid: compact/large modes, FILTER/SORT/SIZE toolbar, scan queue
- **Phase 4** — Skill Detail view: spec compliance, scan report, trust workflow, history table

All session tile/toolbar/persistence changes committed and pushed.

---

## Outstanding known fixes

| Fix | File | Notes |
|---|---|---|
| Watched folders not in folder list | `folders_view.py` | Folders with `watch_enabled=True` in DB (added via discovery) don't appear in left pane without manual "Add Folder" |
| Activity Log nav item | `nav_rail.py` + new `activity_log_view.py` | Nav item needed; backend already writes to `%APPDATA%\SkillScan\activity.log` |
| Options → Watched Folders: AI tooling detection | `options_view.py` | Mechanism to declare installed AI tooling (Claude Desktop, Cursor, etc.) and auto-populate watched folders |

---

## Next phase candidates

Based on `docs/DevelopmentV2.md`:

1. **Clear known fixes first** — 3 items above; all are small-to-medium scope
2. **Phase 5 — Skill Creator** — metadata form + SKILL.md editor + AI Review; `skill_creator_view.py` is a stub
3. **System Setup** — new "Setup" nav item; env analysis + scoring; user has ChatGPT/Gemini/Copilot outputs to feed in when this starts *(memory reminder)*
4. **Actions** — Permanent Delete, Quarantine, Options quarantine path
5. **Governance** — research-first; NIST, NCSC, EU AI Act, ISO 42001

---

## Key file locations

| What | Where |
|---|---|
| Main window | `skill_scan/ui/main_window.py` |
| Folders view | `skill_scan/ui/views/folders_view.py` |
| Skill tile | `skill_scan/ui/views/skill_tile.py` |
| Skill detail | `skill_scan/ui/views/skill_detail_view.py` |
| Flow layout | `skill_scan/ui/_flow_layout.py` |
| DB models | `skill_scan/core/db.py` |
| Colour palette | `skill_scan/ui/_palette.py` |
| Roadmap | `docs/DevelopmentV2.md` |
| Architecture | `docs/ArchitectureV2.md` |
| Config (runtime) | `%APPDATA%\SkillScan\config.json` |
| Database (runtime) | `%APPDATA%\SkillScan\skillscan.db` |
| Activity log (runtime) | `%APPDATA%\SkillScan\activity.log` |

---

## PyQt6 gotchas established this session

- **Hidden widget with stretch** still consumes space. Separate the `addStretch(1)` from `addWidget(section)` — the widget gets no stretch.
- **`reorder_by()` instead of hide/show** — calling `show()` on a widget that still has no parent causes a top-level OS window flash. Reorder `_items` in-place, call `invalidate()`.
- **`update()` after stylesheet change** — `setStyleSheet()` does not force a repaint; call `update()` on the widget for immediate colour change.
- **`raw_json` must be `json.dumps(parsed)`** — scanner stdout contains LiteLLM noise before the JSON; always store the already-parsed dict.
