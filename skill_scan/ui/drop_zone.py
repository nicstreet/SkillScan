"""Small always-on-top floating drop zone window, anchored to bottom-right."""
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget

_MARGIN = 16  # px gap from screen edge


class DropZone(QWidget):
    scan_requested = pyqtSignal(str)  # emits path to scan

    def __init__(self, color: str = "#0ea5e9", parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.setFixedSize(180, 120)
        self._accent = QColor(color)
        self._drag_over = False
        self._drag_pos: QPoint | None = None

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._label = QLabel("⬇  Drop Skill\nFolder Here")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet(
            "color: white; font-size: 14px; font-weight: 600; background: transparent;"
        )
        layout.addWidget(self._label)

    def setOnColor(self, color: str) -> None:
        self._accent = QColor(color)
        self.update()

    def _snap_to_bottom_right(self) -> None:
        """Position in the bottom-right corner of the available work area."""
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.right()  - self.width()  - _MARGIN,
            screen.bottom() - self.height() - _MARGIN,
        )

    # ------------------------------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)
        self._snap_to_bottom_right()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._drag_over:
            bg = QColor(self._accent)
            bg.setAlpha(230)
        else:
            bg = QColor("#1e293b")
            bg.setAlpha(210)
        painter.setBrush(bg)
        border = QColor(self._accent) if not self._drag_over else QColor("white")
        painter.setPen(QPen(border, 2))
        painter.drawRoundedRect(self.rect().adjusted(2, 2, -2, -2), 12, 12)

    # ------------------------------------------------------------------
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._drag_over = True
            self.update()

    def dragLeaveEvent(self, event):
        self._drag_over = False
        self.update()

    def dropEvent(self, event):
        self._drag_over = False
        self.update()
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).is_dir():
                self.scan_requested.emit(path)
                return
        # If a file was dropped, use its parent directory
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            self.scan_requested.emit(str(Path(path).parent))
            return

    # ------------------------------------------------------------------
    # Dragging the window itself
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
