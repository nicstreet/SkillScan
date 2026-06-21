"""Help window — minimal structural skeleton, no content yet.

Reference build for the rounded-corner/border treatment before any real help
content is added. Mirrors main_window.py's MainWindow/_MainPanel split:
HelpWindow is a transparent shell carrying only window flags; _HelpPanel is
the child widget that paints the rounded background + thin border.

Layout: 2 columns. Column 1 is rounded on its outer (left) edge only; column 2
is rounded on its outer (right) edge only — together they form the window's
four gracefully-curved outer corners, with a square seam where they meet in
the middle. Column 2 is split into 2 rows: row 1 holds just the close button,
row 2 is empty.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from ._icons import ICON_CLOSE, fa_reg
from ._palette import (
    SYS_BG_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_CONTROL_BG_CRITICAL_PRESSED,
    SYS_BADGE_UNSAFE,
    SYS_STROKE_DIVIDER,
    SYS_TXT_MUTED,
    SYS_TXT_PRIMARY,
)
from ._widgets import _Surface

_OUTER_RADIUS = 16  # window's own outer corners — the "graceful sweeping curve"
_PANEL_MARGIN = 1  # gap between _HelpPanel's edge and the two columns
_COL_RADIUS = _OUTER_RADIUS - _PANEL_MARGIN  # concentric with the outer curve
_BORDER_WIDTH = 0.5

_CLOSE_STYLE = (
    f"QPushButton{{color:{SYS_TXT_MUTED};background:transparent;border:none;"
    f"border-radius:5px;font-family:'Font Awesome 6 Free';font-weight:400;font-size:11pt;}}"
    f"QPushButton:hover{{background:{SYS_BADGE_UNSAFE};color:{SYS_TXT_PRIMARY};}}"
    f"QPushButton:pressed{{background:{SYS_CONTROL_BG_CRITICAL_PRESSED};color:{SYS_TXT_PRIMARY};}}"
)


class _HelpPanel(QWidget):
    """Draws the rounded SYS_BG_SECONDARY background + thin border — same
    paint approach as main_window.py's _MainPanel, at a larger radius and a
    much thinner (0.5px) border."""

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fill = QPainterPath()
        fill.addRoundedRect(
            0, 0, self.width(), self.height(), _OUTER_RADIUS, _OUTER_RADIUS
        )
        p.fillPath(fill, QColor(SYS_BG_SECONDARY))
        pen = QPen(QColor(SYS_STROKE_DIVIDER))
        pen.setWidthF(_BORDER_WIDTH)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        inset = _BORDER_WIDTH / 2
        border = QPainterPath()
        border.addRoundedRect(
            inset,
            inset,
            self.width() - _BORDER_WIDTH,
            self.height() - _BORDER_WIDTH,
            _OUTER_RADIUS - inset,
            _OUTER_RADIUS - inset,
        )
        p.drawPath(border)
        p.end()


class HelpWindow(QWidget):
    """Frameless floating help window — structural skeleton only."""

    closed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(
            parent,
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._build()
        self.resize(700, 500)
        # No round_corners() mask here on purpose: _HelpPanel and both columns
        # already paint properly antialiased, correctly-nested rounded shapes
        # (see _COL_RADIUS's comment), so nothing square-edged ever reaches the
        # outer boundary that would need clipping. setMask()/QRegion has no
        # antialiasing at all — it's a hard binary pixel boundary — so adding
        # it here would only make the curve rougher, not smoother.

    # -- Build -----------------------------------------------------------------

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._panel = _HelpPanel(self)
        self._panel.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        outer.addWidget(self._panel)

        cols = QHBoxLayout(self._panel)
        cols.setContentsMargins(
            _PANEL_MARGIN, _PANEL_MARGIN, _PANEL_MARGIN, _PANEL_MARGIN
        )
        cols.setSpacing(0)

        # Column 1 — rounded on the left (outer edge) only. Empty by design.
        column1 = _Surface(
            SYS_BG_PRIMARY, radius=_COL_RADIUS, corners=(True, False, False, True)
        )
        column1.setFixedWidth(220)
        cols.addWidget(column1)

        # Column 2 — rounded on the right (outer edge) only. 2 rows.
        column2 = _Surface(
            SYS_BG_SECONDARY, radius=_COL_RADIUS, corners=(False, True, True, False)
        )
        col2_lay = QVBoxLayout(column2)
        col2_lay.setContentsMargins(0, 0, 0, 0)
        col2_lay.setSpacing(0)

        row1 = QWidget()
        row1.setFixedHeight(44)
        row1.setStyleSheet("background:transparent;")
        r1l = QHBoxLayout(row1)
        r1l.setContentsMargins(0, 0, 8, 0)
        r1l.addStretch()
        close_btn = QPushButton(ICON_CLOSE)
        close_btn.setFont(fa_reg(11))
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("Close")
        close_btn.setStyleSheet(_CLOSE_STYLE)
        close_btn.clicked.connect(self.close)
        r1l.addWidget(close_btn)
        col2_lay.addWidget(row1)

        row2 = QWidget()
        row2.setStyleSheet("background:transparent;")
        col2_lay.addWidget(row2, 1)

        cols.addWidget(column2, 1)

    def closeEvent(self, event) -> None:
        self.closed.emit()
        super().closeEvent(event)
