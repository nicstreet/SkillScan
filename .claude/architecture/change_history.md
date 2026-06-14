# SkillScan — Change History

---

## Session: 2026-06-13

Commits: `daff03b` (Phases 2–4 + all tile/toolbar work), `0794a43` (screenshot + README)

### Bug fixes

| Fix | File | Detail |
|---|---|---|
| Tile whitespace (large empty gap) | `skill_tile.py` | `_findings_section` was added with `stretch=1`; hidden widget still allocated layout space. Moved `addStretch(1)` before section; section added with no stretch. |
| Sort ghost artifacts | `_flow_layout.py`, `folders_view.py` | Previous tile's background colour persisted in vacated positions after sort. Fixed: `_tile_container.update()` after `updateGeometry()` forces container repaint. |
| Toolbar button color ghost | `folders_view.py` | SIZE button previous-active colour persisted. Fixed: call `btn.update()` after `btn.setStyleSheet()` in `_update_size_styles()`. |
| Python window flash on sort | `_flow_layout.py` | Calling `tile.show()` before widget had a parent caused it to briefly appear as a top-level OS window. Replaced hide/show approach with `reorder_by()` in-place list shuffle. |
| Persistence: findings lost on restart | `folders_view.py` | `raw_json` was stored as `result.stdout` which contained LiteLLM noise lines before JSON; `json.loads()` on reload always failed silently. Fixed: store `json.dumps(parsed)`. |
| Persistence: analyzers always empty | `folders_view.py` | `analyzers_used` hardcoded to `"[]"`. Fixed: `json.dumps(parsed.get("analyzers_used", []))`. |
| Badge vertical spacing uneven | `skill_tile.py` | Gap between UNSAFE and CRITICAL was smaller than SKILL to UNSAFE. Both left/right columns now use `QVBoxLayout(spacing=8)`. |

### New features

| Feature | File(s) | Detail |
|---|---|---|
| Tile height reduction (60%) | `skill_tile.py` | `TILE_H = 192` (was 320) |
| Compact medium tile mode | `skill_tile.py` | `set_compact(bool)`, `_compact` flag, `_nb` property returns 25%-smaller badge CSS; `_refresh_labels()` centralises all badge stylesheet application |
| Findings severity count row | `skill_tile.py` | Replaced 4-column findings layout with `CRITICAL(x) - HIGH(x) - MEDIUM(x) - LOW(x)` inline RichText row; wrappable; hidden when no findings |
| SORT toolbar control | `folders_view.py` | `QComboBox` with Name / Severity / Results options; inserted between FILTER and SIZE with separators; `_sorted_infos()` + `_reorder_tiles()` implementation |
| FILTER → QComboBox | `folders_view.py` | Replaced button group with `QComboBox`; proper-case labels (All / Skill / MCP / A2A) |
| SIZE → icon buttons | `folders_view.py` | Removed "Small" option; text buttons replaced with Segoe Fluent Icons `QPushButton` 30×30; Medium (GridViewSmall), Large (GridView) |
| SIZE label restored | `folders_view.py` | "SIZE" label added to left of icon buttons |
| FlowLayout `reorder_by()` | `_flow_layout.py` | New method; rearranges `_items` in-place by widget order; calls `invalidate()`; avoids any show/hide |
| README screenshot | `README.md`, `docs/assets/screenshot.png` | Screenshot embedded after first paragraph; image committed to repo |

---

## Earlier sessions (pre-2026-06-13)

### Phase 4 — Skill Detail View

- `skill_detail_view.py` — full implementation: spec compliance tab, scan report (HTML), Raw Output tab, scan history table, history sparkline, trust workflow (Sign/Revoke), `QFileSystemWatcher` auto-revoke on file change

### Phase 3 — Folders View + Skill Tile Grid (initial build)

- `folders_view.py` — folder list pane, tile grid, scan queue, discovery worker wiring, spec-type filter buttons, status bar `tile_counts_changed` signal
- `skill_tile.py` — initial tile widget: severity border, type badge, RESULTS/ANALYZERS/UNSAFE/SEVERITY badges, hover overlay, context menu
- `_flow_layout.py` — `FlowLayout` + `FlowContainer`; width-fill column layout; `QRect.right()` off-by-one fix

### Phase 2 — SQLite + Discovery

- `core/db.py` — SQLAlchemy models: Folder, Skill, ScanResult, BomSnapshot; session context manager; `init_db()`
- `core/skill_discovery.py` — `DiscoveryWorker(QThread)`; SHA-256 trust invalidation
- `core/router.py` — `detect_type()` for SKILL.md / MCP / A2A

### Phase 1 — Main Window Shell

- `ui/main_window.py` — frameless window, custom title bar, drag, drop shadow
- `ui/nav_rail.py` — nav items, active state, separator before Options/About
- Views migrated from v1 dialogs: `testing_view.py`, `options_view.py`, `about_view.py`
- Tray demoted to satellite

### v1.0.0 (original tray app)

All v1 code retained unchanged: `core/config.py`, `core/scanner.py`, `core/clipboard_watcher.py`, `core/watcher.py`, `core/result_store.py`, `core/test_skills.py`, `ui/_palette.py`, `ui/_widgets.py`, `ui/scan_progress.py`, `ui/result_formatter.py`, `ui/toggle_row.py`, `ui/tray.py`, `windows/taskbar_dock.py`, `windows/context_menu.py`
