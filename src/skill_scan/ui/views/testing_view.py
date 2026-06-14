"""Testing view — migrated from SettingsDialog Testing tab."""

from PyQt6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core import test_skills as ts
from ...core.test_skills import McpEval
from .._palette import (
    ACCENT,
    ANCHOR,
    CRITICAL_ACCENT,
    HIGH_ACCENT,
    HOVER_FOCUS,
    LIGHT_CANVAS,
    MEDIUM_ACCENT,
    MUTED_TEXT,
    SAFE_ACCENT,
)

_SEVERITY_COLOUR = {
    "CLEAN": SAFE_ACCENT,
    "MEDIUM": MEDIUM_ACCENT,
    "HIGH": HIGH_ACCENT,
    "CRITICAL": CRITICAL_ACCENT,
}


def _styled_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {LIGHT_CANVAS};
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 5px 14px;
            font-size: 12px;
        }}
        QPushButton:hover   {{ border-color: {ACCENT}; color: {ACCENT}; }}
        QPushButton:pressed {{ background: #0f2028; }}
        QPushButton:disabled {{ color: {MUTED_TEXT}; border-color: #1e293b; }}
    """)
    return btn


def _primary_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {ACCENT};
            color: {LIGHT_CANVAS};
            border: none;
            border-radius: 6px;
            padding: 5px 14px;
            font-size: 12px;
            font-weight: 600;
        }}
        QPushButton:hover   {{ background: {HOVER_FOCUS}; }}
        QPushButton:pressed {{ background: {HOVER_FOCUS}; }}
        QPushButton:disabled {{ background: #1e293b; color: {MUTED_TEXT}; }}
    """)
    return btn


_GRP_STYLE = f"""
    QGroupBox {{
        color: {MUTED_TEXT};
        font-size: 11px;
        font-weight: 600;
        border: 1px solid #334155;
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
        row.setContentsMargins(0, 2, 0, 2)
        row.setSpacing(10)

        # Name
        name_lbl = QLabel(self._eval.name)
        name_lbl.setStyleSheet(
            f"color:{LIGHT_CANVAS};font-size:12px;background:transparent;"
        )
        row.addWidget(name_lbl, 1)

        # Expected severity badge
        sev = self._eval.expected_severity
        sev_color = _SEVERITY_COLOUR.get(sev, MUTED_TEXT)
        sev_lbl = QLabel(sev)
        sev_lbl.setStyleSheet(
            f"color:{sev_color};font-size:10px;font-weight:700;"
            f"background:transparent;letter-spacing:1px;"
        )
        sev_lbl.setFixedWidth(68)
        row.addWidget(sev_lbl)

        # Detection result label (updated by run_detect)
        self._result_lbl = QLabel("—")
        self._result_lbl.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:11px;background:transparent;"
        )
        self._result_lbl.setFixedWidth(80)
        row.addWidget(self._result_lbl)

        # Per-row detect button
        detect_btn = _styled_btn("Detect")
        detect_btn.setFixedWidth(64)
        detect_btn.clicked.connect(self.run_detect)
        row.addWidget(detect_btn)

    def run_detect(self) -> bool:
        """Run router detection, update result label, return True if MCP_MANIFEST."""
        try:
            from ...core.router import detect_type, SpecType

            result = detect_type(self._eval.path)
            if result == SpecType.MCP_MANIFEST:
                self._result_lbl.setText("✓ MCP")
                self._result_lbl.setStyleSheet(
                    f"color:{SAFE_ACCENT};font-size:11px;"
                    f"font-weight:700;background:transparent;"
                )
                return True
            else:
                self._result_lbl.setText(f"✗ {result.value}")
                self._result_lbl.setStyleSheet(
                    f"color:{CRITICAL_ACCENT};font-size:11px;"
                    f"font-weight:700;background:transparent;"
                )
                return False
        except Exception:
            self._result_lbl.setText("error")
            self._result_lbl.setStyleSheet(
                f"color:{MEDIUM_ACCENT};font-size:11px;background:transparent;"
            )
            return False


# ── Main view ────────────────────────────────────────────────────────────────


class TestingView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {ANCHOR};")
        self._mcp_rows: list[_McpEvalRow] = []
        self._build_ui()
        self._refresh_status()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(16)

        heading = QLabel("Testing")
        heading.setStyleSheet(
            f"color:{LIGHT_CANVAS};font-size:20px;font-weight:700;background:transparent;"
        )
        root.addWidget(heading)

        # ── Eval test skills group ─────────────────────────────────────────
        grp = QGroupBox("Eval Test Skills")
        grp.setStyleSheet(_GRP_STYLE)
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(10)

        self._status_lbl = QLabel()
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setStyleSheet(
            f"color:{LIGHT_CANVAS};font-size:12px;background:transparent;"
        )
        grp_layout.addWidget(self._status_lbl)

        dl_row = QHBoxLayout()
        self._dl_btn = _primary_btn("Download Test Skills")
        self._dl_btn.clicked.connect(self._download)
        dl_row.addWidget(self._dl_btn)
        dl_row.addStretch()
        grp_layout.addLayout(dl_row)

        self._progress_lbl = QLabel()
        self._progress_lbl.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:11px;background:transparent;"
        )
        self._progress_lbl.hide()
        grp_layout.addWidget(self._progress_lbl)

        action_row = QHBoxLayout()
        self._folder_btn = _styled_btn("Open Skills Folder")
        self._folder_btn.clicked.connect(ts.open_folder)
        self._guide_btn = _styled_btn("Open Testing Guide")
        self._guide_btn.clicked.connect(ts.open_guide)
        action_row.addWidget(self._folder_btn)
        action_row.addWidget(self._guide_btn)
        action_row.addStretch()
        grp_layout.addLayout(action_row)

        root.addWidget(grp)

        # ── MCP manifest evals group ───────────────────────────────────────
        self._build_mcp_evals_section(root)

        attrib = QLabel(
            "Skills sourced from "
            "<a href='https://github.com/cisco-ai-defense/skill-scanner' "
            f"style='color:{ACCENT};'>"
            "cisco-ai-defense/skill-scanner</a> "
            "(<a href='https://www.apache.org/licenses/LICENSE-2.0' "
            f"style='color:{ACCENT};'>Apache 2.0</a>) "
            "© 2026 Cisco Systems, Inc."
        )
        attrib.setOpenExternalLinks(True)
        attrib.setWordWrap(True)
        attrib.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:10px;background:transparent;"
        )
        root.addWidget(attrib)
        root.addStretch()

    def _build_mcp_evals_section(self, root: QVBoxLayout) -> None:
        mcp_grp = QGroupBox("MCP Manifest Evals")
        mcp_grp.setStyleSheet(_GRP_STYLE)
        mcp_layout = QVBoxLayout(mcp_grp)
        mcp_layout.setSpacing(8)

        evals = ts.mcp_eval_list()

        # Description line
        desc_lbl = QLabel("Tests router type detection for MCP server definitions.")
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(
            f"color:{LIGHT_CANVAS};font-size:12px;background:transparent;"
        )
        mcp_layout.addWidget(desc_lbl)

        if evals:
            # Column header row
            hdr = QHBoxLayout()
            hdr.setContentsMargins(0, 4, 0, 0)
            hdr.setSpacing(10)
            for text, stretch, w in [
                ("Manifest", 1, None),
                ("Expected", 0, 68),
                ("Detected", 0, 80),
                ("", 0, 64),
            ]:
                lbl = QLabel(text)
                lbl.setStyleSheet(
                    f"color:{MUTED_TEXT};font-size:10px;font-weight:700;"
                    f"letter-spacing:1px;background:transparent;"
                )
                if w:
                    lbl.setFixedWidth(w)
                hdr.addWidget(lbl, stretch)
            mcp_layout.addLayout(hdr)

            # Divider
            div = QFrame()
            div.setFrameShape(QFrame.Shape.HLine)
            div.setFixedHeight(1)
            div.setStyleSheet("background:#334155;border:none;")
            mcp_layout.addWidget(div)

            # One row per eval
            for eval_ in evals:
                row_widget = _McpEvalRow(eval_)
                self._mcp_rows.append(row_widget)
                mcp_layout.addWidget(row_widget)

        # Location label
        loc_lbl = QLabel(
            f"<b style='color:{ACCENT}'>{len(evals)} manifest{'s' if len(evals) != 1 else ''}</b>"
            f" bundled at:<br>"
            f"<code style='color:{MUTED_TEXT}'>{ts.MCP_EVALS_DIR}</code>"
        )
        loc_lbl.setWordWrap(True)
        loc_lbl.setStyleSheet(
            f"color:{LIGHT_CANVAS};font-size:12px;background:transparent;"
        )
        mcp_layout.addWidget(loc_lbl)

        # Action row
        action_row = QHBoxLayout()
        detect_all_btn = _primary_btn("Detect All")
        detect_all_btn.clicked.connect(self._run_all_detections)
        action_row.addWidget(detect_all_btn)

        folder_btn = _styled_btn("Open Evals Folder")
        folder_btn.clicked.connect(ts.open_mcp_evals_folder)
        action_row.addWidget(folder_btn)
        action_row.addStretch()
        mcp_layout.addLayout(action_row)

        # Phase note
        note = QLabel(
            "ⓘ  Full severity analysis (LLM-based) for MCP manifests — Phase 7"
        )
        note.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:10px;background:transparent;font-style:italic;"
        )
        mcp_layout.addWidget(note)

        root.addWidget(mcp_grp)

    def _run_all_detections(self) -> None:
        for row in self._mcp_rows:
            row.run_detect()

    def _refresh_status(self):
        if ts.is_downloaded():
            count = ts.skill_count()
            self._status_lbl.setText(
                f"<b style='color:{ACCENT}'>{count} skill{'s' if count != 1 else ''}</b>"
                f" downloaded to:<br>"
                f"<code style='color:{MUTED_TEXT}'>{ts.TEST_SKILLS_DIR}</code>"
            )
            self._dl_btn.setText("Re-download")
            self._folder_btn.setEnabled(True)
            self._guide_btn.setEnabled(True)
        else:
            self._status_lbl.setText(
                "Test skills not yet downloaded.\n"
                "These are curated safe and malicious skill samples from the\n"
                "cisco-ai-defense/skill-scanner eval suite."
            )
            self._dl_btn.setText("Download Test Skills")
            self._folder_btn.setEnabled(False)
            self._guide_btn.setEnabled(False)

    def _download(self):
        self._dl_btn.setEnabled(False)
        self._progress_lbl.setText("Starting…")
        self._progress_lbl.show()
        self._dl_thread = ts.DownloadThread()
        self._dl_thread.progress.connect(self._progress_lbl.setText)
        self._dl_thread.finished.connect(self._on_dl_done)
        self._dl_thread.start()

    def _on_dl_done(self, success: bool, message: str):
        self._dl_btn.setEnabled(True)
        if success:
            self._progress_lbl.setText(f"Done — {message}")
            self._refresh_status()
        else:
            self._progress_lbl.setText(f"Error: {message}")
