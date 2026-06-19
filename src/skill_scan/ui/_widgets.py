"""Shared frameless-window building blocks used across SkillScan dialogs."""

import math

from PyQt6.QtCore import QEvent, QObject, QPoint, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QPolygon, QRegion
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ._icons import fa, ICON_CIRCLE_QUESTION, ICON_CLOSE, ICON_INFO, ICON_WARNING
from ._palette import (
    SYS_ACTION_HOVER,
    SYS_ACTION_PRIMARY,
    SYS_BG_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_BADGE_UNSAFE,
    SYS_BORDER_ADVISORY,
    SYS_STROKE_DIVIDER,
    SYS_TXT_PRIMARY,
    SYS_TXT_MUTED,
    SYS_CONTROL_BG_CRITICAL_PRESSED,
    SYS_SCROLL_HANDLE,
)

# ── Cascade-immune surface with independently roundable corners ──────────────


def _corner_rect_path(
    w: float, h: float, radius: float, corners: tuple[bool, bool, bool, bool]
) -> QPainterPath:
    """Rect path with independently roundable corners: (top_left, top_right, bottom_right, bottom_left)."""
    tl, tr, br, bl = (radius if rounded else 0.0 for rounded in corners)
    path = QPainterPath()
    path.moveTo(tl, 0.0)
    path.lineTo(w - tr, 0.0)
    if tr:
        path.arcTo(w - 2 * tr, 0.0, 2 * tr, 2 * tr, 90.0, -90.0)
    path.lineTo(w, h - br)
    if br:
        path.arcTo(w - 2 * br, h - 2 * br, 2 * br, 2 * br, 0.0, -90.0)
    path.lineTo(bl, h)
    if bl:
        path.arcTo(0.0, h - 2 * bl, 2 * bl, 2 * bl, 270.0, -90.0)
    path.lineTo(0.0, tl)
    if tl:
        path.arcTo(0.0, 0.0, 2 * tl, 2 * tl, 180.0, -90.0)
    path.closeSubpath()
    return path


class _Surface(QWidget):
    """QWidget that paints its own background — immune to stylesheet cascade."""

    def __init__(
        self,
        color: str,
        radius: int = 0,
        parent=None,
        corners: tuple[bool, bool, bool, bool] = (True, True, True, True),
    ):
        super().__init__(parent)
        self._color = QColor(color)
        self._radius = radius
        self._corners = corners

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._radius:
            path = _corner_rect_path(
                float(self.width()),
                float(self.height()),
                float(self._radius),
                self._corners,
            )
            p.fillPath(path, self._color)
        else:
            p.fillRect(self.rect(), self._color)
        p.end()


# ── Dark message dialog ───────────────────────────────────────────────────────

_YES = QMessageBox.StandardButton.Yes
_NO = QMessageBox.StandardButton.No
_OK = QMessageBox.StandardButton.Ok

_BTN_PRIMARY = (
    f"QPushButton{{background:{SYS_ACTION_PRIMARY};color:{SYS_TXT_PRIMARY};"
    f"border:none;border-radius:5px;padding:0 18px;font-size:12px;font-weight:600;}}"
    f"QPushButton:hover{{background:{SYS_ACTION_HOVER};}}"
    f"QPushButton:pressed{{background:{SYS_ACTION_HOVER};}}"
)
_BTN_GHOST = (
    f"QPushButton{{background:{SYS_BG_PRIMARY};color:{SYS_TXT_PRIMARY};"
    f"border:1px solid {SYS_STROKE_DIVIDER};border-radius:5px;padding:0 18px;font-size:12px;}}"
    f"QPushButton:hover{{border-color:{SYS_ACTION_PRIMARY};color:{SYS_ACTION_PRIMARY};}}"
    f"QPushButton:pressed{{background:{SYS_BG_PRIMARY};}}"
)


class _DarkMessageBox(QDialog):
    """Frameless dark modal dialog — no OS chrome, FA icon, palette buttons."""

    def __init__(
        self,
        parent: QWidget | None,
        icon_char: str,
        icon_color: str,
        title: str,
        text: str,
        buttons: list[tuple[str, QMessageBox.StandardButton]],
        default: QMessageBox.StandardButton,
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self._clicked = QMessageBox.StandardButton.NoButton
        self._build(icon_char, icon_color, title, text, buttons, default)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, float(self.width()), float(self.height()), 10, 10)
        p.fillPath(path, QColor(SYS_BG_SECONDARY))
        pen = QPen(QColor(SYS_STROKE_DIVIDER))
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        border = QPainterPath()
        border.addRoundedRect(
            0.5, 0.5, self.width() - 1.0, self.height() - 1.0, 9.5, 9.5
        )
        p.drawPath(border)
        p.end()

    def _build(
        self,
        icon_char: str,
        icon_color: str,
        title: str,
        text: str,
        buttons: list[tuple[str, QMessageBox.StandardButton]],
        default: QMessageBox.StandardButton,
    ) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 16)
        outer.setSpacing(16)

        # Content row: icon + text column
        content = QHBoxLayout()
        content.setSpacing(14)
        content.setContentsMargins(0, 0, 0, 0)

        icon_lbl = QLabel(icon_char)
        icon_lbl.setFont(fa(22))
        icon_lbl.setStyleSheet(f"color:{icon_color};background:transparent;")
        icon_lbl.setFixedWidth(30)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        content.addWidget(icon_lbl)

        text_col = QVBoxLayout()
        text_col.setSpacing(5)
        text_col.setContentsMargins(0, 1, 0, 0)

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color:{SYS_TXT_PRIMARY};font-size:13px;font-weight:700;background:transparent;"
        )
        title_lbl.setWordWrap(True)
        text_col.addWidget(title_lbl)

        msg_lbl = QLabel(text)
        msg_lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:12px;background:transparent;"
        )
        msg_lbl.setWordWrap(True)
        msg_lbl.setMinimumWidth(260)
        text_col.addWidget(msg_lbl)

        content.addLayout(text_col, 1)
        outer.addLayout(content)

        # Button row — right-aligned
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.addStretch()

        for label, std_btn in buttons:
            btn = QPushButton(label)
            btn.setFixedHeight(30)
            btn.setMinimumWidth(72)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(_BTN_PRIMARY if std_btn == default else _BTN_GHOST)
            s = std_btn
            btn.clicked.connect(lambda checked=False, _s=s: self._on_click(_s))
            btn_row.addWidget(btn)

        outer.addLayout(btn_row)
        self.adjustSize()
        self.setMinimumWidth(400)

    def _on_click(self, std: QMessageBox.StandardButton) -> None:
        self._clicked = std
        self.accept()

    def result_button(self) -> QMessageBox.StandardButton:
        return self._clicked


def msg_question(
    parent: QWidget,
    title: str,
    text: str,
    buttons: QMessageBox.StandardButton = _YES | _NO,
    default: QMessageBox.StandardButton = _NO,
) -> QMessageBox.StandardButton:
    dlg = _DarkMessageBox(
        parent,
        ICON_CIRCLE_QUESTION,
        SYS_ACTION_PRIMARY,
        title,
        text,
        [("No", _NO), ("Yes", _YES)],
        default,
    )
    dlg.exec()
    return dlg.result_button()


def msg_information(parent: QWidget, title: str, text: str) -> None:
    _DarkMessageBox(
        parent,
        ICON_INFO,
        SYS_ACTION_PRIMARY,
        title,
        text,
        [("OK", _OK)],
        _OK,
    ).exec()


def msg_warning(parent: QWidget, title: str, text: str) -> None:
    _DarkMessageBox(
        parent,
        ICON_WARNING,
        SYS_BORDER_ADVISORY,
        title,
        text,
        [("OK", _OK)],
        _OK,
    ).exec()


def msg_critical(parent: QWidget, title: str, text: str) -> None:
    _DarkMessageBox(
        parent,
        ICON_WARNING,
        SYS_BADGE_UNSAFE,
        title,
        text,
        [("OK", _OK)],
        _OK,
    ).exec()


# ── Window building blocks ────────────────────────────────────────────────────


class RoundedCard(QFrame):
    """Dark rounded card — use as the top-level container inside a frameless QDialog."""

    def __init__(self, radius: int = 16, parent=None):
        super().__init__(parent)
        self._radius = radius
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(
            0, 0, self.width(), self.height(), self._radius, self._radius
        )
        p.fillPath(path, QColor(SYS_BG_PRIMARY))
        p.end()


class TitleBar(QWidget):
    """Draggable custom title bar with close button."""

    close_requested = pyqtSignal()

    def __init__(self, title: str = "SkillScan", height: int = 46, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)
        self._drag_pos: QPoint | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 10, 0)
        layout.setSpacing(0)

        self._title_lbl = QLabel(title)
        self._title_lbl.setStyleSheet(
            f"color:{SYS_TXT_PRIMARY};font-weight:700;font-size:13px;background:transparent;"
        )
        layout.addWidget(self._title_lbl)
        layout.addStretch()

        close_btn = QPushButton(ICON_CLOSE)  # xmark
        close_btn.setFont(fa(9))
        close_btn.setFixedSize(34, 34)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("Close")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {SYS_TXT_MUTED};
                background: transparent;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover   {{ background: {SYS_BADGE_UNSAFE}; color: {SYS_TXT_PRIMARY}; }}
            QPushButton:pressed {{ background: {SYS_CONTROL_BG_CRITICAL_PRESSED}; color: {SYS_TXT_PRIMARY}; }}
        """)
        close_btn.clicked.connect(self.close_requested)
        layout.addWidget(close_btn)

    def set_title(self, text: str) -> None:
        self._title_lbl.setText(text)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                e.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
            self.window().move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, _e):
        self._drag_pos = None


def card_divider() -> QFrame:
    """Thin horizontal rule — SYS_STROKE_DIVIDER colour."""
    div = QFrame()
    div.setFrameShape(QFrame.Shape.HLine)
    div.setStyleSheet(
        f"color:{SYS_STROKE_DIVIDER};background:{SYS_STROKE_DIVIDER};border:none;max-height:1px;"
    )
    return div


# ── Scrollbar style ───────────────────────────────────────────────────────────
# Qt stylesheet QScrollBar rules do NOT cascade from a parent widget's
# setStyleSheet() into child scrollbar widgets.  Always apply directly:
#   widget.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
# Never concatenate into a QTextBrowser / QPlainTextEdit / QScrollArea stylesheet.
SCROLLBAR_STYLE = (
    "QScrollBar:vertical{background:transparent;width:6px;border:none;margin:0px;}"
    f"QScrollBar::handle:vertical{{background:{SYS_SCROLL_HANDLE};border-radius:3px;min-height:24px;}}"
    "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0px;}"
    "QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{background:none;}"
)


# ── Rounded-corner mask ────────────────────────────────────────────────────────
# Two unrelated problems share one fix:
#  1. QSS border-radius does not clip the viewport of QAbstractScrollArea
#     subclasses (QTableWidget, QListWidget, QTreeWidget, QTextBrowser,
#     QPlainTextEdit) — the viewport paints its background as a plain
#     rectangle regardless of the stylesheet's border-radius.
#  2. A frameless top-level window that paints its own rounded silhouette in
#     paintEvent() does not automatically clip its CHILD widgets to that same
#     shape — any descendant painting a plain rect background (e.g. a page
#     widget sitting only a couple of pixels in from the window edge) pokes
#     square corners out past the parent's rounded curve.
# round_corners() works around both with a resize-tracked QRegion mask.
#
# QPainterPath.toFillPolygon() flattens curves with very few points at small
# radii — the corner ends up as 3-4 long straight segments, which reads as
# jagged diagonal facets rather than a curve once it becomes a hard-edged
# QRegion (no antialiasing to soften it). _rounded_rect_polygon() instead
# samples each corner arc directly at a fixed angular step, independent of
# the path-flattening heuristic, so the corner stays smooth at any size.
_ARC_STEPS = 24  # points per 90° corner — comfortably smooth up to ~20px radius


def _rounded_rect_polygon(w: int, h: int, r: int) -> QPolygon:
    r = max(0, min(r, w // 2, h // 2))
    points: list[QPoint] = []
    # (centre_x, centre_y, start_degrees, end_degrees) per corner, clockwise
    # from top-right, sweeping each quarter-circle in screen coordinates.
    corners = [
        (w - r, r, 270.0, 360.0),  # top-right
        (w - r, h - r, 0.0, 90.0),  # bottom-right
        (r, h - r, 90.0, 180.0),  # bottom-left
        (r, r, 180.0, 270.0),  # top-left
    ]
    for cx, cy, start_deg, end_deg in corners:
        for i in range(_ARC_STEPS + 1):
            angle = math.radians(start_deg + (end_deg - start_deg) * i / _ARC_STEPS)
            points.append(
                QPoint(
                    round(cx + r * math.cos(angle)),
                    round(cy + r * math.sin(angle)),
                )
            )
    return QPolygon(points)


class _RoundedMask(QObject):
    def __init__(self, widget: QWidget, radius: int):
        super().__init__(widget)
        self._widget = widget
        self._radius = radius
        widget.installEventFilter(self)
        self._apply()

    def eventFilter(self, obj, event):
        if obj is self._widget and event.type() == QEvent.Type.Resize:
            self._apply()
        return False

    def _apply(self) -> None:
        polygon = _rounded_rect_polygon(
            self._widget.width(), self._widget.height(), self._radius
        )
        self._widget.setMask(QRegion(polygon))


def round_corners(widget: QWidget, radius: int) -> None:
    """Clip a scroll-area widget to rounded corners; re-applied on every resize."""
    _RoundedMask(widget, radius)
