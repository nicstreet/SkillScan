"""Shared frameless-window building blocks used across SkillScan dialogs."""

from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)

from ._palette import (
    ANCHOR,
    CRITICAL_ACCENT,
    DIVIDER,
    LIGHT_CANVAS,
    MUTED_TEXT,
)


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
        p.fillPath(path, QColor(ANCHOR))
        p.end()


class TitleBar(QWidget):
    """Draggable custom title bar with a Segoe Fluent Icons close button."""

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
            f"color:{LIGHT_CANVAS};font-weight:700;font-size:13px;background:transparent;"
        )
        layout.addWidget(self._title_lbl)
        layout.addStretch()

        close_btn = QPushButton("")  # Segoe Fluent Icons — ChromeClose
        close_btn.setFont(QFont("Segoe Fluent Icons", 9))
        close_btn.setFixedSize(34, 34)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("Close")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {MUTED_TEXT};
                background: transparent;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover   {{ background: {CRITICAL_ACCENT}; color: {LIGHT_CANVAS}; }}
            QPushButton:pressed {{ background: #b91c1c; color: {LIGHT_CANVAS}; }}
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
    """Thin horizontal rule — LOW_BORDER pre-blended at 15 % on ANCHOR."""
    div = QFrame()
    div.setFrameShape(QFrame.Shape.HLine)
    div.setStyleSheet(
        f"color:{DIVIDER};background:{DIVIDER};border:none;max-height:1px;"
    )
    return div


# ── Scrollbar style ───────────────────────────────────────────────────────────
# Qt stylesheet QScrollBar rules do NOT cascade from a parent widget's
# setStyleSheet() into child scrollbar widgets.  Always apply directly:
#   widget.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
# Never concatenate into a QTextBrowser / QPlainTextEdit / QScrollArea stylesheet.
SCROLLBAR_STYLE = (
    "QScrollBar:vertical{background:transparent;width:6px;border:none;margin:0px;}"
    "QScrollBar::handle:vertical{background:#334155;border-radius:3px;min-height:24px;}"
    "QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0px;}"
    "QScrollBar::add-page:vertical,QScrollBar::sub-page:vertical{background:none;}"
)
