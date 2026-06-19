"""Skill Detail View — Phase 4: tabbed scan report, history, trust workflow."""

import hashlib
import html as _html
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from PyQt6.QtCore import Qt, QFileSystemWatcher
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ...core import spec_compliance
from ...core.db import Skill, ScanResult as DbScanResult, init_db, session
from ...core.scanner import ScanJob
from ...core.result_store import ScanResult as LegacyScanResult
from ..result_formatter import format_result_html
from .._compliance_render import render_compliance_html
from .._palette import (
    SYS_ACTION_PRIMARY,
    SYS_ACTION_HOVER,
    SYS_BG_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_BADGE_SAFE,
    SYS_BADGE_UNSAFE,
    SYS_BORDER_ADVISORY,
    SYS_BORDER_LOW,
    SYS_BORDER_WARNING,
    SYS_CRITICAL_BG,
    SYS_STROKE_DIVIDER,
    SYS_STROKE_SUBTLE,
    SYS_TXT_PRIMARY,
    SYS_TXT_SECONDARY,
    SYS_TXT_MUTED,
)
from .._widgets import SCROLLBAR_STYLE

# ── Module-level constants ────────────────────────────────────────────────────

_LOG_PATH = Path(os.environ.get("APPDATA", "~")) / "SkillScan" / "activity.log"

# Spec compliance field lists/weights now live in core/spec_compliance.py —
# the single source of truth shared with Skill Manager. Don't reintroduce
# local copies here.

_SEV_COLOUR = {
    "clean": SYS_BADGE_SAFE,
    "safe": SYS_BADGE_SAFE,
    "low": SYS_BORDER_LOW,
    "medium": SYS_BORDER_ADVISORY,
    "high": SYS_BORDER_WARNING,
    "critical": SYS_BADGE_UNSAFE,
    "unknown": SYS_TXT_MUTED,
}

# Severity badge text — includes Cisco priority designation
_SEV_BADGE_TEXT = {
    "critical": "P1  CRITICAL",
    "high": "P2  WARNING",
    "medium": "P3  ADVISORY",
    "low": "P3  ADVISORY",
    "clean": "CLEAN",
    "safe": "CLEAN",
}

_TYPE_LABEL = {"skill": "SKILL", "mcp": "MCP", "a2a": "A2A", "unknown": "?"}
_BADGE_BG = SYS_BG_SECONDARY
_SEC_TEXT = SYS_TXT_SECONDARY

# Shared badge geometry — matches tile _NB style for visual consistency
_BADGE_H = (
    "font-size:8px;font-weight:700;padding:1px 6px;"
    "border-radius:4px;letter-spacing:1px;"
)

_TAB_STYLE = f"""
    QTabWidget::pane {{
        border: none;
        background: {SYS_BG_SECONDARY};
    }}
    QTabBar {{
        background: {SYS_BG_SECONDARY};
    }}
    QTabBar::tab {{
        background: {SYS_BG_SECONDARY};
        color: {SYS_TXT_MUTED};
        padding: 8px 24px;
        font-size: 12px;
        font-weight: 600;
        border: none;
        border-bottom: 2px solid transparent;
        min-width: 80px;
    }}
    QTabBar::tab:selected {{
        background: {SYS_BG_PRIMARY};
        color: {SYS_TXT_PRIMARY};
        border-bottom: 2px solid {SYS_ACTION_PRIMARY};
    }}
    QTabBar::tab:hover:!selected {{
        color: {SYS_TXT_PRIMARY};
    }}
"""

_HIST_TABLE_STYLE = f"""
    QTableWidget {{
        background: {SYS_BG_SECONDARY};
        alternate-background-color: {SYS_BG_PRIMARY};
        border: none;
        color: {SYS_TXT_PRIMARY};
        font-size: 10px;
        font-weight: 400;
        selection-background-color: {SYS_ACTION_PRIMARY};
    }}
    QHeaderView::section {{
        background: {SYS_ACTION_PRIMARY};
        color: {SYS_TXT_PRIMARY};
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 1px;
        padding: 6px 8px;
        border: none;
        border-right: 1px solid {SYS_STROKE_DIVIDER};
    }}
    QHeaderView::section:last {{ border-right: none; }}
    QTableWidget::item {{ padding: 4px 8px; }}
"""


def _age_str(dt: datetime | None) -> str:
    if dt is None:
        return "—"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    s = int((datetime.now(timezone.utc) - dt).total_seconds())
    if s < 60:
        return "just now"
    if s < 3600:
        return f"{s // 60}m ago"
    if s < 86400:
        return f"{s // 3600}h ago"
    return f"{s // 86400}d ago"


def _parse_raw_json(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        result = json.loads(raw.strip())
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for i, ch in enumerate(raw):
        if ch == "{":
            try:
                obj, _ = decoder.raw_decode(raw, i)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue
    return None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def _log_activity(action: str, detail: str = "") -> None:
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"[{ts}]  {action}"
        if detail:
            line += f"  —  {detail}"
        with open(_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass


# ── Sparkline ─────────────────────────────────────────────────────────────────


class _Sparkline(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._data: list[str] = []
        self.setFixedHeight(14)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet("background:transparent;")

    def set_data(self, severities: list[str]) -> None:
        self._data = severities[-60:]
        self.update()

    def paintEvent(self, _) -> None:
        if not self._data:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        n = len(self._data)
        seg = min(
            16, max(6, (self.width() - (n - 1) * 2) // n if n > 1 else self.width())
        )
        h = self.height()
        x = 0
        for sev in self._data:
            colour = _SEV_COLOUR.get((sev or "unknown").lower(), SYS_TXT_MUTED)
            p.fillRect(x, (h - seg) // 2, seg, seg, QColor(colour))
            x += seg + 2
        p.end()


# ── Button helpers ────────────────────────────────────────────────────────────


def _primary_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"QPushButton{{background:{SYS_ACTION_PRIMARY};color:{SYS_TXT_PRIMARY};border:none;"
        f"border-radius:6px;padding:5px 14px;font-size:12px;font-weight:600;}}"
        f"QPushButton:hover{{background:{SYS_ACTION_HOVER};}}"
        f"QPushButton:pressed{{background:{SYS_ACTION_HOVER};}}"
        f"QPushButton:disabled{{background:{SYS_STROKE_DIVIDER};color:{SYS_TXT_MUTED};}}"
    )
    return btn


def _styled_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    btn.setStyleSheet(
        f"QPushButton{{background:transparent;color:{SYS_TXT_PRIMARY};"
        f"border:1px solid {SYS_STROKE_SUBTLE};border-radius:6px;padding:5px 14px;font-size:12px;}}"
        f"QPushButton:hover{{border-color:{SYS_ACTION_PRIMARY};color:{SYS_ACTION_PRIMARY};}}"
        f"QPushButton:pressed{{background:#0f2028;}}"
        f"QPushButton:disabled{{color:{SYS_TXT_MUTED};border-color:{SYS_STROKE_DIVIDER};}}"
    )
    return btn


# ── Main view ─────────────────────────────────────────────────────────────────


class SkillDetailView(QWidget):
    """Single-skill deep-dive: unified header panel + tabbed Report / History / Raw Output."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._skill_id: int | None = None
        self._skill_path: str = ""
        self._skill_name: str = ""
        self._scan_job: ScanJob | None = None
        self._history: list[dict] = []
        self._file_watcher = QFileSystemWatcher(self)
        self._file_watcher.fileChanged.connect(self._on_file_changed)
        self.setStyleSheet(f"background:{SYS_BG_PRIMARY};")
        self._build_ui()

    # ── Construction ─────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        # Header (type/name/meta/info chips/buttons) and tabs separated by one divider.
        outer.addWidget(self._make_header())
        outer.addWidget(_hdiv())
        outer.addWidget(self._make_tabs(), 1)

    def _make_header(self) -> QWidget:
        """Unified header panel: badges, name, path, info chips, action buttons."""
        hdr = QWidget()
        hdr.setStyleSheet(f"background:{SYS_BG_PRIMARY};")

        # Outer row: left content column | right badges column
        outer = QHBoxLayout(hdr)
        outer.setContentsMargins(24, 16, 24, 14)
        outer.setSpacing(16)

        # ── Left column ───────────────────────────────────────────────────────
        left = QVBoxLayout()
        left.setSpacing(4)
        left.setContentsMargins(0, 0, 0, 0)

        # Type + unsafe badges — natural badge height, no inflation
        badge_row = QHBoxLayout()
        badge_row.setSpacing(0)
        badge_row.setContentsMargins(0, 0, 0, 0)

        self._type_lbl = QLabel("SKILL")
        self._type_lbl.setStyleSheet(
            f"{_BADGE_H}color:{_SEC_TEXT};"
            f"background:{_BADGE_BG};border:1px solid {SYS_ACTION_PRIMARY};"
        )
        self._type_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        badge_row.addWidget(self._type_lbl)
        badge_row.addSpacing(4)

        self._unsafe_badge = QLabel("UNSAFE")
        self._unsafe_badge.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self._unsafe_badge.setStyleSheet(
            f"{_BADGE_H}color:{SYS_BADGE_UNSAFE};"
            f"background:{SYS_CRITICAL_BG};border:1px solid {SYS_BADGE_UNSAFE};"
        )
        self._unsafe_badge.setVisible(False)
        badge_row.addWidget(self._unsafe_badge)
        badge_row.addSpacing(32)

        self._results_badge = QLabel("— RESULTS")
        self._results_badge.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self._results_badge.setStyleSheet(
            f"{_BADGE_H}color:{_SEC_TEXT};"
            f"background:{_BADGE_BG};border:1px solid {SYS_STROKE_SUBTLE};"
        )
        badge_row.addWidget(self._results_badge)
        badge_row.addSpacing(4)

        self._analyzers_badge = QLabel("— ANALYZERS")
        self._analyzers_badge.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self._analyzers_badge.setStyleSheet(
            f"{_BADGE_H}color:{_SEC_TEXT};"
            f"background:{_BADGE_BG};border:1px solid {SYS_STROKE_SUBTLE};"
        )
        badge_row.addWidget(self._analyzers_badge)
        badge_row.addStretch()
        left.addLayout(badge_row)

        # Skill name
        self._name_lbl = QLabel("—")
        self._name_lbl.setStyleSheet(
            f"color:{SYS_TXT_PRIMARY};font-size:14px;font-weight:700;background:transparent;"
        )
        left.addWidget(self._name_lbl)

        # Path · version · authors
        self._meta_lbl = QLabel("—")
        self._meta_lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;"
        )
        self._meta_lbl.setWordWrap(True)
        left.addWidget(self._meta_lbl)

        # Action buttons
        left.addSpacing(12)
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.setContentsMargins(0, 0, 0, 0)

        self._scan_btn = _primary_btn("Scan Now")
        self._scan_btn.clicked.connect(self._scan_now)
        btn_row.addWidget(self._scan_btn)

        self._trust_btn = _styled_btn("Trust")
        self._trust_btn.clicked.connect(self._toggle_trust)
        btn_row.addWidget(self._trust_btn)

        self._open_file_btn = _styled_btn("Open File")
        self._open_file_btn.clicked.connect(self._open_file)
        btn_row.addWidget(self._open_file_btn)

        self._creator_btn = _styled_btn("Open in Creator")
        self._creator_btn.setEnabled(False)
        self._creator_btn.setToolTip("Available in Phase 5 — Skill Creator")
        btn_row.addWidget(self._creator_btn)

        btn_row.addStretch()
        left.addLayout(btn_row)

        outer.addLayout(left, 1)

        # ── Right column: severity → LLM skipped → trust (top-aligned) ───────
        right = QVBoxLayout()
        right.setSpacing(4)
        right.setContentsMargins(0, 0, 0, 0)
        right.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._sev_badge = QLabel("UNSCANNED")
        self._sev_badge.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self._set_sev_badge(None)
        right.addWidget(self._sev_badge, 0, Qt.AlignmentFlag.AlignRight)

        self._llm_badge = QLabel("LLM  SKIPPED")
        self._llm_badge.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
        )
        self._llm_badge.setStyleSheet(
            f"{_BADGE_H}color:{SYS_BORDER_ADVISORY};"
            f"background:transparent;border:1px solid {SYS_BORDER_ADVISORY};"
        )
        self._llm_badge.setVisible(False)
        right.addWidget(self._llm_badge, 0, Qt.AlignmentFlag.AlignRight)

        self._trust_badge = QLabel("")
        self._trust_badge.setStyleSheet(
            f"color:{SYS_ACTION_PRIMARY};font-size:10px;font-weight:700;"
            f"background:transparent;letter-spacing:1px;"
        )
        right.addWidget(self._trust_badge, 0, Qt.AlignmentFlag.AlignRight)

        outer.addLayout(right)

        return hdr

    def _make_tabs(self) -> QTabWidget:
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(_TAB_STYLE)
        self._tabs.setDocumentMode(True)

        # ── Report ────────────────────────────────────────────────────────
        report_w = QWidget()
        report_w.setStyleSheet(f"background:{SYS_BG_SECONDARY};")
        rl = QVBoxLayout(report_w)
        rl.setContentsMargins(0, 0, 0, 0)
        self._browser = QTextBrowser()
        self._browser.setStyleSheet(
            f"QTextBrowser{{background:{SYS_BG_SECONDARY};border:none;"
            f"color:{SYS_TXT_PRIMARY};font-family:Segoe UI,sans-serif;padding:16px;}}"
        )
        self._browser.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        self._browser.setOpenExternalLinks(False)
        self._browser.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        rl.addWidget(self._browser)
        self._tabs.addTab(report_w, "Report")

        # ── History ───────────────────────────────────────────────────────
        hist_w = QWidget()
        hist_w.setStyleSheet(f"background:{SYS_BG_SECONDARY};")
        hl = QVBoxLayout(hist_w)
        hl.setContentsMargins(20, 16, 20, 16)
        hl.setSpacing(12)

        self._sparkline = _Sparkline()
        hl.addWidget(self._sparkline)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(["When", "Severity", "Duration", "Safe"])
        hh = self._table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setStyleSheet(_HIST_TABLE_STYLE)
        self._table.currentCellChanged.connect(self._on_row_changed)
        hl.addWidget(self._table)
        self._tabs.addTab(hist_w, "History")

        # ── Raw Output ────────────────────────────────────────────────────
        raw_w = QWidget()
        raw_w.setStyleSheet(f"background:{SYS_BG_PRIMARY};")
        rawl = QVBoxLayout(raw_w)
        rawl.setContentsMargins(0, 0, 0, 0)
        self._raw_edit = QPlainTextEdit()
        self._raw_edit.setReadOnly(True)
        self._raw_edit.setStyleSheet(
            f"QPlainTextEdit{{background:{SYS_BG_PRIMARY};color:{SYS_TXT_MUTED};"
            f"font-family:Consolas,monospace;font-size:11px;"
            f"border:none;padding:16px;}}"
        )
        self._raw_edit.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        rawl.addWidget(self._raw_edit)
        self._tabs.addTab(raw_w, "Raw Output")

        # ── Compliance ───────────────────────────────────────────────────
        comp_w = QWidget()
        comp_w.setStyleSheet(f"background:{SYS_BG_PRIMARY};")
        compl = QVBoxLayout(comp_w)
        compl.setContentsMargins(0, 0, 0, 0)
        self._compliance_browser = QTextBrowser()
        self._compliance_browser.setStyleSheet(
            f"QTextBrowser{{background:{SYS_BG_PRIMARY};border:none;"
            f"color:{SYS_TXT_PRIMARY};font-family:Segoe UI,sans-serif;padding:16px;}}"
        )
        self._compliance_browser.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        self._compliance_browser.setOpenExternalLinks(False)
        self._compliance_browser.setTextInteractionFlags(
            Qt.TextInteractionFlag.NoTextInteraction
        )
        compl.addWidget(self._compliance_browser)
        self._tabs.addTab(comp_w, "Compliance")

        return self._tabs

    # ── Entry point ───────────────────────────────────────────────────────────

    def load(self, skill_id: int) -> None:
        self._skill_id = skill_id
        self._tabs.setCurrentIndex(0)
        self._refresh()

    # ── Data refresh ──────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        if self._skill_id is None:
            return
        try:
            init_db()
            with session() as s:
                skill = s.query(Skill).filter_by(id=self._skill_id).first()
                if skill is None:
                    return
                results = (
                    s.query(DbScanResult)
                    .filter_by(skill_id=self._skill_id)
                    .order_by(DbScanResult.timestamp.desc())
                    .limit(50)
                    .all()
                )
                sd = {
                    "name": skill.name,
                    "path": skill.path,
                    "spec_type": skill.spec_type,
                    "version": skill.version,
                    "authors": skill.authors,
                    "trusted": skill.trusted,
                }
                history = [
                    {
                        "timestamp": r.timestamp,
                        "severity": r.severity,
                        "is_safe": r.is_safe,
                        "raw_json": r.raw_json,
                        "findings_json": r.findings_json,
                        "duration_ms": r.duration_ms,
                        "returncode": r.returncode,
                    }
                    for r in results
                ]
        except Exception:
            return

        self._skill_path = sd["path"]
        self._skill_name = sd["name"]
        self._history = history
        latest = history[0] if history else None

        # Keep file watcher pointed at current skill file
        for p in self._file_watcher.files():
            self._file_watcher.removePath(p)
        if Path(self._skill_path).exists():
            self._file_watcher.addPath(self._skill_path)

        self._update_header(sd)
        self._update_actions(sd, latest)
        self._update_history(history)
        self._update_compliance(sd["path"], sd["spec_type"])

        if latest:
            self._show_result(latest)
        else:
            self._show_no_scan()

    def _update_header(self, sd: dict) -> None:
        self._type_lbl.setText(_TYPE_LABEL.get(sd["spec_type"] or "unknown", "?"))
        self._name_lbl.setText(sd["name"])
        parts = [sd["path"]]
        if sd.get("version"):
            parts.append(f"v{sd['version']}")
        try:
            authors = json.loads(sd.get("authors") or "[]")
            if authors:
                parts.append(", ".join(authors))
        except Exception:
            pass
        self._meta_lbl.setText("  ·  ".join(parts))
        self._trust_badge.setText("✓  TRUSTED" if sd["trusted"] else "")

    def _update_actions(self, sd: dict, latest: dict | None) -> None:
        scanning = self._scan_job is not None
        self._scan_btn.setEnabled(
            sd["spec_type"] in ("skill", "mcp", "a2a") and not scanning
        )
        self._scan_btn.setText("Scanning…" if scanning else "Scan Now")
        trusted = sd["trusted"]
        is_safe = latest["is_safe"] if latest else False
        if trusted:
            self._trust_btn.setText("Revoke Trust")
            self._trust_btn.setEnabled(True)
        elif is_safe:
            self._trust_btn.setText("Trust")
            self._trust_btn.setEnabled(True)
        else:
            self._trust_btn.setText("Trust")
            self._trust_btn.setEnabled(False)
        self._open_file_btn.setEnabled(Path(sd["path"]).exists())

    def _update_llm_badge(self, parsed: dict | None) -> None:
        if parsed is None:
            self._llm_badge.setVisible(False)
            return
        llm_failed = bool(
            parsed.get("analyzers_failed")
            or any(
                f.get("rule_id") == "LLM_ANALYSIS_FAILED"
                for f in parsed.get("findings", [])
            )
        )
        self._llm_badge.setVisible(llm_failed)

    def _update_info_chips(
        self, parsed: dict | None, is_safe: bool | None = None
    ) -> None:
        if parsed is None:
            self._unsafe_badge.setVisible(False)
            self._results_badge.setText("— RESULTS")
            self._analyzers_badge.setText("— ANALYZERS")
            self._analyzers_badge.setToolTip("")
            return

        safe = (
            parsed.get("is_safe")
            if parsed.get("is_safe") is not None
            else bool(is_safe)
        )
        self._unsafe_badge.setVisible(not safe)

        real_finds = [
            f
            for f in parsed.get("findings", [])
            if f.get("rule_id") != "LLM_ANALYSIS_FAILED"
        ]
        n = len(real_finds)
        self._results_badge.setText(f"{n} RESULT{'S' if n != 1 else ''}")

        analyzers = parsed.get("analyzers_used", [])
        n_a = len(analyzers)
        self._analyzers_badge.setText(
            f"{n_a} ANALYZER{'S' if n_a != 1 else ''}" if analyzers else "— ANALYZERS"
        )
        self._analyzers_badge.setToolTip("\n".join(analyzers) if analyzers else "")

    def _update_history(self, history: list[dict]) -> None:
        self._sparkline.set_data(
            [(r["severity"] or "unknown") for r in reversed(history)]
        )
        self._table.blockSignals(True)
        try:
            self._table.setRowCount(0)
            if not history:
                self._table.setRowCount(1)
                item = QTableWidgetItem("No scan history")
                item.setForeground(QColor(SYS_TXT_MUTED))
                self._table.setItem(0, 0, item)
                self._table.setSpan(0, 0, 1, 4)
                return
            self._table.setRowCount(len(history))
            for row, r in enumerate(history):
                sev = r["severity"] or "unknown"
                dur = (
                    f"{(r['duration_ms'] or 0) / 1000:.1f}s"
                    if r["duration_ms"]
                    else "—"
                )
                ts = r["timestamp"]
                when = _age_str(ts)

                w_item = QTableWidgetItem(when)
                w_item.setForeground(QColor(SYS_TXT_PRIMARY))
                if ts:
                    fmt = "%Y-%m-%d %H:%M:%S UTC" if ts.tzinfo else "%Y-%m-%d %H:%M:%S"
                    w_item.setToolTip(ts.strftime(fmt))

                s_item = QTableWidgetItem(sev.upper())
                s_item.setForeground(
                    QColor(_SEV_COLOUR.get(sev.lower(), SYS_TXT_MUTED))
                )

                d_item = QTableWidgetItem(dur)
                d_item.setForeground(QColor(SYS_TXT_PRIMARY))
                safe_item = QTableWidgetItem("Yes" if r["is_safe"] else "No")
                safe_item.setForeground(QColor(SYS_TXT_PRIMARY))

                self._table.setItem(row, 0, w_item)
                self._table.setItem(row, 1, s_item)
                self._table.setItem(row, 2, d_item)
                self._table.setItem(row, 3, safe_item)
            self._table.selectRow(0)
        finally:
            self._table.blockSignals(False)

    # ── Spec compliance ───────────────────────────────────────────────────────

    def _update_compliance(self, path: str, spec_type: str | None = None) -> None:
        """Parse SKILL.md frontmatter, score it, and render the Compliance tab."""
        if (spec_type or "").lower() != "skill" or not Path(path).exists():
            self._compliance_browser.setHtml(
                f'<html><body style="background:{SYS_BG_PRIMARY};color:{SYS_TXT_MUTED};'
                f'font-family:Segoe UI,sans-serif;font-size:12px;margin:24px;">'
                f"<p>Spec compliance is only available for SKILL.md files.</p>"
                f"</body></html>"
            )
            return

        meta = spec_compliance.parse_frontmatter(path)
        body = spec_compliance.parse_body(path)
        result = spec_compliance.score(
            meta, folder_name=Path(path).parent.name, body=body
        )
        score = result.score

        # Persist score to DB
        try:
            with session() as s:
                skill = s.query(Skill).filter_by(path=path).first()
                if skill:
                    skill.spec_score = score
                    s.commit()
        except Exception:
            pass

        self._compliance_browser.setHtml(render_compliance_html(meta, result))

    def _on_file_changed(self, path: str) -> None:
        """File watcher callback — if trusted skill's file changed, auto-revoke trust."""
        if self._skill_id is None:
            return
        try:
            skill_path = Path(path)
            # Re-add path: some editors replace the file (delete + create) which drops it
            if skill_path.exists():
                self._file_watcher.addPath(path)
            with session() as s:
                skill = s.query(Skill).filter_by(id=self._skill_id).first()
                if skill is None or not skill.trusted:
                    return
                current_hash = _sha256_file(skill_path)
                if current_hash and current_hash != (skill.file_hash or ""):
                    skill.trusted = False
                    skill.trust_signed_at = None
                    s.commit()
                    _log_activity(
                        "Trust auto-revoked — file changed", skill.name or path
                    )
        except Exception:
            return
        self._refresh()

    # ── Report rendering ──────────────────────────────────────────────────────

    def _show_result(self, r: dict) -> None:
        self._set_sev_badge(r.get("severity"))
        self._raw_edit.setPlainText(r.get("raw_json") or "")

        parsed = _parse_raw_json(r.get("raw_json"))
        if parsed is None:
            try:
                findings = json.loads(r["findings_json"] or "[]")
            except Exception:
                findings = []
            is_safe = r.get("is_safe", False)
            parsed = {
                "is_safe": is_safe,
                "max_severity": r.get("severity", "unknown"),
                "findings": findings,
                "findings_count": len(findings),
                "scan_duration_seconds": (r.get("duration_ms") or 0) / 1000,
                "analyzers_used": [],
            }

        self._update_info_chips(parsed, r.get("is_safe"))
        self._update_llm_badge(parsed)

        legacy = LegacyScanResult(
            path=self._skill_path,
            timestamp=(r["timestamp"].isoformat() if r.get("timestamp") else ""),
            returncode=r.get("returncode") or 0,
            stdout=r.get("raw_json") or "",
            stderr="",
            parsed=parsed,
        )
        self._browser.setHtml(format_result_html(legacy))

    def _show_no_scan(self) -> None:
        self._set_sev_badge(None)
        self._update_info_chips(None)
        self._update_llm_badge(None)
        self._raw_edit.setPlainText("")
        self._browser.setHtml(
            f'<html><body style="background:{SYS_BG_PRIMARY};color:{SYS_TXT_MUTED};'
            f'font-family:Segoe UI,sans-serif;font-size:13px;padding:32px 24px;">'
            f'<p style="margin-top:60px;text-align:center;font-size:14px;">'
            f"This skill has not been scanned yet.</p>"
            f'<p style="text-align:center;margin-top:8px;">'
            f'Click <b style="color:{SYS_ACTION_PRIMARY};">Scan Now</b> to run the security scanner.'
            f"</p></body></html>"
        )

    def _set_sev_badge(self, severity: str | None) -> None:
        sev = (severity or "").lower()
        text = _SEV_BADGE_TEXT.get(sev, "UNSCANNED") if sev else "UNSCANNED"
        if not sev:
            style = (
                f"{_BADGE_H}color:{SYS_TXT_MUTED};"
                f"background:transparent;border:1px solid {SYS_TXT_MUTED};"
            )
        elif sev == "critical":
            style = (
                f"{_BADGE_H}color:{SYS_BADGE_UNSAFE};"
                f"background:{SYS_CRITICAL_BG};border:1px solid {SYS_BADGE_UNSAFE};"
            )
        else:
            colour = _SEV_COLOUR.get(sev, SYS_TXT_MUTED)
            style = (
                f"{_BADGE_H}color:{colour};"
                f"background:transparent;border:1px solid {colour};"
            )
        self._sev_badge.setText(text)
        self._sev_badge.setStyleSheet(style)

    # ── History row selection ─────────────────────────────────────────────────

    def _on_row_changed(self, current_row: int, _cc: int, _pr: int, _pc: int) -> None:
        if 0 <= current_row < len(self._history):
            self._show_result(self._history[current_row])

    # ── Actions ───────────────────────────────────────────────────────────────

    def _scan_now(self) -> None:
        if self._skill_id is None or self._scan_job is not None:
            return
        try:
            with session() as s:
                skill = s.query(Skill).filter_by(id=self._skill_id).first()
                if skill is None:
                    return
                # skill-scanner expects the parent directory; mcp/a2a scanners take the file path
                if skill.spec_type == "skill":
                    scan_path = str(Path(skill.path).parent)
                else:
                    scan_path = skill.path
                skill_id = skill.id
                skill_name = skill.name
        except Exception:
            return
        self._scan_btn.setText("Scanning…")
        self._scan_btn.setEnabled(False)
        _log_activity("Scan started", skill_name)
        job = ScanJob(scan_path)
        job.finished.connect(
            lambda result: self._on_scan_done(skill_id, skill_name, result)
        )
        job.error.connect(self._on_scan_error)
        self._scan_job = job
        job.start()

    def _on_scan_done(self, skill_id: int, skill_name: str, result) -> None:
        self._scan_job = None
        parsed = result.parsed or {}
        is_safe = bool(parsed.get("is_safe", False))
        severity = "clean" if is_safe else parsed.get("max_severity", "unknown")
        findings_count = len(parsed.get("findings", []))
        try:
            with session() as s:
                s.add(
                    DbScanResult(
                        skill_id=skill_id,
                        timestamp=datetime.now(timezone.utc),
                        severity=severity,
                        is_safe=is_safe,
                        raw_json=result.stdout,
                        findings_json=json.dumps(parsed.get("findings", [])),
                        returncode=result.returncode,
                        analyzers_used="[]",
                    )
                )
                s.commit()
        except Exception:
            pass
        _log_activity(
            "Scan complete",
            f"{skill_name}  severity={severity.upper()}  findings={findings_count}",
        )
        self._refresh()

    def _on_scan_error(self, msg: str = "") -> None:
        self._scan_job = None
        self._scan_btn.setText("Scan Now")
        self._scan_btn.setEnabled(True)
        _log_activity(
            "Scan error", f"{self._skill_name}  —  {msg}" if msg else self._skill_name
        )
        self._browser.setHtml(
            f'<html><body style="background:{SYS_BG_SECONDARY};'
            f'font-family:Segoe UI,sans-serif;font-size:10px;padding:24px;">'
            f'<p style="color:{SYS_BADGE_UNSAFE};font-weight:700;margin-bottom:8px;">Scan failed</p>'
            f'<p style="color:{SYS_TXT_MUTED};">{_html.escape(msg)}</p>'
            f"</body></html>"
        )

    def _toggle_trust(self) -> None:
        if self._skill_id is None:
            return
        try:
            with session() as s:
                skill = s.query(Skill).filter_by(id=self._skill_id).first()
                if skill is None:
                    return
                new_trusted = not skill.trusted
                skill.trusted = new_trusted
                skill.trust_signed_at = (
                    datetime.now(timezone.utc) if new_trusted else None
                )
                if new_trusted:
                    skill.file_hash = _sha256_file(Path(skill.path))
                s.commit()
                action = "granted" if new_trusted else "revoked"
        except Exception:
            return
        _log_activity(f"Trust {action}", self._skill_name)
        self._refresh()

    def _open_file(self) -> None:
        if not self._skill_path:
            return
        p = Path(self._skill_path)
        if p.exists():
            subprocess.Popen(["notepad.exe", str(p)])


# ── Widget helpers ────────────────────────────────────────────────────────────


def _chip(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;")
    return lbl


def _dot() -> QLabel:
    lbl = QLabel("  ·  ")
    lbl.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;")
    return lbl


def _hdiv() -> QFrame:
    div = QFrame()
    div.setFrameShape(QFrame.Shape.HLine)
    div.setFixedHeight(1)
    div.setStyleSheet(f"background:{SYS_STROKE_DIVIDER};border:none;")
    return div
