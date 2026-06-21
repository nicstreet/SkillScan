"""Dashboard view — scrollable card grid with drag-and-drop, edit mode, 60s auto-refresh."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .._icons import fa, ICON_EDIT_PEN, ICON_CHECK
from .._palette import (
    SYS_ACTION_PRIMARY,
    SYS_BADGE_UNSAFE,
    SYS_BG_SECONDARY,
    SYS_STROKE_DIVIDER,
    SYS_TXT_MUTED,
    SYS_TXT_PRIMARY,
    SYS_TXT_SECONDARY,
)
from .._widgets import SCROLLBAR_STYLE, msg_question
from ...core import config as _cfg

from .dashboard import DEFAULT_LAYOUT, REGISTRY, DashboardWidget
from .dashboard._base import SIZE_TO_SPAN
from .dashboard._widgets import QuickActionsWidget

logger = logging.getLogger(__name__)

_REFRESH_MS = 60_000
_WIDGET_GAP = 4
_PANE_PADDING = 6


# ── Configure dialog ──────────────────────────────────────────────────────────


class _ConfigureDialog(QDialog):
    """Checkbox list for showing/hiding dashboard widgets."""

    def __init__(self, hidden: list[str], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Configure Dashboard")
        self.setMinimumWidth(340)
        self.setStyleSheet(
            f"QDialog{{background:{SYS_BG_SECONDARY};}}"
            f"QLabel{{color:{SYS_TXT_PRIMARY};background:transparent;border:none;}}"
            f"QCheckBox{{color:{SYS_TXT_SECONDARY};background:transparent;border:none;}}"
            "QCheckBox::indicator{width:14px;height:14px;}"
            f"QCheckBox::indicator:checked{{background:{SYS_ACTION_PRIMARY};"
            f"border:1px solid {SYS_ACTION_PRIMARY};border-radius:3px;}}"
            f"QCheckBox::indicator:unchecked{{background:transparent;"
            f"border:1px solid {SYS_STROKE_DIVIDER};border-radius:3px;}}"
            f"QDialogButtonBox QPushButton{{background:{SYS_ACTION_PRIMARY};"
            f"color:{SYS_TXT_PRIMARY};border:none;border-radius:4px;padding:5px 16px;}}"
            "QDialogButtonBox QPushButton:hover{background:#0f9e92;}"
        )
        root = QVBoxLayout(self)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        hint = QLabel("Select widgets to show on your dashboard.")
        hint.setFont(QFont("Segoe UI", 9))
        hint.setStyleSheet(f"color:{SYS_TXT_MUTED};background:transparent;border:none;")
        root.addWidget(hint)
        root.addSpacing(4)

        self._checks: dict[str, QCheckBox] = {}
        for cls in REGISTRY:
            cb = QCheckBox(cls.TITLE)
            cb.setFont(QFont("Segoe UI", 10))
            cb.setChecked(cls.WIDGET_ID not in hidden)
            self._checks[cls.WIDGET_ID] = cb
            root.addWidget(cb)

        root.addSpacing(8)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    def get_hidden(self) -> list[str]:
        return [wid for wid, cb in self._checks.items() if not cb.isChecked()]


# ── Drop indicator ────────────────────────────────────────────────────────────


class _DropIndicator(QWidget):
    """Thin coloured line rendered over the drop zone to show insertion point."""

    def __init__(self, parent: QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet(f"background:{SYS_ACTION_PRIMARY};border-radius:2px;")
        self.hide()

    def show_h(self, x: int, y: int, width: int) -> None:
        """Horizontal bar (between rows)."""
        self.setGeometry(x, y - 2, width, 3)
        self.show()
        self.raise_()

    def show_v(self, x: int, y: int, height: int) -> None:
        """Vertical bar (between columns in a row)."""
        self.setGeometry(x - 2, y, 3, height)
        self.show()
        self.raise_()


# ── Drop zone ─────────────────────────────────────────────────────────────────


class _DropZone(QWidget):
    """Scrollable inner content — acts as the drag-and-drop target."""

    # widget_id, target_row, target_col, as_new_row
    drop_requested = pyqtSignal(str, int, int, bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAcceptDrops(True)
        self._indicator = _DropIndicator(self)
        self._rows: list[tuple[QWidget, list[str]]] = []
        self._drop_target: Optional[tuple] = None
        self._edit_mode: bool = False

    def set_edit_mode(self, enabled: bool) -> None:
        self._edit_mode = enabled
        if not enabled:
            self._indicator.hide()

    def update_rows(self, rows: list[tuple[QWidget, list[str]]]) -> None:
        self._rows = rows

    # ── Drag-and-drop events ──────────────────────────────────────────────────

    def dragEnterEvent(self, event) -> None:
        if self._edit_mode and event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragLeaveEvent(self, event) -> None:
        self._indicator.hide()
        self._drop_target = None

    def dragMoveEvent(self, event) -> None:
        if not self._edit_mode or not event.mimeData().hasText():
            event.ignore()
            return
        event.acceptProposedAction()
        self._update_indicator(event.position().toPoint())

    def dropEvent(self, event) -> None:
        self._indicator.hide()
        if not event.mimeData().hasText() or self._drop_target is None:
            event.ignore()
            return
        widget_id = event.mimeData().text()
        target = self._drop_target
        self._drop_target = None
        event.acceptProposedAction()

        if target[0] == "before_row":
            self.drop_requested.emit(widget_id, target[1], 0, True)
        elif target[0] == "in_row":
            self.drop_requested.emit(widget_id, target[1], target[2], False)
        else:  # after_all
            self.drop_requested.emit(widget_id, len(self._rows), 0, True)

    # ── Indicator positioning ─────────────────────────────────────────────────

    def _update_indicator(self, pos) -> None:
        if not self._rows:
            self._indicator.hide()
            return

        ind_w = self.width() - 2 * _PANE_PADDING

        for i, (row_w, _) in enumerate(self._rows):
            geo = row_w.geometry()
            if pos.y() <= geo.bottom():
                if pos.y() < geo.top():
                    # In the gap above this row
                    self._indicator.show_h(
                        _PANE_PADDING,
                        geo.top() - _WIDGET_GAP // 2 - 1,
                        ind_w,
                    )
                    self._drop_target = ("before_row", i)
                else:
                    # Within this row
                    self._find_col_target(i, row_w, geo, pos)
                return

        # Below all rows
        last_geo = self._rows[-1][0].geometry()
        self._indicator.show_h(
            _PANE_PADDING,
            last_geo.bottom() + _WIDGET_GAP // 2,
            ind_w,
        )
        self._drop_target = ("after_all",)

    def _find_col_target(
        self,
        row_idx: int,
        row_w: QWidget,
        row_geo,
        pos,
    ) -> None:
        layout = row_w.layout()
        children = [
            layout.itemAt(j).widget()
            for j in range(layout.count())
            if layout.itemAt(j) and layout.itemAt(j).widget()
        ]

        if not children:
            self._indicator.show_v(
                row_geo.center().x(),
                row_geo.top(),
                row_geo.height(),
            )
            self._drop_target = ("in_row", row_idx, 0)
            return

        for j, child in enumerate(children):
            # Map child position into _DropZone coordinates
            child_left = row_w.mapToParent(child.pos()).x()
            child_mid = child_left + child.width() // 2
            if pos.x() <= child_mid:
                ind_x = max(_PANE_PADDING, child_left - _WIDGET_GAP // 2 - 1)
                self._indicator.show_v(ind_x, row_geo.top(), row_geo.height())
                self._drop_target = ("in_row", row_idx, j)
                return

        # After all children
        last = children[-1]
        last_right = row_w.mapToParent(last.pos()).x() + last.width()
        self._indicator.show_v(
            last_right + _WIDGET_GAP // 2,
            row_geo.top(),
            row_geo.height(),
        )
        self._drop_target = ("in_row", row_idx, len(children))


# ── Main dashboard view ───────────────────────────────────────────────────────


class DashboardView(QWidget):
    """Full dashboard — widget grid with drag-and-drop, edit mode, auto-refresh."""

    navigate_to_folders = pyqtSignal()
    navigate_to_activity = pyqtSignal()
    navigate_to_options = pyqtSignal()
    scan_all_requested = pyqtSignal()
    page_actions_changed = pyqtSignal(object)  # emits QWidget or None

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(f"background:{SYS_BG_SECONDARY};")

        self._edit_mode = False
        self._widgets: list[DashboardWidget] = []

        self._build_ui()
        self._build_grid()

        self._timer = QTimer(self)
        self._timer.setInterval(_REFRESH_MS)
        self._timer.timeout.connect(self._refresh_all)
        self._timer.start()

    # ── UI skeleton ───────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Standalone actions widget - lives in the taskbar when this view is active
        self._actions_widget = QWidget()
        self._actions_widget.setStyleSheet("background:transparent;")
        acts_lay = QHBoxLayout(self._actions_widget)
        acts_lay.setContentsMargins(0, 0, 0, 0)
        acts_lay.setSpacing(6)

        self._reset_btn = QPushButton("Reset")
        self._reset_btn.setFont(QFont("Segoe UI", 9))
        self._reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._reset_btn.setFixedHeight(26)
        self._reset_btn.setVisible(False)
        self._reset_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{SYS_BADGE_UNSAFE};"
            f"border:1px solid {SYS_BADGE_UNSAFE};border-radius:4px;padding:0 10px;}}"
            f"QPushButton:hover{{background:rgba(225,29,72,.12);}}"
        )
        self._reset_btn.clicked.connect(self._on_reset)
        acts_lay.addWidget(self._reset_btn)

        self._cfg_btn = QPushButton("Configure")
        self._cfg_btn.setFont(QFont("Segoe UI", 9))
        self._cfg_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cfg_btn.setFixedHeight(26)
        self._cfg_btn.setVisible(False)
        self._cfg_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{SYS_TXT_SECONDARY};"
            f"border:1px solid {SYS_STROKE_DIVIDER};border-radius:4px;padding:0 10px;}}"
            f"QPushButton:hover{{border-color:{SYS_ACTION_PRIMARY};color:{SYS_ACTION_PRIMARY};}}"
        )
        self._cfg_btn.clicked.connect(self._open_configure)
        acts_lay.addWidget(self._cfg_btn)

        self._edit_btn = QPushButton(ICON_EDIT_PEN)
        self._edit_btn.setFont(fa(11))
        self._edit_btn.setFixedSize(28, 28)
        self._edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._edit_btn.setToolTip("Edit Dashboard")
        self._edit_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{SYS_TXT_MUTED};"
            f"border:none;border-radius:5px;}}"
            f"QPushButton:hover{{background:{SYS_BG_SECONDARY};color:{SYS_ACTION_PRIMARY};}}"
            f"QPushButton[editing=true]{{background:{SYS_ACTION_PRIMARY};"
            f"color:{SYS_TXT_PRIMARY};}}"
        )
        self._edit_btn.clicked.connect(self._toggle_edit_mode)
        acts_lay.addWidget(self._edit_btn)

        # Scroll area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self._scroll.setStyleSheet(f"background:{SYS_BG_SECONDARY};border:none;")
        self._scroll.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)

        self._drop_zone = _DropZone()
        self._drop_zone.setStyleSheet(f"background:{SYS_BG_SECONDARY};border:none;")
        self._drop_zone.drop_requested.connect(self._on_drop)

        self._grid_lay = QVBoxLayout(self._drop_zone)
        self._grid_lay.setContentsMargins(
            _PANE_PADDING + 6, _PANE_PADDING, _PANE_PADDING, _PANE_PADDING
        )
        self._grid_lay.setSpacing(_WIDGET_GAP)
        self._grid_lay.addStretch()

        self._scroll.setWidget(self._drop_zone)
        root.addWidget(self._scroll, 1)

    # ── Layout helpers ────────────────────────────────────────────────────────

    def _get_editable_order(self, cfg: dict) -> list[list[str]]:
        """Return a modifiable copy of the current visible layout order."""
        order = cfg.get("dashboard_order", [])
        if order:
            return [list(row) for row in order]
        # Fall back to DEFAULT_LAYOUT minus hidden
        hidden = cfg.get("dashboard_hidden", [])
        result = []
        for row in DEFAULT_LAYOUT:
            visible = [wid for wid in row if wid not in hidden]
            if visible:
                result.append(visible)
        return result

    # ── Grid construction ─────────────────────────────────────────────────────

    def _build_grid(self) -> None:
        while self._grid_lay.count() > 1:
            item = self._grid_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._widgets.clear()

        cfg = _cfg.load()
        order = self._get_editable_order(cfg)
        spans: dict[str, int] = cfg.get("dashboard_spans", {})
        cls_map = {cls.WIDGET_ID: cls for cls in REGISTRY}

        row_entries: list[tuple[QWidget, list[str]]] = []

        for row_ids in order:
            if not row_ids:
                continue

            row_widget = QWidget()
            row_widget.setStyleSheet("background:transparent;border:none;")
            row_lay = QHBoxLayout(row_widget)
            row_lay.setContentsMargins(0, 0, 0, 0)
            row_lay.setSpacing(_WIDGET_GAP)

            for wid in row_ids:
                cls = cls_map.get(wid)
                if cls is None:
                    continue
                w = cls()
                span = spans.get(wid, SIZE_TO_SPAN.get(cls.SIZE, 6))
                w.set_span(span)
                w.set_edit_mode(self._edit_mode)
                w.remove_requested.connect(self._on_remove_widget)
                w.span_changed.connect(self._on_span_changed)
                self._widgets.append(w)
                row_lay.addWidget(w, span)
                self._wire_quick_actions(w)

            self._grid_lay.insertWidget(self._grid_lay.count() - 1, row_widget)
            row_entries.append((row_widget, row_ids))

        self._drop_zone.update_rows(row_entries)

    def _wire_quick_actions(self, w: DashboardWidget) -> None:
        if isinstance(w, QuickActionsWidget):
            w.navigate_to_folders.connect(self.navigate_to_folders)
            w.navigate_to_activity.connect(self.navigate_to_activity)
            w.navigate_to_options.connect(self.navigate_to_options)
            w.scan_all_requested.connect(self.scan_all_requested)

    # ── Edit mode ─────────────────────────────────────────────────────────────

    def _toggle_edit_mode(self) -> None:
        self._edit_mode = not self._edit_mode
        self._edit_btn.setText(ICON_CHECK if self._edit_mode else ICON_EDIT_PEN)
        self._edit_btn.setToolTip("Done" if self._edit_mode else "Edit Dashboard")
        self._edit_btn.setProperty("editing", self._edit_mode)
        self._edit_btn.style().unpolish(self._edit_btn)
        self._edit_btn.style().polish(self._edit_btn)
        self._cfg_btn.setVisible(self._edit_mode)
        self._reset_btn.setVisible(self._edit_mode)
        self._drop_zone.set_edit_mode(self._edit_mode)
        for w in self._widgets:
            w.set_edit_mode(self._edit_mode)

    # ── Drop handler ──────────────────────────────────────────────────────────

    def _on_drop(
        self,
        widget_id: str,
        target_row: int,
        target_col: int,
        as_new_row: bool,
    ) -> None:
        cfg = _cfg.load()
        order = self._get_editable_order(cfg)

        # Find and remove source
        src_row_idx = -1
        src_col_idx = -1
        src_was_sole = False
        for ri, row in enumerate(order):
            if widget_id in row:
                src_row_idx = ri
                src_col_idx = row.index(widget_id)
                src_was_sole = len(row) == 1
                row.remove(widget_id)
                break

        if src_row_idx == -1:
            return

        # Remove now-empty rows
        order = [r for r in order if r]

        # Adjust target row: if source row disappeared and was before target, shift up
        adj_row = target_row
        if src_was_sole and src_row_idx < target_row:
            adj_row -= 1
        adj_row = max(0, adj_row)

        if as_new_row:
            idx = min(adj_row, len(order))
            order.insert(idx, [widget_id])
        else:
            if adj_row >= len(order):
                order.append([widget_id])
            else:
                row = order[adj_row]
                adj_col = target_col
                # If dragging right within same row, the col already shifted by removal
                if (
                    not src_was_sole
                    and adj_row == src_row_idx
                    and src_col_idx < target_col
                ):
                    adj_col -= 1
                adj_col = max(0, min(adj_col, len(row)))
                row.insert(adj_col, widget_id)

        cfg["dashboard_order"] = order
        _cfg.save(cfg)
        logger.info(
            f"Dashboard: moved '{widget_id}' to row={adj_row} as_new_row={as_new_row}"
        )
        self._rebuild_in_edit_mode()

    # ── Span handler ──────────────────────────────────────────────────────────

    def _on_span_changed(self, widget_id: str, cols: int) -> None:
        cfg = _cfg.load()
        spans: dict[str, int] = cfg.get("dashboard_spans", {})
        spans[widget_id] = cols
        cfg["dashboard_spans"] = spans
        _cfg.save(cfg)
        logger.info(f"Dashboard: span '{widget_id}' -> {cols}/12 cols")
        self._rebuild_in_edit_mode()

    # ── Remove / configure / reset ────────────────────────────────────────────

    def _on_remove_widget(self, widget_id: str) -> None:
        cfg = _cfg.load()
        order = self._get_editable_order(cfg)
        for row in order:
            if widget_id in row:
                row.remove(widget_id)
                break
        order = [r for r in order if r]
        cfg["dashboard_order"] = order
        hidden: list[str] = cfg.get("dashboard_hidden", [])
        if widget_id not in hidden:
            hidden.append(widget_id)
        cfg["dashboard_hidden"] = hidden
        _cfg.save(cfg)
        logger.info(f"Dashboard: hidden '{widget_id}'")
        self._rebuild_in_edit_mode()

    def _open_configure(self) -> None:
        cfg = _cfg.load()
        hidden = cfg.get("dashboard_hidden", [])
        dlg = _ConfigureDialog(hidden, parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        new_hidden = dlg.get_hidden()
        newly_shown = [wid for wid in hidden if wid not in new_hidden]

        order = self._get_editable_order(cfg)
        for wid in newly_shown:
            order.append([wid])

        cfg["dashboard_order"] = order
        cfg["dashboard_hidden"] = new_hidden
        _cfg.save(cfg)
        self._rebuild_in_edit_mode()

    def _on_reset(self) -> None:
        reply = msg_question(
            self,
            "Reset Dashboard",
            "Reset the dashboard to defaults?\n\n"
            "All widget positions, sizes, and visibility will be restored.",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        cfg = _cfg.load()
        cfg["dashboard_order"] = []
        cfg["dashboard_hidden"] = []
        cfg["dashboard_spans"] = {}
        _cfg.save(cfg)
        logger.info("Dashboard: reset to defaults")
        self._rebuild_in_edit_mode()

    # ── Shared rebuild helper ─────────────────────────────────────────────────

    def _rebuild_in_edit_mode(self) -> None:
        self._build_grid()
        self._drop_zone.set_edit_mode(self._edit_mode)
        for w in self._widgets:
            w.set_edit_mode(self._edit_mode)

    # ── Refresh ───────────────────────────────────────────────────────────────

    def _refresh_all(self) -> None:
        for w in self._widgets:
            try:
                w.refresh()
            except Exception:
                logger.debug(f"Widget refresh failed: {w.WIDGET_ID}", exc_info=True)

    def on_activated(self) -> None:
        """Called by main_window when this view becomes visible."""
        self._refresh_all()
        self.page_actions_changed.emit(self._actions_widget)
