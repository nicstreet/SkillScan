"""DashboardWidget — base card class for all SkillScan dashboard widgets."""

from __future__ import annotations

import logging
from typing import Optional

from PyQt6.QtCore import QMimeData, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QDrag, QFont
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..._icons import fa, ICON_REMOVE
from ..._palette import (
    SYS_ACTION_PRIMARY,
    SYS_BG_PRIMARY,
    SYS_STROKE_DIVIDER,
    SYS_TXT_MUTED,
    SYS_TXT_PRIMARY,
    SYS_TXT_SECONDARY,
)

logger = logging.getLogger(__name__)

_ICON_FONT = fa(11)
_HDR_H = 30

# 12-column grid — each preset is (col_count, display_label)
SPAN_PRESETS: list[tuple[int, str]] = [
    (3, "¼"),
    (4, "⅓"),
    (6, "½"),
    (8, "⅔"),
    (9, "¾"),
    (12, "█"),
]

SIZE_TO_SPAN: dict[str, int] = {
    "full": 12,
    "half": 6,
    "third": 4,
}


class DashboardWidget(QFrame):
    """Self-contained dashboard card.

    Subclasses set WIDGET_ID / TITLE / ICON / SIZE and implement
    build_content() + refresh().
    """

    remove_requested = pyqtSignal(str)  # emits WIDGET_ID
    span_changed = pyqtSignal(str, int)  # emits (WIDGET_ID, col_count)

    WIDGET_ID: str = ""
    TITLE: str = ""
    ICON: str = ""
    SIZE: str = "half"  # "full" | "half" | "third"

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName(f"dw_{self.WIDGET_ID}")
        self._current_span: int = SIZE_TO_SPAN.get(self.SIZE, 6)
        self._remove_btn: Optional[QPushButton] = None
        self._span_picker: Optional[QWidget] = None
        self._span_btns: list[QPushButton] = []
        self._edit_mode_active: bool = False
        self._drag_start: Optional[QPoint] = None
        self._apply_card_style(edit=False)
        self._setup_frame()

    # ── Style helpers ─────────────────────────────────────────────────────────

    def _apply_card_style(self, edit: bool) -> None:
        border = "1px dashed #334155" if edit else f"1px solid {SYS_STROKE_DIVIDER}"
        self.setStyleSheet(
            f"QFrame#dw_{self.WIDGET_ID}{{"
            f"background:{SYS_BG_PRIMARY};"
            f"border:{border};"
            f"border-radius:7px;"
            f"}}"
        )

    # ── Frame construction ────────────────────────────────────────────────────

    def _setup_frame(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._make_header())
        body = self._make_body()
        if body:
            root.addWidget(body, 1)

    def _make_header(self) -> QWidget:
        hdr = QWidget()
        hdr.setObjectName("_dwhdr")
        hdr.setFixedHeight(_HDR_H)
        hdr.setStyleSheet(
            "QWidget#_dwhdr{"
            f"background:{SYS_BG_PRIMARY};"
            f"border-bottom:1px solid {SYS_STROKE_DIVIDER};"
            "border-radius:7px 7px 0 0;}"
        )
        lay = QHBoxLayout(hdr)
        lay.setContentsMargins(10, 0, 8, 0)
        lay.setSpacing(5)

        if self.ICON:
            ico = QLabel(self.ICON)
            ico.setFont(_ICON_FONT)
            ico.setStyleSheet(
                f"color:{SYS_TXT_MUTED};background:transparent;border:none;"
            )
            lay.addWidget(ico)

        title_lbl = QLabel(self.TITLE.upper())
        title_lbl.setFont(QFont("Segoe UI", 8))
        title_lbl.setStyleSheet(
            f"color:{SYS_TXT_SECONDARY};background:transparent;"
            "border:none;letter-spacing:1px;"
        )
        lay.addWidget(title_lbl)
        lay.addStretch()

        # ── Span picker (hidden until edit mode) ──────────────────────────────
        self._span_picker = QWidget()
        self._span_picker.setStyleSheet("background:transparent;border:none;")
        self._span_picker.setVisible(False)
        picker_lay = QHBoxLayout(self._span_picker)
        picker_lay.setContentsMargins(0, 0, 6, 0)
        picker_lay.setSpacing(2)

        for cols, label in SPAN_PRESETS:
            btn = QPushButton(label)
            btn.setFixedSize(22, 18)
            btn.setFont(QFont("Segoe UI", 8))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(f"{label} width ({cols}/12 columns)")
            btn.setProperty("spanCols", cols)
            btn.clicked.connect(self._on_span_btn_clicked)
            self._span_btns.append(btn)
            picker_lay.addWidget(btn)

        self._update_span_buttons()
        lay.addWidget(self._span_picker)

        # ── Remove button ─────────────────────────────────────────────────────
        self._remove_btn = QPushButton(ICON_REMOVE)
        self._remove_btn.setFixedSize(18, 18)
        self._remove_btn.setFont(fa(7))
        self._remove_btn.setVisible(False)
        self._remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remove_btn.setToolTip("Remove from dashboard")
        self._remove_btn.setStyleSheet(
            "QPushButton{background:rgba(225,29,72,.15);border:none;"
            "border-radius:3px;color:#E11D48;}"
            "QPushButton:hover{background:rgba(225,29,72,.3);}"
        )
        self._remove_btn.clicked.connect(
            lambda: self.remove_requested.emit(self.WIDGET_ID)
        )
        lay.addWidget(self._remove_btn)
        return hdr

    def _make_body(self) -> Optional[QWidget]:
        container = QWidget()
        container.setStyleSheet("background:transparent;border:none;")
        lay = QVBoxLayout(container)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)
        content = self.build_content()
        if content is not None:
            lay.addWidget(content)
        return container

    # ── Drag initiation ───────────────────────────────────────────────────────

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._edit_mode_active:
            self._drag_start = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (
            self._edit_mode_active
            and self._drag_start is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            dist = (event.position().toPoint() - self._drag_start).manhattanLength()
            if dist >= QApplication.startDragDistance():
                self._start_drag()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_start = None
        super().mouseReleaseEvent(event)

    def _start_drag(self) -> None:
        self._drag_start = None
        mime = QMimeData()
        mime.setText(self.WIDGET_ID)
        drag = QDrag(self)
        drag.setMimeData(mime)
        pixmap = self.grab()
        scaled = pixmap.scaled(
            pixmap.width() * 2 // 3,
            pixmap.height() * 2 // 3,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        drag.setPixmap(scaled)
        drag.setHotSpot(QPoint(scaled.width() // 2, 12))
        drag.exec(Qt.DropAction.MoveAction)

    # ── Span picker helpers ───────────────────────────────────────────────────

    def _on_span_btn_clicked(self) -> None:
        btn = self.sender()
        if btn is None:
            return
        cols = btn.property("spanCols")
        if cols == self._current_span:
            return
        self._current_span = cols
        self._update_span_buttons()
        self.span_changed.emit(self.WIDGET_ID, cols)

    def _update_span_buttons(self) -> None:
        for btn in self._span_btns:
            active = btn.property("spanCols") == self._current_span
            if active:
                btn.setStyleSheet(
                    f"QPushButton{{background:{SYS_ACTION_PRIMARY};color:{SYS_TXT_PRIMARY};"
                    "border:none;border-radius:3px;}"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton{{background:transparent;color:{SYS_TXT_MUTED};"
                    f"border:1px solid {SYS_STROKE_DIVIDER};border-radius:3px;}}"
                    f"QPushButton:hover{{color:{SYS_TXT_SECONDARY};"
                    f"border-color:{SYS_ACTION_PRIMARY};}}"
                )

    # ── Public API ────────────────────────────────────────────────────────────

    def build_content(self) -> Optional[QWidget]:
        """Return the widget body. Called once during construction."""
        return None

    def refresh(self) -> None:
        """Refresh displayed data. Called on a timer and after layout changes."""
        pass

    def set_span(self, cols: int) -> None:
        """Set the current span without emitting span_changed."""
        self._current_span = cols
        self._update_span_buttons()

    def set_edit_mode(self, enabled: bool) -> None:
        self._edit_mode_active = enabled
        self._apply_card_style(edit=enabled)
        if self._remove_btn:
            self._remove_btn.setVisible(enabled)
        if self._span_picker:
            self._span_picker.setVisible(enabled)
