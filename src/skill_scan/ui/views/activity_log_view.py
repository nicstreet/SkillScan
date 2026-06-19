"""Activity Log view — filterable scan and trust event history."""

import os
import re
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .._widgets import msg_question

from .._palette import (
    SYS_ACTION_PRIMARY,
    SYS_BG_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_BADGE_SAFE,
    SYS_BADGE_UNSAFE,
    SYS_BORDER_ADVISORY,
    SYS_BORDER_LOW,
    SYS_BORDER_WARNING,
    SYS_STROKE_DIVIDER,
    SYS_STROKE_SUBTLE,
    SYS_TXT_PRIMARY,
    SYS_TXT_MUTED,
)
from .._widgets import SCROLLBAR_STYLE

_LOG_PATH = Path(os.environ.get("APPDATA", "~")) / "SkillScan" / "activity.log"
_LOG_RE = re.compile(
    r"\[(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2}) UTC\]\s+(.+?)(?:\s+—\s+(.*))?$"
)
_SEV_RE = re.compile(r"severity=(\w+)", re.IGNORECASE)
_FIND_RE = re.compile(r"findings=\d+")
_MAX_ROWS = 500

_SEV_COLOUR: dict[str, str] = {
    "CRITICAL": SYS_BADGE_UNSAFE,
    "HIGH": SYS_BORDER_WARNING,
    "MEDIUM": SYS_BORDER_ADVISORY,
    "LOW": SYS_BORDER_LOW,
}


def _event_colour(event: str, severity: str) -> str:
    ev = event.lower()
    if "error" in ev:
        return SYS_BADGE_UNSAFE
    if "auto-revoked" in ev or ("revoked" in ev and "auto" not in ev):
        return SYS_BORDER_WARNING
    if "granted" in ev:
        return SYS_BADGE_SAFE
    if "config" in ev:
        return SYS_ACTION_PRIMARY
    return _SEV_COLOUR.get(severity.upper(), SYS_TXT_MUTED)


class _Surface(QWidget):
    def __init__(self, color: str, radius: int = 0, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._radius = radius

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._radius:
            path = QPainterPath()
            path.addRoundedRect(
                0, 0, self.width(), self.height(), self._radius, self._radius
            )
            p.fillPath(path, self._color)
        else:
            p.fillRect(self.rect(), self._color)
        p.end()


class ActivityLogView(QWidget):
    """Reads %APPDATA%\\SkillScan\\activity.log and displays newest-first."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter = "all"
        self._rows: list[dict] = []
        self._build_ui()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(SYS_BG_SECONDARY))
        p.end()

    def showEvent(self, e) -> None:
        super().showEvent(e)
        self.refresh()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        root.addWidget(self._make_toolbar())

        card = _Surface(SYS_BG_PRIMARY, radius=8)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(1, 1, 1, 1)
        card_lay.setSpacing(0)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(
            ["Time", "Event", "Skill / Detail", "Severity"]
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().hide()
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)

        hdr = self._table.horizontalHeader()
        self._table.setColumnWidth(0, 72)
        self._table.setColumnWidth(1, 200)
        self._table.setColumnWidth(3, 90)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.setDefaultAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self._table.verticalHeader().setDefaultSectionSize(24)

        self._table.setStyleSheet(f"""
            QTableWidget {{
                background: {SYS_BG_PRIMARY};
                alternate-background-color: {SYS_BG_SECONDARY};
                border: none;
                font-size: 12px;
                color: {SYS_TXT_MUTED};
                outline: none;
            }}
            QTableWidget::item {{
                padding: 2px 8px;
                border: none;
            }}
            QTableWidget::item:selected {{
                background: {SYS_ACTION_PRIMARY}33;
                color: {SYS_TXT_PRIMARY};
            }}
            QHeaderView::section {{
                background: {SYS_TXT_MUTED};
                color: {SYS_TXT_PRIMARY};
                border: none;
                border-right: 1px solid {SYS_STROKE_DIVIDER};
                padding: 4px 8px;
                font-size: 12px;
                font-weight: 400;
            }}
            QHeaderView::section:last {{
                border-right: none;
            }}
        """)
        self._table.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        card_lay.addWidget(self._table)
        root.addWidget(card, 1)

        self._empty_lbl = QLabel("No activity logged yet.")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:13px;background:transparent;"
        )
        self._empty_lbl.setVisible(False)
        root.addWidget(self._empty_lbl)

    def _make_toolbar(self) -> QWidget:
        bar = _Surface(SYS_BG_PRIMARY, radius=6)
        bar.setFixedHeight(36)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(4)

        filt_css = (
            f"QPushButton{{background:transparent;color:{SYS_TXT_MUTED};"
            f"border:none;font-size:11px;padding:2px 10px;border-radius:4px;}}"
            f"QPushButton:hover{{color:{SYS_TXT_PRIMARY};}}"
            f"QPushButton:checked{{background:{SYS_ACTION_PRIMARY};color:{SYS_TXT_PRIMARY};}}"
        )
        self._btn_all = QPushButton("All")
        self._btn_scans = QPushButton("Scans")
        self._btn_trust = QPushButton("Trust")
        self._btn_errors = QPushButton("Errors")
        self._btn_config = QPushButton("Config")
        for btn, mode in (
            (self._btn_all, "all"),
            (self._btn_scans, "scans"),
            (self._btn_trust, "trust"),
            (self._btn_errors, "errors"),
            (self._btn_config, "config"),
        ):
            btn.setCheckable(True)
            btn.setFixedHeight(24)
            btn.setStyleSheet(filt_css)
            btn.clicked.connect(lambda _, m=mode: self._set_filter(m))
            lay.addWidget(btn)
        self._btn_all.setChecked(True)

        lay.addStretch()

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setFixedHeight(24)
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{SYS_TXT_MUTED};"
            f"border:1px solid {SYS_STROKE_SUBTLE};border-radius:4px;"
            f"font-size:11px;padding:2px 10px;}}"
            f"QPushButton:hover{{color:{SYS_TXT_PRIMARY};border-color:{SYS_TXT_PRIMARY};}}"
        )
        refresh_btn.clicked.connect(self.refresh)
        lay.addWidget(refresh_btn)

        clear_btn = QPushButton("Clear Log")
        clear_btn.setFixedHeight(24)
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{SYS_BADGE_UNSAFE};"
            f"border:1px solid {SYS_BADGE_UNSAFE};border-radius:4px;"
            f"font-size:11px;padding:2px 10px;}}"
            f"QPushButton:hover{{background:{SYS_BADGE_UNSAFE};color:{SYS_TXT_PRIMARY};}}"
        )
        clear_btn.clicked.connect(self._clear_log)
        lay.addWidget(clear_btn)

        return bar

    # ── Data ──────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        self._rows = self._parse_log()
        self._populate()

    def _parse_log(self) -> list[dict]:
        rows: list[dict] = []
        try:
            lines = _LOG_PATH.read_text(encoding="utf-8").splitlines()
        except OSError:
            return rows
        for line in reversed(lines[-_MAX_ROWS:]):
            m = _LOG_RE.match(line.strip())
            if not m:
                continue
            date, time_, event, raw_detail = (
                m.group(1),
                m.group(2),
                m.group(3).strip(),
                m.group(4) or "",
            )
            sm = _SEV_RE.search(raw_detail)
            severity = sm.group(1) if sm else ""
            detail = _SEV_RE.sub("", raw_detail)
            detail = _FIND_RE.sub("", detail).strip().strip("—").strip()
            rows.append(
                {
                    "date": date,
                    "time": time_,
                    "event": event,
                    "detail": detail,
                    "severity": severity,
                }
            )
        return rows

    def _filtered(self) -> list[dict]:
        if self._filter == "scans":
            return [r for r in self._rows if "scan" in r["event"].lower()]
        if self._filter == "trust":
            return [r for r in self._rows if "trust" in r["event"].lower()]
        if self._filter == "errors":
            return [r for r in self._rows if "error" in r["event"].lower()]
        if self._filter == "config":
            return [r for r in self._rows if "config" in r["event"].lower()]
        return self._rows

    def _populate(self) -> None:
        rows = self._filtered()
        self._empty_lbl.setVisible(not rows)
        self._table.setVisible(bool(rows))
        self._table.setRowCount(0)

        for row in rows:
            idx = self._table.rowCount()
            self._table.insertRow(idx)
            self._table.setRowHeight(idx, 24)

            colour = _event_colour(row["event"], row["severity"])

            def _item(text: str, fg: str = colour) -> QTableWidgetItem:
                it = QTableWidgetItem(text)
                it.setForeground(QColor(fg))
                return it

            sev_text = row["severity"].title() if row["severity"] else "—"
            self._table.setItem(idx, 0, _item(row["time"], SYS_TXT_MUTED))
            self._table.setItem(idx, 1, _item(row["event"]))
            self._table.setItem(idx, 2, _item(row["detail"], SYS_TXT_MUTED))
            self._table.setItem(idx, 3, _item(sev_text))

    def _set_filter(self, mode: str) -> None:
        self._filter = mode
        for btn, m in (
            (self._btn_all, "all"),
            (self._btn_scans, "scans"),
            (self._btn_trust, "trust"),
            (self._btn_errors, "errors"),
            (self._btn_config, "config"),
        ):
            btn.setChecked(m == mode)
        self._populate()

    def _clear_log(self) -> None:
        reply = msg_question(
            self,
            "Clear Activity Log",
            "Delete all activity log entries? This cannot be undone.",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            _LOG_PATH.write_text("", encoding="utf-8")
        except OSError:
            pass
        self.refresh()
