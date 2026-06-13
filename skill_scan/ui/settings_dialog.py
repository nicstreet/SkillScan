from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
    QFileDialog,
)

from ..core import config as cfg
from ..core import test_skills as ts


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("SkillScan — Settings")
        self.setMinimumWidth(480)
        self._data = cfg.load()
        self._build_ui()
        self._populate()

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        tabs = QTabWidget()
        root.addWidget(tabs)

        tabs.addTab(self._make_llm_tab(), "LLM")
        tabs.addTab(self._make_analyzers_tab(), "Analyzers")
        tabs.addTab(self._make_clipboard_tab(), "Clipboard")
        tabs.addTab(self._make_folders_tab(), "Watched Folders")
        tabs.addTab(self._make_testing_tab(), "Testing")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    # ---- LLM tab -------------------------------------------------------
    def _make_llm_tab(self):
        w = QWidget()
        form = QFormLayout(w)
        form.setContentsMargins(12, 12, 12, 12)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)

        self._llm_provider = QComboBox()
        self._llm_provider.addItems(["anthropic", "openai"])
        self._llm_provider.currentTextChanged.connect(self._update_model_placeholder)
        form.addRow("LLM Provider", self._llm_provider)

        self._llm_api_key = QLineEdit()
        self._llm_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._llm_api_key.setPlaceholderText("sk-...")
        form.addRow("API Key", self._llm_api_key)

        self._llm_model = QLineEdit()
        form.addRow("Model", self._llm_model)

        self._virustotal_key = QLineEdit()
        self._virustotal_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._virustotal_key.setPlaceholderText("optional")
        form.addRow("VirusTotal API Key", self._virustotal_key)

        self._ai_defense_key = QLineEdit()
        self._ai_defense_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._ai_defense_key.setPlaceholderText("optional")
        form.addRow("Cisco AI Defense API Key", self._ai_defense_key)

        return w

    def _update_model_placeholder(self, provider: str):
        if provider == "anthropic":
            self._llm_model.setPlaceholderText("anthropic/claude-sonnet-4-20250514")
        else:
            self._llm_model.setPlaceholderText("openai/gpt-4o")

    # ---- Analyzers tab -------------------------------------------------
    def _make_analyzers_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)

        grp = QGroupBox("Enable Analyzers")
        grp_layout = QVBoxLayout(grp)

        self._chk_behavioral = QCheckBox("Behavioral  (--use-behavioral)")
        self._chk_llm = QCheckBox("LLM-based  (--use-llm)")
        self._chk_trigger = QCheckBox("Trigger detection  (--use-trigger)")
        self._chk_aidefense = QCheckBox("Cisco AI Defense  (--use-aidefense)")
        self._chk_virustotal = QCheckBox("VirusTotal binary scan  (--use-virustotal)")
        self._chk_detailed = QCheckBox("Include detailed output  (--detailed)")

        for chk in (
            self._chk_behavioral, self._chk_llm, self._chk_trigger,
            self._chk_aidefense, self._chk_virustotal, self._chk_detailed,
        ):
            grp_layout.addWidget(chk)

        layout.addWidget(grp)

        policy_grp = QGroupBox("Policy")
        policy_layout = QFormLayout(policy_grp)
        self._policy = QComboBox()
        self._policy.addItems(["permissive", "strict"])
        policy_layout.addRow("Sensitivity", self._policy)

        self._fail_on = QComboBox()
        self._fail_on.addItems(["(none)", "low", "medium", "high", "critical"])
        policy_layout.addRow("Fail on severity", self._fail_on)
        layout.addWidget(policy_grp)
        layout.addStretch()
        return w

    # ---- Clipboard tab -------------------------------------------------
    def _make_clipboard_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)

        grp = QGroupBox("Background Clipboard Monitor")
        form = QFormLayout(grp)

        self._cb_watch_enabled = QCheckBox("Enable automatic clipboard scanning")
        self._cb_watch_enabled.toggled.connect(self._update_clipboard_fields)
        form.addRow(self._cb_watch_enabled)

        self._cb_interval = QSpinBox()
        self._cb_interval.setRange(5, 3600)
        self._cb_interval.setSuffix(" seconds")
        self._cb_interval.setToolTip("How often to check the clipboard for new content")
        form.addRow("Check interval", self._cb_interval)

        self._cb_min_chars = QSpinBox()
        self._cb_min_chars.setRange(10, 100000)
        self._cb_min_chars.setSuffix(" characters")
        self._cb_min_chars.setToolTip("Only scan clipboard content that exceeds this length")
        form.addRow("Minimum characters", self._cb_min_chars)

        layout.addWidget(grp)
        layout.addWidget(QLabel(
            "When enabled, the clipboard is checked on the interval above.\n"
            "If the content has changed and exceeds the character threshold,\n"
            "a silent background scan runs — result appears as a tray notification."
        ))
        layout.addStretch()
        return w

    def _update_clipboard_fields(self, enabled: bool):
        self._cb_interval.setEnabled(enabled)
        self._cb_min_chars.setEnabled(enabled)

    # ---- Watched folders tab -------------------------------------------
    def _make_folders_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)

        layout.addWidget(QLabel("Auto-scan when SKILL.md changes in these folders:"))

        self._folder_list = QListWidget()
        layout.addWidget(self._folder_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Folder…")
        add_btn.clicked.connect(self._add_folder)
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_folder)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(remove_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)
        return w

    def _add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select folder to watch")
        if folder:
            self._folder_list.addItem(QListWidgetItem(folder))

    def _remove_folder(self):
        for item in self._folder_list.selectedItems():
            self._folder_list.takeItem(self._folder_list.row(item))

    # ---- Testing tab ---------------------------------------------------
    def _make_testing_tab(self):
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        grp = QGroupBox("Eval Test Skills")
        grp_layout = QVBoxLayout(grp)
        grp_layout.setSpacing(8)

        self._test_status = QLabel()
        self._test_status.setWordWrap(True)
        grp_layout.addWidget(self._test_status)

        dl_row = QHBoxLayout()
        self._dl_btn = QPushButton("Download Test Skills")
        self._dl_btn.clicked.connect(self._download_test_skills)
        dl_row.addWidget(self._dl_btn)
        dl_row.addStretch()
        grp_layout.addLayout(dl_row)

        self._dl_progress = QLabel("")
        self._dl_progress.setStyleSheet("color: #6b7280; font-size: 11px;")
        self._dl_progress.hide()
        grp_layout.addWidget(self._dl_progress)

        action_row = QHBoxLayout()
        self._open_folder_btn = QPushButton("Open Skills Folder")
        self._open_folder_btn.clicked.connect(ts.open_folder)
        self._open_guide_btn = QPushButton("Open Testing Guide")
        self._open_guide_btn.clicked.connect(ts.open_guide)
        action_row.addWidget(self._open_folder_btn)
        action_row.addWidget(self._open_guide_btn)
        action_row.addStretch()
        grp_layout.addLayout(action_row)

        layout.addWidget(grp)

        attrib = QLabel(
            "Skills sourced from "
            "<a href='https://github.com/cisco-ai-defense/skill-scanner'>"
            "cisco-ai-defense/skill-scanner</a> "
            "(<a href='https://www.apache.org/licenses/LICENSE-2.0'>Apache 2.0</a>) "
            "© 2026 Cisco Systems, Inc."
        )
        attrib.setOpenExternalLinks(True)
        attrib.setWordWrap(True)
        attrib.setStyleSheet("color: #6b7280; font-size: 10px;")
        layout.addWidget(attrib)

        layout.addStretch()
        self._refresh_test_status()
        return w

    def _refresh_test_status(self):
        if ts.is_downloaded():
            count = ts.skill_count()
            self._test_status.setText(
                f"<b>{count} skill{'s' if count != 1 else ''}</b> downloaded to:<br>"
                f"<code>{ts.TEST_SKILLS_DIR}</code>"
            )
            self._dl_btn.setText("Re-download")
            self._open_folder_btn.setEnabled(True)
            self._open_guide_btn.setEnabled(True)
        else:
            self._test_status.setText(
                "Test skills not yet downloaded.\n"
                "These are curated safe and malicious skill samples from the\n"
                "cisco-ai-defense/skill-scanner eval suite."
            )
            self._dl_btn.setText("Download Test Skills")
            self._open_folder_btn.setEnabled(False)
            self._open_guide_btn.setEnabled(False)

    def _download_test_skills(self):
        self._dl_btn.setEnabled(False)
        self._dl_progress.setText("Starting…")
        self._dl_progress.show()
        self._dl_thread = ts.DownloadThread()
        self._dl_thread.progress.connect(self._dl_progress.setText)
        self._dl_thread.finished.connect(self._on_dl_finished)
        self._dl_thread.start()

    def _on_dl_finished(self, success: bool, message: str):
        self._dl_btn.setEnabled(True)
        if success:
            self._dl_progress.setText(f"Done — {message}")
            self._refresh_test_status()
        else:
            self._dl_progress.setText(f"Error: {message}")

    # ------------------------------------------------------------------
    def _populate(self):
        d = self._data
        idx = self._llm_provider.findText(d.get("llm_provider", "anthropic"))
        self._llm_provider.setCurrentIndex(max(0, idx))
        self._llm_api_key.setText(d.get("llm_api_key", ""))
        self._llm_model.setText(d.get("llm_model", ""))
        self._virustotal_key.setText(d.get("virustotal_api_key", ""))
        self._ai_defense_key.setText(d.get("ai_defense_api_key", ""))

        self._chk_behavioral.setChecked(d.get("use_behavioral", True))
        self._chk_llm.setChecked(d.get("use_llm", True))
        self._chk_trigger.setChecked(d.get("use_trigger", False))
        self._chk_aidefense.setChecked(d.get("use_aidefense", False))
        self._chk_virustotal.setChecked(d.get("use_virustotal", False))
        self._chk_detailed.setChecked(d.get("detailed", True))

        policy_idx = self._policy.findText(d.get("policy", "permissive"))
        self._policy.setCurrentIndex(max(0, policy_idx))

        fail_on = d.get("fail_on_severity", "") or "(none)"
        fail_idx = self._fail_on.findText(fail_on)
        self._fail_on.setCurrentIndex(max(0, fail_idx))

        for folder in d.get("watched_folders", []):
            self._folder_list.addItem(QListWidgetItem(folder))

        self._cb_watch_enabled.setChecked(d.get("clipboard_watch_enabled", False))
        self._cb_interval.setValue(d.get("clipboard_watch_interval_secs", 30))
        self._cb_min_chars.setValue(d.get("clipboard_min_chars", 200))
        self._update_clipboard_fields(d.get("clipboard_watch_enabled", False))

        self._update_model_placeholder(d.get("llm_provider", "anthropic"))

    def _save(self):
        d = self._data
        d["llm_provider"] = self._llm_provider.currentText()
        d["llm_api_key"] = self._llm_api_key.text().strip()
        d["llm_model"] = self._llm_model.text().strip()
        d["virustotal_api_key"] = self._virustotal_key.text().strip()
        d["ai_defense_api_key"] = self._ai_defense_key.text().strip()

        d["use_behavioral"] = self._chk_behavioral.isChecked()
        d["use_llm"] = self._chk_llm.isChecked()
        d["use_trigger"] = self._chk_trigger.isChecked()
        d["use_aidefense"] = self._chk_aidefense.isChecked()
        d["use_virustotal"] = self._chk_virustotal.isChecked()
        d["detailed"] = self._chk_detailed.isChecked()

        d["policy"] = self._policy.currentText()
        fail_on = self._fail_on.currentText()
        d["fail_on_severity"] = "" if fail_on == "(none)" else fail_on

        d["watched_folders"] = [
            self._folder_list.item(i).text()
            for i in range(self._folder_list.count())
        ]

        d["clipboard_watch_enabled"] = self._cb_watch_enabled.isChecked()
        d["clipboard_watch_interval_secs"] = self._cb_interval.value()
        d["clipboard_min_chars"] = self._cb_min_chars.value()

        cfg.save(d)
        self.accept()
