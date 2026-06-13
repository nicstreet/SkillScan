"""Inventory view — stub for Phase 9 implementation."""
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .._palette import ANCHOR, LIGHT_CANVAS, MUTED_TEXT


class InventoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {ANCHOR};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(8)

        heading = QLabel("Inventory")
        heading.setStyleSheet(
            f"color:{LIGHT_CANVAS};font-size:20px;font-weight:700;background:transparent;"
        )
        layout.addWidget(heading)

        sub = QLabel(
            "Table view of all tracked skills with spec score, severity, and trust status.\n"
            "AI BOM export — Phase 9."
        )
        sub.setStyleSheet(f"color:{MUTED_TEXT};font-size:13px;background:transparent;")
        sub.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(sub)
        layout.addStretch()
