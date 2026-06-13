"""Periodic clipboard monitor — emits scan_requested when content changes and exceeds threshold."""
import hashlib

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QApplication


class ClipboardWatcher(QObject):
    scan_requested = pyqtSignal(str)  # emits clipboard text when a new, large-enough payload appears

    def __init__(self, parent=None):
        super().__init__(parent)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._check)
        self._last_hash = ""
        self._min_chars = 200

    def configure(self, enabled: bool, interval_secs: int, min_chars: int) -> None:
        self._min_chars = max(1, min_chars)
        interval_ms = max(5, interval_secs) * 1000
        if enabled:
            self._timer.start(interval_ms)
        else:
            self._timer.stop()

    def _check(self) -> None:
        app = QApplication.instance()
        if app is None:
            return
        text = app.clipboard().text()
        if len(text) < self._min_chars:
            return
        h = hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()
        if h == self._last_hash:
            return
        self._last_hash = h
        self.scan_requested.emit(text)
