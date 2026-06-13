"""About view — migrated from AboutDialog, adapted for main window."""
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QVBoxLayout, QWidget,
)

from ... import __version__
from ...core import config as cfg
from .._palette import ACCENT, ANCHOR, LIGHT_CANVAS, MUTED_TEXT, SOFT_SURFACE
from .._widgets import card_divider

_RESOURCES = Path(__file__).parent.parent.parent / "resources"


def _scanner_version() -> str:
    try:
        return pkg_version("cisco-ai-skill-scanner")
    except PackageNotFoundError:
        return "not installed"


class AboutView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {ANCHOR};")
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(0)

        # ── Logo ──────────────────────────────────────────────────────────
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        logo_lbl.setStyleSheet("background:transparent;")
        logo_path = _RESOURCES / "logo.png"
        if logo_path.exists():
            px = QPixmap(str(logo_path)).scaled(
                96, 96,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_lbl.setPixmap(px)
        else:
            logo_lbl.setText("⬡")
            logo_lbl.setStyleSheet(f"font-size:56px;color:{ACCENT};background:transparent;")
        root.addWidget(logo_lbl)
        root.addSpacing(14)

        # ── Title wordmark ─────────────────────────────────────────────────
        title = QLabel(
            f"<span style='color:{LIGHT_CANVAS};letter-spacing:3px;'>SKILL</span>"
            f"<span style='color:{ACCENT};letter-spacing:3px;'>SCAN</span>"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setStyleSheet("font-size:22px;font-weight:700;background:transparent;")
        root.addWidget(title)
        root.addSpacing(20)

        root.addWidget(card_divider())
        root.addSpacing(20)

        # ── Info rows ─────────────────────────────────────────────────────
        c = cfg.load()
        provider = c.get("llm_provider", "—")
        model = c.get("llm_model", "") or "—"

        rows = [
            ("SkillScan", f"v{__version__}"),
            ("Cisco AI Defense Skill Scanner:", f"v{_scanner_version()}"),
            ("LLM Provider:", provider),
            ("Model:", model),
        ]

        for label, value in rows:
            row_w = QWidget()
            row_w.setStyleSheet("background:transparent;")
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color:{LIGHT_CANVAS};font-size:12px;background:transparent;")
            val = QLabel(value)
            val.setStyleSheet(f"color:{MUTED_TEXT};font-size:12px;background:transparent;")
            val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            row_l.addWidget(lbl)
            row_l.addStretch()
            row_l.addWidget(val)
            root.addWidget(row_w)

        root.addStretch()

        # ── Attribution ────────────────────────────────────────────────────
        powered = QLabel(
            f"Powered by the "
            f"<a href='https://github.com/cisco-ai-defense/skill-scanner' "
            f"style='color:{SOFT_SURFACE};'>"
            f"Cisco AI Defense Skill Scanner</a>"
        )
        powered.setOpenExternalLinks(True)
        powered.setAlignment(Qt.AlignmentFlag.AlignCenter)
        powered.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:11px;background:transparent;"
        )
        root.addWidget(powered)

        attrib = QLabel(
            "Test skills sourced from "
            f"<a href='https://github.com/cisco-ai-defense/skill-scanner' "
            f"style='color:{SOFT_SURFACE};'>cisco-ai-defense/skill-scanner</a> "
            f"(<a href='https://www.apache.org/licenses/LICENSE-2.0' "
            f"style='color:{SOFT_SURFACE};'>Apache 2.0</a>) © 2026 Cisco Systems, Inc."
        )
        attrib.setOpenExternalLinks(True)
        attrib.setWordWrap(True)
        attrib.setAlignment(Qt.AlignmentFlag.AlignCenter)
        attrib.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:9px;margin-top:4px;background:transparent;"
        )
        root.addWidget(attrib)
        root.addSpacing(8)
