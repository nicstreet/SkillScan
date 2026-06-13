"""SkillTile — card widget representing a single discovered skill or manifest."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QMenu,
    QSizePolicy, QVBoxLayout, QWidget,
)

from .._palette import (
    ACCENT, ANCHOR, CRITICAL_ACCENT, CRITICAL_BG, DEEP_SURFACE, DIVIDER,
    HIGH_ACCENT, LIGHT_CANVAS, MEDIUM_ACCENT, MUTED_TEXT,
    SAFE_ACCENT, SOFT_SURFACE,
)

TILE_H = 192          # fixed height; width is set responsively by FlowContainer
_TILE_BG    = "#475569"
_TILE_BG_HV = "#3D4D5E"
_SEC_TEXT   = "#CBD5E1"
_BADGE_BG   = DEEP_SURFACE

_SEVERITY_COLOUR: dict[Optional[str], str] = {
    None:       DIVIDER,
    "clean":    SAFE_ACCENT,
    "safe":     SAFE_ACCENT,
    "low":      SOFT_SURFACE,
    "medium":   MEDIUM_ACCENT,
    "high":     HIGH_ACCENT,
    "critical": CRITICAL_ACCENT,
    "unknown":  MUTED_TEXT,
}

_SEV_BADGE_TEXT = {
    "critical": "P1  CRITICAL",
    "high":     "P2  WARNING",
    "medium":   "P3  ADVISORY",
    "low":      "P3  ADVISORY",
    "clean":    "CLEAN",
    "safe":     "CLEAN",
    "unknown":  "UNKNOWN",
}

_TYPE_LABEL = {"skill": "SKILL", "mcp": "MCP", "a2a": "A2A", "unknown": "?"}

_FIND_SEV_ORDER  = ["critical", "high", "medium", "low", "info"]
_FIND_SEV_COLOUR = {
    "critical": CRITICAL_ACCENT,
    "high":     HIGH_ACCENT,
    "medium":   MEDIUM_ACCENT,
    "low":      SOFT_SURFACE,
    "info":     MUTED_TEXT,
    "unknown":  MUTED_TEXT,
}

# Shared badge geometry — matches _BADGE_H in skill_detail_view for visual consistency
_NB = (
    "font-size:10px;font-weight:700;padding:3px 8px;"
    "border-radius:4px;letter-spacing:1px;"
)


@dataclass
class SkillInfo:
    skill_id: int
    path: str
    name: str
    spec_type: str              # "skill" / "mcp" / "a2a" / "unknown"
    description: str
    trusted: bool
    severity: Optional[str]    # None = never scanned
    is_safe: bool
    last_scanned: Optional[datetime]
    n_results: int = 0
    n_analyzers: int = 0
    llm_skipped: bool = False
    findings: list = field(default_factory=list)   # [{severity, category}]


class SkillTile(QFrame):
    scan_requested        = pyqtSignal(int, str)   # (skill_id, scan_dir)
    detail_requested      = pyqtSignal(int)        # skill_id
    trust_toggled         = pyqtSignal(int, bool)  # (skill_id, new_trusted)
    open_folder_requested = pyqtSignal(str)        # folder path

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
            return ("font-size:8px;font-weight:700;padding:2px 6px;"
                    "border-radius:3px;letter-spacing:1px;")
        return _NB

    def set_compact(self, compact: bool) -> None:
        if self._compact == compact:
            return
        self._compact = compact
        self._refresh_labels()

    # ── Construction ─────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(0)

        # ── Row 1: name (left) · type badge (right) ──────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.setContentsMargins(0, 0, 0, 0)

        self._name_lbl = QLabel(self._info.name)
        self._name_lbl.setStyleSheet(
            f"color:{LIGHT_CANVAS};font-size:13px;font-weight:700;"
            f"background:transparent;border:none;"
        )
        self._name_lbl.setWordWrap(True)
        row1.addWidget(self._name_lbl, 1, Qt.AlignmentFlag.AlignTop)

        self._type_lbl = QLabel(_TYPE_LABEL.get(self._info.spec_type, "?"))
        self._type_lbl.setStyleSheet(
            f"{_NB}color:{_SEC_TEXT};"
            f"background:{_BADGE_BG};border:1px solid #334155;"
        )
        self._type_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        row1.addWidget(self._type_lbl, 0, Qt.AlignmentFlag.AlignTop)

        root.addLayout(row1)
        root.addSpacing(8)

        # ── Row 2: [results · analyzers] left | [unsafe · severity] right ────
        meta_row = QHBoxLayout()
        meta_row.setSpacing(0)
        meta_row.setContentsMargins(0, 0, 0, 0)
        meta_row.setAlignment(Qt.AlignmentFlag.AlignTop)

        left_col = QVBoxLayout()
        left_col.setSpacing(8)
        left_col.setContentsMargins(0, 0, 0, 0)

        self._results_lbl = QLabel("—")
        self._results_lbl.setStyleSheet(
            f"{_NB}color:{_SEC_TEXT};background:{_BADGE_BG};border:1px solid #334155;"
        )
        self._results_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        left_col.addWidget(self._results_lbl)

        self._analyzers_lbl = QLabel("—")
        self._analyzers_lbl.setStyleSheet(
            f"{_NB}color:{_SEC_TEXT};background:{_BADGE_BG};border:1px solid #334155;"
        )
        self._analyzers_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        left_col.addWidget(self._analyzers_lbl)
        meta_row.addLayout(left_col)

        meta_row.addStretch()

        right_col = QVBoxLayout()
        right_col.setSpacing(8)
        right_col.setContentsMargins(0, 0, 0, 0)

        self._unsafe_lbl = QLabel("UNSAFE")
        self._unsafe_lbl.setStyleSheet(
            f"{_NB}color:{CRITICAL_ACCENT};background:{CRITICAL_BG};"
            f"border:1px solid {CRITICAL_ACCENT};"
        )
        self._unsafe_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self._unsafe_lbl.setVisible(False)
        right_col.addWidget(self._unsafe_lbl, 0, Qt.AlignmentFlag.AlignRight)

        self._sev_lbl = QLabel("")
        self._sev_lbl.setStyleSheet(
            f"{_NB}color:{MUTED_TEXT};background:transparent;border:none;"
        )
        self._sev_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        right_col.addWidget(self._sev_lbl, 0, Qt.AlignmentFlag.AlignRight)
        meta_row.addLayout(right_col)

        root.addLayout(meta_row)
        root.addSpacing(8)

        # ── Row 3: description ───────────────────────────────────────────────
        self._desc_lbl = QLabel(self._info.description or "No description")
        self._desc_lbl.setStyleSheet(
            f"color:{_SEC_TEXT};font-size:11px;background:transparent;"
            f"border:none;line-height:140%;"
        )
        self._desc_lbl.setWordWrap(True)
        self._desc_lbl.setMaximumHeight(36)   # ~2 lines
        root.addWidget(self._desc_lbl)
        root.addSpacing(8)

        # ── Findings section: divider + severity columns ──────────────────────
        self._findings_section = QWidget()
        self._findings_section.setStyleSheet("background:transparent;")
        fs_layout = QVBoxLayout(self._findings_section)
        fs_layout.setContentsMargins(0, 0, 0, 0)
        fs_layout.setSpacing(6)

        hdiv = QFrame()
        hdiv.setFrameShape(QFrame.Shape.HLine)
        hdiv.setFixedHeight(1)
        hdiv.setStyleSheet(f"background:{DIVIDER};border:none;")
        fs_layout.addWidget(hdiv)

        self._sev_row_lbl = QLabel()
        self._sev_row_lbl.setWordWrap(True)
        self._sev_row_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._sev_row_lbl.setStyleSheet(
            "background:transparent;border:none;font-size:10px;font-weight:700;"
        )
        fs_layout.addWidget(self._sev_row_lbl)

        self._findings_section.setVisible(False)
        root.addStretch(1)
        root.addWidget(self._findings_section)

        self._refresh_labels()

    # ── Label refresh ─────────────────────────────────────────────────────────

    def _refresh_labels(self) -> None:
        nb = self._nb
        sev_fs = "8px" if self._compact else "10px"

        # Apply badge styles (all scale with compact mode)
        _badge_neutral = f"{nb}color:{_SEC_TEXT};background:{_BADGE_BG};border:1px solid #334155;"
        self._type_lbl.setStyleSheet(_badge_neutral)
        self._results_lbl.setStyleSheet(_badge_neutral)
        self._analyzers_lbl.setStyleSheet(_badge_neutral)
        self._unsafe_lbl.setStyleSheet(
            f"{nb}color:{CRITICAL_ACCENT};background:{CRITICAL_BG};"
            f"border:1px solid {CRITICAL_ACCENT};"
        )
        self._sev_row_lbl.setStyleSheet(
            f"background:transparent;border:none;font-size:{sev_fs};font-weight:700;"
        )

        sev = self._info.severity
        sev_lower = (sev or "").lower()
        color = _SEVERITY_COLOUR.get(sev_lower, MUTED_TEXT)

        if sev is None:
            self._results_lbl.setText("—")
            self._analyzers_lbl.setText("—")
            self._unsafe_lbl.setVisible(False)
            self._sev_lbl.setText("")
            self._sev_lbl.setStyleSheet(
                f"{nb}color:{MUTED_TEXT};background:transparent;border:none;"
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
                    f"{nb}color:{CRITICAL_ACCENT};background:{CRITICAL_BG};"
                    f"border:1px solid {CRITICAL_ACCENT};"
                )
            elif sev_lower in ("clean", "safe"):
                self._sev_lbl.setStyleSheet(
                    f"{nb}color:{SAFE_ACCENT};background:transparent;"
                    f"border:1px solid {SAFE_ACCENT};"
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
            "critical": CRITICAL_ACCENT,
            "high": HIGH_ACCENT,
            "medium": MEDIUM_ACCENT,
            "low": SOFT_SURFACE,
        }

        parts = [
            f'<span style="color:{_COLOURS.get(s, MUTED_TEXT)};">'
            f'{s.upper()}({counts[s]})</span>'
            for s in _ORDER if s in counts
        ]
        if not parts:
            self._findings_section.setVisible(False)
            return

        sep = f' <span style="color:{MUTED_TEXT};font-weight:400;">-</span> '
        self._sev_row_lbl.setText(sep.join(parts))
        self._findings_section.setVisible(True)

    # ── Border ────────────────────────────────────────────────────────────────

    def _apply_border(self, hovered: bool = False) -> None:
        bg = _TILE_BG_HV if hovered else _TILE_BG
        color = _SEVERITY_COLOUR.get((self._info.severity or "").lower(), DIVIDER)
        if self._info.severity is None:
            bc = ACCENT if hovered else DIVIDER
            self.setStyleSheet(
                f"QFrame#SkillTile{{background:{bg};border-radius:8px;border:2px dashed {bc};}}"
            )
        else:
            self.setStyleSheet(
                f"QFrame#SkillTile{{background:{bg};border-radius:8px;border:2px solid {color};}}"
            )

    # ── Public refresh ────────────────────────────────────────────────────────

    def refresh(self, severity: Optional[str], is_safe: bool,
                last_scanned: Optional[datetime], trusted: bool,
                n_results: int = 0, n_analyzers: int = 0,
                llm_skipped: bool = False,
                findings: list | None = None) -> None:
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
        if (self._hovered and self._info.severity is None
                and self._info.spec_type == "skill"):
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.fillRect(self.rect(), QColor(13, 148, 136, 80))
            p.setPen(QColor(LIGHT_CANVAS))
            p.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "▶  Scan now")
            p.end()

    # ── Mouse / context menu ──────────────────────────────────────────────────

    def _scan_dir(self) -> str:
        return str(Path(self._info.path).parent)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            if self._info.spec_type == "skill" and self._info.severity is None:
                self.scan_requested.emit(self._info.skill_id, self._scan_dir())
            else:
                self.detail_requested.emit(self._info.skill_id)
        super().mousePressEvent(e)

    def contextMenuEvent(self, e) -> None:
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{DEEP_SURFACE};color:{LIGHT_CANVAS};"
            f"border:1px solid {DIVIDER};border-radius:6px;padding:4px;}}"
            f"QMenu::item{{padding:5px 20px;border-radius:4px;}}"
            f"QMenu::item:selected{{background:{ACCENT};}}"
            f"QMenu::separator{{height:1px;background:{DIVIDER};margin:2px 8px;}}"
        )
        if self._info.spec_type == "skill":
            scan_act = menu.addAction("Scan")
            scan_act.triggered.connect(
                lambda: self.scan_requested.emit(self._info.skill_id, self._scan_dir())
            )
            menu.addSeparator()
        open_act = menu.addAction("Open Folder")
        open_act.triggered.connect(
            lambda: self.open_folder_requested.emit(self._scan_dir())
        )
        copy_act = menu.addAction("Copy Path")
        copy_act.triggered.connect(
            lambda: QApplication.clipboard().setText(self._info.path)
        )
        menu.addSeparator()
        if self._info.trusted:
            t = menu.addAction("Revoke Trust")
            t.triggered.connect(lambda: self.trust_toggled.emit(self._info.skill_id, False))
        elif self._info.is_safe:
            t = menu.addAction("Trust")
            t.triggered.connect(lambda: self.trust_toggled.emit(self._info.skill_id, True))
        else:
            t = menu.addAction("Trust  (scan clean first)")
            t.setEnabled(False)
        menu.exec(e.globalPos())
