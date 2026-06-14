"""Folders view — left pane folder list + right pane skill tile grid with scan queue."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from collections import Counter

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...core import config as cfg
from ...core.db import (
    Folder,
    Skill,
    ScanResult as DbScanResult,
    get_or_create_folder,
    init_db,
    session,
)
from ...core.scanner import ScanJob
from ...core.skill_discovery import DiscoveryWorker
from .._flow_layout import FlowContainer
from .._palette import (
    ACCENT,
    ANCHOR,
    DEEP_SURFACE,
    DIVIDER,
    HOVER_FOCUS,
    LIGHT_CANVAS,
    MEDIUM_ACCENT,
    MUTED_TEXT,
)
from .._widgets import SCROLLBAR_STYLE
from .skill_tile import SkillInfo, SkillTile

# ── Folder list row ───────────────────────────────────────────────────────────


class _FolderRow(QWidget):
    def __init__(
        self, path: str, skill_count: int, show_tooltip: bool = True, parent=None
    ):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 10, 8)
        layout.setSpacing(8)

        name_lbl = QLabel(Path(path).name or path)
        name_lbl.setStyleSheet(
            f"color:{LIGHT_CANVAS};font-size:12px;background:transparent;"
        )
        name_lbl.setMaximumWidth(160)
        layout.addWidget(name_lbl, 1)

        self._count_lbl = QLabel(str(skill_count))
        self._count_lbl.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:10px;"
            f"background:{ANCHOR};border-radius:8px;padding:1px 7px;min-width:20px;"
        )
        self._count_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self._count_lbl)
        self.setSizeHint = lambda: self.sizeHint()

        if show_tooltip:
            self.setToolTip(path)

    def set_count(self, n: int) -> None:
        self._count_lbl.setText(str(n))


# ── Main view ────────────────────────────────────────────────────────────────

_FILTER_KEYS = ["all", "skill", "mcp", "a2a"]
_FILTER_LABELS = {"all": "All", "skill": "Skill", "mcp": "MCP", "a2a": "A2A"}

_SIZE_KEYS = ["medium", "large"]
_SIZE_LABELS = {"medium": "Medium", "large": "Large"}
_SIZE_COLS = {"medium": 4, "large": 3}
_SIZE_ICONS = {"medium": "", "large": ""}  # GridViewSmall, GridView

_SORT_KEYS = ["name", "severity", "results"]
_SORT_LABELS = {"name": "Name", "severity": "Severity", "results": "Results"}
_SEVERITY_RANK = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "clean": 4,
    "safe": 4,
    "unknown": 5,
    None: 6,
}


class FoldersView(QWidget):
    skill_detail_requested = pyqtSignal(int)  # skill_id — wired up in Phase 4
    tile_counts_changed = pyqtSignal(str)  # formatted count string for status bar

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background:{ANCHOR};")

        self._current_folder_id: int | None = None
        self._active_filter: str = "all"
        self._active_tile_size: str = "large"
        self._active_sort: str = "name"
        self._tiles: dict[int, SkillTile] = {}
        self._tile_infos: list[SkillInfo] = []

        # Keep discovery workers alive until their threads finish
        self._workers: list[DiscoveryWorker] = []

        # Sequential scan queue: list of (skill_id, scan_dir)
        self._scan_queue: list[tuple[int, str]] = []
        self._active_job: ScanJob | None = None
        self._scan_done = 0
        self._scan_total = 0

        self._build_ui()
        QTimer.singleShot(0, self._init_folders)

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        outer.addWidget(self._make_left_pane())

        vdiv = QFrame()
        vdiv.setFrameShape(QFrame.Shape.VLine)
        vdiv.setFixedWidth(1)
        vdiv.setStyleSheet(f"background:{DIVIDER};border:none;")
        outer.addWidget(vdiv)

        outer.addWidget(self._make_right_pane(), 1)

    def _make_left_pane(self) -> QWidget:
        pane = QWidget()
        pane.setFixedWidth(240)
        pane.setStyleSheet(f"background:{DEEP_SURFACE};")
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(47)
        header.setStyleSheet(f"background:{DEEP_SURFACE};")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 8, 0)

        lbl = QLabel("FOLDERS")
        lbl.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:10px;font-weight:700;"
            f"letter-spacing:2px;background:transparent;"
        )
        header_layout.addWidget(lbl)
        header_layout.addStretch()

        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setToolTip("Add folder")
        add_btn.setStyleSheet(
            f"QPushButton{{background:{ACCENT};color:{LIGHT_CANVAS};border:none;"
            f"border-radius:5px;font-size:16px;font-weight:300;padding-bottom:2px;}}"
            f"QPushButton:hover{{background:{HOVER_FOCUS};}}"
        )
        add_btn.clicked.connect(self._add_folder)
        header_layout.addWidget(add_btn)
        layout.addWidget(header)

        hdiv = QFrame()
        hdiv.setFrameShape(QFrame.Shape.HLine)
        hdiv.setFixedHeight(1)
        hdiv.setStyleSheet(f"background:{DIVIDER};border:none;")
        layout.addWidget(hdiv)

        self._folder_list = QListWidget()
        self._folder_list.setStyleSheet(f"""
            QListWidget {{
                background: {DEEP_SURFACE};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                border-bottom: 1px solid {DIVIDER};
                padding: 0px;
            }}
            QListWidget::item:selected {{
                background: {ANCHOR};
            }}
            QListWidget::item:hover:!selected {{
                background: #162033;
            }}
        """)
        self._folder_list.setSelectionMode(
            QAbstractItemView.SelectionMode.SingleSelection
        )
        self._folder_list.currentItemChanged.connect(self._on_folder_changed)
        self._folder_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._folder_list.customContextMenuRequested.connect(self._folder_context_menu)
        layout.addWidget(self._folder_list, 1)
        return pane

    def _make_right_pane(self) -> QWidget:
        pane = QWidget()
        pane.setStyleSheet(f"background:{ANCHOR};")
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Toolbar + crisp 1px divider below it
        layout.addWidget(self._make_toolbar())
        tdiv = QFrame()
        tdiv.setFrameShape(QFrame.Shape.HLine)
        tdiv.setFixedHeight(1)
        tdiv.setStyleSheet(f"background:{DIVIDER};border:none;")
        layout.addWidget(tdiv)

        # Content stack: empty state (0) | tile scroll area (1)
        self._content_stack = QStackedWidget()
        self._content_stack.setStyleSheet(f"background:{ANCHOR};")

        # Page 0 — empty state
        empty = QWidget()
        empty.setStyleSheet(f"background:{ANCHOR};")
        empty_layout = QVBoxLayout(empty)
        empty_layout.addStretch()
        empty_lbl = QLabel("Select a folder to view skills")
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lbl.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:14px;background:transparent;"
        )
        empty_layout.addWidget(empty_lbl)
        empty_layout.addStretch()
        self._content_stack.addWidget(empty)

        # Page 1 — tile scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(f"background:{ANCHOR};border:none;")
        self._scroll.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)

        self._tile_container = FlowContainer(h_spacing=12, v_spacing=12)
        self._tile_container.setStyleSheet(f"background:{ANCHOR};")
        self._tile_container.setContentsMargins(20, 20, 20, 20)
        self._tile_container.set_cols(_SIZE_COLS[self._active_tile_size])
        self._scroll.setWidget(self._tile_container)
        self._content_stack.addWidget(self._scroll)

        layout.addWidget(self._content_stack, 1)
        return pane

    def _make_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(47)
        bar.setStyleSheet(f"background:{DEEP_SURFACE};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 12, 0)
        layout.setSpacing(8)

        _combo_style = (
            f"QComboBox{{background:transparent;color:{MUTED_TEXT};"
            f"border:1px solid #334155;border-radius:4px;"
            f"padding:2px 4px 2px 8px;font-size:10px;font-weight:700;"
            f"letter-spacing:1px;min-width:80px;}}"
            f"QComboBox:hover{{color:{LIGHT_CANVAS};border-color:{ACCENT};}}"
            f"QComboBox::drop-down{{border:none;width:16px;}}"
            f"QComboBox QAbstractItemView{{background:{DEEP_SURFACE};"
            f"color:{LIGHT_CANVAS};selection-background-color:{ACCENT};"
            f"border:1px solid {DIVIDER};font-size:10px;font-weight:700;"
            f"padding:2px;}}"
        )

        # Filter dropdown
        filters_lbl = QLabel("FILTER")
        filters_lbl.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:10px;font-weight:700;"
            f"letter-spacing:2px;background:transparent;"
        )
        layout.addWidget(filters_lbl)
        layout.addSpacing(6)

        self._filter_combo = QComboBox()
        self._filter_combo.setFixedHeight(26)
        self._filter_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._filter_combo.setStyleSheet(_combo_style)
        for key in _FILTER_KEYS:
            self._filter_combo.addItem(_FILTER_LABELS[key], key)
        self._filter_combo.currentIndexChanged.connect(
            lambda i: self._set_filter(self._filter_combo.itemData(i))
        )
        layout.addWidget(self._filter_combo)

        # Separator
        vsep = QFrame()
        vsep.setFrameShape(QFrame.Shape.VLine)
        vsep.setFixedSize(1, 20)
        vsep.setStyleSheet(f"background:{DIVIDER};border:none;")
        layout.addSpacing(4)
        layout.addWidget(vsep)
        layout.addSpacing(4)

        # Sort dropdown
        sort_lbl = QLabel("SORT")
        sort_lbl.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:10px;font-weight:700;"
            f"letter-spacing:2px;background:transparent;"
        )
        layout.addWidget(sort_lbl)
        layout.addSpacing(6)

        self._sort_combo = QComboBox()
        self._sort_combo.setFixedHeight(26)
        self._sort_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self._sort_combo.setStyleSheet(_combo_style)
        for key in _SORT_KEYS:
            self._sort_combo.addItem(_SORT_LABELS[key], key)
        self._sort_combo.currentIndexChanged.connect(
            lambda i: self._set_sort(self._sort_combo.itemData(i))
        )
        layout.addWidget(self._sort_combo)

        # Separator before SIZE
        vsep2 = QFrame()
        vsep2.setFrameShape(QFrame.Shape.VLine)
        vsep2.setFixedSize(1, 20)
        vsep2.setStyleSheet(f"background:{DIVIDER};border:none;")
        layout.addSpacing(4)
        layout.addWidget(vsep2)
        layout.addSpacing(4)

        # Size icon buttons
        size_lbl = QLabel("SIZE")
        size_lbl.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:10px;font-weight:700;"
            f"letter-spacing:2px;background:transparent;"
        )
        layout.addWidget(size_lbl)
        layout.addSpacing(6)

        self._size_btns: dict[str, QPushButton] = {}
        _icon_font = QFont("Segoe Fluent Icons", 16)
        for key in _SIZE_KEYS:
            btn = QPushButton(_SIZE_ICONS[key])
            btn.setFont(_icon_font)
            btn.setFixedSize(30, 30)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(_SIZE_LABELS[key])
            btn.clicked.connect(lambda _=False, k=key: self._set_tile_size(k))
            self._size_btns[key] = btn
            layout.addWidget(btn)
        self._update_size_styles()

        layout.addStretch()

        self._scan_progress_lbl = QLabel("")
        self._scan_progress_lbl.setStyleSheet(
            f"color:{MEDIUM_ACCENT};font-size:11px;background:transparent;"
        )
        layout.addWidget(self._scan_progress_lbl)

        self._skill_count_lbl = QLabel("")
        self._skill_count_lbl.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:11px;background:transparent;"
        )
        layout.addWidget(self._skill_count_lbl)

        self._scan_all_btn = QPushButton("Scan All")
        self._scan_all_btn.setEnabled(False)
        self._scan_all_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._scan_all_btn.setStyleSheet(
            f"QPushButton{{background:{ACCENT};color:{LIGHT_CANVAS};border:none;"
            f"border-radius:6px;padding:5px 14px;font-size:12px;font-weight:600;}}"
            f"QPushButton:hover{{background:{HOVER_FOCUS};}}"
            f"QPushButton:disabled{{background:{DIVIDER};color:{MUTED_TEXT};}}"
        )
        self._scan_all_btn.clicked.connect(self._scan_all)
        layout.addWidget(self._scan_all_btn)
        return bar

    def _set_filter(self, key: str) -> None:
        if self._active_filter == key:
            return
        self._active_filter = key
        self._apply_filter()

    def _apply_filter(self) -> None:
        for skill_id, tile in self._tiles.items():
            if self._active_filter == "all":
                tile.setVisible(True)
            else:
                tile.setVisible(tile._info.spec_type == self._active_filter)
        self._tile_container.updateGeometry()

    def _update_size_styles(self) -> None:
        for key, btn in self._size_btns.items():
            active = key == self._active_tile_size
            btn.setStyleSheet(
                f"QPushButton{{background:{ACCENT if active else 'transparent'};"
                f"color:{LIGHT_CANVAS if active else MUTED_TEXT};"
                f"border:1px solid {ACCENT if active else '#334155'};"
                f"border-radius:4px;padding:0px;}}"
                f"QPushButton:hover{{color:{LIGHT_CANVAS};border-color:{ACCENT};}}"
            )
            btn.update()

    def _set_tile_size(self, key: str) -> None:
        if self._active_tile_size == key:
            return
        self._active_tile_size = key
        self._update_size_styles()
        compact = key == "medium"
        for tile in self._tiles.values():
            tile.set_compact(compact)
        self._tile_container.set_cols(_SIZE_COLS[key])

    def _set_sort(self, key: str) -> None:
        if self._active_sort == key:
            return
        self._active_sort = key
        self._reorder_tiles()
        self._apply_filter()

    def _sorted_infos(self) -> list:
        infos = list(self._tile_infos)
        if self._active_sort == "name":
            infos.sort(key=lambda i: i.name.lower())
        elif self._active_sort == "severity":
            infos.sort(key=lambda i: _SEVERITY_RANK.get(i.severity, 6))
        elif self._active_sort == "results":
            infos.sort(key=lambda i: -i.n_results)
        return infos

    def _reorder_tiles(self) -> None:
        flow = self._tile_container.flow
        sorted_infos = self._sorted_infos()

        # Add tiles not yet in the flow (initial load path)
        in_flow = {
            flow.itemAt(i).widget()
            for i in range(flow.count())
            if flow.itemAt(i) and flow.itemAt(i).widget()
        }
        for info in sorted_infos:
            tile = self._tiles.get(info.skill_id)
            if tile and tile not in in_flow:
                self._tile_container.addWidget(tile)

        # Rearrange in-place — no hide/show, no reparenting
        ordered = [
            self._tiles[i.skill_id] for i in sorted_infos if i.skill_id in self._tiles
        ]
        flow.reorder_by(ordered)
        self._tile_container.updateGeometry()
        self._tile_container.update()

    # ── Data loading ──────────────────────────────────────────────────────────

    def _init_folders(self) -> None:
        try:
            init_db()
            c = cfg.load()
            for path in c.get("watched_folders", []):
                if Path(path).is_dir():
                    get_or_create_folder(path, watch_enabled=True)
        except Exception:
            pass
        self._load_folders()

    def _load_folders(self) -> None:
        current_id = self._current_folder_id
        self._folder_list.blockSignals(True)
        self._folder_list.clear()
        try:
            with session() as s:
                folders = s.query(Folder).order_by(Folder.added_at).all()
                folder_data = [
                    (f.id, f.path, s.query(Skill).filter_by(folder_id=f.id).count())
                    for f in folders
                ]
        except Exception:
            self._folder_list.blockSignals(False)
            return

        show_tt = cfg.load().get("show_folder_tooltip", True)
        restore_idx = -1
        for i, (folder_id, path, count) in enumerate(folder_data):
            row = _FolderRow(path, count, show_tooltip=show_tt)
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, folder_id)
            item.setData(Qt.ItemDataRole.UserRole + 1, path)
            item.setSizeHint(row.sizeHint())
            self._folder_list.addItem(item)
            self._folder_list.setItemWidget(item, row)
            if folder_id == current_id:
                restore_idx = i

        self._folder_list.blockSignals(False)

        if restore_idx >= 0:
            self._folder_list.setCurrentRow(restore_idx)
        elif self._folder_list.count() > 0 and current_id is None:
            pass  # don't auto-select

    def _on_folder_changed(self, current, _prev) -> None:
        if current is None:
            self._current_folder_id = None
            self._scan_all_btn.setEnabled(False)
            self._skill_count_lbl.setText("")
            self.tile_counts_changed.emit("")
            self._clear_tiles()
            self._content_stack.setCurrentIndex(0)
            return

        folder_id = current.data(Qt.ItemDataRole.UserRole)
        self._current_folder_id = folder_id
        self._content_stack.setCurrentIndex(1)
        self._load_tiles(folder_id)

    def _load_tiles(self, folder_id: int) -> None:
        self._clear_tiles()
        try:
            with session() as s:
                skills = (
                    s.query(Skill)
                    .filter_by(folder_id=folder_id)
                    .order_by(Skill.name)
                    .all()
                )
                infos: list[SkillInfo] = []
                for sk in skills:
                    latest = (
                        s.query(DbScanResult)
                        .filter_by(skill_id=sk.id)
                        .order_by(DbScanResult.timestamp.desc())
                        .first()
                    )
                    n_results = n_analyzers = 0
                    llm_skipped = False
                    findings: list = []
                    if latest:
                        try:
                            raw = json.loads(latest.raw_json or "{}")
                            all_finds = raw.get("findings", [])
                            real_finds = [
                                f
                                for f in all_finds
                                if f.get("rule_id") != "LLM_ANALYSIS_FAILED"
                            ]
                            n_results = len(real_finds)
                            n_analyzers = len(raw.get("analyzers_used", []))
                            llm_skipped = bool(
                                raw.get("analyzers_failed")
                                or any(
                                    f.get("rule_id") == "LLM_ANALYSIS_FAILED"
                                    for f in all_finds
                                )
                            )
                            findings = [
                                {
                                    "severity": (
                                        f.get("severity") or "unknown"
                                    ).lower(),
                                    "category": f.get("category")
                                    or f.get("title")
                                    or "—",
                                }
                                for f in real_finds
                            ]
                        except Exception:
                            pass
                    infos.append(
                        SkillInfo(
                            skill_id=sk.id,
                            path=sk.path,
                            name=sk.name,
                            spec_type=sk.spec_type,
                            description=sk.description or "",
                            trusted=sk.trusted,
                            severity=latest.severity if latest else None,
                            is_safe=bool(latest.is_safe) if latest else False,
                            last_scanned=latest.timestamp if latest else None,
                            n_results=n_results,
                            n_analyzers=n_analyzers,
                            llm_skipped=llm_skipped,
                            findings=findings,
                        )
                    )
        except Exception:
            return

        self._tile_infos = infos
        compact = self._active_tile_size == "medium"
        for info in infos:
            tile = SkillTile(info, compact=compact)
            tile.scan_requested.connect(self._enqueue_scan)
            tile.detail_requested.connect(self.skill_detail_requested)
            tile.trust_toggled.connect(self._on_trust_toggled)
            tile.open_folder_requested.connect(self._open_in_explorer)
            self._tiles[info.skill_id] = tile
        self._reorder_tiles()

        self._apply_filter()
        self._update_count_label(infos)
        self._scan_all_btn.setEnabled(len(infos) > 0)
        self._tile_container.updateGeometry()

    def _update_count_label(self, infos: list) -> None:
        counts = Counter((i.spec_type or "unknown").lower() for i in infos)
        parts = []
        if counts.get("skill"):
            n = counts["skill"]
            parts.append(f"{n} SKILL{'S' if n != 1 else ''}")
        if counts.get("mcp"):
            parts.append(f"{counts['mcp']} MCP")
        if counts.get("a2a"):
            parts.append(f"{counts['a2a']} A2A")
        other = sum(v for k, v in counts.items() if k not in ("skill", "mcp", "a2a"))
        if other:
            parts.append(f"{other} OTHER")
        text = "  ·  ".join(parts)
        self._skill_count_lbl.setText(text)
        self.tile_counts_changed.emit(text)

    def _clear_tiles(self) -> None:
        self._tiles.clear()
        flow = self._tile_container.flow
        while flow.count():
            item = flow.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()
        self._tile_container.updateGeometry()

    # ── Folder management ─────────────────────────────────────────────────────

    def _run_discovery(self, folder_id: int, path: str, on_done) -> None:
        """Start a DiscoveryWorker and keep a reference until it finishes."""
        worker = DiscoveryWorker(folder_id, path)
        self._workers.append(worker)

        def _finished(result):
            try:
                self._workers.remove(worker)
            except ValueError:
                pass
            on_done(result)

        worker.finished.connect(_finished)
        worker.start()

    def _add_folder(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select folder to watch")
        if not path:
            return
        try:
            folder_id = get_or_create_folder(path, watch_enabled=True)
        except Exception:
            return
        self._load_folders()
        self._run_discovery(folder_id, path, lambda _r: self._load_folders())

    def _folder_context_menu(self, pos) -> None:
        item = self._folder_list.itemAt(pos)
        if item is None:
            return
        folder_id = item.data(Qt.ItemDataRole.UserRole)
        folder_path = item.data(Qt.ItemDataRole.UserRole + 1)

        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{DEEP_SURFACE};color:{LIGHT_CANVAS};"
            f"border:1px solid {DIVIDER};border-radius:6px;padding:4px;}}"
            f"QMenu::item{{padding:5px 20px;border-radius:4px;}}"
            f"QMenu::item:selected{{background:{ACCENT};}}"
            f"QMenu::separator{{height:1px;background:{DIVIDER};margin:2px 8px;}}"
        )
        menu.addAction("Scan All").triggered.connect(
            lambda: self._scan_folder(folder_id)
        )
        menu.addAction("Refresh").triggered.connect(
            lambda: self._refresh_folder(folder_id, folder_path)
        )
        menu.addSeparator()
        menu.addAction("Open in Explorer").triggered.connect(
            lambda: self._open_in_explorer(folder_path)
        )
        menu.addSeparator()
        menu.addAction("Remove Folder").triggered.connect(
            lambda: self._remove_folder(folder_id)
        )
        menu.exec(self._folder_list.mapToGlobal(pos))

    def _remove_folder(self, folder_id: int) -> None:
        try:
            with session() as s:
                f = s.query(Folder).filter_by(id=folder_id).first()
                if f:
                    s.delete(f)
                    s.commit()
        except Exception:
            return
        if self._current_folder_id == folder_id:
            self._current_folder_id = None
            self._clear_tiles()
            self._content_stack.setCurrentIndex(0)
            self._scan_all_btn.setEnabled(False)
            self._skill_count_lbl.setText("")
        self._load_folders()

    def _refresh_folder(self, folder_id: int, folder_path: str) -> None:
        self._run_discovery(
            folder_id, folder_path, lambda _r: self._load_tiles(folder_id)
        )

    # ── Scan queue ────────────────────────────────────────────────────────────

    def _enqueue_scan(self, skill_id: int, scan_dir: str) -> None:
        if (skill_id, scan_dir) not in self._scan_queue:
            self._scan_queue.append((skill_id, scan_dir))
        if self._active_job is None:
            self._scan_total = len(self._scan_queue)
            self._scan_done = 0
            self._scan_next()

    def _scan_all(self) -> None:
        self._scan_folder(self._current_folder_id)

    def _scan_folder(self, folder_id: int | None) -> None:
        if folder_id is None:
            return
        try:
            with session() as s:
                skills = (
                    s.query(Skill)
                    .filter_by(folder_id=folder_id, spec_type="skill")
                    .all()
                )
                batch = [(sk.id, str(Path(sk.path).parent)) for sk in skills]
        except Exception:
            return
        if not batch:
            return
        self._scan_queue = batch
        self._scan_total = len(batch)
        self._scan_done = 0
        if self._active_job is None:
            self._scan_next()

    def _scan_next(self) -> None:
        if not self._scan_queue:
            self._active_job = None
            self._scan_progress_lbl.setText("")
            self._scan_all_btn.setEnabled(True)
            return

        skill_id, scan_dir = self._scan_queue.pop(0)
        self._scan_progress_lbl.setText(
            f"Scanning {self._scan_done + 1} / {self._scan_total}…"
        )
        self._scan_all_btn.setEnabled(False)

        job = ScanJob(scan_dir)
        job.finished.connect(lambda result: self._on_scan_finished(skill_id, result))
        job.error.connect(lambda msg: self._on_scan_error(skill_id, msg))
        self._active_job = job
        job.start()

    def _on_scan_finished(self, skill_id: int, result) -> None:
        self._active_job = None
        self._scan_done += 1

        parsed = result.parsed or {}
        is_safe = bool(parsed.get("is_safe", False))
        severity = "clean" if is_safe else parsed.get("max_severity", "unknown")

        try:
            with session() as s:
                s.add(
                    DbScanResult(
                        skill_id=skill_id,
                        timestamp=datetime.now(timezone.utc),
                        severity=severity,
                        is_safe=is_safe,
                        raw_json=json.dumps(parsed),
                        findings_json=json.dumps(parsed.get("findings", [])),
                        returncode=result.returncode,
                        analyzers_used=json.dumps(parsed.get("analyzers_used", [])),
                    )
                )
                s.commit()
        except Exception:
            pass

        if skill_id in self._tiles:
            all_finds = parsed.get("findings", [])
            real_finds = [
                f for f in all_finds if f.get("rule_id") != "LLM_ANALYSIS_FAILED"
            ]
            self._tiles[skill_id].refresh(
                severity=severity,
                is_safe=is_safe,
                last_scanned=datetime.now(timezone.utc),
                trusted=False,
                n_results=len(real_finds),
                n_analyzers=len(parsed.get("analyzers_used", [])),
                llm_skipped=bool(
                    parsed.get("analyzers_failed")
                    or any(f.get("rule_id") == "LLM_ANALYSIS_FAILED" for f in all_finds)
                ),
                findings=[
                    {
                        "severity": (f.get("severity") or "unknown").lower(),
                        "category": f.get("category") or f.get("title") or "—",
                    }
                    for f in real_finds
                ],
            )

        self._scan_next()

    def _on_scan_error(self, skill_id: int, _msg: str) -> None:
        self._active_job = None
        self._scan_done += 1
        if skill_id in self._tiles:
            self._tiles[skill_id].refresh(
                severity="unknown",
                is_safe=False,
                last_scanned=datetime.now(timezone.utc),
                trusted=False,
            )
        self._scan_next()

    # ── Trust management ──────────────────────────────────────────────────────

    def _on_trust_toggled(self, skill_id: int, new_trusted: bool) -> None:
        now = datetime.now(timezone.utc)
        try:
            with session() as s:
                sk = s.query(Skill).filter_by(id=skill_id).first()
                if sk:
                    sk.trusted = new_trusted
                    sk.trust_signed_at = now if new_trusted else None
                    s.commit()
        except Exception:
            return
        if skill_id in self._tiles:
            tile = self._tiles[skill_id]
            tile.refresh(
                severity=tile._info.severity,
                is_safe=tile._info.is_safe,
                last_scanned=tile._info.last_scanned,
                trusted=new_trusted,
            )

    # ── Utility ───────────────────────────────────────────────────────────────

    def _open_in_explorer(self, path: str) -> None:
        p = Path(path)
        target = str(p) if p.is_dir() else str(p.parent)
        subprocess.Popen(["explorer", target])

    def refresh_folder(self) -> None:
        """Public — reload tiles for the current folder (called after settings change)."""
        if self._current_folder_id is not None:
            self._load_tiles(self._current_folder_id)
