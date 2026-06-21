"""Skill Competence Builder view - bundle skills and let Claude generate a working app."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .._palette import SYS_TXT_MUTED, SYS_TXT_PRIMARY


class SkillCompetenceView(QWidget):
    """Skill Competence Builder placeholder view."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = QLabel("Skill Competence Builder")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color:{SYS_TXT_PRIMARY};font-size:18px;font-weight:600;")

        sub = QLabel(
            "Bundle a set of skills and ask Claude to build a documented app from them\n"
            "Coming soon"
        )
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:13px;")

        lay.addWidget(title)
        lay.addSpacing(8)
        lay.addWidget(sub)
