"""Inventory view — stub for Phase 9 implementation."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .._palette import SYS_BG_SECONDARY, SYS_TXT_PRIMARY, SYS_TXT_MUTED


class InventoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("inventoryViewRoot")
        self.setStyleSheet(f"#inventoryViewRoot {{ background: {SYS_BG_SECONDARY}; }}")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(8)

        heading = QLabel("Inventory")
        heading.setStyleSheet(
            f"color:{SYS_TXT_PRIMARY};font-size:20px;font-weight:700;background:transparent;"
        )
        layout.addWidget(heading)

        sub = QLabel(
            "Table view of all tracked skills with spec score, severity, and trust status.\n"
            "AI BOM export — Phase 9."
        )
        sub.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;"
        )
        sub.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(sub)
        layout.addStretch()
