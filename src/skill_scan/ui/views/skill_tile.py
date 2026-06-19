"""SkillTile — card widget representing a single discovered skill or manifest."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .._palette import (
    SYS_ACTION_PRIMARY,
    SYS_BADGE_UNSAFE,
    SYS_CRITICAL_BG,
    SYS_BG_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_BG_WARNING,
    SYS_STROKE_DIVIDER,
    SYS_BORDER_WARNING,
    SYS_TXT_PRIMARY,
    SYS_TXT_SECONDARY,
    SYS_BORDER_ADVISORY,
    SYS_TXT_MUTED,
    SYS_BADGE_SAFE,
    SYS_BORDER_LOW,
    SYS_TILE_BG_UNSCANNED,
    SYS_TILE_BG_HOVER,
)

TILE_H = 140  # fixed height; width is set responsively by FlowContainer
_TILE_BG = SYS_TILE_BG_UNSCANNED
_TILE_BG_HV = SYS_TILE_BG_HOVER
_SEC_TEXT = SYS_TXT_SECONDARY
_BADGE_BG = SYS_BG_SECONDARY

_SEVERITY_COLOUR: dict[Optional[str], str] = {
    None: SYS_STROKE_DIVIDER,
    "clean": SYS_BADGE_SAFE,
    "safe": SYS_BADGE_SAFE,
    "low": SYS_BORDER_LOW,
    "medium": SYS_BORDER_ADVISORY,
    "high": SYS_BORDER_WARNING,
    "critical": SYS_BADGE_UNSAFE,
    "unknown": SYS_TXT_MUTED,
}

_SEV_BADGE_TEXT = {
    "critical": "P1  CRITICAL",
    "high": "P2  WARNING",
    "medium": "P3  ADVISORY",
    "low": "P3  ADVISORY",
    "clean": "CLEAN",
    "safe": "CLEAN",
    "unknown": "UNKNOWN",
}

_TYPE_LABEL = {"skill": "SKILL", "mcp": "MCP", "a2a": "A2A", "unknown": "?"}

_FIND_SEV_ORDER = ["critical", "high", "medium", "low", "info"]
_FIND_SEV_COLOUR = {
    "critical": SYS_BADGE_UNSAFE,
    "high": SYS_BORDER_WARNING,
    "medium": SYS_BORDER_ADVISORY,
    "low": SYS_BORDER_LOW,
    "info": SYS_TXT_MUTED,
    "unknown": SYS_TXT_MUTED,
}

# Shared badge geometry — matches _BADGE_H in skill_detail_view for visual consistency
_NB = (
    "font-size:8px;font-weight:700;padding:1px;" "border-radius:4px;letter-spacing:1px;"
)
_NB_UNSAFE = (
    "font-size:8px;font-weight:700;padding:1px 4px;"
    "border-radius:4px;letter-spacing:1px;"
)


@dataclass
class SkillInfo:
    skill_id: int
    path: str
    name: str
    spec_type: str  # "skill" / "mcp" / "a2a" / "unknown"
    description: str
    trusted: bool
    severity: Optional[str]  # None = never scanned
    is_safe: bool
    last_scanned: Optional[datetime]
    n_results: int = 0
    n_analyzers: int = 0
    llm_skipped: bool = False
    findings: list = field(default_factory=list)  # [{severity, category}]


class SkillTile(QFrame):
    scan_requested = pyqtSignal(int, str)  # (skill_id, scan_dir)
    detail_requested = pyqtSignal(int)  # skill_id
    trust_toggled = pyqtSignal(int, bool)  # (skill_id, new_trusted)
    open_folder_requested = pyqtSignal(str)  # folder path

    def __init__(self, info: SkillInfo, compact: bool = False, parent=None):
        super().__init__(parent)
        self._info = info
        self._compact = compact
        self._hovered = False
        self.setObjectName("SkillTile")
        self.setFixedHeight(TILE_H)
        self.setMinimumWidth(220)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui()
        self._apply_border()

    # ── Compact mode ─────────────────────────────────────────────────────────

    @property
    def _nb(self) -> str:
        """Badge base style — 25% smaller in compact (medium) mode."""
        if self._compact:
            return (
                "font-size:8px;font-weight:700;padding:1px 6px;"
                "border-radius:3px;letter-spacing:1px;"
            )
        return _NB

    def set_compact(self, compact: bool) -> None:
        if self._compact == compact:
            return
        self._compact = compact
        self._refresh_labels()

    # ── Construction ─────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 2, 4, 4)
        root.setSpacing(0)

        # ── Row 1: type badge (left) · name (right) ──────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.setContentsMargins(0, 0, 0, 0)

        self._type_lbl = QLabel(_TYPE_LABEL.get(self._info.spec_type, "?"))
        self._type_lbl.setStyleSheet(
            f"{_NB}color:{SYS_TXT_PRIMARY};"
            f"background:{SYS_ACTION_PRIMARY};border:1px solid {SYS_BG_PRIMARY};"
        )
        self._type_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        row1.addWidget(self._type_lbl, 0, Qt.AlignmentFlag.AlignVCenter)

        self._name_lbl = QLabel(self._info.name)
        self._name_lbl.setStyleSheet(
            f"color:{SYS_TXT_PRIMARY};font-size:12px;font-weight:700;"
            f"background:transparent;border:none;"
        )
        self._name_lbl.setWordWrap(True)
        self._name_lbl.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        )
        row1.addWidget(self._name_lbl, 1, Qt.AlignmentFlag.AlignVCenter)

        root.addLayout(row1)
        root.addSpacing(4)

        hdiv1 = QFrame()
        hdiv1.setFrameShape(QFrame.Shape.HLine)
        hdiv1.setFixedHeight(1)
        hdiv1.setStyleSheet(f"background:{SYS_STROKE_DIVIDER};border:none;")
        root.addWidget(hdiv1)
        root.addSpacing(4)

        # ── Row 2: results · analyzers ──────────────────────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(4)
        row2.setContentsMargins(0, 0, 0, 0)

        self._results_lbl = QLabel("—")
        self._results_lbl.setStyleSheet(
            f"{_NB}color:{SYS_TXT_PRIMARY};background:{SYS_BG_SECONDARY};border:1px solid {SYS_BG_PRIMARY};"
        )
        self._results_lbl.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        row2.addWidget(self._results_lbl)

        self._analyzers_lbl = QLabel("—")
        self._analyzers_lbl.setStyleSheet(
            f"{_NB}color:{SYS_TXT_PRIMARY};background:{SYS_BG_SECONDARY};border:1px solid {SYS_BG_PRIMARY};"
        )
        self._analyzers_lbl.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        row2.addWidget(self._analyzers_lbl)
        row2.addStretch()
        root.addLayout(row2)
        root.addSpacing(4)

        # ── Row 3: unsafe · severity ─────────────────────────────────────────
        row3 = QHBoxLayout()
        row3.setSpacing(6)
        row3.setContentsMargins(0, 0, 0, 0)

        self._unsafe_lbl = QLabel("UNSAFE")
        self._unsafe_lbl.setStyleSheet(
            f"{_NB_UNSAFE}color:{SYS_BADGE_UNSAFE};background:{SYS_CRITICAL_BG};"
            f"border:1px solid {SYS_BADGE_UNSAFE};"
        )
        self._unsafe_lbl.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self._unsafe_lbl.setVisible(False)
        row3.addWidget(self._unsafe_lbl)

        self._sev_lbl = QLabel("")
        self._sev_lbl.setStyleSheet(
            f"{_NB}color:{SYS_TXT_MUTED};background:transparent;border:none;"
        )
        self._sev_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        row3.addWidget(self._sev_lbl)
        row3.addStretch()
        root.addLayout(row3)
        root.addSpacing(4)

        # ── Row 4: description ───────────────────────────────────────────────
        self._desc_lbl = QLabel(self._info.description or "No description")
        self._desc_lbl.setStyleSheet(
            f"color:{_SEC_TEXT};font-size:10px;background:transparent;"
            f"border:none;line-height:140%;"
        )
        self._desc_lbl.setWordWrap(True)
        self._desc_lbl.setMaximumHeight(48)
        root.addWidget(self._desc_lbl)
        root.addSpacing(4)

        # ── Row 5: findings severity row ─────────────────────────────────────
        self._findings_section = QWidget()
        self._findings_section.setStyleSheet("background:transparent;")
        self._findings_section.setMaximumHeight(18)
        fs_layout = QVBoxLayout(self._findings_section)
        fs_layout.setContentsMargins(0, 0, 0, 0)
        fs_layout.setSpacing(0)

        self._sev_row_lbl = QLabel()
        self._sev_row_lbl.setWordWrap(True)
        self._sev_row_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._sev_row_lbl.setStyleSheet(
            "background:transparent;border:none;font-size:10px;font-weight:700;"
        )
        fs_layout.addWidget(self._sev_row_lbl)

        self._findings_section.setVisible(False)
        root.addWidget(self._findings_section)

        self._refresh_labels()

    # ── Label refresh ─────────────────────────────────────────────────────────

    def _refresh_labels(self) -> None:
        nb = self._nb
        sev_fs = "8px" if self._compact else "10px"

        # Apply badge styles (all scale with compact mode)
        _badge_neutral = f"{nb}color:{SYS_TXT_PRIMARY};background:{SYS_ACTION_PRIMARY};border:1px solid {SYS_BG_PRIMARY};"
        _badge_data = f"{nb}color:{SYS_TXT_PRIMARY};background:{SYS_BG_SECONDARY};border:1px solid {SYS_BG_PRIMARY};"
        self._type_lbl.setStyleSheet(_badge_neutral)
        self._results_lbl.setStyleSheet(_badge_data)
        self._analyzers_lbl.setStyleSheet(_badge_data)
        self._unsafe_lbl.setStyleSheet(
            f"{_NB_UNSAFE}color:{SYS_BADGE_UNSAFE};background:{SYS_CRITICAL_BG};"
            f"border:1px solid {SYS_BADGE_UNSAFE};"
        )
        self._sev_row_lbl.setStyleSheet(
            f"background:transparent;border:none;font-size:{sev_fs};font-weight:700;"
        )

        sev = self._info.severity
        sev_lower = (sev or "").lower()
        color = _SEVERITY_COLOUR.get(sev_lower, SYS_TXT_MUTED)

        if sev is None:
            self._results_lbl.setText("—")
            self._analyzers_lbl.setText("—")
            self._unsafe_lbl.setVisible(False)
            self._sev_lbl.setText("")
            self._sev_lbl.setStyleSheet(
                f"{nb}color:{SYS_TXT_MUTED};background:transparent;border:none;"
            )
            self._findings_section.setVisible(False)
        else:
            n = self._info.n_results
            self._results_lbl.setText(f"{n} RESULT{'S' if n != 1 else ''}")
            na = self._info.n_analyzers
            self._analyzers_lbl.setText(
                f"{na} ANALYZER{'S' if na != 1 else ''}" if na else "— ANALYZERS"
            )

            self._unsafe_lbl.setVisible(not self._info.is_safe)

            badge_text = _SEV_BADGE_TEXT.get(sev_lower, sev_lower.upper())
            if sev_lower == "critical":
                self._sev_lbl.setStyleSheet(
                    f"{nb}color:{SYS_BADGE_UNSAFE};background:{SYS_CRITICAL_BG};"
                    f"border:1px solid {SYS_BADGE_UNSAFE};"
                )
            elif sev_lower == "high":
                self._sev_lbl.setStyleSheet(
                    f"{nb}color:{SYS_TXT_PRIMARY};background:{SYS_BORDER_WARNING};"
                    f"border:1px solid {SYS_BG_PRIMARY};"
                )
            elif sev_lower in ("clean", "safe"):
                self._sev_lbl.setStyleSheet(
                    f"{nb}color:{SYS_BADGE_SAFE};background:{SYS_BG_WARNING};"
                    f"border:1px solid {SYS_BADGE_SAFE};"
                )
            else:
                self._sev_lbl.setStyleSheet(
                    f"{nb}color:{color};background:transparent;"
                    f"border:1px solid {color};"
                )
            self._sev_lbl.setText(badge_text)

            self._rebuild_findings()

    def _rebuild_findings(self) -> None:
        findings = self._info.findings
        if not findings:
            self._findings_section.setVisible(False)
            return

        counts: dict[str, int] = {}
        for f in findings:
            s = (f.get("severity") or "unknown").lower()
            counts[s] = counts.get(s, 0) + 1

        _ORDER = ["critical", "high", "medium", "low"]
        _COLOURS = {
            "critical": SYS_BADGE_UNSAFE,
            "high": SYS_BORDER_WARNING,
            "medium": SYS_BORDER_ADVISORY,
            "low": SYS_BORDER_LOW,
        }

        parts = [
            f'<span style="color:{_COLOURS.get(s, SYS_TXT_MUTED)};">'
            f"{s.upper()}({counts[s]})</span>"
            for s in _ORDER
            if s in counts
        ]
        if not parts:
            self._findings_section.setVisible(False)
            return

        sep = f' <span style="color:{SYS_TXT_MUTED};font-weight:400;">-</span> '
        self._sev_row_lbl.setText(sep.join(parts))
        self._findings_section.setVisible(True)

    # ── Border ────────────────────────────────────────────────────────────────

    def _apply_border(self, hovered: bool = False) -> None:
        bg = _TILE_BG_HV if hovered else _TILE_BG
        self.setStyleSheet(
            f"QFrame#SkillTile{{background:{bg};border-radius:8px;border:1px solid {SYS_BG_PRIMARY};}}"
        )

    # ── Public refresh ────────────────────────────────────────────────────────

    def refresh(
        self,
        severity: Optional[str],
        is_safe: bool,
        last_scanned: Optional[datetime],
        trusted: bool,
        n_results: int = 0,
        n_analyzers: int = 0,
        llm_skipped: bool = False,
        findings: list | None = None,
    ) -> None:
        self._info.severity = severity
        self._info.is_safe = is_safe
        self._info.last_scanned = last_scanned
        self._info.trusted = trusted
        self._info.n_results = n_results
        self._info.n_analyzers = n_analyzers
        self._info.llm_skipped = llm_skipped
        if findings is not None:
            self._info.findings = findings
        self._refresh_labels()
        self._apply_border(self._hovered)
        self.update()

    # ── Hover overlay ─────────────────────────────────────────────────────────

    def enterEvent(self, e) -> None:
        self._hovered = True
        self._apply_border(hovered=True)
        self.update()
        super().enterEvent(e)

    def leaveEvent(self, e) -> None:
        self._hovered = False
        self._apply_border(hovered=False)
        self.update()
        super().leaveEvent(e)

    def paintEvent(self, e) -> None:
        super().paintEvent(e)
        if (
            self._hovered
            and self._info.severity is None
            and self._info.spec_type == "skill"
        ):
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.fillRect(self.rect(), QColor(13, 148, 136, 80))
            p.setPen(QColor(SYS_TXT_PRIMARY))
            p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "▶  Scan now")
            p.end()

    # ── Mouse / context menu ──────────────────────────────────────────────────

    def _scan_path(self) -> str:
        if self._info.spec_type == "skill":
            return str(Path(self._info.path).parent)
        return self._info.path

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            if (
                self._info.spec_type in ("skill", "mcp", "a2a")
                and self._info.severity is None
            ):
                self.scan_requested.emit(self._info.skill_id, self._scan_path())
            else:
                self.detail_requested.emit(self._info.skill_id)
        super().mousePressEvent(e)

    def contextMenuEvent(self, e) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{SYS_BG_SECONDARY};color:{SYS_TXT_PRIMARY};"
            f"border:1px solid {SYS_STROKE_DIVIDER};border-radius:6px;padding:4px;}}"
            f"QMenu::item{{padding:5px 20px;border-radius:4px;}}"
            f"QMenu::item:selected{{background:{SYS_ACTION_PRIMARY};}}"
            f"QMenu::separator{{height:1px;background:{SYS_STROKE_DIVIDER};margin:2px 8px;}}"
        )
        if self._info.spec_type in ("skill", "mcp", "a2a"):
            scan_act = menu.addAction("Scan")
            scan_act.triggered.connect(
                lambda: self.scan_requested.emit(self._info.skill_id, self._scan_path())
            )
            menu.addSeparator()
        open_act = menu.addAction("Open Folder")
        open_act.triggered.connect(
            lambda: self.open_folder_requested.emit(str(Path(self._info.path).parent))
        )
        copy_act = menu.addAction("Copy Path")
        copy_act.triggered.connect(
            lambda: QApplication.clipboard().setText(self._info.path)
        )
        menu.addSeparator()
        if self._info.trusted:
            t = menu.addAction("Revoke Trust")
            t.triggered.connect(
                lambda: self.trust_toggled.emit(self._info.skill_id, False)
            )
        elif self._info.is_safe:
            t = menu.addAction("Trust")
            t.triggered.connect(
                lambda: self.trust_toggled.emit(self._info.skill_id, True)
            )
        else:
            t = menu.addAction("Trust  (scan clean first)")
            t.setEnabled(False)
        menu.exec(e.globalPos())
