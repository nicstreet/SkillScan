"""Project Setup — entry screen for the "process chain from prompt onwards"
(see .claude/architecture/project-setup-flow.md). The first user-facing
screen in the chain: type a rough idea, pick where to build it, and a
background worker runs Intent Parser -> local skill matching -> Project
Scaffolder, then hands off to HandoffSummaryView.

Framework only, deliberately - not yet wired into main_window.py's nav
stack. Greenfield only (same boundary core/project_scaffolder.py already
draws): no named templates, no retrofit, no folder-root picker beyond
"where should the new project folder go". This is the piece that finally
makes the chain runnable end-to-end as one flow, not three separately-
tested pieces - what it does NOT yet do (Gap Detection, the background
Skill Supply Chain, a Cowork launch option) is exactly what's still listed
as deferred in todo.md.
"""

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ...core.project_build_worker import ProjectBuildWorker
from .._palette import (
    SYS_ACTION_PRIMARY,
    SYS_BADGE_UNSAFE,
    SYS_CONTROL_BG,
    SYS_STROKE_SUBTLE,
    SYS_TXT_MUTED,
    SYS_TXT_PRIMARY,
)
from .._widgets import msg_critical
from .handoff_summary_view import HandoffSummaryView

_TEXT_INPUT_STYLE = (
    f"background:{SYS_CONTROL_BG};color:{SYS_TXT_PRIMARY};"
    f"border:1px solid {SYS_STROKE_SUBTLE};border-radius:5px;padding:6px;font-size:12px;"
)


class ProjectSetupView(QWidget):
    """Entry screen: rough idea in, scaffolded project + Handoff Summary out."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: ProjectBuildWorker | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        self._entry_page = self._build_entry_page()
        self._stack.addWidget(self._entry_page)

        self._summary_view = HandoffSummaryView()
        self._stack.addWidget(self._summary_view)

    def _build_entry_page(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(10)

        title = QLabel("Build a New Project")
        title.setStyleSheet(
            f"color:{SYS_TXT_PRIMARY};font-size:16px;font-weight:700;background:transparent;"
        )
        lay.addWidget(title)

        subtitle = QLabel(
            "Describe what you want to build, in your own words — a rough idea is fine."
        )
        subtitle.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:12px;background:transparent;"
        )
        subtitle.setWordWrap(True)
        lay.addWidget(subtitle)

        self._idea_edit = QPlainTextEdit()
        self._idea_edit.setPlaceholderText(
            "e.g. I want something that helps me track my photo collection "
            "and find duplicates"
        )
        self._idea_edit.setFixedHeight(90)
        self._idea_edit.setStyleSheet(f"QPlainTextEdit{{{_TEXT_INPUT_STYLE}}}")
        self._idea_edit.textChanged.connect(self._update_build_enabled)
        lay.addWidget(self._idea_edit)

        dir_row = QHBoxLayout()
        self._dir_edit = QLineEdit()
        self._dir_edit.setReadOnly(True)
        self._dir_edit.setPlaceholderText("Where should the new project folder go?")
        self._dir_edit.setStyleSheet(_TEXT_INPUT_STYLE)
        dir_row.addWidget(self._dir_edit, 1)

        browse_btn = QPushButton("Browse…")
        browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        browse_btn.setStyleSheet(
            f"QPushButton{{background:{SYS_CONTROL_BG};color:{SYS_TXT_PRIMARY};"
            f"border:1px solid {SYS_STROKE_SUBTLE};border-radius:5px;padding:6px 14px;"
            "font-size:12px;}"
        )
        browse_btn.clicked.connect(self._on_browse_clicked)
        dir_row.addWidget(browse_btn)
        lay.addLayout(dir_row)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;"
        )
        lay.addWidget(self._status_lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._build_btn = QPushButton("Build It")
        self._build_btn.setFixedHeight(32)
        self._build_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_btn.setEnabled(False)
        self._build_btn.setStyleSheet(
            f"QPushButton{{background:{SYS_ACTION_PRIMARY};color:{SYS_TXT_PRIMARY};"
            "border:none;border-radius:5px;padding:0 18px;font-size:12px;font-weight:600;}"
            "QPushButton:hover{background:#0f9e92;}"
            f"QPushButton:disabled{{background:{SYS_STROKE_SUBTLE};color:{SYS_TXT_MUTED};}}"
        )
        self._build_btn.clicked.connect(self._on_build_clicked)
        btn_row.addWidget(self._build_btn)
        lay.addLayout(btn_row)

        lay.addStretch(1)
        return page

    def _update_build_enabled(self) -> None:
        has_idea = bool(self._idea_edit.toPlainText().strip())
        has_dir = bool(self._dir_edit.text().strip())
        self._build_btn.setEnabled(has_idea and has_dir and self._worker is None)

    def _on_browse_clicked(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select where to create the new project folder"
        )
        if folder:
            self._dir_edit.setText(folder)
            self._update_build_enabled()

    def _on_build_clicked(self) -> None:
        rough_idea = self._idea_edit.toPlainText().strip()
        parent_dir = Path(self._dir_edit.text().strip())
        if not rough_idea or not parent_dir:
            return

        self._build_btn.setEnabled(False)
        self._set_status("Understanding your idea…", error=False)

        self._worker = ProjectBuildWorker(rough_idea, parent_dir, parent=self)
        self._worker.progress.connect(lambda msg: self._set_status(msg, error=False))
        self._worker.finished.connect(self._on_build_finished)
        self._worker.error.connect(self._on_build_error)
        self._worker.start()

    def _on_build_finished(self, intent, scaffold_result) -> None:
        self._worker = None
        self._set_status("", error=False)
        self._build_btn.setEnabled(True)
        self._summary_view.load(intent, scaffold_result)
        self._stack.setCurrentWidget(self._summary_view)

    def _on_build_error(self, message: str) -> None:
        self._worker = None
        self._build_btn.setEnabled(True)
        self._set_status("", error=False)
        msg_critical(self, "Build Failed", message)

    def _set_status(self, text: str, error: bool) -> None:
        color = SYS_BADGE_UNSAFE if error else SYS_TXT_MUTED
        self._status_lbl.setStyleSheet(
            f"color:{color};font-size:11px;background:transparent;"
        )
        self._status_lbl.setText(text)
