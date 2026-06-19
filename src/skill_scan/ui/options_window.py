"""Standalone frameless Options window — no titlebar, no dragging; closing the
window (or amending any setting) saves immediately via OptionsView's autosave.

Structure mirrors main_window.py's MainWindow/_MainPanel split: the top-level
QWidget is a plain transparent shell carrying only window flags, and a child
_OptionsPanel does the actual rounded background + border painting. Native
top-level frameless widgets get a default OS drop shadow on Windows unless
NoDropShadowWindowHint is set — _MainPanel never showed one because nothing
in this file had asked Qt to suppress it either way until now.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from ._icons import ICON_CLOSE, fa_reg
from ._palette import (
    SYS_BG_SECONDARY,
    SYS_CONTROL_BG_CRITICAL_PRESSED,
    SYS_BADGE_UNSAFE,
    SYS_STROKE_DIVIDER,
    SYS_TXT_MUTED,
    SYS_TXT_PRIMARY,
)
from .views.options_view import OptionsView

_CORNER_RADIUS = 12
_BORDER_WIDTH = 0.75  # halved from 1.5 — see _OptionsPanel.paintEvent
_BORDER_INSET = _BORDER_WIDTH / 2
_BORDER_RADIUS = _CORNER_RADIUS - _BORDER_INSET

_CLOSE_STYLE = (
    f"QPushButton{{color:{SYS_TXT_MUTED};background:transparent;border:none;"
    f"border-radius:5px;font-family:'Font Awesome 6 Free';font-weight:400;font-size:11pt;}}"
    f"QPushButton:hover{{background:{SYS_BADGE_UNSAFE};color:{SYS_TXT_PRIMARY};}}"
    f"QPushButton:pressed{{background:{SYS_CONTROL_BG_CRITICAL_PRESSED};color:{SYS_TXT_PRIMARY};}}"
)


class _OptionsPanel(QWidget):
    """Draws the rounded SYS_BG_SECONDARY background that acts as the window
    surface — same paint code as main_window.py's _MainPanel."""

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fill = QPainterPath()
        fill.addRoundedRect(
            0, 0, self.width(), self.height(), _CORNER_RADIUS, _CORNER_RADIUS
        )
        p.fillPath(fill, QColor(SYS_BG_SECONDARY))
        pen = QPen(QColor(SYS_STROKE_DIVIDER))
        pen.setWidthF(_BORDER_WIDTH)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        border = QPainterPath()
        border.addRoundedRect(
            _BORDER_INSET,
            _BORDER_INSET,
            self.width() - _BORDER_WIDTH,
            self.height() - _BORDER_WIDTH,
            _BORDER_RADIUS,
            _BORDER_RADIUS,
        )
        p.drawPath(border)
        p.end()


class OptionsWindow(QWidget):
    """Frameless floating window that hosts the Options view."""

    settings_changed = pyqtSignal()
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
        # 850x650 was confirmed seam-free on a real screen (820x640 hit a
        # fixed-size sub-pixel/DPI-rounding coincidence between
        # independently-laid-out widgets — see change_history.md). Grown to
        # 870x670 here (+20px each) so nav/content_col end up larger,
        # compensating for the halved border width above. UNTESTED at this
        # new size — re-check for the seam on a real screen, since it's tied
        # to the exact pixel dimensions and this is a different value than
        # the one already confirmed.
        self.resize(870, 670)

    # -- Build -----------------------------------------------------------------

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._panel = _OptionsPanel(self)
        self._panel.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        outer.addWidget(self._panel)

        # No round_corners() mask — see pyqt6-frameless-window and
        # help_window.py. OptionsView's nav + content_col now both paint their
        # own correctly-nested rounded shapes (instead of OptionsView painting
        # one flat square fillRect), so nothing square-edged ever reaches this
        # panel's outer curve. A setMask() here would only make the corners
        # rougher than the antialiased paintEvent below already makes them.

        panel_vbox = QVBoxLayout(self._panel)
        panel_vbox.setContentsMargins(1, 1, 1, 1)
        panel_vbox.setSpacing(0)

        # OptionsView's own nav-content split fills the whole panel — the nav
        # column then spans the full panel height. The close button sits in
        # OptionsView's thin content-column header row (column 2 only), not in
        # a full-width row above everything, so it never pushes the nav down.
        self._options_view = OptionsView(self._panel)
        self._options_view.settings_changed.connect(self.settings_changed)
        self._options_view.add_header_widget(self._make_close_button())
        panel_vbox.addWidget(self._options_view, 1)

    def _make_close_button(self) -> QPushButton:
        close_btn = QPushButton(ICON_CLOSE)
        close_btn.setFont(fa_reg(11))
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("Close")
        close_btn.setStyleSheet(_CLOSE_STYLE)
        close_btn.clicked.connect(self.close)
        return close_btn

    def closeEvent(self, event) -> None:
        # Safety net: catches a field whose commit signal (e.g. editingFinished)
        # hasn't fired yet because focus never left it before the window closed.
        self._options_view.save_now()
        self.closed.emit()
        super().closeEvent(event)
