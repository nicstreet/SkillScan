"""LicensePicker — reusable license combo with No License / curated SPDX list /
Custom, plus a live info panel (category, description, source-disclosure
obligation, link to legal text). Used by Options Skill Defaults and Skill Manager.
"""

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QComboBox, QLabel, QLineEdit, QVBoxLayout, QWidget

from ..core.license_registry import load_licenses
from ._palette import (
    SYS_ACTION_PRIMARY,
    SYS_BG_PRIMARY,
    SYS_BORDER_WARNING,
    SYS_STROKE_SUBTLE,
    SYS_TXT_MUTED,
    SYS_TXT_PRIMARY,
)
from ._widgets import SCROLLBAR_STYLE

_FIELD_STYLE = (
    f"background:{SYS_TXT_MUTED};color:{SYS_BG_PRIMARY};border:none;"
    f"border-radius:5px;padding:3px 8px;font-size:11px;"
)
_COMBO_STYLE = (
    f"QComboBox{{{_FIELD_STYLE}}}"
    f"QComboBox::drop-down{{border:none;}}"
    f"QComboBox QAbstractItemView{{background:{SYS_BG_PRIMARY};color:{SYS_TXT_PRIMARY};"
    f"font-size:9pt;selection-background-color:{SYS_ACTION_PRIMARY};"
    f"border:1px solid {SYS_STROKE_SUBTLE};}}"
)
_CUSTOM_DATA = "__custom__"


class LicensePicker(QWidget):
    """Resolve to either an SPDX identifier, "" (No License), or free text (Custom)."""

    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        self._licenses = load_licenses()

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)

        self._combo = QComboBox()
        self._combo.setStyleSheet(_COMBO_STYLE)
        self._combo.view().verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        for lic in self._licenses:
            self._combo.addItem(lic["name"], lic["spdx"])
        self._combo.addItem("Custom…", _CUSTOM_DATA)
        self._combo.currentIndexChanged.connect(self._on_combo_changed)
        lay.addWidget(self._combo)

        self._custom_field = QLineEdit()
        self._custom_field.setPlaceholderText(
            "e.g. Proprietary. LICENSE.txt has complete terms"
        )
        self._custom_field.setStyleSheet(_FIELD_STYLE)
        self._custom_field.setVisible(False)
        self._custom_field.textChanged.connect(lambda: self.changed.emit())
        lay.addWidget(self._custom_field)

        self._info_label = QLabel("")
        self._info_label.setWordWrap(True)
        self._info_label.setOpenExternalLinks(True)
        self._info_label.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:10px;")
        lay.addWidget(self._info_label)

        self._update_info()

    def _on_combo_changed(self, _index: int) -> None:
        self._custom_field.setVisible(self._combo.currentData() == _CUSTOM_DATA)
        self._update_info()
        self.changed.emit()

    def _update_info(self) -> None:
        data = self._combo.currentData()
        if data == _CUSTOM_DATA:
            self._info_label.setText(
                "Free text - written exactly as entered into the license field."
            )
            return
        lic = next((entry for entry in self._licenses if entry["spdx"] == data), None)
        if not lic:
            self._info_label.setText("")
            return
        link = (
            f' · <a href="{lic["url"]}" style="color:{SYS_BORDER_WARNING};">License Advice →</a>'
            if lic.get("url")
            else ""
        )
        self._info_label.setText(
            f"<b>{lic['category']}</b> - {lic['description']}<br>"
            f"Must disclose source: {lic.get('discloses_source', 'No')}{link}"
        )

    def value(self) -> str:
        """The string to write into the license frontmatter field."""
        if self._combo.currentData() == _CUSTOM_DATA:
            return self._custom_field.text().strip()
        return self._combo.currentData() or ""

    def set_value(self, value: str) -> None:
        value = (value or "").strip()
        idx = self._combo.findData(value)
        if idx >= 0:
            self._combo.setCurrentIndex(idx)
            return
        custom_idx = self._combo.findData(_CUSTOM_DATA)
        self._combo.setCurrentIndex(custom_idx)
        self._custom_field.setText(value)
