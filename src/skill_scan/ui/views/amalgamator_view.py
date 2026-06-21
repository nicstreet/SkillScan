"""Amalgamator view - merge multiple skills into an improved combined skill."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .._palette import SYS_TXT_MUTED, SYS_TXT_PRIMARY


class AmalgamatorView(QWidget):
    """Skill Amalgamator placeholder view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Skill Amalgamator")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color:{SYS_TXT_PRIMARY};font-size:18px;font-weight:600;")

        sub = QLabel(
            "Analyse multiple skills and synthesise an improved combined skill\nComing soon"
        )
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:13px;")

        lay.addWidget(title)
        lay.addSpacing(8)
        lay.addWidget(sub)
