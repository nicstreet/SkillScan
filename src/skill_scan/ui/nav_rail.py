"""Nav rail — 56px left sidebar with icon + label nav items and active-state indicator."""

from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import QFrame, QVBoxLayout, QWidget

from ._icons import (
    fa,
    ICON_DASHBOARD,
    ICON_FOLDERS,
    ICON_INVENTORY,
    ICON_MANAGE,
    ICON_TESTING,
    ICON_ACTIVITY,
    ICON_OPTIONS,
    ICON_ABOUT,
    ICON_EXIT,
)
from ._palette import (
    SYS_ACTION_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_STROKE_DIVIDER,
    SYS_TXT_MUTED,
)


class NavItem(QWidget):
    """Single nav icon + label button with active-state paint."""

    clicked = pyqtSignal()

    _ICON_FONT = fa(15)
    _LABEL_FONT = QFont("Segoe UI", 7)

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self._icon = icon
        self._label = label
        self._active = False
        self._hover = False
        self.setFixedHeight(52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(label)

    def set_active(self, active: bool) -> None:
        if self._active != active:
            self._active = active
            self.update()

    def enterEvent(self, _e) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, _e) -> None:
        self._hover = False
        self.update()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        if self._active:
            p.fillRect(0, 0, w, h, QColor(13, 148, 136, 31))  # SYS_ACTION_PRIMARY @ 12%
            p.fillRect(0, 8, 3, h - 16, QColor(SYS_ACTION_PRIMARY))  # 3px left bar
        elif self._hover:
            p.fillRect(0, 0, w, h, QColor(30, 41, 59, 200))  # SYS_BG_SECONDARY hover

        color = QColor(SYS_ACTION_PRIMARY) if self._active else QColor(SYS_TXT_MUTED)
        p.setPen(color)

        p.setFont(self._ICON_FONT)
        p.drawText(
            QRect(0, 4, w, 30),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            self._icon,
        )

        p.setFont(self._LABEL_FONT)
        p.drawText(
            QRect(0, 34, w, 14),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            self._label,
        )
        p.end()


class NavRail(QWidget):
    """Vertical icon navigation rail — 56px, SYS_BG_SECONDARY background."""

    page_changed = pyqtSignal(int)
    exit_requested = pyqtSignal()

    # (icon codepoint, label) — index maps directly to QStackedWidget page
    _TOP: list[tuple[str, str]] = [
        (ICON_DASHBOARD, "Dashboard"),  # 0
        (ICON_FOLDERS, "Folders"),  # 1
        (ICON_INVENTORY, "Inventory"),  # 2
        (ICON_MANAGE, "Manage"),  # 3
        (ICON_TESTING, "Testing"),  # 4
        (ICON_ACTIVITY, "Activity"),  # 5
    ]
    _BOTTOM: list[tuple[str, str]] = [
        (ICON_OPTIONS, "Options"),  # 6
        (ICON_ABOUT, "About"),  # 7
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(56)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 8)
        vbox.setSpacing(0)

        self._items: list[NavItem] = []

        for i, (icon, label) in enumerate(self._TOP):
            item = NavItem(icon, label, self)
            item.clicked.connect(lambda idx=i: self._select(idx))
            vbox.addWidget(item)
            self._items.append(item)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{SYS_STROKE_DIVIDER};border:none;")
        vbox.addWidget(sep)

        offset = len(self._TOP)
        for i, (icon, label) in enumerate(self._BOTTOM):
            item = NavItem(icon, label, self)
            item.clicked.connect(lambda idx=i + offset: self._select(idx))
            vbox.addWidget(item)
            self._items.append(item)

        vbox.addStretch()

        exit_item = NavItem(ICON_EXIT, "Exit", self)
        exit_item.clicked.connect(self.exit_requested)
        vbox.addWidget(exit_item)

        self._select(0, emit=False)

    def _select(self, index: int, emit: bool = True) -> None:
        for i, item in enumerate(self._items):
            item.set_active(i == index)
        if emit:
            self.page_changed.emit(index)

    def set_current(self, index: int) -> None:
        """Update active item without emitting — used by back navigation."""
        self._select(index, emit=False)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(SYS_BG_SECONDARY))
        p.end()
