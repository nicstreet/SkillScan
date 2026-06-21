"""TEMPORARY diagnostic window — not part of the app, remove once the
options_view.py seam (see change_history.md) is root-caused.

Bisection step 4. Step 1 (bare nav + content_col), step 2 (+ content_header/
QStackedWidget structure, blank page), and step 3 (+ real _section_scroll()
machinery, zero cards) were all confirmed faultless on a real screen — the
seam is not the skeleton, not the container structure, and not the
QScrollArea/viewport/inner-_Surface plumbing. This step adds the actual
General-page card content — _ToggleSwitch, _setting_row, _card_wrap, all
imported directly from options_view.py, not reimplemented — so the only
remaining unknown is the toggle rows themselves. If the seam finally appears
here, the card content (or a widget inside it) is the cause.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ._icons import ICON_CLOSE, fa_reg
from ._palette import (
    SYS_BADGE_UNSAFE,
    SYS_BG_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_CONTROL_BG_CRITICAL_PRESSED,
    SYS_STROKE_DIVIDER,
    SYS_TXT_MUTED,
    SYS_TXT_PRIMARY,
)
from ._widgets import _Surface
from .views.options_view import _ToggleSwitch, _card_wrap, _section_scroll, _setting_row

_CORNER_RADIUS = 12
_PANEL_MARGIN = 2
_CONTENT_RADIUS = _CORNER_RADIUS - _PANEL_MARGIN
_NAV_WIDTH = 180

_CLOSE_STYLE = (
    f"QPushButton{{color:{SYS_TXT_MUTED};background:transparent;border:none;"
    f"border-radius:5px;font-family:'Font Awesome 6 Free';font-weight:400;font-size:11pt;}}"
    f"QPushButton:hover{{background:{SYS_BADGE_UNSAFE};color:{SYS_TXT_PRIMARY};}}"
    f"QPushButton:pressed{{background:{SYS_CONTROL_BG_CRITICAL_PRESSED};color:{SYS_TXT_PRIMARY};}}"
)


class _TestPanel(QWidget):
    """Same fill/border paint code as _MainPanel / _OptionsPanel / _HelpPanel."""

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        fill = QPainterPath()
        fill.addRoundedRect(
            0, 0, self.width(), self.height(), _CORNER_RADIUS, _CORNER_RADIUS
        )
        p.fillPath(fill, QColor(SYS_BG_SECONDARY))
        pen = QPen(QColor(SYS_STROKE_DIVIDER))
        pen.setWidthF(1.5)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        border = QPainterPath()
        border.addRoundedRect(
            0.75, 0.75, self.width() - 1.5, self.height() - 1.5, 11.25, 11.25
        )
        p.drawPath(border)
        p.end()


class TestWindow(QWidget):
    """Diagnostic-only. No round_corners() mask — see help_window.py."""

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
        self.resize(820, 640)

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        panel = _TestPanel(self)
        panel.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        outer.addWidget(panel)

        cols = QHBoxLayout(panel)
        cols.setContentsMargins(
            _PANEL_MARGIN, _PANEL_MARGIN, _PANEL_MARGIN, _PANEL_MARGIN
        )
        cols.setSpacing(0)

        nav = _Surface(
            SYS_BG_PRIMARY, radius=_CONTENT_RADIUS, corners=(True, False, False, True)
        )
        nav.setFixedWidth(_NAV_WIDTH)
        cols.addWidget(nav)

        # From here down mirrors options_view.py's _build_ui() exactly —
        # same _Surface params, same ccl margins, same content_header +
        # content_stack split — just with a blank page instead of a real one.
        content_col = _Surface(
            SYS_BG_SECONDARY, radius=_CONTENT_RADIUS, corners=(False, True, True, False)
        )
        ccl = QVBoxLayout(content_col)
        ccl.setContentsMargins(8, 4, _CONTENT_RADIUS, _CONTENT_RADIUS)
        ccl.setSpacing(4)

        content_header = QWidget()
        content_header.setStyleSheet("background:transparent;")
        chl = QHBoxLayout(content_header)
        chl.setContentsMargins(0, 0, 0, 0)
        chl.addStretch()
        close_btn = QPushButton(ICON_CLOSE)
        close_btn.setFont(fa_reg(11))
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(_CLOSE_STYLE)
        close_btn.clicked.connect(self.close)
        chl.addWidget(close_btn)
        ccl.addWidget(content_header)

        content_stack = QStackedWidget()  # no styleSheet — see options_view.py
        # Exact copy of OptionsView._make_general_page() — same helpers, same
        # two rows, just without the self._chk_* attribute assignment (this
        # window throws the toggles away, nothing reads their state).
        general_page = _section_scroll(
            [
                _card_wrap(
                    [
                        _setting_row(
                            "Launch at login",
                            "Start SkillScan minimised to the system tray on Windows startup.",
                            _ToggleSwitch(),
                        ),
                        _setting_row(
                            "Show full folder path in tooltip",
                            "Display the complete path when hovering over a folder name.",
                            _ToggleSwitch(),
                        ),
                    ]
                )
            ]
        )
        content_stack.addWidget(general_page)
        ccl.addWidget(content_stack, 1)

        cols.addWidget(content_col, 1)

    def closeEvent(self, event) -> None:
        self.closed.emit()
        super().closeEvent(event)
