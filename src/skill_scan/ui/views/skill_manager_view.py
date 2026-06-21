"""Skill Studio view — Phase 5.

Packages, validates, and remediates skill content against the agentskills.io
specification (https://agentskills.io/specification). Skills are assumed to be
drafted by an AI agent elsewhere (chat, clipboard, another session) — this view
reviews/amends that content, validates it, and writes a spec-correct package.
"""

import difflib
import html as _html
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QClipboard, QColor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from ...core import config as cfg
from ...core import script_lint, spec_compliance
from ...core.llm import LLMJob
from ...core.scanner import ScanJob
from .._license_picker import LicensePicker
from ..result_formatter import format_result_html
from .._palette import (
    SYS_ACTION_PRIMARY,
    SYS_ACTION_HOVER,
    SYS_BADGE_SAFE,
    SYS_BADGE_UNSAFE,
    SYS_BG_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_BORDER_ADVISORY,
    SYS_BORDER_WARNING,
    SYS_STROKE_DIVIDER,
    SYS_STROKE_SUBTLE,
    SYS_TXT_PRIMARY,
    SYS_TXT_MUTED,
)
from .._icons import (
    fa,
    ICON_AI_USAGE,
    ICON_BUILD,
    ICON_CHECK,
    ICON_LOAD_FILE,
    ICON_NEW_SKILL,
    ICON_PASTE,
    ICON_REVIEW,
    ICON_RIGHT_LEFT,
    ICON_SAVE,
    ICON_SCAN,
)
from .._status import AiStatusRoutine
from .._widgets import (
    SCROLLBAR_STYLE,
    TitleBar,
    msg_critical,
    msg_information,
    msg_question,
    msg_warning,
)

_SAMPLE_BODY = """## Step-by-step instructions

1. ...

## Examples

...

## Gotchas

- ...
"""

_FIELD_STYLE = (
    f"background:{SYS_BG_SECONDARY};color:{SYS_TXT_PRIMARY};border:none;"
    f"border-radius:5px;padding:5px 8px;font-size:11px;"
    f"selection-background-color:{SYS_ACTION_PRIMARY};"
)


# ── Cascade-immune surface ────────────────────────────────────────────────────


class _Surface(QWidget):
    def __init__(self, color: str, radius: int = 0, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._radius = radius

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._radius:
            path = QPainterPath()
            path.addRoundedRect(
                0.0,
                0.0,
                float(self.width()),
                float(self.height()),
                self._radius,
                self._radius,
            )
            p.fillPath(path, self._color)
        else:
            p.fillRect(self.rect(), self._color)
        p.end()


def _action_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(26)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {SYS_ACTION_PRIMARY}; color: {SYS_TXT_PRIMARY};
            border: none; border-radius: 4px; padding: 2px 14px;
            font-size: 11px; font-weight: 600;
        }}
        QPushButton:hover {{ background: {SYS_ACTION_HOVER}; }}
        QPushButton:disabled {{ background: {SYS_STROKE_SUBTLE}; color: {SYS_TXT_MUTED}; }}
    """)
    return btn


def _ghost_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(26)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent; color: {SYS_TXT_MUTED};
            border: 1px solid {SYS_STROKE_SUBTLE}; border-radius: 4px;
            padding: 2px 14px; font-size: 11px;
        }}
        QPushButton:hover {{ border-color: {SYS_ACTION_PRIMARY}; color: {SYS_TXT_PRIMARY}; }}
        QPushButton:disabled {{ color: {SYS_TXT_MUTED}; border-color: {SYS_STROKE_SUBTLE}; }}
    """)
    return btn


def _section_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        f"color:{SYS_ACTION_PRIMARY};font-size:12px;font-weight:600;background:transparent;"
    )
    return lbl


def _error_label() -> QLabel:
    lbl = QLabel("")
    lbl.setStyleSheet(
        f"color:{SYS_BADGE_UNSAFE};font-size:10px;background:transparent;"
    )
    lbl.setWordWrap(True)
    lbl.setVisible(False)
    return lbl


def _hdivider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet(f"background:{SYS_STROKE_DIVIDER};border:none;")
    return f


def _vdivider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setFixedWidth(1)
    f.setStyleSheet(f"background:{SYS_STROKE_DIVIDER};border:none;")
    return f


_ICON_FONT = fa(11)
_PA_FONT = fa(10)  # page-action buttons in the taskbar


def _icon_btn(icon: str, tooltip: str, primary: bool = False) -> QPushButton:
    """32×32 icon button for views (not taskbar page actions)."""
    btn = QPushButton(icon)
    btn.setFixedSize(32, 32)
    btn.setToolTip(tooltip)
    btn.setFont(_ICON_FONT)
    bg = SYS_ACTION_PRIMARY if primary else "transparent"
    hover_bg = SYS_ACTION_HOVER if primary else f"{SYS_ACTION_PRIMARY}40"
    border = (
        f"1px solid {SYS_ACTION_HOVER}" if primary else f"1px solid {SYS_STROKE_SUBTLE}"
    )
    hover_border = (
        f"1px solid {SYS_TXT_PRIMARY}" if primary else f"1px solid {SYS_ACTION_PRIMARY}"
    )
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {bg}; color: {SYS_TXT_PRIMARY};
            border: {border}; border-radius: 6px; padding: 0px;
        }}
        QPushButton:hover {{ background: {hover_bg}; border: {hover_border}; }}
        QPushButton:disabled {{
            color: {SYS_TXT_MUTED}; background: transparent;
            border-color: {SYS_STROKE_SUBTLE};
        }}
    """)
    return btn


def _pa_btn(icon: str, tooltip: str, primary: bool = False) -> QPushButton:
    """26×26 icon button styled for the taskbar page-actions slot."""
    btn = QPushButton(icon)
    btn.setFixedSize(26, 26)
    btn.setFont(_PA_FONT)
    btn.setToolTip(tooltip)
    btn.setCursor(Qt.CursorShape.PointingHandCursor)
    if primary:
        btn.setStyleSheet(f"""
            QPushButton {{
                background: {SYS_ACTION_PRIMARY}; color: {SYS_TXT_PRIMARY};
                border: none; border-radius: 5px;
            }}
            QPushButton:hover {{ background: {SYS_ACTION_HOVER}; }}
            QPushButton:disabled {{ background: {SYS_STROKE_SUBTLE}; color: {SYS_TXT_MUTED}; }}
        """)
    else:
        btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {SYS_TXT_MUTED};
                border: none; border-radius: 5px;
            }}
            QPushButton:hover {{ background: {SYS_BG_SECONDARY}; color: {SYS_ACTION_PRIMARY}; }}
            QPushButton:disabled {{ color: {SYS_STROKE_SUBTLE}; }}
        """)
    return btn


# ── Compact structure folder file-list ───────────────────────────────────────


class _CompactFileBox(QWidget):
    """Compact file list: inline Add button, auto-sizing list, right-click to remove."""

    changed = pyqtSignal()

    def __init__(self, folder_name: str, parent=None):
        super().__init__(parent)
        self.folder_name = folder_name
        self.setStyleSheet("background:transparent;")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 2, 0, 2)
        lay.setSpacing(3)

        hdr = QHBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.setSpacing(4)
        lbl = QLabel(f"{folder_name}/")
        lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:10px;background:transparent;"
        )
        hdr.addWidget(lbl)
        hdr.addStretch()
        add_btn = QPushButton("+ Add")
        add_btn.setFixedHeight(18)
        add_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {SYS_TXT_MUTED};
                border: 1px solid {SYS_STROKE_SUBTLE}; border-radius: 3px;
                padding: 0 6px; font-size: 10px;
            }}
            QPushButton:hover {{ border-color: {SYS_ACTION_PRIMARY}; color: {SYS_TXT_PRIMARY}; }}
        """)
        add_btn.clicked.connect(self._add_file)
        hdr.addWidget(add_btn)
        lay.addLayout(hdr)

        self._list = QListWidget()
        self._list.setStyleSheet(
            f"QListWidget{{background:{SYS_BG_PRIMARY};color:{SYS_TXT_PRIMARY};"
            f"border:none;border-radius:4px;font-size:10px;padding:2px;}}"
            f"QListWidget::item{{padding:1px 4px;}}"
            f"QListWidget::item:selected{{background:{SYS_ACTION_PRIMARY}55;}}"
        )
        self._list.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        self._list.setMaximumHeight(0)  # collapsed when empty
        self._list.setToolTip("Right-click to remove selected file")
        self._list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._list.customContextMenuRequested.connect(self._remove_selected)
        lay.addWidget(self._list)

    def _add_file(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, f"Add files to {self.folder_name}/"
        )
        for p in paths:
            item = QListWidgetItem(Path(p).name)
            item.setData(Qt.ItemDataRole.UserRole, p)
            self._list.addItem(item)
        if paths:
            self._sync_height()
            self.changed.emit()

    def _remove_selected(self) -> None:
        for item in self._list.selectedItems():
            self._list.takeItem(self._list.row(item))
        self._sync_height()
        self.changed.emit()

    def _sync_height(self) -> None:
        n = self._list.count()
        if n == 0:
            self._list.setMaximumHeight(0)
        else:
            row_h = max(self._list.sizeHintForRow(0), 16) + 2
            self._list.setMaximumHeight(min(n * row_h + 6, 72))

    def clear(self) -> None:
        self._list.clear()
        self._sync_height()

    def paths(self) -> list[str]:
        result = []
        for i in range(self._list.count()):
            item = self._list.item(i)
            stored = item.data(Qt.ItemDataRole.UserRole)
            result.append(stored if stored else item.text())
        return result


# ── Additional metadata key-value editor ─────────────────────────────────────


class _MetadataEditor(QWidget):
    """Dynamic key-value editor for extra SKILL.md frontmatter fields."""

    changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        self._rows: list[tuple[QLineEdit, QLineEdit, QWidget]] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(3)

        self._rows_widget = QWidget()
        self._rows_widget.setStyleSheet("background:transparent;")
        self._rows_lay = QVBoxLayout(self._rows_widget)
        self._rows_lay.setContentsMargins(0, 0, 0, 0)
        self._rows_lay.setSpacing(3)
        outer.addWidget(self._rows_widget)

        add_btn = _ghost_btn("+ Add field")
        add_btn.setFixedHeight(22)
        add_btn.clicked.connect(lambda: self.add_row())
        outer.addWidget(add_btn)

    def add_row(self, key: str = "", value: str = "") -> None:
        row = QWidget()
        row.setStyleSheet("background:transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(4)

        key_f = QLineEdit(str(key))
        key_f.setPlaceholderText("key")
        key_f.setFixedWidth(90)
        key_f.setStyleSheet(_FIELD_STYLE)
        key_f.textChanged.connect(self.changed)

        val_f = QLineEdit(str(value))
        val_f.setPlaceholderText("value")
        val_f.setStyleSheet(_FIELD_STYLE)
        val_f.textChanged.connect(self.changed)

        rem = QPushButton("×")
        rem.setFixedSize(20, 20)
        rem.setCursor(Qt.CursorShape.PointingHandCursor)
        rem.setStyleSheet(
            f"QPushButton{{background:transparent;color:{SYS_TXT_MUTED};"
            f"border:none;font-size:13px;padding:0;}}"
            f"QPushButton:hover{{color:{SYS_BADGE_UNSAFE};}}"
        )
        rem.clicked.connect(lambda: self._remove_row(row, key_f, val_f))

        rl.addWidget(key_f)
        rl.addWidget(val_f, 1)
        rl.addWidget(rem)

        self._rows.append((key_f, val_f, row))
        self._rows_lay.addWidget(row)
        self.changed.emit()

    def _remove_row(self, row: QWidget, key_f: QLineEdit, val_f: QLineEdit) -> None:
        self._rows = [(k, v, r) for k, v, r in self._rows if k is not key_f]
        row.deleteLater()
        self.changed.emit()

    def set_metadata(self, meta: dict) -> None:
        for _, _, row in self._rows:
            row.deleteLater()
        self._rows.clear()
        for k, v in meta.items():
            self.add_row(str(k), str(v))

    def get_metadata(self) -> dict:
        return {
            k.text().strip(): v.text().strip()
            for k, v, _ in self._rows
            if k.text().strip()
        }


# ── Frameless diff dialog ─────────────────────────────────────────────────────


class _DiffDialog(QDialog):
    def __init__(self, html: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self.resize(820, 560)
        self._build(html)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        from .._palette import SYS_BG_PRIMARY as _BG, SYS_STROKE_DIVIDER as _DIV

        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, float(self.width()), float(self.height()), 10, 10)
        p.fillPath(path, QColor(_BG))
        pen = QPen(QColor(_DIV))
        pen.setWidthF(1.0)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        border = QPainterPath()
        border.addRoundedRect(
            0.5, 0.5, self.width() - 1.0, self.height() - 1.0, 9.5, 9.5
        )
        p.drawPath(border)
        p.end()

    def _build(self, html: str) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        title_bar = TitleBar("Skill Diff — Original vs Revised", height=40)
        title_bar.close_requested.connect(self.accept)
        outer.addWidget(title_bar)

        inner = QVBoxLayout()
        inner.setContentsMargins(16, 8, 16, 16)
        inner.setSpacing(10)

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setStyleSheet(
            f"QTextBrowser{{background:{SYS_BG_SECONDARY};border:none;"
            f"border-radius:6px;padding:4px;}}"
        )
        browser.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        browser.setHtml(html)
        inner.addWidget(browser, 1)

        close_btn = _action_btn("Close")
        close_btn.setFixedWidth(90)
        close_btn.clicked.connect(self.accept)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        inner.addLayout(btn_row)

        outer.addLayout(inner)


# ── Main view ─────────────────────────────────────────────────────────────────


class SkillManagerView(QWidget):
    status_changed = pyqtSignal(str, str)
    page_actions_changed = pyqtSignal(object)  # emits QWidget | None

    def __init__(self, parent=None):
        super().__init__(parent)
        self._initializing = True
        self._loaded_dir: str | None = None
        self._scan_job: ScanJob | None = None
        self._llm_job: LLMJob | None = None
        self._in_review_mode: bool = False
        self._original_description: str = ""
        self._original_body: str = ""
        self._pre_optimize_desc: str = ""
        self._optimized_desc: str = ""
        self._showing_original: bool = False
        self._ai_status = AiStatusRoutine(lambda m, c: self.status_changed.emit(m, c))
        self._page_actions_widget = self._make_page_actions()
        self._build_ui()
        self._apply_defaults()
        self._initializing = False
        self._show_empty_compliance_state()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(SYS_BG_SECONDARY))
        p.end()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.page_actions_changed.emit(self._page_actions_widget)

    # ── Page actions (taskbar) ────────────────────────────────────────────

    def _make_page_actions(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(0, 0, 4, 0)
        lay.setSpacing(2)

        new_btn = _pa_btn(ICON_NEW_SKILL, "New Skill", primary=True)
        new_btn.clicked.connect(self._new_skill)
        lay.addWidget(new_btn)

        lay.addWidget(_vdivider())

        load_btn = _pa_btn(ICON_LOAD_FILE, "Load SKILL.md", primary=True)
        load_btn.clicked.connect(self._load_skill_md)
        lay.addWidget(load_btn)

        paste_btn = _pa_btn(ICON_PASTE, "Paste from Clipboard", primary=True)
        paste_btn.clicked.connect(self._paste_from_clipboard)
        lay.addWidget(paste_btn)

        lay.addWidget(_vdivider())

        self._review_btn = _pa_btn(ICON_REVIEW, "Review & Improve", primary=True)
        self._review_btn.clicked.connect(self._ai_review)
        lay.addWidget(self._review_btn)

        self._scan_btn = _pa_btn(ICON_SCAN, "Scan Now", primary=True)
        self._scan_btn.clicked.connect(self._scan_now)
        lay.addWidget(self._scan_btn)

        lay.addWidget(_vdivider())

        self._save_source_btn = _pa_btn(ICON_SAVE, "Save to Source", primary=True)
        self._save_source_btn.setEnabled(False)
        self._save_source_btn.setToolTip("Load a SKILL.md file first to enable this")
        self._save_source_btn.clicked.connect(self._save_to_source)
        lay.addWidget(self._save_source_btn)

        self._build_btn = _pa_btn(ICON_BUILD, "Build Package", primary=True)
        self._build_btn.clicked.connect(self._build_package)
        lay.addWidget(self._build_btn)

        return bar

    # ── Build ─────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)
        root.addWidget(self._make_left_panel(), 1)
        root.addWidget(self._make_right_panel(), 1)

    def _make_left_panel(self) -> QWidget:
        col = QWidget()
        col.setStyleSheet("background:transparent;")
        col_lay = QVBoxLayout(col)
        col_lay.setContentsMargins(0, 0, 0, 0)
        col_lay.setSpacing(0)

        inner = _Surface(SYS_BG_SECONDARY)
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(4, 4, 16, 20)
        lay.setSpacing(12)

        # ── Metadata card ─────────────────────────────────────────────────
        meta_card = _Surface(SYS_BG_PRIMARY, radius=8)
        ml = QVBoxLayout(meta_card)
        ml.setContentsMargins(14, 12, 14, 12)
        ml.setSpacing(6)
        ml.addWidget(_section_label("Metadata"))

        ml.addWidget(QLabel("Name"), 0)
        self._name_field = QLineEdit()
        self._name_field.setPlaceholderText("e.g. pdf-processing")
        self._name_field.setStyleSheet(_FIELD_STYLE)
        self._name_field.textChanged.connect(self._revalidate)
        ml.addWidget(self._name_field)
        self._name_error = _error_label()
        ml.addWidget(self._name_error)

        # Description row: [label][robot][toggle][accept][stretch][counter]
        desc_row = QHBoxLayout()
        desc_row.setSpacing(4)
        desc_row.addWidget(QLabel("Description"))
        self._robot_btn = self._make_inline_icon_btn(
            ICON_AI_USAGE,
            "Optimize Description",
        )
        self._robot_btn.clicked.connect(self._optimize_description)
        desc_row.addWidget(self._robot_btn)
        self._desc_toggle_btn = self._make_inline_icon_btn(
            ICON_RIGHT_LEFT,
            "View original",
        )
        self._desc_toggle_btn.setVisible(False)
        self._desc_toggle_btn.clicked.connect(self._toggle_optimize_version)
        desc_row.addWidget(self._desc_toggle_btn)
        self._desc_accept_btn = self._make_inline_icon_btn(
            ICON_CHECK,
            "Accept this version",
        )
        self._desc_accept_btn.setVisible(False)
        self._desc_accept_btn.clicked.connect(self._accept_optimize_version)
        desc_row.addWidget(self._desc_accept_btn)
        desc_row.addStretch()
        self._desc_counter = QLabel("0 / 1024")
        self._desc_counter.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:10px;")
        desc_row.addWidget(self._desc_counter)
        ml.addLayout(desc_row)

        self._desc_field = QPlainTextEdit()
        self._desc_field.setFixedHeight(48)
        self._desc_field.setStyleSheet(_FIELD_STYLE)
        self._desc_field.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        self._desc_field.textChanged.connect(self._revalidate)
        ml.addWidget(self._desc_field)
        self._desc_error = _error_label()
        ml.addWidget(self._desc_error)

        ml.addWidget(_hdivider())

        ml.addWidget(QLabel("License"))
        self._license_field = LicensePicker()
        self._license_field.changed.connect(self._revalidate)
        ml.addWidget(self._license_field)

        for label, attr, placeholder in [
            ("Compatibility", "_compat_field", "leave blank unless needed"),
            ("Allowed tools", "_allowed_tools_field", "e.g. Bash(git:*) Read"),
        ]:
            ml.addWidget(QLabel(label))
            field = QLineEdit()
            field.setPlaceholderText(placeholder)
            field.setStyleSheet(_FIELD_STYLE)
            field.textChanged.connect(self._revalidate)
            setattr(self, attr, field)
            ml.addWidget(field)

        ml.addWidget(_hdivider())
        ml.addWidget(_section_label("Additional Metadata"))
        note = QLabel(
            "Extra frontmatter fields — defaults can be set in Options › Skill Defaults."
        )
        note.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:10px;background:transparent;"
        )
        note.setWordWrap(True)
        ml.addWidget(note)
        self._metadata_editor = _MetadataEditor()
        self._metadata_editor.changed.connect(self._revalidate)
        ml.addWidget(self._metadata_editor)

        lay.addWidget(meta_card)

        # ── Structure card ────────────────────────────────────────────────
        struct_card = _Surface(SYS_BG_PRIMARY, radius=8)
        sl = QVBoxLayout(struct_card)
        sl.setContentsMargins(14, 10, 14, 10)
        sl.setSpacing(4)
        sl.addWidget(_section_label("Structure"))
        sub = QLabel(
            "Optional subfolders — files are copied in when the package is built. Right-click a file to remove it."
        )
        sub.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:10px;")
        sub.setWordWrap(True)
        sl.addWidget(sub)

        self._scripts_box = _CompactFileBox("scripts")
        self._scripts_box.changed.connect(self._run_script_lint)
        self._references_box = _CompactFileBox("references")
        self._assets_box = _CompactFileBox("assets")
        for box in (self._scripts_box, self._references_box, self._assets_box):
            sl.addWidget(_hdivider())
            sl.addWidget(box)

        self._lint_label = QLabel("")
        self._lint_label.setWordWrap(True)
        self._lint_label.setStyleSheet(f"color:{SYS_BORDER_WARNING};font-size:10px;")
        self._lint_label.setVisible(False)
        sl.addWidget(self._lint_label)

        lay.addWidget(struct_card)
        lay.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(inner)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {SYS_BG_SECONDARY}; border: none; }}"
        )
        scroll.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        col_lay.addWidget(scroll, 1)
        return col

    def _make_right_panel(self) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("background:transparent;")
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 4, 0, 0)
        lay.setSpacing(8)

        # ── SKILL.md body card ────────────────────────────────────────────
        body_card = _Surface(SYS_BG_PRIMARY, radius=8)
        bl = QVBoxLayout(body_card)
        bl.setContentsMargins(14, 12, 14, 12)
        bl.setSpacing(6)

        head_row = QHBoxLayout()
        head_row.addWidget(_section_label("SKILL.md Body"))
        head_row.addStretch()
        self._budget_label = QLabel("")
        self._budget_label.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:10px;")
        head_row.addWidget(self._budget_label)
        bl.addLayout(head_row)

        self._body_field = QPlainTextEdit()
        self._body_field.setPlaceholderText(_SAMPLE_BODY)
        self._body_field.setStyleSheet(
            f"background:{SYS_BG_SECONDARY};color:{SYS_TXT_PRIMARY};border:none;"
            f"border-radius:5px;padding:8px;font-size:11px;"
            f"font-family:Consolas,monospace;"
        )
        self._body_field.setMinimumHeight(260)
        self._body_field.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        self._body_field.textChanged.connect(self._revalidate)
        bl.addWidget(self._body_field, 1)

        lay.addWidget(body_card, 2)

        # ── AI Review card (hidden until review arrives) ───────────────────
        self._review_card = _Surface(SYS_BG_PRIMARY, radius=8)
        self._review_card.setVisible(False)
        rl = QVBoxLayout(self._review_card)
        rl.setContentsMargins(14, 12, 14, 12)
        rl.setSpacing(6)

        rl.addWidget(_section_label("AI Review"))

        self._review_browser = QTextBrowser()
        self._review_browser.setMinimumHeight(100)
        self._review_browser.setMaximumHeight(220)
        self._review_browser.setStyleSheet(
            f"QTextBrowser{{background:{SYS_BG_SECONDARY};border:none;"
            f"border-radius:5px;padding:6px;font-size:11px;}}"
        )
        self._review_browser.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        rl.addWidget(self._review_browser)

        review_btns = QHBoxLayout()
        review_btns.setContentsMargins(0, 4, 0, 0)
        review_btns.setSpacing(8)
        self._revert_btn = _ghost_btn("Revert to Original")
        self._revert_btn.clicked.connect(self._revert_to_original)
        self._diff_btn = _ghost_btn("View Diff")
        self._diff_btn.clicked.connect(self._view_diff)
        self._save_review_btn = _ghost_btn("Save Review")
        self._save_review_btn.clicked.connect(self._save_review)
        review_btns.addWidget(self._revert_btn)
        review_btns.addWidget(self._diff_btn)
        review_btns.addWidget(self._save_review_btn)
        review_btns.addStretch()
        rl.addLayout(review_btns)

        lay.addWidget(self._review_card, 0)

        # ── Specification Compliance card ─────────────────────────────────
        comp_card = _Surface(SYS_BG_PRIMARY, radius=8)
        cl = QVBoxLayout(comp_card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(6)

        score_row = QHBoxLayout()
        comp_title = QLabel(
            f'<span style="color:{SYS_ACTION_PRIMARY};font-weight:600;">'
            f"Specification Compliance</span>"
            f' · <a href="https://agentskills.io/specification" '
            f'style="color:{SYS_BORDER_WARNING};font-size:10px;">Agent Skill Specification →</a>'
        )
        comp_title.setStyleSheet("font-size:12px;background:transparent;")
        comp_title.setOpenExternalLinks(True)
        score_row.addWidget(comp_title)
        score_row.addStretch()
        self._score_label = QLabel("")
        self._score_label.setStyleSheet("font-size:18px;font-weight:700;")
        score_row.addWidget(self._score_label)
        cl.addLayout(score_row)

        self._issues_browser = QTextBrowser()
        self._issues_browser.setMinimumHeight(120)
        self._issues_browser.setStyleSheet(
            f"QTextBrowser{{background:{SYS_BG_SECONDARY};border:none;"
            f"border-radius:5px;padding:6px;font-size:11px;}}"
        )
        self._issues_browser.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        cl.addWidget(self._issues_browser)

        lay.addWidget(comp_card, 1)
        return panel

    # ── Inline icon buttons ───────────────────────────────────────────────

    @staticmethod
    def _make_inline_icon_btn(icon: str, tooltip: str) -> QPushButton:
        btn = QPushButton(icon)
        btn.setFixedSize(22, 22)
        btn.setFont(fa(10))
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setStyleSheet(
            f"QPushButton{{background:{SYS_ACTION_PRIMARY};color:{SYS_TXT_PRIMARY};"
            f"border:none;border-radius:4px;}}"
            f"QPushButton:hover{{background:{SYS_ACTION_HOVER};}}"
            f"QPushButton:disabled{{background:{SYS_STROKE_SUBTLE};color:{SYS_TXT_MUTED};}}"
        )
        return btn

    # ── Optimize version toggle ───────────────────────────────────────────

    def _set_toggle_btn_state(self) -> None:
        if self._showing_original:
            color = SYS_BORDER_ADVISORY
            tip = "View AI version"
        else:
            color = SYS_ACTION_PRIMARY
            tip = "View original"
        self._desc_toggle_btn.setToolTip(tip)
        self._desc_toggle_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{color};"
            f"border:none;border-radius:3px;}}"
            f"QPushButton:hover{{background:{SYS_ACTION_PRIMARY}30;}}"
        )

    def _toggle_optimize_version(self) -> None:
        self._showing_original = not self._showing_original
        text = (
            self._pre_optimize_desc if self._showing_original else self._optimized_desc
        )
        self._desc_field.blockSignals(True)
        self._desc_field.setPlainText(text)
        self._desc_field.blockSignals(False)
        self._set_toggle_btn_state()

    def _accept_optimize_version(self) -> None:
        self._pre_optimize_desc = ""
        self._optimized_desc = ""
        self._showing_original = False
        self._desc_toggle_btn.setVisible(False)
        self._desc_accept_btn.setVisible(False)
        self._robot_btn.setEnabled(True)
        self._revalidate()

    # ── New / reset ───────────────────────────────────────────────────────

    def _has_content(self) -> bool:
        return bool(
            self._name_field.text().strip()
            or self._desc_field.toPlainText().strip()
            or self._body_field.toPlainText().strip()
            or self._scripts_box.paths()
            or self._references_box.paths()
            or self._assets_box.paths()
        )

    def _new_skill(self) -> None:
        if self._has_content():
            reply = msg_question(
                self,
                "New Skill",
                "Clear all fields and start a new skill?\nUnsaved changes will be lost.",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._loaded_dir = None
        self._save_source_btn.setEnabled(False)
        self._save_source_btn.setToolTip("Load a SKILL.md file first to enable this")
        self._pre_optimize_desc = ""
        self._optimized_desc = ""
        self._showing_original = False
        self._desc_toggle_btn.setVisible(False)
        self._desc_accept_btn.setVisible(False)

        if self._in_review_mode:
            self._exit_review_mode()

        for w in (self._name_field, self._desc_field, self._body_field):
            w.blockSignals(True)
        self._name_field.clear()
        self._desc_field.clear()
        self._body_field.clear()
        for w in (self._name_field, self._desc_field, self._body_field):
            w.blockSignals(False)

        for box in (self._scripts_box, self._references_box, self._assets_box):
            box.clear()

        self._lint_label.setVisible(False)
        self._apply_defaults()
        self._show_empty_compliance_state()

    # ── Defaults / load ───────────────────────────────────────────────────

    def _apply_defaults(self) -> None:
        d = cfg.load()
        self._license_field.set_value(d.get("default_license", ""))
        self._compat_field.setText(d.get("default_compatibility", ""))
        self._allowed_tools_field.setText(d.get("default_allowed_tools", ""))
        self._metadata_editor.set_metadata(d.get("default_metadata", {}))

    def _load_skill_md(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Load SKILL.md",
            "",
            "SKILL.md (SKILL.md);;Markdown (*.md);;All files (*)",
        )
        if not path:
            return
        self._populate_from_file(path)

    def _paste_from_clipboard(self) -> None:
        text = QApplication.clipboard().text(QClipboard.Mode.Clipboard)
        if not text.strip():
            msg_information(self, "Skill Studio", "Clipboard is empty.")
            return
        self._loaded_dir = None
        self._save_source_btn.setEnabled(False)
        self._save_source_btn.setToolTip("Load a SKILL.md file first to enable this")
        self._populate_from_text(text)

    def _populate_from_file(self, path: str) -> None:
        self._loaded_dir = str(Path(path).parent)
        self._save_source_btn.setEnabled(True)
        self._save_source_btn.setToolTip("Save to Source")
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        self._populate_from_text(text)

    def _populate_from_text(self, text: str) -> None:
        meta: dict = {}
        body = text
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                import yaml

                try:
                    meta = yaml.safe_load(text[3:end]) or {}
                except Exception:
                    meta = {}
                body = text[end + 4 :].lstrip("\n")

        self._name_field.setText(str(meta.get("name", "")))
        self._desc_field.setPlainText(str(meta.get("description", "")))
        self._license_field.set_value(str(meta.get("license", "")))
        self._compat_field.setText(str(meta.get("compatibility", "")))
        self._allowed_tools_field.setText(str(meta.get("allowed-tools", "")))
        self._metadata_editor.set_metadata(dict(meta.get("metadata") or {}))
        self._body_field.setPlainText(body)
        self._revalidate()

    # ── Live validation ───────────────────────────────────────────────────

    def _current_meta(self) -> dict:
        meta = {
            "name": self._name_field.text().strip(),
            "description": self._desc_field.toPlainText().strip(),
        }
        if self._license_field.value():
            meta["license"] = self._license_field.value()
        if self._compat_field.text().strip():
            meta["compatibility"] = self._compat_field.text().strip()
        if self._allowed_tools_field.text().strip():
            meta["allowed-tools"] = self._allowed_tools_field.text().strip()
        extra = self._metadata_editor.get_metadata()
        if extra:
            meta["metadata"] = extra
        return meta

    def _show_empty_compliance_state(self) -> None:
        self._score_label.setText("")
        self._score_label.setStyleSheet("font-size:18px;font-weight:700;")
        self._issues_browser.setHtml(
            f'<html><body style="background:{SYS_BG_SECONDARY};color:{SYS_TXT_MUTED};'
            f'font-family:Segoe UI,sans-serif;font-size:11px;">'
            f"<p>Load a skill, start editing, or click Scan Now to see compliance results.</p>"
            f"</body></html>"
        )
        self._build_btn.setEnabled(False)
        self._budget_label.setText("")
        self._desc_counter.setText("")

    def _revalidate(self) -> None:
        if self._initializing:
            return
        desc_populated = bool(self._desc_field.toPlainText().strip())
        self._robot_btn.setEnabled(desc_populated)
        self._desc_toggle_btn.setEnabled(desc_populated)
        self._desc_accept_btn.setEnabled(desc_populated)
        meta = self._current_meta()
        body = self._body_field.toPlainText()
        folder_name = Path(self._loaded_dir).name if self._loaded_dir else None
        result = spec_compliance.score(meta, folder_name=folder_name, body=body)

        desc_len = len(meta["description"])
        self._desc_counter.setText(f"{desc_len} / 1024")

        self._name_error.setText(" · ".join(result.name_errors))
        self._name_error.setVisible(bool(result.name_errors))
        self._desc_error.setText(" · ".join(result.description_errors))
        self._desc_error.setVisible(bool(result.description_errors))

        lines = body.count("\n") + 1
        tokens = len(body) // 4
        self._budget_label.setText(
            f"{lines} / {spec_compliance.MAX_BODY_LINES} lines  ·  "
            f"~{tokens} / {spec_compliance.MAX_BODY_TOKENS} tokens"
        )

        self._render_compliance(result)
        self._build_btn.setEnabled(
            not result.missing_required
            and not result.name_errors
            and not result.description_errors
        )

    def _render_compliance(self, result: spec_compliance.ComplianceResult) -> None:
        if result.score >= 75:
            colour = SYS_BADGE_SAFE
        elif result.score >= 50:
            colour = SYS_BORDER_ADVISORY
        else:
            colour = SYS_BADGE_UNSAFE
        self._score_label.setText(str(result.score))
        self._score_label.setStyleSheet(
            f"font-size:18px;font-weight:700;color:{colour};"
        )

        rows = []
        for f in result.missing_required:
            rows.append(
                f'<li style="color:{SYS_BADGE_UNSAFE};">missing required: {f}</li>'
            )
        for f in result.missing_recommended:
            rows.append(f'<li style="color:{SYS_BORDER_ADVISORY};">not set: {f}</li>')
        for issue in result.name_errors + result.description_errors:
            rows.append(
                f'<li style="color:{SYS_BADGE_UNSAFE};">{_html.escape(issue)}</li>'
            )
        for warning in result.body_warnings:
            rows.append(
                f'<li style="color:{SYS_BORDER_ADVISORY};">{_html.escape(warning)}</li>'
            )

        if not rows:
            html = f'<p style="color:{SYS_BADGE_SAFE};">All checks pass.</p>'
        else:
            html = f'<ul style="margin:0;padding-left:16px;">{"".join(rows)}</ul>'
        self._issues_browser.setHtml(
            f'<html><body style="background:{SYS_BG_SECONDARY};color:{SYS_TXT_MUTED};'
            f'font-family:Segoe UI,sans-serif;font-size:11px;">{html}</body></html>'
        )

    # ── LLM actions ───────────────────────────────────────────────────────

    _OPTIMIZE_SYSTEM = (
        "You are a skill description optimizer for AI agent skills following the "
        "agentskills.io specification.\n\n"
        "Rules for a great skill description:\n"
        "- Start with an imperative verb (e.g. Convert, Scan, Generate, Analyse)\n"
        "- Describe WHAT THE USER ACCOMPLISHES — never HOW it works internally\n"
        "  (no tool names, section counts, framework names, file formats, "
        "internal mechanics)\n"
        "- Should work as an invocation trigger — an AI model reading this should "
        "know exactly when to use the skill\n"
        "- HARD LENGTH LIMIT: 200 characters maximum. Count carefully before "
        "returning. If you are over 200 characters, cut words until you are under.\n"
        "- No jargon, no references to internal tools or APIs\n\n"
        "Return ONLY the improved description text — no explanation, no quotes, "
        "no preamble. Do not exceed 200 characters under any circumstances."
    )

    _REVIEW_SYSTEM = (
        "You are a senior reviewer for AI agent skills following the agentskills.io specification.\n\n"
        "Analyse the skill, then return your response using EXACTLY these XML tags in this order:\n\n"
        "<ISSUES>\n"
        "- [CRITICAL|WARNING|INFO] <finding>\n"
        "</ISSUES>\n"
        "<CHANGES_MADE>\n"
        "- <brief description of each change you made>\n"
        "</CHANGES_MADE>\n"
        "<REVISED_DESCRIPTION>\n"
        "<improved description — imperative verb, user-intent focused, under 200 chars>\n"
        "</REVISED_DESCRIPTION>\n"
        "<REVISED_BODY>\n"
        "<full revised SKILL.md body markdown>\n"
        "</REVISED_BODY>\n\n"
        "Review criteria:\n"
        "- Spec: name must be lowercase-hyphen; description <= 200 chars, "
        "start with imperative verb, user-intent only (no internal mechanics)\n"
        "- Best practices: step-by-step instructions, Examples section, Gotchas section in body\n"
        "- Body budget: warn if over 500 lines or ~5000 tokens\n"
        "- Scripts: non-interactive (no input()/getpass()/read), must have --help, use exit codes\n"
        "- Description: imperative verb, user-intent focused, not vague or implementation-specific\n"
        "If a section has no items write '- None'.\n"
        "For REVISED_BODY: preserve existing structure, improve clarity, add missing sections "
        "(Examples, Gotchas) if absent. Return the full body, not a summary.\n"
        "For REVISED_DESCRIPTION: strictly enforce the 200-character hard limit."
    )

    def _set_llm_busy(self, active_btn: QPushButton, label: str) -> None:
        self._robot_btn.setEnabled(False)
        self._review_btn.setEnabled(False)
        self._ai_status.authenticating()
        QTimer.singleShot(800, self._ai_status.sending)

    def _set_llm_idle(self) -> None:
        self._robot_btn.setEnabled(True)
        self._review_btn.setEnabled(True)

    def _optimize_description(self) -> None:
        name = self._name_field.text().strip()
        description = self._desc_field.toPlainText().strip()
        self._pre_optimize_desc = description
        body = self._body_field.toPlainText()
        prompt = (
            f"Skill name: {name or '(not set)'}\n"
            f"Current description: {description or '(empty)'}\n\n"
            f"SKILL.md body (for context — do not summarise the body into the description):\n"
            f"{body[:2000]}"
        )
        self._set_llm_busy(self._robot_btn, "Optimising…")
        self._llm_job = LLMJob(prompt, system=self._OPTIMIZE_SYSTEM)
        self._llm_job.finished.connect(self._on_optimize_done)
        self._llm_job.error.connect(self._on_llm_error)
        self._llm_job.start()

    def _on_optimize_done(self, result: str) -> None:
        self._set_llm_idle()
        self._ai_status.done("Description optimised")
        self._optimized_desc = result.strip().strip('"').strip("'")
        self._showing_original = False
        self._desc_field.blockSignals(True)
        self._desc_field.setPlainText(self._optimized_desc)
        self._desc_field.blockSignals(False)
        self._set_toggle_btn_state()
        self._desc_toggle_btn.setVisible(True)
        self._desc_accept_btn.setVisible(True)
        self._robot_btn.setEnabled(False)
        self._revalidate()

    _MAX_REVIEW_BODY_CHARS = (
        16_000  # ~4 000 tokens — stays well inside any model's context
    )

    def _ai_review(self) -> None:
        meta = self._current_meta()
        import yaml

        try:
            frontmatter = yaml.dump(meta, default_flow_style=False, allow_unicode=True)
        except Exception:
            frontmatter = str(meta)
        body = self._body_field.toPlainText()
        if len(body) > self._MAX_REVIEW_BODY_CHARS:
            body = body[: self._MAX_REVIEW_BODY_CHARS]
            body += "\n\n[Body truncated at 16 000 characters for review]"
        skill_content = f"---\n{frontmatter}---\n\n{body}"
        self._set_llm_busy(self._review_btn, "Reviewing…")
        self._llm_job = LLMJob(skill_content, system=self._REVIEW_SYSTEM)
        self._llm_job.finished.connect(self._on_review_done)
        self._llm_job.error.connect(self._on_llm_error)
        self._llm_job.start()

    @staticmethod
    def _parse_review_response(text: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for tag in ("ISSUES", "CHANGES_MADE", "REVISED_DESCRIPTION", "REVISED_BODY"):
            open_tag = f"<{tag}>"
            close_tag = f"</{tag}>"
            start = text.find(open_tag)
            if start == -1:
                result[tag] = ""
                continue
            start += len(open_tag)
            # Use rfind so a closing tag inside a code example doesn't truncate early
            end = text.rfind(close_tag)
            result[tag] = (
                text[start:end].strip() if end > start else text[start:].strip()
            )
        return result

    def _on_review_done(self, result: str) -> None:
        self._set_llm_idle()
        self._ai_status.done("AI review complete")
        parsed = self._parse_review_response(result)
        issues = parsed.get("ISSUES", "- None")
        changes = parsed.get("CHANGES_MADE", "- None")
        revised_desc = parsed.get("REVISED_DESCRIPTION", "")
        revised_body = parsed.get("REVISED_BODY", "")
        if not revised_desc and not revised_body:
            msg_warning(
                self,
                "Review & Improve",
                "The AI response did not contain the expected structured sections.\n\n"
                "Check Options - Scanning to confirm the LLM model is set correctly.",
            )
            return
        self._enter_review_mode(issues, changes, revised_desc, revised_body)

    def _enter_review_mode(
        self, issues: str, changes: str, revised_desc: str, revised_body: str
    ) -> None:
        self._in_review_mode = True
        self._original_description = self._desc_field.toPlainText()
        self._original_body = self._body_field.toPlainText()

        for w in (self._desc_field, self._body_field):
            w.blockSignals(True)
        if revised_desc:
            self._desc_field.setPlainText(revised_desc)
        if revised_body:
            self._body_field.setPlainText(revised_body)
        for w in (self._desc_field, self._body_field):
            w.blockSignals(False)

        review_md = f"**Issues**\n\n{issues}\n\n**Changes made**\n\n{changes}"
        self._review_browser.setMarkdown(review_md)
        self._save_review_btn.setEnabled(bool(self._loaded_dir))
        self._review_card.setVisible(True)
        self._revalidate()

    def _exit_review_mode(self) -> None:
        self._in_review_mode = False
        self._review_card.setVisible(False)
        self._review_browser.clear()
        self._revalidate()

    def _revert_to_original(self) -> None:
        for w in (self._desc_field, self._body_field):
            w.blockSignals(True)
        self._desc_field.setPlainText(self._original_description)
        self._body_field.setPlainText(self._original_body)
        for w in (self._desc_field, self._body_field):
            w.blockSignals(False)
        self._exit_review_mode()

    def _diff_to_html(self, unified_lines: list[str]) -> str:
        rows = []
        for line in unified_lines:
            escaped = _html.escape(line.rstrip("\n"))
            if line.startswith("+++") or line.startswith("---"):
                rows.append(
                    f'<div style="color:{SYS_TXT_MUTED};font-weight:600;">{escaped}</div>'
                )
            elif line.startswith("@@"):
                rows.append(f'<div style="color:{SYS_ACTION_PRIMARY};">{escaped}</div>')
            elif line.startswith("+"):
                rows.append(
                    f'<div style="color:{SYS_BADGE_SAFE};'
                    f'background:{SYS_BADGE_SAFE}22;">{escaped}</div>'
                )
            elif line.startswith("-"):
                rows.append(
                    f'<div style="color:{SYS_BADGE_UNSAFE};'
                    f'background:{SYS_BADGE_UNSAFE}22;">{escaped}</div>'
                )
            else:
                rows.append(f'<div style="color:{SYS_TXT_MUTED};">{escaped}</div>')
        return (
            f'<html><body style="background:{SYS_BG_PRIMARY};'
            f'font-family:Consolas,monospace;font-size:11px;padding:8px;">'
            f'{"".join(rows)}</body></html>'
        )

    def _view_diff(self) -> None:
        desc_diff = list(
            difflib.unified_diff(
                self._original_description.splitlines(keepends=True),
                self._desc_field.toPlainText().splitlines(keepends=True),
                fromfile="description (original)",
                tofile="description (revised)",
                lineterm="\n",
            )
        )
        body_diff = list(
            difflib.unified_diff(
                self._original_body.splitlines(keepends=True),
                self._body_field.toPlainText().splitlines(keepends=True),
                fromfile="body (original)",
                tofile="body (revised)",
                lineterm="\n",
            )
        )
        all_lines = desc_diff + (["\n"] if desc_diff and body_diff else []) + body_diff
        if not all_lines:
            msg_information(
                self, "View Diff", "No differences - the content is unchanged."
            )
            return
        html = self._diff_to_html(all_lines)
        dlg = _DiffDialog(html, parent=self)
        dlg.exec()

    def _save_review(self) -> None:
        if not self._loaded_dir:
            return
        name = self._name_field.text().strip() or "skill"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        desc_diff = "".join(
            difflib.unified_diff(
                self._original_description.splitlines(keepends=True),
                self._desc_field.toPlainText().splitlines(keepends=True),
                fromfile="description (original)",
                tofile="description (revised)",
            )
        )
        body_diff = "".join(
            difflib.unified_diff(
                self._original_body.splitlines(keepends=True),
                self._body_field.toPlainText().splitlines(keepends=True),
                fromfile="body (original)",
                tofile="body (revised)",
            )
        )
        review_text = self._review_browser.toMarkdown()
        content = (
            f"# Skill Review - {name}\n"
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"{review_text}\n\n"
            f"## Description Diff\n\n```diff\n{desc_diff or '(no changes)'}\n```\n\n"
            f"## Body Diff\n\n```diff\n{body_diff or '(no changes)'}\n```\n"
        )
        out_path = Path(self._loaded_dir) / f"skill-review-{timestamp}.md"
        try:
            out_path.write_text(content, encoding="utf-8")
            msg_information(self, "Review Saved", f"Review saved to:\n{out_path}")
        except OSError as exc:
            msg_critical(self, "Save Failed", str(exc))

    def _on_llm_error(self, msg: str) -> None:
        self._set_llm_idle()
        self._ai_status.error("AI error")
        msg_critical(self, "LLM Error", msg)

    # ── Script lint ───────────────────────────────────────────────────────

    def _run_script_lint(self) -> None:
        results = script_lint.lint_scripts(self._scripts_box.paths())
        if not results:
            self._lint_label.setVisible(False)
            return
        lines = []
        for filename, warnings in results.items():
            for w in warnings:
                lines.append(f"{filename}: {w}")
        self._lint_label.setText("\n".join(lines))
        self._lint_label.setVisible(True)

    # ── Package writing ───────────────────────────────────────────────────

    def _write_package(self, dest_root: str) -> Path:
        name = self._name_field.text().strip()
        return self._write_package_into(Path(dest_root) / name)

    def _write_package_into(self, skill_dir: Path) -> Path:
        skill_dir.mkdir(parents=True, exist_ok=True)

        meta = self._current_meta()
        frontmatter_lines = [
            "---",
            f"name: {meta['name']}",
            f"description: {meta['description']}",
        ]
        if "license" in meta:
            frontmatter_lines.append(f"license: {meta['license']}")
        if "compatibility" in meta:
            frontmatter_lines.append(f"compatibility: {meta['compatibility']}")
        if "allowed-tools" in meta:
            frontmatter_lines.append(f"allowed-tools: {meta['allowed-tools']}")
        if meta.get("metadata"):
            frontmatter_lines.append("metadata:")
            for k, v in meta["metadata"].items():
                frontmatter_lines.append(f'  {k}: "{v}"')
        frontmatter_lines.append("---")
        frontmatter = "\n".join(frontmatter_lines)

        body = self._body_field.toPlainText()
        (skill_dir / "SKILL.md").write_text(
            f"{frontmatter}\n\n{body}\n", encoding="utf-8"
        )

        for box, folder in (
            (self._scripts_box, "scripts"),
            (self._references_box, "references"),
            (self._assets_box, "assets"),
        ):
            file_paths = box.paths()
            if not file_paths:
                continue
            target_dir = skill_dir / folder
            target_dir.mkdir(exist_ok=True)
            for src in file_paths:
                try:
                    shutil.copy2(src, target_dir / Path(src).name)
                except OSError:
                    pass

        return skill_dir

    # ── Scan Now ──────────────────────────────────────────────────────────

    def _scan_now(self) -> None:
        self._revalidate()
        if not self._build_btn.isEnabled():
            msg_warning(
                self,
                "Skill Studio",
                "Fix the validation issues shown in Specification Compliance before scanning.",
            )
            return
        self._scan_tmp_dir = tempfile.mkdtemp(prefix="skillscan_staged_")
        skill_dir = self._write_package(self._scan_tmp_dir)

        self._scan_btn.setEnabled(False)
        self._scan_job = ScanJob(str(skill_dir))
        self._scan_job.finished.connect(self._on_scan_done)
        self._scan_job.error.connect(self._on_scan_error)
        self._scan_job.start()

    def _on_scan_done(self, result) -> None:
        self._scan_btn.setEnabled(True)
        self._issues_browser.setHtml(format_result_html(result))
        shutil.rmtree(self._scan_tmp_dir, ignore_errors=True)

    def _on_scan_error(self, msg: str) -> None:
        self._scan_btn.setEnabled(True)
        msg_critical(self, "Scan failed", msg)
        shutil.rmtree(self._scan_tmp_dir, ignore_errors=True)

    # ── Build Package ─────────────────────────────────────────────────────

    def _build_package(self) -> None:
        self._revalidate()
        if not self._build_btn.isEnabled():
            msg_warning(
                self,
                "Skill Studio",
                "Name and description must be valid before building the package.",
            )
            return
        dest_root = QFileDialog.getExistingDirectory(
            self, "Choose a destination folder"
        )
        if not dest_root:
            return
        skill_dir = self._write_package(dest_root)
        msg_information(
            self, "Package built", f"Skill package written to:\n{skill_dir}"
        )

    # ── Save to Source ────────────────────────────────────────────────────

    def _save_to_source(self) -> None:
        if not self._loaded_dir:
            return

        name = self._name_field.text().strip()
        old_dir = Path(self._loaded_dir)
        target_dir = old_dir.parent / name

        meta = self._current_meta()
        body = self._body_field.toPlainText()
        result = spec_compliance.score(meta, folder_name=target_dir.name, body=body)
        if result.missing_required or result.name_errors or result.description_errors:
            self._revalidate()
            msg_warning(
                self,
                "Skill Studio",
                "Fix the validation issues shown in Specification Compliance before saving.",
            )
            return

        if target_dir != old_dir:
            if target_dir.exists():
                msg_critical(
                    self,
                    "Save to Source",
                    f"Can't rename - a folder named '{name}' already exists at:\n{target_dir}",
                )
                return
            reply = msg_question(
                self,
                "Save to Source",
                f"The name changed since loading. Rename the source folder to match?\n\n"
                f"{old_dir}\n-> {target_dir}",
                default=QMessageBox.StandardButton.Yes,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            old_dir.rename(target_dir)
        else:
            reply = msg_question(
                self,
                "Save to Source",
                f"Overwrite the package at:\n{target_dir}",
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        self._write_package_into(target_dir)
        self._loaded_dir = str(target_dir)
        msg_information(self, "Saved", f"Package updated at:\n{target_dir}")
