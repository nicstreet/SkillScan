"""Options view — migrated from SettingsDialog, adapted as a persistent view."""
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

from ...core import config as cfg
from .._palette import ACCENT, ANCHOR, HOVER_FOCUS, LIGHT_CANVAS, MUTED_TEXT


def _primary_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {ACCENT};
            color: {LIGHT_CANVAS};
            border: none;
            border-radius: 6px;
            padding: 6px 20px;
            font-size: 13px;
            font-weight: 600;
        }}
        QPushButton:hover   {{ background: {HOVER_FOCUS}; }}
        QPushButton:pressed {{ background: {HOVER_FOCUS}; }}
    """)
    return btn


class OptionsView(QWidget):
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {ANCHOR};")
        self._data = cfg.load()
        self._build_ui()
        self._populate()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(40, 40, 40, 40)
        root.setSpacing(16)

        heading = QLabel("Options")
        heading.setStyleSheet(
            f"color:{LIGHT_CANVAS};font-size:20px;font-weight:700;background:transparent;"
        )
        root.addWidget(heading)

        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid #334155;
                border-radius: 6px;
                background: #0d1829;
            }}
            QTabBar::tab {{
                background: transparent;
                color: {MUTED_TEXT};
                padding: 6px 16px;
                border: none;
                border-bottom: 2px solid transparent;
                font-size: 12px;
            }}
            QTabBar::tab:selected {{
                color: {LIGHT_CANVAS};
                border-bottom: 2px solid {ACCENT};
            }}
            QTabBar::tab:hover {{ color: {LIGHT_CANVAS}; }}
        """)
        tabs.addTab(self._make_llm_tab(), "LLM")
        tabs.addTab(self._make_analyzers_tab(), "Analyzers")
        tabs.addTab(self._make_clipboard_tab(), "Clipboard")
        tabs.addTab(self._make_folders_tab(), "Watched Folders")
        root.addWidget(tabs, 1)

        btn_row = QHBoxLayout()
        save_btn = _primary_btn("Save Settings")
        save_btn.clicked.connect(self._save)
        btn_row.addStretch()
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)

    # ── LLM tab ────────────────────────────────────────────────────────────
    def _make_llm_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background: transparent;")
        form = QFormLayout(w)
        form.setContentsMargins(16, 16, 16, 16)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapAllRows)
        form.setLabelAlignment(
            form.labelAlignment() | __import__("PyQt6.QtCore", fromlist=["Qt"]).Qt.AlignmentFlag.AlignLeft
        )

        _field_style = (
            f"background:#0d1829;color:{LIGHT_CANVAS};border:1px solid #334155;"
            f"border-radius:5px;padding:4px 8px;font-size:12px;"
            f"selection-background-color:{ACCENT};"
        )
        _label_style = f"color:{MUTED_TEXT};font-size:12px;background:transparent;"

        self._llm_provider = QComboBox()
        self._llm_provider.addItems(["anthropic", "openai"])
        self._llm_provider.currentTextChanged.connect(self._update_model_placeholder)
        self._llm_provider.setStyleSheet(
            f"QComboBox{{{_field_style}}}"
            f"QComboBox::drop-down{{border:none;}}"
        )

        self._llm_api_key = QLineEdit()
        self._llm_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._llm_api_key.setPlaceholderText("sk-...")
        self._llm_api_key.setStyleSheet(_field_style)

        self._llm_model = QLineEdit()
        self._llm_model.setStyleSheet(_field_style)

        self._virustotal_key = QLineEdit()
        self._virustotal_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._virustotal_key.setPlaceholderText("optional")
        self._virustotal_key.setStyleSheet(_field_style)

        self._ai_defense_key = QLineEdit()
        self._ai_defense_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._ai_defense_key.setPlaceholderText("optional")
        self._ai_defense_key.setStyleSheet(_field_style)

        for label, widget in [
            ("LLM Provider", self._llm_provider),
            ("API Key", self._llm_api_key),
            ("Model", self._llm_model),
            ("VirusTotal API Key", self._virustotal_key),
            ("Cisco AI Defense API Key", self._ai_defense_key),
        ]:
            lbl = QLabel(label)
            lbl.setStyleSheet(_label_style)
            form.addRow(lbl, widget)

        return w

    def _update_model_placeholder(self, provider: str):
        if provider == "anthropic":
            self._llm_model.setPlaceholderText("anthropic/claude-sonnet-4-20250514")
        else:
            self._llm_model.setPlaceholderText("openai/gpt-4o")

    # ── Analyzers tab ──────────────────────────────────────────────────────
    def _make_analyzers_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)

        _chk_style = f"QCheckBox{{color:{LIGHT_CANVAS};font-size:12px;background:transparent;}}"

        grp = QGroupBox("Enable Analyzers")
        grp.setStyleSheet(
            f"QGroupBox{{color:{MUTED_TEXT};font-size:11px;font-weight:600;"
            f"border:1px solid #334155;border-radius:8px;margin-top:8px;padding-top:8px;}}"
            f"QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}"
        )
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
            chk.setStyleSheet(_chk_style)
            grp_layout.addWidget(chk)

        layout.addWidget(grp)

        _combo_style = (
            f"QComboBox{{background:#0d1829;color:{LIGHT_CANVAS};border:1px solid #334155;"
            f"border-radius:5px;padding:4px 8px;font-size:12px;}}"
            f"QComboBox::drop-down{{border:none;}}"
        )

        policy_grp = QGroupBox("Policy")
        policy_grp.setStyleSheet(grp.styleSheet())
        policy_layout = QFormLayout(policy_grp)

        policy_lbl = QLabel("Sensitivity")
        policy_lbl.setStyleSheet(f"color:{MUTED_TEXT};font-size:12px;background:transparent;")
        self._policy = QComboBox()
        self._policy.addItems(["permissive", "strict"])
        self._policy.setStyleSheet(_combo_style)

        fail_lbl = QLabel("Fail on severity")
        fail_lbl.setStyleSheet(f"color:{MUTED_TEXT};font-size:12px;background:transparent;")
        self._fail_on = QComboBox()
        self._fail_on.addItems(["(none)", "low", "medium", "high", "critical"])
        self._fail_on.setStyleSheet(_combo_style)

        policy_layout.addRow(policy_lbl, self._policy)
        policy_layout.addRow(fail_lbl, self._fail_on)
        layout.addWidget(policy_grp)
        layout.addStretch()
        return w

    # ── Clipboard tab ──────────────────────────────────────────────────────
    def _make_clipboard_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)

        grp = QGroupBox("Background Clipboard Monitor")
        grp.setStyleSheet(
            f"QGroupBox{{color:{MUTED_TEXT};font-size:11px;font-weight:600;"
            f"border:1px solid #334155;border-radius:8px;margin-top:8px;padding-top:8px;}}"
            f"QGroupBox::title{{subcontrol-origin:margin;left:10px;padding:0 4px;}}"
        )
        form = QFormLayout(grp)

        _chk_style = f"QCheckBox{{color:{LIGHT_CANVAS};font-size:12px;background:transparent;}}"
        _spin_style = (
            f"QSpinBox{{background:#0d1829;color:{LIGHT_CANVAS};border:1px solid #334155;"
            f"border-radius:5px;padding:4px 8px;font-size:12px;}}"
        )

        self._cb_watch_enabled = QCheckBox("Enable automatic clipboard scanning")
        self._cb_watch_enabled.setStyleSheet(_chk_style)
        self._cb_watch_enabled.toggled.connect(self._update_clipboard_fields)
        form.addRow(self._cb_watch_enabled)

        lbl_interval = QLabel("Check interval")
        lbl_interval.setStyleSheet(f"color:{MUTED_TEXT};font-size:12px;background:transparent;")
        self._cb_interval = QSpinBox()
        self._cb_interval.setRange(5, 3600)
        self._cb_interval.setSuffix(" seconds")
        self._cb_interval.setStyleSheet(_spin_style)
        form.addRow(lbl_interval, self._cb_interval)

        lbl_chars = QLabel("Minimum characters")
        lbl_chars.setStyleSheet(f"color:{MUTED_TEXT};font-size:12px;background:transparent;")
        self._cb_min_chars = QSpinBox()
        self._cb_min_chars.setRange(10, 100000)
        self._cb_min_chars.setSuffix(" characters")
        self._cb_min_chars.setStyleSheet(_spin_style)
        form.addRow(lbl_chars, self._cb_min_chars)

        layout.addWidget(grp)

        info = QLabel(
            "When enabled, the clipboard is checked on the interval above.\n"
            "If content has changed and exceeds the character threshold,\n"
            "a silent background scan runs — result appears as a tray notification."
        )
        info.setStyleSheet(f"color:{MUTED_TEXT};font-size:11px;background:transparent;")
        layout.addWidget(info)
        layout.addStretch()
        return w

    def _update_clipboard_fields(self, enabled: bool):
        self._cb_interval.setEnabled(enabled)
        self._cb_min_chars.setEnabled(enabled)

    # ── Watched Folders tab ────────────────────────────────────────────────
    def _make_folders_tab(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background:transparent;")
        layout = QVBoxLayout(w)
        layout.setContentsMargins(16, 16, 16, 16)

        info = QLabel("Auto-scan when SKILL.md changes in these folders:")
        info.setStyleSheet(f"color:{MUTED_TEXT};font-size:12px;background:transparent;")
        layout.addWidget(info)

        self._folder_list = QListWidget()
        self._folder_list.setStyleSheet(
            f"QListWidget{{background:#0d1829;color:{LIGHT_CANVAS};"
            f"border:1px solid #334155;border-radius:6px;font-size:12px;}}"
            f"QListWidget::item:selected{{background:{ACCENT};}}"
        )
        layout.addWidget(self._folder_list)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Folder…")
        add_btn.setStyleSheet(
            f"QPushButton{{background:{ACCENT};color:{LIGHT_CANVAS};border:none;"
            f"border-radius:5px;padding:5px 12px;font-size:12px;}}"
            f"QPushButton:hover{{background:{HOVER_FOCUS};}}"
        )
        add_btn.clicked.connect(self._add_folder)

        rem_btn = QPushButton("Remove Selected")
        rem_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{LIGHT_CANVAS};"
            f"border:1px solid #334155;border-radius:5px;padding:5px 12px;font-size:12px;}}"
            f"QPushButton:hover{{border-color:{ACCENT};color:{ACCENT};}}"
        )
        rem_btn.clicked.connect(self._remove_folder)

        btn_row.addWidget(add_btn)
        btn_row.addWidget(rem_btn)
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

    # ── Populate / save ────────────────────────────────────────────────────
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
        self.settings_changed.emit()
