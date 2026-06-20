"""Skill Audit view — batch spec-compliance audit of Claude Code's own skills.

Scans ~/.claude/skills/ plus any user-added project .claude/skills/ folders
against core/spec_compliance.py and surfaces per-skill findings. Distinct from
Folders/Inventory, which track arbitrary scanned locations in the DB — this is
ephemeral (re-run each session) and targets Claude Code's own skill ecosystem.
"""

import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ...core import config as cfg
from ...core.skill_audit import DEFAULT_AUDIT_ROOT, AuditEntry, SkillAuditWorker
from ...core.skill_budget import aggregate_budget_report, check_description_length
from .._compliance_render import render_compliance_html, score_colour
from .._palette import (
    SYS_ACTION_PRIMARY,
    SYS_BADGE_SAFE,
    SYS_BADGE_UNSAFE,
    SYS_BG_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_BORDER_ADVISORY,
    SYS_STROKE_DIVIDER,
    SYS_STROKE_SUBTLE,
    SYS_TXT_MUTED,
    SYS_TXT_PRIMARY,
)
from .._widgets import SCROLLBAR_STYLE, _Surface


def _status_label(score: int) -> str:
    if score >= 75:
        return "Healthy"
    if score >= 50:
        return "Needs Attention"
    return "At Risk"


class SkillAuditView(QWidget):
    """Table of audited skills (worst score first) + detail pane on selection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._extra_roots: list[str] = []
        self._entries: list[AuditEntry] = []
        self._worker: SkillAuditWorker | None = None
        self._scanned_once = False
        self._build_ui()
        self._load_roots()

    def showEvent(self, e) -> None:
        super().showEvent(e)
        if not self._scanned_once:
            self._scanned_once = True
            self._run_scan()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        root.addWidget(self._make_roots_bar())
        root.addWidget(self._make_toolbar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(8)
        splitter.setStyleSheet("QSplitter::handle{background:transparent;}")

        table_card = _Surface(SYS_BG_PRIMARY, radius=8)
        table_lay = QVBoxLayout(table_card)
        table_lay.setContentsMargins(1, 1, 1, 1)
        table_lay.setSpacing(0)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["Name", "Folder", "Score", "Status", "Desc. Chars"]
        )
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.verticalHeader().hide()
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(True)

        hdr = self._table.horizontalHeader()
        self._table.setColumnWidth(2, 60)
        self._table.setColumnWidth(3, 130)
        self._table.setColumnWidth(4, 90)
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
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
        self._table.itemSelectionChanged.connect(self._on_row_selected)
        table_lay.addWidget(self._table)

        detail_card = _Surface(SYS_BG_PRIMARY, radius=8)
        detail_lay = QVBoxLayout(detail_card)
        detail_lay.setContentsMargins(1, 1, 1, 1)
        detail_lay.setSpacing(0)

        self._detail_browser = QTextBrowser()
        self._detail_browser.setStyleSheet(
            f"QTextBrowser{{background:{SYS_BG_PRIMARY};border:none;}}"
        )
        self._detail_browser.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        self._set_detail_placeholder("Select a skill to view its compliance breakdown.")
        detail_lay.addWidget(self._detail_browser, 1)

        self._open_folder_btn = QPushButton("Open Folder")
        self._open_folder_btn.setFixedHeight(28)
        self._open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_folder_btn.setEnabled(False)
        self._open_folder_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{SYS_TXT_MUTED};"
            f"border:1px solid {SYS_STROKE_SUBTLE};border-radius:4px;"
            f"margin:8px;font-size:11px;}}"
            f"QPushButton:hover{{color:{SYS_TXT_PRIMARY};border-color:{SYS_TXT_PRIMARY};}}"
            f"QPushButton:disabled{{color:{SYS_STROKE_SUBTLE};}}"
        )
        self._open_folder_btn.clicked.connect(self._open_selected_folder)
        detail_lay.addWidget(self._open_folder_btn)

        splitter.addWidget(table_card)
        splitter.addWidget(detail_card)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        root.addWidget(splitter, 1)

        self._empty_lbl = QLabel(
            f"No SKILL.md files found under {DEFAULT_AUDIT_ROOT}.\n"
            "Add a project folder above, or create skills with Skill Studio."
        )
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:13px;background:transparent;"
        )
        self._empty_lbl.setVisible(False)
        root.addWidget(self._empty_lbl)

    def _make_roots_bar(self) -> QWidget:
        bar = _Surface(SYS_BG_PRIMARY, radius=6)
        bar.setFixedHeight(36)
        self._roots_lay = QHBoxLayout(bar)
        self._roots_lay.setContentsMargins(10, 0, 10, 0)
        self._roots_lay.setSpacing(6)
        return bar

    def _make_toolbar(self) -> QWidget:
        bar = _Surface(SYS_BG_PRIMARY, radius=6)
        bar.setFixedHeight(36)
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(10, 0, 10, 0)
        lay.setSpacing(14)

        self._summary_lbl = QLabel("")
        self._summary_lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;"
        )
        lay.addWidget(self._summary_lbl)

        lay.addStretch()

        self._scan_btn = QPushButton("Scan Now")
        self._scan_btn.setFixedHeight(24)
        self._scan_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._scan_btn.setStyleSheet(
            f"QPushButton{{background:{SYS_ACTION_PRIMARY};color:{SYS_TXT_PRIMARY};"
            "border:none;border-radius:4px;padding:2px 14px;font-size:11px;}"
            "QPushButton:hover{background:#0f9e92;}"
            f"QPushButton:disabled{{background:{SYS_STROKE_SUBTLE};color:{SYS_TXT_MUTED};}}"
        )
        self._scan_btn.clicked.connect(self._run_scan)
        lay.addWidget(self._scan_btn)

        return bar

    # ── Folder roots ──────────────────────────────────────────────────────────

    def _load_roots(self) -> None:
        c = cfg.load()
        self._extra_roots = list(c.get("audit_roots", []))
        self._render_roots()

    def _render_roots(self) -> None:
        while self._roots_lay.count():
            item = self._roots_lay.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

        default_chip = QLabel(f"  {DEFAULT_AUDIT_ROOT}  (default)  ")
        default_chip.setStyleSheet(
            f"background:{SYS_BG_SECONDARY};color:{SYS_TXT_MUTED};"
            "border-radius:4px;font-size:11px;padding:2px 4px;"
        )
        self._roots_lay.addWidget(default_chip)

        for path in self._extra_roots:
            self._roots_lay.addWidget(self._make_root_chip(path))

        self._roots_lay.addStretch()

        add_btn = QPushButton("+ Add Folder…")
        add_btn.setFixedHeight(24)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{SYS_TXT_MUTED};"
            f"border:1px solid {SYS_STROKE_SUBTLE};border-radius:4px;"
            f"font-size:11px;padding:2px 10px;}}"
            f"QPushButton:hover{{color:{SYS_TXT_PRIMARY};border-color:{SYS_TXT_PRIMARY};}}"
        )
        add_btn.clicked.connect(self._add_root)
        self._roots_lay.addWidget(add_btn)

    def _make_root_chip(self, path: str) -> QWidget:
        chip = _Surface(SYS_BG_SECONDARY, radius=4)
        chip.setFixedHeight(22)
        lay = QHBoxLayout(chip)
        lay.setContentsMargins(8, 0, 4, 0)
        lay.setSpacing(4)
        lbl = QLabel(path)
        lbl.setStyleSheet(
            f"color:{SYS_TXT_PRIMARY};font-size:11px;background:transparent;"
        )
        lay.addWidget(lbl)
        remove_btn = QPushButton("x")
        remove_btn.setFixedSize(16, 16)
        remove_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remove_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{SYS_TXT_MUTED};"
            "border:none;font-size:11px;}"
            f"QPushButton:hover{{color:{SYS_BADGE_UNSAFE};}}"
        )
        remove_btn.clicked.connect(lambda: self._remove_root(path))
        lay.addWidget(remove_btn)
        return chip

    def _add_root(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Add Project Skills Folder")
        if not folder or folder in self._extra_roots:
            return
        self._extra_roots.append(folder)
        c = cfg.load()
        c["audit_roots"] = self._extra_roots
        cfg.save(c)
        self._render_roots()

    def _remove_root(self, path: str) -> None:
        if path in self._extra_roots:
            self._extra_roots.remove(path)
            c = cfg.load()
            c["audit_roots"] = self._extra_roots
            cfg.save(c)
            self._render_roots()

    # ── Scan ──────────────────────────────────────────────────────────────────

    def _run_scan(self) -> None:
        if self._worker is not None:
            return
        roots = [DEFAULT_AUDIT_ROOT] + [Path(p) for p in self._extra_roots]
        self._scan_btn.setEnabled(False)
        self._scan_btn.setText("Scanning…")
        self._worker = SkillAuditWorker(roots)
        self._worker.finished.connect(self._on_scan_finished)
        self._worker.start()

    def _on_scan_finished(self, entries: list) -> None:
        self._entries = entries
        self._worker = None
        self._scan_btn.setEnabled(True)
        self._scan_btn.setText("Scan Now")
        self._populate_table()

    # ── Table ─────────────────────────────────────────────────────────────────

    def _populate_table(self) -> None:
        self._table.setRowCount(0)
        self._empty_lbl.setVisible(not self._entries)
        self._table.setVisible(bool(self._entries))

        healthy = sum(1 for e in self._entries if e.score >= 75)
        needs_attention = sum(1 for e in self._entries if 50 <= e.score < 75)
        at_risk = sum(1 for e in self._entries if e.score < 50)

        budget = aggregate_budget_report(
            {e.name: str(e.meta.get("description") or "") for e in self._entries}
        )
        self._summary_lbl.setText(
            f"{len(self._entries)} skill(s)  ·  "
            f"{healthy} healthy  ·  {needs_attention} needs attention  ·  {at_risk} at risk  ·  "
            f"description budget: {budget.estimated_total_with_overhead:,}/"
            f"{budget.fallback_budget:,} chars ({budget.budget_used_fraction:.0%})  ·  "
            f"{len(budget.over_legacy_cap)} over legacy cap"
        )

        for entry in self._entries:
            row = self._table.rowCount()
            self._table.insertRow(row)
            self._table.setRowHeight(row, 24)

            colour = score_colour(entry.score)
            desc_status = check_description_length(
                str(entry.meta.get("description") or "")
            )
            if desc_status.over_current_cap:
                desc_colour = SYS_BADGE_UNSAFE
            elif desc_status.over_legacy_cap:
                desc_colour = SYS_BORDER_ADVISORY
            else:
                desc_colour = SYS_BADGE_SAFE

            name_item = QTableWidgetItem(entry.name)
            name_item.setForeground(self._fg(SYS_TXT_PRIMARY))
            folder_item = QTableWidgetItem(entry.folder)
            folder_item.setForeground(self._fg(SYS_TXT_MUTED))
            score_item = QTableWidgetItem(str(entry.score))
            score_item.setForeground(self._fg(colour))
            status_item = QTableWidgetItem(_status_label(entry.score))
            status_item.setForeground(self._fg(colour))
            desc_item = QTableWidgetItem(str(desc_status.description_length))
            desc_item.setForeground(self._fg(desc_colour))

            self._table.setItem(row, 0, name_item)
            self._table.setItem(row, 1, folder_item)
            self._table.setItem(row, 2, score_item)
            self._table.setItem(row, 3, status_item)
            self._table.setItem(row, 4, desc_item)

        if self._entries:
            self._table.selectRow(0)

    @staticmethod
    def _fg(colour: str) -> QColor:
        return QColor(colour)

    def _on_row_selected(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            self._open_folder_btn.setEnabled(False)
            return
        index = rows[0].row()
        if index >= len(self._entries):
            return
        entry = self._entries[index]
        self._detail_browser.setHtml(render_compliance_html(entry.meta, entry.result))
        self._open_folder_btn.setEnabled(True)

    def _set_detail_placeholder(self, text: str) -> None:
        self._detail_browser.setHtml(
            f'<html><body style="background:{SYS_BG_PRIMARY};color:{SYS_TXT_MUTED};'
            f'font-family:Segoe UI,sans-serif;font-size:12px;padding:24px;">'
            f"<p>{text}</p></body></html>"
        )

    def _open_selected_folder(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        index = rows[0].row()
        if index >= len(self._entries):
            return
        subprocess.Popen(["explorer", self._entries[index].folder])
