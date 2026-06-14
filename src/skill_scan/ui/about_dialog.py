from importlib.metadata import version as pkg_version, PackageNotFoundError
from pathlib import Path

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..core import config as cfg
from ._palette import (
    ACCENT,
    HOVER_FOCUS,
    LIGHT_CANVAS,
    MUTED_TEXT,
    SOFT_SURFACE,
)
from ._widgets import RoundedCard, card_divider

_RESOURCES = Path(__file__).parent.parent / "resources"


def _scanner_version() -> str:
    try:
        return pkg_version("cisco-ai-skill-scanner")
    except PackageNotFoundError:
        return "not installed"


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(420)
        self.setMinimumHeight(572)
        self._drag_pos: QPoint | None = None
        self._build_ui()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, _e):
        self._drag_pos = None

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)

        card = RoundedCard(radius=18, parent=self)
        inner = QVBoxLayout(card)
        inner.setContentsMargins(28, 28, 28, 16)
        inner.setSpacing(0)

        # ── Logo ──────────────────────────────────────────────────────────
        logo_lbl = QLabel()
        logo_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_path = _RESOURCES / "logo.png"
        if logo_path.exists():
            px = QPixmap(str(logo_path)).scaled(
                120,
                120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            logo_lbl.setPixmap(px)
        else:
            logo_lbl.setText("⬡")
            logo_lbl.setStyleSheet(f"font-size:64px;color:{ACCENT};")
        inner.addWidget(logo_lbl)
        inner.addSpacing(16)

        # ── Title ─────────────────────────────────────────────────────────
        title = QLabel(
            f"<span style='color:{LIGHT_CANVAS};letter-spacing:2px;'>SKILL</span>"
            f"<span style='color:{ACCENT};letter-spacing:2px;'>SCAN</span>"
        )
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:22px;font-weight:700;")
        inner.addWidget(title)
        inner.addSpacing(16)

        inner.addWidget(card_divider())
        inner.addSpacing(16)

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

        rows_widget = QWidget()
        rows_layout = QVBoxLayout(rows_widget)
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_layout.setSpacing(8)
        for label, value in rows:
            row_w = QWidget()
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color:{LIGHT_CANVAS};font-size:12px;")
            val = QLabel(value)
            val.setStyleSheet(f"color:{MUTED_TEXT};font-size:12px;")
            val.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
            row_l.addWidget(lbl)
            row_l.addStretch()
            row_l.addWidget(val)
            rows_layout.addWidget(row_w)
        inner.addWidget(rows_widget)

        # Push OK + attribution to bottom
        inner.addStretch(1)

        # ── OK button ─────────────────────────────────────────────────────
        ok_btn = QPushButton("OK")
        ok_btn.setFixedWidth(120)
        ok_btn.setFixedHeight(36)
        ok_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ACCENT}; color: {LIGHT_CANVAS};
                border: none; border-radius: 8px;
                font-weight: 600; font-size: 13px;
            }}
            QPushButton:hover   {{ background-color: {HOVER_FOCUS}; }}
            QPushButton:pressed {{ background-color: {HOVER_FOCUS}; }}
        """)
        ok_btn.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(ok_btn)
        btn_row.addStretch()
        inner.addLayout(btn_row)

        inner.addSpacing(32)

        # ── Attribution (pinned to bottom, 16 px from card edge) ──────────
        powered = QLabel(
            f"Powered by the "
            f"<a href='https://github.com/cisco-ai-defense/skill-scanner' "
            f"style='color:{SOFT_SURFACE};'>"
            f"Cisco AI Defense Skill Scanner</a>"
        )
        powered.setOpenExternalLinks(True)
        powered.setAlignment(Qt.AlignmentFlag.AlignCenter)
        powered.setStyleSheet(f"color:{MUTED_TEXT};font-size:11px;")
        inner.addWidget(powered)

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
        attrib.setStyleSheet(f"color:{MUTED_TEXT};font-size:9px;margin-top:4px;")
        inner.addWidget(attrib)

        outer.addWidget(card)
