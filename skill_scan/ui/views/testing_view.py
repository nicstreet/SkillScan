"""Testing view — migrated from SettingsDialog Testing tab."""
from PyQt6.QtWidgets import (
    QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

from ...core import test_skills as ts
from .._palette import ANCHOR, ACCENT, HOVER_FOCUS, LIGHT_CANVAS, MUTED_TEXT


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


class TestingView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {ANCHOR};")
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
        grp.setStyleSheet(f"""
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
        """)
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
