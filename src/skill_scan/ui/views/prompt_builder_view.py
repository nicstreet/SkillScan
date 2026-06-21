"""Prompt Builder view - compose and refine AI prompts using loaded skills."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .._palette import SYS_TXT_MUTED, SYS_TXT_PRIMARY


class PromptBuilderView(QWidget):
    """AI Prompt Builder placeholder view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("AI Prompt Builder")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color:{SYS_TXT_PRIMARY};font-size:18px;font-weight:600;")

        sub = QLabel(
            "Compose and refine AI prompts using your loaded skills\nComing soon"
        )
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:13px;")

        lay.addWidget(title)
        lay.addSpacing(8)
        lay.addWidget(sub)
