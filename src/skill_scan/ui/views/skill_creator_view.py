"""Skill Creator view — stub for Phase 5 implementation."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from .._palette import ANCHOR, LIGHT_CANVAS, MUTED_TEXT


class SkillCreatorView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {ANCHOR};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(8)

        heading = QLabel("Create")
        heading.setStyleSheet(
            f"color:{LIGHT_CANVAS};font-size:20px;font-weight:700;background:transparent;"
        )
        layout.addWidget(heading)

        sub = QLabel(
            "Metadata form + SKILL.md editor with spec validation and AI Review.\n"
            "Full Skill Creator — Phase 5."
        )
        sub.setStyleSheet(f"color:{MUTED_TEXT};font-size:13px;background:transparent;")
        sub.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(sub)
        layout.addStretch()
