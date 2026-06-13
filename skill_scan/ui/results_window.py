import json
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QSplitter, QTextEdit, QVBoxLayout, QWidget,
)

from ..core.result_store import get_history, ScanResult

_SEV_COLORS = {
    "pass": "#22c55e",
    "low": "#facc15",
    "medium": "#fb923c",
    "high": "#ef4444",
    "critical": "#7c3aed",
    "error": "#6b7280",
}


class ResultsWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SkillScan — Results")
        self.setMinimumSize(720, 480)
        self._build_ui()
        self._refresh()

        # Auto-refresh when shown
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(3000)

    def _build_ui(self):
        root = QVBoxLayout(self)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter)

        # Left: history list
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Scan History"))
        self._list = QListWidget()
        self._list.setMinimumWidth(260)
        self._list.currentRowChanged.connect(self._on_select)
        left_layout.addWidget(self._list)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self._refresh)
        left_layout.addWidget(refresh_btn)
        splitter.addWidget(left)

        # Right: detail
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        self._header = QLabel("Select a scan to view details")
        self._header.setWordWrap(True)
        right_layout.addWidget(self._header)

        self._detail = QTextEdit()
        self._detail.setReadOnly(True)
        mono = QFont("Consolas", 10)
        self._detail.setFont(mono)
        right_layout.addWidget(self._detail)
        splitter.addWidget(right)
        splitter.setSizes([260, 460])

    def _refresh(self):
        current_row = self._list.currentRow()
        self._results = get_history()
        self._list.clear()
        for r in self._results:
            sev = r.severity_label
            color = _SEV_COLORS.get(sev, "#6b7280")
            badge = f"[{sev.upper():8s}]"
            item = QListWidgetItem(f"{badge}  {r.short_path}\n  {r.timestamp[:19]}")
            item.setForeground(QColor(color))
            self._list.addItem(item)
        if 0 <= current_row < self._list.count():
            self._list.setCurrentRow(current_row)

    def _on_select(self, row: int):
        if row < 0 or row >= len(self._results):
            return
        r = self._results[row]
        sev = r.severity_label
        color = _SEV_COLORS.get(sev, "#6b7280")
        self._header.setText(
            f'<b style="color:{color}">{sev.upper()}</b> &nbsp; '
            f'{r.path} &nbsp; <small>{r.timestamp[:19]}</small>'
        )
        self._header.setTextFormat(Qt.TextFormat.RichText)

        if r.parsed:
            text = json.dumps(r.parsed, indent=2)
        else:
            text = r.stdout or r.stderr or "(no output)"
        self._detail.setPlainText(text)

    def showEvent(self, event):
        super().showEvent(event)
        self._refresh()
