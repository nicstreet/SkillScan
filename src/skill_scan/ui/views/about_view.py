"""About view — migrated from AboutDialog, adapted for main window."""

from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ... import __version__
from ...core import config as cfg
from .._palette import (
    SYS_ACTION_PRIMARY,
    SYS_BG_PRIMARY,
    SYS_TXT_PRIMARY,
    SYS_TXT_MUTED,
    SYS_BORDER_LOW,
)
from .._widgets import card_divider

_RESOURCES = Path(__file__).parent.parent.parent / "resources"


def _scanner_version(pkg: str) -> str:
    try:
        return pkg_version(pkg)
    except PackageNotFoundError:
        return "not installed"


class AboutView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {SYS_BG_PRIMARY};")
        self._build_ui()

    def _build_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addStretch(1)

        centre = QWidget()
        centre.setStyleSheet(f"background: {SYS_BG_PRIMARY};")
        centre.setMinimumWidth(380)
        centre.setMaximumWidth(560)
        outer.addWidget(centre, 1)
        outer.addStretch(1)

        root = QVBoxLayout(centre)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(0)

        # ── Logo ──────────────────────────────────────────────────────────
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        logo_lbl.setStyleSheet("background:transparent;")
        logo_path = _RESOURCES / "logo.png"
        if logo_path.exists():
            px = QPixmap(str(logo_path)).scaled(
                96,
                96,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_lbl.setPixmap(px)
        else:
            logo_lbl.setText("⬡")
            logo_lbl.setStyleSheet(
                f"font-size:56px;color:{SYS_ACTION_PRIMARY};background:transparent;"
            )
        root.addWidget(logo_lbl)
        root.addSpacing(14)

        # ── Title wordmark ─────────────────────────────────────────────────
        title = QLabel(
            f"<span style='color:{SYS_TXT_PRIMARY};letter-spacing:3px;'>SKILL</span>"
            f"<span style='color:{SYS_ACTION_PRIMARY};letter-spacing:3px;'>SCAN</span>"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        title.setStyleSheet("font-size:22px;font-weight:700;background:transparent;")
        root.addWidget(title)
        root.addSpacing(20)

        root.addWidget(card_divider())
        root.addSpacing(20)

        # ── Info rows ─────────────────────────────────────────────────────
        c = cfg.load()
        from ...core.config import get_llm_creds

        inapp = get_llm_creds(c, "inapp")
        scanner = get_llm_creds(c, "scanner")
        inapp_label = f"{inapp['provider']} / {inapp['model'].split('/')[-1] or '—'}"
        scanner_label = (
            f"{scanner['provider']} / {scanner['model'].split('/')[-1] or '—'}"
        )

        rows = [
            ("SkillScan", f"v{__version__}"),
            ("Skill Scanner:", f"v{_scanner_version('cisco-ai-skill-scanner')}"),
            ("MCP Scanner:", f"v{_scanner_version('cisco-ai-mcp-scanner')}"),
            ("Skill Studio LLM:", inapp_label),
            ("Scanner LLM:", scanner_label),
        ]

        _lbl_style = f"color:{SYS_TXT_PRIMARY};font-size:11px;background:transparent;"
        _val_style = f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;"

        for label, value in rows:
            row_w = QWidget()
            row_w.setStyleSheet("background:transparent;")
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 2, 0, 2)
            lbl = QLabel(label)
            lbl.setStyleSheet(_lbl_style)
            val = QLabel(value)
            val.setStyleSheet(_val_style)
            val.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            row_l.addWidget(lbl)
            row_l.addStretch()
            row_l.addWidget(val)
            root.addWidget(row_w)

        root.addStretch()

        # ── Attribution ────────────────────────────────────────────────────
        powered = QLabel(
            f"Powered by the "
            f"<a href='https://github.com/cisco-ai-defense/skill-scanner' "
            f"style='color:{SYS_BORDER_LOW};'>"
            f"Cisco AI Defense Skill Scanner</a>"
        )
        powered.setOpenExternalLinks(True)
        powered.setAlignment(Qt.AlignmentFlag.AlignCenter)
        powered.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;"
        )
        root.addWidget(powered)

        attrib = QLabel(
            "Test skills sourced from "
            f"<a href='https://github.com/cisco-ai-defense/skill-scanner' "
            f"style='color:{SYS_BORDER_LOW};'>cisco-ai-defense/skill-scanner</a> "
            f"(<a href='https://www.apache.org/licenses/LICENSE-2.0' "
            f"style='color:{SYS_BORDER_LOW};'>Apache 2.0</a>) © 2026 Cisco Systems, Inc."
        )
        attrib.setOpenExternalLinks(True)
        attrib.setWordWrap(True)
        attrib.setAlignment(Qt.AlignmentFlag.AlignCenter)
        attrib.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:9px;margin-top:4px;background:transparent;"
        )
        root.addWidget(attrib)
        root.addSpacing(8)
