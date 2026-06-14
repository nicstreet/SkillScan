"""Drop zone strip that docks flush against the Windows taskbar edge."""

import ctypes
import ctypes.wintypes as wintypes
from pathlib import Path

from PyQt6.QtCore import (
    QEasingCurve,
    QPropertyAnimation,
    Qt,
    pyqtProperty,
    pyqtSignal,
)
from PyQt6.QtGui import QColor, QPainter, QFont
from PyQt6.QtWidgets import QApplication, QWidget

# ---------------------------------------------------------------------------
# Win32 helpers
# ---------------------------------------------------------------------------

_ABM_GETTASKBARPOS = 0x00000005
_ABE_LEFT, _ABE_TOP, _ABE_RIGHT, _ABE_BOTTOM = 0, 1, 2, 3


class _APPBARDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uCallbackMessage", wintypes.UINT),
        ("uEdge", wintypes.UINT),
        ("rc", wintypes.RECT),
        ("lParam", wintypes.LPARAM),
    ]


def _taskbar_info() -> tuple[int, wintypes.RECT]:
    """Return (edge, RECT) for the Windows taskbar."""
    abd = _APPBARDATA()
    abd.cbSize = ctypes.sizeof(_APPBARDATA)
    ctypes.windll.shell32.SHAppBarMessage(_ABM_GETTASKBARPOS, ctypes.byref(abd))
    return abd.uEdge, abd.rc


# ---------------------------------------------------------------------------
# Dock widget
# ---------------------------------------------------------------------------

_COLLAPSED_THICKNESS = 6  # px — the thin sliver when idle
_EXPANDED_THICKNESS = 56  # px — height/width when a drag is over it


class TaskbarDock(QWidget):
    """Slim strip docked to the taskbar edge; accepts skill folder drops."""

    scan_requested = pyqtSignal(str)

    def __init__(self, color: str = "#0ea5e9", parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)

        self._color = QColor(color)
        self._drag_over = False
        self._thickness: float = _COLLAPSED_THICKNESS

        self._anim = QPropertyAnimation(self, b"thickness", self)
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._edge = _ABE_BOTTOM
        self._snap()

    # ------------------------------------------------------------------
    # Qt property for thickness animation
    @pyqtProperty(float)
    def thickness(self) -> float:
        return self._thickness

    @thickness.setter
    def thickness(self, v: float) -> None:
        self._thickness = v
        self._apply_geometry()
        self.update()

    # ------------------------------------------------------------------
    def setOnColor(self, color: str) -> None:
        self._color = QColor(color)
        self.update()

    def _snap(self) -> None:
        """Position flush against the taskbar edge."""
        self._edge, rc = _taskbar_info()
        screen = QApplication.primaryScreen().geometry()
        # Win32 SHAppBarMessage returns physical pixels; Qt setGeometry uses
        # logical pixels. Divide by devicePixelRatio to correct for DPI scaling.
        dpr = QApplication.primaryScreen().devicePixelRatio()
        tb_left = int(rc.left / dpr)
        tb_top = int(rc.top / dpr)
        tb_right = int(rc.right / dpr)
        tb_bottom = int(rc.bottom / dpr)

        if self._edge == _ABE_BOTTOM:
            self.setGeometry(
                screen.left(),
                tb_top - _COLLAPSED_THICKNESS,
                screen.width(),
                _COLLAPSED_THICKNESS,
            )
        elif self._edge == _ABE_TOP:
            self.setGeometry(
                screen.left(), tb_bottom, screen.width(), _COLLAPSED_THICKNESS
            )
        elif self._edge == _ABE_LEFT:
            self.setGeometry(
                tb_right, screen.top(), _COLLAPSED_THICKNESS, screen.height()
            )
        else:  # RIGHT
            self.setGeometry(
                tb_left - _COLLAPSED_THICKNESS,
                screen.top(),
                _COLLAPSED_THICKNESS,
                screen.height(),
            )

    def _apply_geometry(self) -> None:
        """Resize the dock to the current animated thickness."""
        _, rc = _taskbar_info()
        screen = QApplication.primaryScreen().geometry()
        dpr = QApplication.primaryScreen().devicePixelRatio()
        tb_left = int(rc.left / dpr)
        tb_top = int(rc.top / dpr)
        tb_right = int(rc.right / dpr)
        tb_bottom = int(rc.bottom / dpr)
        t = int(self._thickness)

        if self._edge == _ABE_BOTTOM:
            self.setGeometry(screen.left(), tb_top - t, screen.width(), t)
        elif self._edge == _ABE_TOP:
            self.setGeometry(screen.left(), tb_bottom, screen.width(), t)
        elif self._edge == _ABE_LEFT:
            self.setGeometry(tb_right, screen.top(), t, screen.height())
        else:
            self.setGeometry(tb_left - t, screen.top(), t, screen.height())

    def _expand(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._thickness)
        self._anim.setEndValue(float(_EXPANDED_THICKNESS))
        self._anim.start()

    def _collapse(self) -> None:
        self._anim.stop()
        self._anim.setStartValue(self._thickness)
        self._anim.setEndValue(float(_COLLAPSED_THICKNESS))
        self._anim.start()

    # ------------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._drag_over = True
            self._expand()

    def dragLeaveEvent(self, event):
        self._drag_over = False
        self._collapse()

    def dropEvent(self, event):
        self._drag_over = False
        self._collapse()
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            target = path if Path(path).is_dir() else str(Path(path).parent)
            self.scan_requested.emit(target)
            return

    # ------------------------------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)
        self._snap()  # re-snap in case taskbar moved since last shown

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        bg = QColor(self._color)
        bg.setAlpha(220 if self._drag_over else 180)
        p.setBrush(bg)
        p.setPen(Qt.PenStyle.NoPen)

        r = self.rect()

        # Round only the inward-facing corners
        if self._edge == _ABE_BOTTOM:
            p.drawRoundedRect(r.adjusted(0, 0, 0, 4), 6, 6)
        elif self._edge == _ABE_TOP:
            p.drawRoundedRect(r.adjusted(0, -4, 0, 0), 6, 6)
        elif self._edge == _ABE_LEFT:
            p.drawRoundedRect(r.adjusted(-4, 0, 0, 0), 6, 6)
        else:
            p.drawRoundedRect(r.adjusted(0, 0, 4, 0), 6, 6)

        if self._thickness >= _EXPANDED_THICKNESS * 0.7 and self._drag_over:
            p.setPen(QColor("white"))
            font = QFont("Segoe UI", 10, QFont.Weight.Medium)
            p.setFont(font)
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, "Drop Skill Folder")

        p.end()
