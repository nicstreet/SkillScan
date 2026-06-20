"""Skill Audit view — batch spec-compliance audit of Claude Code's own skills.

Scans ~/.claude/skills/ plus any user-added project .claude/skills/ folders
against core/spec_compliance.py and surfaces per-skill findings. Distinct from
Folders/Inventory, which track arbitrary scanned locations in the DB — this is
ephemeral (re-run each session) and targets Claude Code's own skill ecosystem.
"""

import html as _html
import subprocess
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QDialog,
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
from ...core import spec_compliance
from ...core.activity_log import log_activity
from ...core.llm import LLMJob
from ...core.skill_audit import DEFAULT_AUDIT_ROOT, AuditEntry, SkillAuditWorker
from ...core.skill_budget import (
    PER_SKILL_CAP_LEGACY,
    aggregate_budget_report,
    check_description_length,
)
from ...core.skill_crowding import CrowdingPair, detect_crowding
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
from .._widgets import SCROLLBAR_STYLE, _BTN_GHOST, _BTN_PRIMARY, _Surface, msg_critical

_REMEDIATE_SYSTEM = (
    "You fix compliance issues in a Claude Agent Skill's SKILL.md frontmatter. "
    "You only ever change the `name` and `description` fields - never invent or "
    "rewrite the skill's body content, which you are shown only for context.\n\n"
    "agentskills.io spec rules for `name`: lowercase letters, numbers, and single "
    "hyphens only; no consecutive or leading/trailing hyphens; must exactly match "
    "the skill's folder name; max 64 characters.\n\n"
    "agentskills.io spec rules for `description`: required, non-empty, max 1024 "
    "characters, must describe both what the skill does and when to use it.\n\n"
    "Claude Code also enforces an unofficial, undocumented shared character "
    "budget across every installed skill's description (~8,000 chars total, "
    "~250 chars before older versions truncate a single entry) - when asked to "
    "shorten a description for this reason, preserve the specific trigger "
    "phrasing that tells Claude *when* to use the skill; do not just truncate.\n\n"
    "Respond with ONLY:\n"
    "<REVISED_NAME>\n...\n</REVISED_NAME>\n"
    "<REVISED_DESCRIPTION>\n...\n</REVISED_DESCRIPTION>\n"
    "<CHANGES_MADE>\n- ...\n</CHANGES_MADE>"
)


def _status_label(score: int) -> str:
    if score >= 75:
        return "Healthy"
    if score >= 50:
        return "Needs Attention"
    return "At Risk"


class _RemediateDialog(QDialog):
    """Frameless modal showing the proposed name/description fix before it's
    written to disk - mirrors _DarkMessageBox's frameless rounded-rect chrome."""

    def __init__(
        self,
        parent,
        skill_name: str,
        old_name: str,
        new_name: str,
        old_desc: str,
        new_desc: str,
        changes: str,
    ):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self._build(skill_name, old_name, new_name, old_desc, new_desc, changes)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, float(self.width()), float(self.height()), 10, 10)
        p.fillPath(path, QColor(SYS_BG_SECONDARY))
        pen = QPen(QColor(SYS_STROKE_DIVIDER))
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        border = QPainterPath()
        border.addRoundedRect(
            0.5, 0.5, self.width() - 1.0, self.height() - 1.0, 9.5, 9.5
        )
        p.drawPath(border)
        p.end()

    def _build(
        self,
        skill_name: str,
        old_name: str,
        new_name: str,
        old_desc: str,
        new_desc: str,
        changes: str,
    ) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 16)
        outer.setSpacing(12)

        title_lbl = QLabel(f"Remediate — {skill_name}")
        title_lbl.setStyleSheet(
            f"color:{SYS_TXT_PRIMARY};font-size:14px;font-weight:700;background:transparent;"
        )
        outer.addWidget(title_lbl)

        browser = QTextBrowser()
        browser.setMinimumSize(480, 320)
        browser.setStyleSheet(
            f"QTextBrowser{{background:{SYS_BG_PRIMARY};border:none;border-radius:6px;}}"
        )
        browser.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        browser.setHtml(
            self._render_html(old_name, new_name, old_desc, new_desc, changes)
        )
        outer.addWidget(browser, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addStretch()
        reject_btn = QPushButton("Reject")
        reject_btn.setFixedHeight(30)
        reject_btn.setMinimumWidth(72)
        reject_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reject_btn.setStyleSheet(_BTN_GHOST)
        reject_btn.clicked.connect(self.reject)
        btn_row.addWidget(reject_btn)
        accept_btn = QPushButton("Accept && Apply")
        accept_btn.setFixedHeight(30)
        accept_btn.setMinimumWidth(110)
        accept_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        accept_btn.setStyleSheet(_BTN_PRIMARY)
        accept_btn.clicked.connect(self.accept)
        btn_row.addWidget(accept_btn)
        outer.addLayout(btn_row)

        self.setMinimumWidth(520)

    @staticmethod
    def _render_html(
        old_name: str, new_name: str, old_desc: str, new_desc: str, changes: str
    ) -> str:
        def block(label: str, old: str, new: str) -> str:
            old_e = _html.escape(old or "(missing)")
            new_e = _html.escape(new or "(missing)")
            if old == new:
                old_html, new_html = old_e, new_e
            else:
                old_html = (
                    f'<span style="background:{SYS_BADGE_UNSAFE}22;'
                    f'color:{SYS_BADGE_UNSAFE};text-decoration:line-through;">{old_e}</span>'
                )
                new_html = (
                    f'<span style="background:{SYS_BADGE_SAFE}22;'
                    f'color:{SYS_BADGE_SAFE};">{new_e}</span>'
                )
            return (
                f'<p style="font-size:11px;font-weight:700;color:{SYS_TXT_MUTED};'
                f'letter-spacing:1px;margin-bottom:6px;">{label}</p>'
                f'<p style="margin:2px 0;">Before: {old_html}</p>'
                f'<p style="margin:2px 0 16px;">After: {new_html}</p>'
            )

        changes_html = ""
        lines = [ln.lstrip("- ").strip() for ln in changes.splitlines() if ln.strip()]
        if lines:
            items = "".join(f"<li>{_html.escape(ln)}</li>" for ln in lines)
            changes_html = (
                f'<p style="font-size:11px;font-weight:700;color:{SYS_TXT_MUTED};'
                f'letter-spacing:1px;margin-bottom:6px;">CHANGES MADE</p>'
                f'<ul style="margin:0;padding-left:18px;">{items}</ul>'
            )

        return (
            f'<html><body style="background:{SYS_BG_PRIMARY};color:{SYS_TXT_PRIMARY};'
            f'font-family:Segoe UI,sans-serif;font-size:12px;padding:4px;">'
            + block("NAME", old_name, new_name)
            + block("DESCRIPTION", old_desc, new_desc)
            + changes_html
            + "</body></html>"
        )


class SkillAuditView(QWidget):
    """Table of audited skills (worst score first) + detail pane on selection."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._extra_roots: list[str] = []
        self._entries: list[AuditEntry] = []
        self._crowding_pairs: list[CrowdingPair] = []
        self._worker: SkillAuditWorker | None = None
        self._scanned_once = False
        self._remediate_entry: AuditEntry | None = None
        self._remediate_job: LLMJob | None = None
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

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(8, 0, 8, 8)
        btn_row.setSpacing(8)

        self._open_folder_btn = QPushButton("Open Folder")
        self._open_folder_btn.setFixedHeight(28)
        self._open_folder_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._open_folder_btn.setEnabled(False)
        self._open_folder_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{SYS_TXT_MUTED};"
            f"border:1px solid {SYS_STROKE_SUBTLE};border-radius:4px;font-size:11px;}}"
            f"QPushButton:hover{{color:{SYS_TXT_PRIMARY};border-color:{SYS_TXT_PRIMARY};}}"
            f"QPushButton:disabled{{color:{SYS_STROKE_SUBTLE};}}"
        )
        self._open_folder_btn.clicked.connect(self._open_selected_folder)
        btn_row.addWidget(self._open_folder_btn)

        self._remediate_btn = QPushButton("Remediate")
        self._remediate_btn.setFixedHeight(28)
        self._remediate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._remediate_btn.setEnabled(False)
        self._remediate_btn.setStyleSheet(
            f"QPushButton{{background:{SYS_ACTION_PRIMARY};color:{SYS_TXT_PRIMARY};"
            "border:none;border-radius:4px;font-size:11px;}"
            "QPushButton:hover{background:#0f9e92;}"
            f"QPushButton:disabled{{background:{SYS_STROKE_SUBTLE};color:{SYS_TXT_MUTED};}}"
        )
        self._remediate_btn.clicked.connect(self._remediate_selected)
        btn_row.addWidget(self._remediate_btn)

        detail_lay.addLayout(btn_row)

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

        descriptions = {
            e.name: str(e.meta.get("description") or "") for e in self._entries
        }
        budget = aggregate_budget_report(descriptions)
        self._crowding_pairs = detect_crowding(descriptions)
        self._summary_lbl.setText(
            f"{len(self._entries)} skill(s)  ·  "
            f"{healthy} healthy  ·  {needs_attention} needs attention  ·  {at_risk} at risk  ·  "
            f"description budget: {budget.estimated_total_with_overhead:,}/"
            f"{budget.fallback_budget:,} chars ({budget.budget_used_fraction:.0%})  ·  "
            f"{len(budget.over_legacy_cap)} over legacy cap  ·  "
            f"{len(self._crowding_pairs)} crowding pair(s)"
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
            self._remediate_btn.setEnabled(False)
            return
        index = rows[0].row()
        if index >= len(self._entries):
            return
        entry = self._entries[index]
        html = render_compliance_html(entry.meta, entry.result)
        crowding_html = self._crowding_html(entry.name)
        if crowding_html:
            html = html.replace("</body></html>", crowding_html + "</body></html>")
        self._detail_browser.setHtml(html)
        self._open_folder_btn.setEnabled(True)
        self._remediate_btn.setEnabled(
            self._remediate_job is None and self._entry_has_issues(entry)
        )

    def _crowding_html(self, skill_name: str) -> str:
        related = [
            p for p in self._crowding_pairs if skill_name in (p.skill_a, p.skill_b)
        ]
        if not related:
            return ""
        rows = []
        for p in related:
            other = p.skill_b if p.skill_a == skill_name else p.skill_a
            rows.append(
                f"<li>Overlaps with <b>{_html.escape(other)}</b> "
                f"({p.overlap:.0%} shared vocabulary: "
                f'{_html.escape(", ".join(p.shared_keywords[:6]))})</li>'
            )
        return (
            f'<p style="font-size:11px;font-weight:700;color:{SYS_TXT_MUTED};'
            f'letter-spacing:1px;margin:16px 0 8px;">DOMAIN CROWDING</p>'
            f'<ul style="margin:0;padding-left:18px;color:{SYS_BORDER_ADVISORY};">'
            + "".join(rows)
            + "</ul>"
            f'<p style="font-size:10px;color:{SYS_TXT_MUTED};margin-top:4px;">'
            "Lexical-overlap heuristic, not certain - a vague sibling can "
            "degrade a clear neighbor's selection accuracy even when both "
            "descriptions are individually fine. See evals/skill_selection/ "
            "for the benchmark that found this.</p>"
        )

    @staticmethod
    def _entry_has_issues(entry: AuditEntry) -> bool:
        if entry.score < 100:
            return True
        desc = str(entry.meta.get("description") or "")
        return check_description_length(desc).over_legacy_cap

    # ── Remediate ─────────────────────────────────────────────────────────────

    def _build_remediate_prompt(self, entry: AuditEntry) -> str:
        meta = entry.meta
        result = entry.result
        folder_name = Path(entry.folder).name

        issues: list[str] = []
        if "name" in result.missing_required:
            issues.append("name is missing")
        if "description" in result.missing_required:
            issues.append("description is missing")
        issues.extend(result.name_errors)
        issues.extend(result.description_errors)
        desc_status = check_description_length(str(meta.get("description") or ""))
        if desc_status.over_legacy_cap:
            issues.append(
                f"description is {desc_status.description_length} characters - "
                f"shorten to roughly {PER_SKILL_CAP_LEGACY} characters or fewer to "
                f"stay clear of Claude Code's per-skill listing-display cap"
            )
        if not issues:
            issues.append("description could be clearer about when to use this skill")

        body = spec_compliance.parse_body(entry.path)[:2000]

        return (
            f"Skill folder name (the `name` field MUST exactly match this): {folder_name}\n\n"
            f"Current name: {meta.get('name') or '(missing)'}\n"
            f"Current description: {meta.get('description') or '(missing)'}\n\n"
            f"Issues to fix:\n" + "\n".join(f"- {i}" for i in issues) + "\n\n"
            f"Body content (for context only - do not rewrite this):\n{body}"
        )

    @staticmethod
    def _parse_remediate_response(text: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for tag in ("REVISED_NAME", "REVISED_DESCRIPTION", "CHANGES_MADE"):
            open_tag, close_tag = f"<{tag}>", f"</{tag}>"
            start = text.find(open_tag)
            if start == -1:
                result[tag] = ""
                continue
            start += len(open_tag)
            end = text.rfind(close_tag)
            result[tag] = (
                text[start:end].strip() if end > start else text[start:].strip()
            )
        return result

    def _remediate_selected(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        if not rows:
            return
        index = rows[0].row()
        if index >= len(self._entries):
            return
        entry = self._entries[index]
        self._remediate_entry = entry
        prompt = self._build_remediate_prompt(entry)

        self._remediate_btn.setEnabled(False)
        self._remediate_btn.setText("Remediating…")
        self._remediate_job = LLMJob(prompt, system=_REMEDIATE_SYSTEM)
        self._remediate_job.finished.connect(self._on_remediate_done)
        self._remediate_job.error.connect(self._on_remediate_error)
        self._remediate_job.start()

    def _on_remediate_done(self, text: str) -> None:
        self._remediate_job = None
        self._remediate_btn.setText("Remediate")
        entry = self._remediate_entry
        if entry is None:
            return

        parsed = self._parse_remediate_response(text)
        old_name = str(entry.meta.get("name") or "")
        old_desc = str(entry.meta.get("description") or "")
        new_name = parsed.get("REVISED_NAME", "").strip() or old_name or entry.name
        new_desc = parsed.get("REVISED_DESCRIPTION", "").strip() or old_desc

        dlg = _RemediateDialog(
            self,
            entry.name,
            old_name,
            new_name,
            old_desc,
            new_desc,
            parsed.get("CHANGES_MADE", ""),
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._apply_remediation(entry, new_name, new_desc)
        else:
            self._remediate_btn.setEnabled(self._entry_has_issues(entry))

    def _on_remediate_error(self, message: str) -> None:
        self._remediate_job = None
        self._remediate_btn.setText("Remediate")
        if self._remediate_entry is not None:
            self._remediate_btn.setEnabled(
                self._entry_has_issues(self._remediate_entry)
            )
        msg_critical(self, "Remediate Failed", message)

    def _apply_remediation(
        self, entry: AuditEntry, new_name: str, new_desc: str
    ) -> None:
        path = entry.path
        try:
            original_text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            msg_critical(self, "Remediate Failed", f"Could not read {path}: {exc}")
            return

        meta = dict(entry.meta)
        meta["name"] = new_name.strip()
        meta["description"] = new_desc.strip()
        body = spec_compliance.parse_body(path)

        import yaml

        frontmatter = yaml.dump(
            meta, default_flow_style=False, allow_unicode=True, sort_keys=False
        )
        new_text = f"---\n{frontmatter}---\n\n{body}"

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = path.parent / f"{path.name}.bak-{timestamp}"
        try:
            backup_path.write_text(original_text, encoding="utf-8")
            path.write_text(new_text, encoding="utf-8")
        except OSError as exc:
            msg_critical(self, "Remediate Failed", f"Could not write {path}: {exc}")
            return

        log_activity("Skill remediated", f"{entry.name} (backup: {backup_path.name})")
        self._run_scan()

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
