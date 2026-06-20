"""Handoff Summary — final screen in the "process chain from prompt onwards"
(see .claude/architecture/project-setup-flow.md). Shows what got built and
which skills got wired in, then launches Claude Code as its own process.

Framework only, deliberately - not wired into main_window's nav stack yet
(there's no prompt-entry screen to reach it from), but real and directly
testable rather than waiting for the full Project Setup wizard to exist
first. Will grow: a Cowork launch option once that mechanism is confirmed
(see core/launch.py), gap-detection results once that's built, a richer
file-tree preview, and the approval-dialog step for anything the background
Skill Supply Chain flags - none of that exists yet, so none of it is here.
"""

import html as _html

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ...core.intent_parser import IntentResult
from ...core.launch import LaunchError, claude_code_available, launch_claude_code
from ...core.project_scaffolder import ScaffoldResult
from .._palette import (
    SYS_ACTION_PRIMARY,
    SYS_BADGE_SAFE,
    SYS_BADGE_UNSAFE,
    SYS_BG_PRIMARY,
    SYS_STROKE_SUBTLE,
    SYS_TXT_MUTED,
    SYS_TXT_PRIMARY,
)
from .._widgets import SCROLLBAR_STYLE, _Surface, msg_critical


class HandoffSummaryView(QWidget):
    """What got built, which skills wired in, then launch."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scaffold_result: ScaffoldResult | None = None
        self._build_ui()

    def load(self, intent: IntentResult, scaffold_result: ScaffoldResult) -> None:
        self._scaffold_result = scaffold_result
        self._browser.setHtml(self._render_html(intent, scaffold_result))
        self._update_launch_availability()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel("Project Ready")
        title.setStyleSheet(
            f"color:{SYS_TXT_PRIMARY};font-size:16px;font-weight:700;background:transparent;"
        )
        root.addWidget(title)

        card = _Surface(SYS_BG_PRIMARY, radius=8)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(1, 1, 1, 1)
        card_lay.setSpacing(0)

        self._browser = QTextBrowser()
        self._browser.setStyleSheet(
            f"QTextBrowser{{background:{SYS_BG_PRIMARY};border:none;}}"
        )
        self._browser.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        self._set_placeholder("No project scaffolded yet.")
        card_lay.addWidget(self._browser)
        root.addWidget(card, 1)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;"
        )
        root.addWidget(self._status_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._launch_btn = QPushButton("Launch Claude Code")
        self._launch_btn.setFixedHeight(32)
        self._launch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._launch_btn.setEnabled(False)
        self._launch_btn.setStyleSheet(
            f"QPushButton{{background:{SYS_ACTION_PRIMARY};color:{SYS_TXT_PRIMARY};"
            "border:none;border-radius:5px;padding:0 18px;font-size:12px;font-weight:600;}"
            "QPushButton:hover{background:#0f9e92;}"
            f"QPushButton:disabled{{background:{SYS_STROKE_SUBTLE};color:{SYS_TXT_MUTED};}}"
        )
        self._launch_btn.clicked.connect(self._on_launch_clicked)
        btn_row.addWidget(self._launch_btn)
        root.addLayout(btn_row)

    def _update_launch_availability(self) -> None:
        available = claude_code_available()
        self._launch_btn.setEnabled(available and self._scaffold_result is not None)
        if not available:
            self._status_lbl.setText(
                "claude CLI not found on PATH — install Claude Code to launch."
            )
            self._status_lbl.setStyleSheet(
                f"color:{SYS_BADGE_UNSAFE};font-size:11px;background:transparent;"
            )
        else:
            self._status_lbl.setText("")

    def _on_launch_clicked(self) -> None:
        if self._scaffold_result is None:
            return
        try:
            launch_claude_code(self._scaffold_result.target_dir)
            self._status_lbl.setText(
                f"Launched Claude Code in {self._scaffold_result.target_dir}"
            )
            self._status_lbl.setStyleSheet(
                f"color:{SYS_BADGE_SAFE};font-size:11px;background:transparent;"
            )
        except LaunchError as exc:
            msg_critical(self, "Launch Failed", str(exc))

    def _set_placeholder(self, text: str) -> None:
        self._browser.setHtml(
            f'<html><body style="background:{SYS_BG_PRIMARY};color:{SYS_TXT_MUTED};'
            f'font-family:Segoe UI,sans-serif;font-size:12px;padding:24px;">'
            f"<p>{text}</p></body></html>"
        )

    @staticmethod
    def _render_html(intent: IntentResult, scaffold_result: ScaffoldResult) -> str:
        parts = [
            f'<html><body style="background:{SYS_BG_PRIMARY};color:{SYS_TXT_PRIMARY};'
            f'font-family:Segoe UI,sans-serif;font-size:12px;padding:4px;">',
            f'<p style="font-size:14px;font-weight:700;">{_html.escape(intent.project_type)}</p>',
            f'<p style="color:{SYS_TXT_MUTED};">{_html.escape(intent.summary)}</p>',
            f'<p style="font-size:11px;font-weight:700;color:{SYS_TXT_MUTED};'
            f'letter-spacing:1px;margin-top:16px;">STACK</p>',
            f"<p>{_html.escape(intent.stack)}</p>",
            f'<p style="font-size:11px;font-weight:700;color:{SYS_TXT_MUTED};'
            f'letter-spacing:1px;margin-top:16px;">LOCATION</p>',
            f"<p>{_html.escape(str(scaffold_result.target_dir))}</p>",
            f'<p style="font-size:11px;font-weight:700;color:{SYS_TXT_MUTED};'
            f'letter-spacing:1px;margin-top:16px;">BUILD PLAN</p>',
        ]
        for stage in intent.stages:
            parts.append(
                f'<p style="margin:8px 0 2px;"><b>{_html.escape(stage.name)}</b></p>'
            )
            parts.append(
                f'<p style="color:{SYS_TXT_MUTED};margin:0 0 4px;">'
                f"{_html.escape(stage.goal)}</p>"
            )
        if scaffold_result.wired_skills:
            parts.append(
                f'<p style="font-size:11px;font-weight:700;color:{SYS_TXT_MUTED};'
                f'letter-spacing:1px;margin-top:16px;">SKILLS WIRED IN '
                f"({len(scaffold_result.wired_skills)})</p>"
            )
            parts.append('<ul style="margin:4px 0;padding-left:18px;">')
            for name in scaffold_result.wired_skills:
                parts.append(f"<li>{_html.escape(name)}</li>")
            parts.append("</ul>")
        else:
            parts.append(
                f'<p style="color:{SYS_BADGE_UNSAFE};margin-top:16px;">'
                "No local skills matched - nothing wired in yet.</p>"
            )
        parts.append("</body></html>")
        return "".join(parts)
