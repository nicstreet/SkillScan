"""Testing view — eval test skills and MCP manifest detection."""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ...core import test_skills as ts
from ...core.test_skills import McpEval
from .._palette import (
    SYS_ACTION_PRIMARY,
    SYS_ACTION_HOVER,
    SYS_BG_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_BADGE_UNSAFE,
    SYS_BORDER_WARNING,
    SYS_STROKE_SUBTLE,
    SYS_TXT_PRIMARY,
    SYS_BORDER_ADVISORY,
    SYS_TXT_MUTED,
    SYS_BADGE_SAFE,
)

_SEVERITY_COLOUR = {
    "CLEAN": SYS_BADGE_SAFE,
    "MEDIUM": SYS_BORDER_ADVISORY,
    "HIGH": SYS_BORDER_WARNING,
    "CRITICAL": SYS_BADGE_UNSAFE,
}


def _styled_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {SYS_TXT_PRIMARY};
            border: 1px solid {SYS_STROKE_SUBTLE};
            border-radius: 6px;
            padding: 5px 14px;
            font-size: 12px;
        }}
        QPushButton:hover   {{ border-color: {SYS_ACTION_PRIMARY}; color: {SYS_ACTION_PRIMARY}; }}
        QPushButton:pressed {{ background: #0f2028; }}
        QPushButton:disabled {{ color: {SYS_TXT_MUTED}; border-color: {SYS_STROKE_SUBTLE}; }}
    """)
    return btn


def _primary_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {SYS_ACTION_PRIMARY};
            color: {SYS_TXT_PRIMARY};
            border: none;
            border-radius: 6px;
            padding: 5px 14px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover   {{ background: {SYS_ACTION_HOVER}; }}
        QPushButton:pressed {{ background: {SYS_ACTION_HOVER}; }}
        QPushButton:disabled {{ background: {SYS_BG_PRIMARY}; color: {SYS_TXT_MUTED}; }}
    """)
    return btn


def _divider() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setFixedHeight(1)
    line.setStyleSheet(f"background:{SYS_STROKE_SUBTLE};border:none;")
    return line


_GRP_STYLE = f"""
    QGroupBox {{
        color: {SYS_TXT_MUTED};
        font-size: 11px;
        font-weight: 600;
        border: 1px solid {SYS_STROKE_SUBTLE};
        border-radius: 8px;
        margin-top: 8px;
        padding-top: 8px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
    }}
"""


# ── MCP eval row ──────────────────────────────────────────────────────────────


class _McpEvalRow(QWidget):
    def __init__(self, eval: McpEval, parent=None):
        super().__init__(parent)
        self._eval = eval
        self._build_ui()

    def _build_ui(self) -> None:
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 3, 0, 3)
        row.setSpacing(10)

        name_lbl = QLabel(self._eval.name)
        name_lbl.setStyleSheet(
            f"color:{SYS_TXT_PRIMARY};font-size:11px;background:transparent;"
        )
        row.addWidget(name_lbl, 1)

        sev = self._eval.expected_severity
        sev_color = _SEVERITY_COLOUR.get(sev, SYS_TXT_MUTED)
        sev_lbl = QLabel(sev)
        sev_lbl.setStyleSheet(
            f"color:{sev_color};font-size:10px;font-weight:700;"
            f"background:transparent;letter-spacing:1px;"
        )
        sev_lbl.setFixedWidth(72)
        row.addWidget(sev_lbl)

        self._result_lbl = QLabel("—")
        self._result_lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;"
        )
        self._result_lbl.setFixedWidth(84)
        row.addWidget(self._result_lbl)

        detect_btn = _styled_btn("Detect")
        detect_btn.setFixedWidth(68)
        detect_btn.clicked.connect(self.run_detect)
        row.addWidget(detect_btn)

    def run_detect(self) -> bool:
        try:
            from ...core.router import detect_type, SpecType

            result = detect_type(self._eval.path)
            if result == SpecType.MCP_MANIFEST:
                self._result_lbl.setText("✓ MCP")
                self._result_lbl.setStyleSheet(
                    f"color:{SYS_BADGE_SAFE};font-size:11px;"
                    f"font-weight:700;background:transparent;"
                )
                return True
            else:
                self._result_lbl.setText(f"✗ {result.value}")
                self._result_lbl.setStyleSheet(
                    f"color:{SYS_BADGE_UNSAFE};font-size:11px;"
                    f"font-weight:700;background:transparent;"
                )
                return False
        except Exception:
            self._result_lbl.setText("error")
            self._result_lbl.setStyleSheet(
                f"color:{SYS_BORDER_ADVISORY};font-size:11px;background:transparent;"
            )
            return False


# ── Main view ────────────────────────────────────────────────────────────────


class TestingView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {SYS_BG_SECONDARY};")
        self._mcp_rows: list[_McpEvalRow] = []
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"background:{SYS_BG_SECONDARY};border:none;")

        content = QWidget()
        content.setStyleSheet(f"background:{SYS_BG_SECONDARY};")
        root = QVBoxLayout(content)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(20)

        heading = QLabel("Testing")
        heading.setAlignment(Qt.AlignmentFlag.AlignLeft)
        heading.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:14px;background:transparent;"
        )
        root.addWidget(heading)

        self._build_skills_section(root)
        self._build_mcp_section(root)

        attrib = QLabel(
            "Skills sourced from "
            "<a href='https://github.com/cisco-ai-defense/skill-scanner' "
            f"style='color:{SYS_ACTION_PRIMARY};'>"
            "cisco-ai-defense/skill-scanner</a> "
            "(<a href='https://www.apache.org/licenses/LICENSE-2.0' "
            f"style='color:{SYS_ACTION_PRIMARY};'>Apache 2.0</a>) "
            "© 2026 Cisco Systems, Inc."
        )
        attrib.setOpenExternalLinks(True)
        attrib.setWordWrap(True)
        attrib.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:10px;background:transparent;"
        )
        root.addWidget(attrib)
        root.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    # ── Eval Test Skills ──────────────────────────────────────────────────────

    def _build_skills_section(self, root: QVBoxLayout) -> None:
        grp = QGroupBox("Evaluation Skills  (for testing purposes only)")
        grp.setStyleSheet(_GRP_STYLE)
        lay = QVBoxLayout(grp)
        lay.setSpacing(12)
        lay.setContentsMargins(16, 12, 16, 16)

        desc = QLabel(
            "Curated safe and malicious SKILL.md samples from the "
            "cisco-ai-defense/skill-scanner eval suite."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;"
        )
        lay.addWidget(desc)

        lay.addWidget(_divider())

        self._skill_loc_lbl = QLabel()
        self._skill_loc_lbl.setWordWrap(True)
        self._skill_loc_lbl.setStyleSheet(
            f"color:{SYS_TXT_PRIMARY};font-size:11px;background:transparent;"
        )
        lay.addWidget(self._skill_loc_lbl)

        self._skill_progress_lbl = QLabel()
        self._skill_progress_lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;"
        )
        self._skill_progress_lbl.hide()
        lay.addWidget(self._skill_progress_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._dl_skills_btn = _primary_btn("Download Skills")
        self._dl_skills_btn.clicked.connect(self._download_skills)
        btn_row.addWidget(self._dl_skills_btn)

        self._open_skills_btn = _styled_btn("Open Skills Folder")
        self._open_skills_btn.clicked.connect(ts.open_folder)
        btn_row.addWidget(self._open_skills_btn)

        guide_btn = _styled_btn("Open Testing Guide")
        guide_btn.clicked.connect(ts.open_guide)
        btn_row.addWidget(guide_btn)

        btn_row.addStretch()
        lay.addLayout(btn_row)

        root.addWidget(grp)
        self._refresh_skills_status()

    def _refresh_skills_status(self) -> None:
        if ts.is_downloaded():
            count = ts.skill_count()
            self._skill_loc_lbl.setText(
                f"<b style='color:{SYS_ACTION_PRIMARY}'>{count} skill{'s' if count != 1 else ''}</b>"
                f" downloaded to:<br>"
                f"<code style='color:{SYS_TXT_MUTED}'>{ts.SKILL_EVALS_DIR}</code>"
            )
            self._dl_skills_btn.setText("Re-download Skills")
            self._open_skills_btn.setEnabled(True)
        else:
            self._skill_loc_lbl.setText(
                f"<span style='color:{SYS_TXT_MUTED}'>No skills downloaded yet.</span><br>"
                f"<code style='color:{SYS_TXT_MUTED}'>{ts.SKILL_EVALS_DIR}</code>"
            )
            self._dl_skills_btn.setText("Download Skills")
            self._open_skills_btn.setEnabled(False)

    def _download_skills(self) -> None:
        self._dl_skills_btn.setEnabled(False)
        self._skill_progress_lbl.setText("Starting…")
        self._skill_progress_lbl.show()
        self._dl_skills_thread = ts.DownloadThread()
        self._dl_skills_thread.progress.connect(self._skill_progress_lbl.setText)
        self._dl_skills_thread.finished.connect(self._on_skills_done)
        self._dl_skills_thread.start()

    def _on_skills_done(self, success: bool, message: str) -> None:
        self._dl_skills_btn.setEnabled(True)
        if success:
            self._skill_progress_lbl.setText(f"Done — {message}")
            self._refresh_skills_status()
        else:
            self._skill_progress_lbl.setText(f"Error: {message}")

    # ── MCP Manifest Evals ────────────────────────────────────────────────────

    def _build_mcp_section(self, root: QVBoxLayout) -> None:
        grp = QGroupBox("Evaluation MCP Manifests  (for testing purposes only)")
        grp.setStyleSheet(_GRP_STYLE)
        lay = QVBoxLayout(grp)
        lay.setSpacing(12)
        lay.setContentsMargins(16, 12, 16, 16)

        desc = QLabel("Tests router type detection for MCP server definitions.")
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;"
        )
        lay.addWidget(desc)

        lay.addWidget(_divider())

        self._mcp_loc_lbl = QLabel()
        self._mcp_loc_lbl.setWordWrap(True)
        self._mcp_loc_lbl.setStyleSheet(
            f"color:{SYS_TXT_PRIMARY};font-size:11px;background:transparent;"
        )
        lay.addWidget(self._mcp_loc_lbl)

        self._mcp_progress_lbl = QLabel()
        self._mcp_progress_lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;"
        )
        self._mcp_progress_lbl.hide()
        lay.addWidget(self._mcp_progress_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._dl_mcp_btn = _primary_btn("Download MCPs")
        self._dl_mcp_btn.clicked.connect(self._download_mcp)
        btn_row.addWidget(self._dl_mcp_btn)

        self._open_mcp_btn = _styled_btn("Open MCPs Folder")
        self._open_mcp_btn.clicked.connect(ts.open_mcp_evals_folder)
        btn_row.addWidget(self._open_mcp_btn)

        btn_row.addStretch()
        lay.addLayout(btn_row)

        evals = ts.mcp_eval_list()
        if evals:
            lay.addWidget(_divider())

            hdr = QHBoxLayout()
            hdr.setContentsMargins(0, 4, 0, 0)
            hdr.setSpacing(10)
            for text, stretch, w in [
                ("Manifest", 1, None),
                ("Expected", 0, 72),
                ("Detected", 0, 84),
                ("", 0, 68),
            ]:
                lbl = QLabel(text)
                lbl.setStyleSheet(
                    f"color:{SYS_TXT_MUTED};font-size:10px;font-weight:700;"
                    f"letter-spacing:1px;background:transparent;"
                )
                if w:
                    lbl.setFixedWidth(w)
                hdr.addWidget(lbl, stretch)
            lay.addLayout(hdr)

            for eval_ in evals:
                row_widget = _McpEvalRow(eval_)
                self._mcp_rows.append(row_widget)
                lay.addWidget(row_widget)

            detect_row = QHBoxLayout()
            detect_all_btn = _primary_btn("Detect All")
            detect_all_btn.clicked.connect(self._run_all_detections)
            detect_row.addWidget(detect_all_btn)
            detect_row.addStretch()
            lay.addLayout(detect_row)

        note = QLabel(
            "ⓘ  Full severity analysis (LLM-based) for MCP manifests — Phase 7"
        )
        note.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:10px;background:transparent;font-style:italic;"
        )
        lay.addWidget(note)

        root.addWidget(grp)
        self._refresh_mcp_status()

    def _refresh_mcp_status(self) -> None:
        count = ts.mcp_eval_count()
        if count:
            self._mcp_loc_lbl.setText(
                f"<b style='color:{SYS_ACTION_PRIMARY}'>{count} manifest{'s' if count != 1 else ''}</b>"
                f" bundled at:<br>"
                f"<code style='color:{SYS_TXT_MUTED}'>{ts.MCP_EVALS_DIR}</code>"
            )
            self._dl_mcp_btn.setText("Re-download MCPs")
            self._open_mcp_btn.setEnabled(True)
        else:
            self._mcp_loc_lbl.setText(
                f"<span style='color:{SYS_TXT_MUTED}'>No MCP manifests found.</span><br>"
                f"<code style='color:{SYS_TXT_MUTED}'>{ts.MCP_EVALS_DIR}</code>"
            )
            self._dl_mcp_btn.setText("Download MCPs")
            self._open_mcp_btn.setEnabled(False)

    def _download_mcp(self) -> None:
        self._dl_mcp_btn.setEnabled(False)
        self._mcp_progress_lbl.setText("Starting…")
        self._mcp_progress_lbl.show()
        self._dl_mcp_thread = ts.DownloadMcpThread()
        self._dl_mcp_thread.progress.connect(self._mcp_progress_lbl.setText)
        self._dl_mcp_thread.finished.connect(self._on_mcp_done)
        self._dl_mcp_thread.start()

    def _on_mcp_done(self, success: bool, message: str) -> None:
        self._dl_mcp_btn.setEnabled(True)
        if success:
            self._mcp_progress_lbl.setText(f"Done — {message}")
            self._refresh_mcp_status()
        else:
            self._mcp_progress_lbl.setText(f"Error: {message}")

    def _run_all_detections(self) -> None:
        for row in self._mcp_rows:
            row.run_detect()
