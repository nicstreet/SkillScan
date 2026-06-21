"""Options view — two-pane layout: nav list | section content."""

import getpass
import os
import sys
import winreg
from datetime import datetime as _dt
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as pkg_version
from pathlib import Path

from PyQt6.QtCore import QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ...core import config as cfg
from .._icons import (
    fa,
    ICON_AI_USAGE,
    ICON_FOLDERS,
    ICON_INTEGRATION,
    ICON_NEW_SKILL,
    ICON_OPTIONS,
    ICON_PASTE,
    ICON_SEARCH,
    ICON_SECURITY,
    ICON_UPDATES,
)
from .._license_picker import LicensePicker
from .._palette import (
    SYS_ACTION_PRIMARY,
    SYS_ACTION_HOVER,
    SYS_BG_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_BORDER_WARNING,
    SYS_STROKE_SUBTLE,
    SYS_TXT_PRIMARY,
    SYS_TXT_MUTED,
)
from .._widgets import SCROLLBAR_STYLE, _Surface, round_corners

_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_APP_NAME = "SkillScan"
_SKILL_PKG = "cisco-ai-skill-scanner"
_MCP_PKG = "cisco-ai-mcp-scanner"
_LOG_PATH = Path(os.environ.get("APPDATA", "~")) / "SkillScan" / "activity.log"
_DEFAULT_SKILL_VERSION = "1.0.0"
# Nav and content_col both sit flush against this view's own edges (root layout
# has zero margins) and, when standalone, only options_window.py's _OptionsPanel
# margin (2px) separates them from the host window's own 12px-radius curve.
# 8 keeps every corner comfortably inside that clearance on every side that
# matters — see pyqt6-frameless-window's concentric-radius rule.
_CONTENT_RADIUS = 8
# Skill Defaults metadata table — suggested starter rows shown only when nothing
# has been saved yet. Not mandatory; the user can edit, fill in, or remove either.
_METADATA_SUGGESTIONS = [("author", ""), ("version", _DEFAULT_SKILL_VERSION)]


def _log_config_changes(old: dict, new: dict) -> None:
    """Write one audit log line per changed config field."""
    changes: list[str] = []

    # Watched folders
    old_folders = set(old.get("watched_folders", []))
    new_folders = set(new.get("watched_folders", []))
    for f in sorted(new_folders - old_folders):
        changes.append(f"Watched folder added: {f}")
    for f in sorted(old_folders - new_folders):
        changes.append(f"Watched folder removed: {f}")

    # LLM active provider selectors
    for key, label in [
        ("inapp_llm_provider", "Skill Studio LLM provider"),
        ("scanner_llm_provider", "Scanner LLM provider"),
    ]:
        if old.get(key) != new.get(key):
            changes.append(f"{label}: {old.get(key) or '(none)'} → {new.get(key)}")

    # Per-provider model/URL changes
    for key, label in [
        ("anthropic_model", "Anthropic model"),
        ("openai_model", "OpenAI model"),
        ("ollama_model", "Ollama model"),
        ("ollama_base_url", "Ollama base URL"),
        ("openai_local_model", "OpenAI Local model"),
        ("openai_local_base_url", "OpenAI Local base URL"),
    ]:
        if old.get(key) != new.get(key):
            changes.append(
                f"{label}: {old.get(key) or '(none)'} → {new.get(key) or '(none)'}"
            )

    # API keys — log action, never the value
    for key, label in [
        ("anthropic_api_key", "Anthropic API key"),
        ("openai_api_key", "OpenAI API key"),
        ("openai_local_api_key", "OpenAI Local API key"),
        ("virustotal_api_key", "VirusTotal API key"),
        ("ai_defense_api_key", "AI Defense API key"),
        ("mcp_api_key", "MCP API key"),
    ]:
        if old.get(key) != new.get(key):
            if not old.get(key) and new.get(key):
                action = "set"
            elif old.get(key) and not new.get(key):
                action = "cleared"
            else:
                action = "updated"
            changes.append(f"{label}: {action}")

    # Feature toggles
    for key, label in [
        ("use_behavioral", "Behavioral analyzer"),
        ("use_llm", "LLM analyzer"),
        ("use_trigger", "Trigger detection"),
        ("use_aidefense", "AI Defense"),
        ("use_virustotal", "VirusTotal"),
        ("detailed", "Detailed output"),
        ("mcp_use_llm", "MCP LLM-as-judge"),
        ("mcp_use_api", "MCP AI Defense"),
        ("clipboard_watch_enabled", "Clipboard watch"),
    ]:
        if old.get(key) != new.get(key):
            changes.append(f"{label}: {'enabled' if new.get(key) else 'disabled'}")

    # Policy / sensitivity
    if old.get("policy") != new.get("policy"):
        changes.append(
            f"Sensitivity: {old.get('policy') or '(none)'} → {new.get('policy')}"
        )
    if old.get("fail_on_severity") != new.get("fail_on_severity"):
        changes.append(
            f"Fail-on severity: {old.get('fail_on_severity') or '(none)'} "
            f"→ {new.get('fail_on_severity') or '(none)'}"
        )

    # Clipboard intervals
    if old.get("clipboard_watch_interval_secs") != new.get(
        "clipboard_watch_interval_secs"
    ):
        changes.append(
            f"Clipboard interval: {old.get('clipboard_watch_interval_secs')}s "
            f"→ {new.get('clipboard_watch_interval_secs')}s"
        )
    if old.get("clipboard_min_chars") != new.get("clipboard_min_chars"):
        changes.append(
            f"Clipboard min chars: {old.get('clipboard_min_chars')} "
            f"→ {new.get('clipboard_min_chars')}"
        )

    # Skill Defaults (Skill Manager package defaults)
    for key, label in [
        ("default_license", "Default license"),
        ("default_compatibility", "Default compatibility"),
        ("default_allowed_tools", "Default allowed-tools"),
    ]:
        if old.get(key) != new.get(key):
            changes.append(
                f"{label}: {old.get(key) or '(none)'} → {new.get(key) or '(none)'}"
            )
    if old.get("default_metadata") != new.get("default_metadata"):
        changes.append("Default metadata: updated")

    if not changes:
        return

    try:
        user = getpass.getuser()
    except Exception:
        user = "unknown"

    ts = _dt.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    try:
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _LOG_PATH.open("a", encoding="utf-8") as fh:
            for change in changes:
                fh.write(f"[{ts}]  Config changed  —  {change}  user={user}\n")
    except OSError:
        pass


def _pkg_version(pkg: str) -> str:
    try:
        return pkg_version(pkg)
    except PackageNotFoundError:
        return "not installed"


# ── Cascade-immune surface ────────────────────────────────────────────────────

# ── Toggle switch ─────────────────────────────────────────────────────────────


class _ToggleSwitch(QWidget):
    toggled = pyqtSignal(bool)

    def __init__(self, checked: bool = False, parent=None):
        super().__init__(parent)
        self._checked = checked
        self.setFixedSize(24, 16)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def isChecked(self) -> bool:
        return self._checked

    def setChecked(self, value: bool) -> None:
        if self._checked != value:
            self._checked = value
            self.update()
            self.toggled.emit(self._checked)

    def mousePressEvent(self, _e) -> None:
        if self.isEnabled():
            self.setChecked(not self._checked)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if not self.isEnabled():
            p.setOpacity(0.4)
        track = QColor(SYS_ACTION_PRIMARY if self._checked else SYS_STROKE_SUBTLE)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(0, 2, 24, 12, 6, 6)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(14 if self._checked else 2, 4, 8, 8)
        p.end()


# ── Nav list row (icon + label, selection-aware) ──────────────────────────────


class _NavRow(QWidget):
    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background:transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 7, 10, 7)
        lay.setSpacing(10)

        self._icon_lbl = QLabel(icon)
        self._icon_lbl.setFont(fa(12))
        self._icon_lbl.setFixedWidth(16)
        self._icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._icon_lbl)

        self._text_lbl = QLabel(text)
        lay.addWidget(self._text_lbl, 1)

        self.set_selected(False)

    def set_selected(self, selected: bool) -> None:
        colour = SYS_TXT_PRIMARY if selected else SYS_TXT_MUTED
        self._icon_lbl.setStyleSheet(f"color:{colour};background:transparent;")
        self._text_lbl.setStyleSheet(
            f"color:{colour};font-size:12px;background:transparent;"
        )


# ── Update thread ─────────────────────────────────────────────────────────────


class _UpdateThread(QThread):
    line = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def run(self) -> None:
        import subprocess

        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            f"{_SKILL_PKG}[all]",
            _MCP_PKG,
        ]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            for raw in proc.stdout:
                self.line.emit(raw.rstrip())
            proc.wait()
            self.finished.emit(proc.returncode == 0)
        except Exception as exc:
            self.line.emit(f"Error: {exc}")
            self.finished.emit(False)


# ── Registry helpers ──────────────────────────────────────────────────────────


def _get_login_enabled() -> bool:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, _RUN_KEY) as k:
            winreg.QueryValueEx(k, _APP_NAME)
            return True
    except OSError:
        return False


def _set_login_enabled(enabled: bool) -> None:
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, _RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as k:
        if enabled:
            winreg.SetValueEx(k, _APP_NAME, 0, winreg.REG_SZ, sys.executable)
        else:
            try:
                winreg.DeleteValue(k, _APP_NAME)
            except OSError:
                pass


# ── Style constants ───────────────────────────────────────────────────────────

_FIELD_STYLE = (
    f"background:{SYS_TXT_MUTED};color:{SYS_BG_PRIMARY};border:none;"
    f"border-radius:5px;padding:3px 8px;font-size:11px;"
    f"selection-background-color:{SYS_ACTION_PRIMARY};"
)
_COMBO_STYLE = (
    f"QComboBox{{{_FIELD_STYLE}}}"
    f"QComboBox::drop-down{{border:none;}}"
    f"QComboBox:disabled{{background:{SYS_STROKE_SUBTLE};color:{SYS_TXT_MUTED};}}"
    f"QComboBox QAbstractItemView{{background:{SYS_BG_PRIMARY};color:{SYS_TXT_PRIMARY};"
    f"font-size:9pt;"
    f"selection-background-color:{SYS_ACTION_PRIMARY};"
    f"border:1px solid {SYS_STROKE_SUBTLE};}}"
)


def _action_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(24)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: {SYS_ACTION_PRIMARY};
            color: {SYS_TXT_PRIMARY};
            border: none; border-radius: 4px;
            padding: 2px 12px; font-size: 11px; font-weight: 600;
        }}
        QPushButton:hover   {{ background: {SYS_ACTION_HOVER}; }}
        QPushButton:pressed {{ background: {SYS_ACTION_HOVER}; }}
        QPushButton:disabled {{ background: {SYS_STROKE_SUBTLE}; color: {SYS_TXT_MUTED}; }}
    """)
    return btn


def _ghost_btn(text: str) -> QPushButton:
    btn = QPushButton(text)
    btn.setFixedHeight(24)
    btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {SYS_TXT_MUTED};
            border: 1px solid {SYS_STROKE_SUBTLE};
            border-radius: 4px; padding: 2px 12px; font-size: 11px;
        }}
        QPushButton:hover {{ border-color: {SYS_ACTION_PRIMARY}; color: {SYS_TXT_PRIMARY}; }}
    """)
    return btn


def _hdivider() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFixedHeight(1)
    f.setStyleSheet(f"background:{SYS_STROKE_SUBTLE};border:none;")
    return f


def _setting_row(title: str, desc: str, control: QWidget) -> QWidget:
    """Single setting row: [title + description | control]."""
    row = QWidget()
    hl = QHBoxLayout(row)
    hl.setContentsMargins(0, 6, 0, 6)
    hl.setSpacing(16)

    text_col = QVBoxLayout()
    text_col.setSpacing(2)

    t = QLabel(title)
    t.setStyleSheet(f"color:{SYS_ACTION_PRIMARY};font-size:12px;font-weight:600;")
    d = QLabel(desc)
    d.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:10px;")
    d.setWordWrap(True)
    d.setOpenExternalLinks(True)
    d.setTextFormat(Qt.TextFormat.RichText)
    text_col.addWidget(t)
    text_col.addWidget(d)

    hl.addLayout(text_col, 1)
    hl.addWidget(
        control, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
    )
    return row


def _card_wrap(widgets: list) -> _Surface:
    """Wraps a list of widgets in a SYS_BG_PRIMARY rounded card."""
    card = _Surface(SYS_BG_PRIMARY, radius=8)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(16, 4, 16, 4)
    lay.setSpacing(0)
    for i, w in enumerate(widgets):
        lay.addWidget(w)
        if i < len(widgets) - 1:
            lay.addWidget(_hdivider())
    return card


def _provider_card(title: str, widgets: list) -> _Surface:
    """Titled provider card — SYS_ACTION_PRIMARY label + divider + setting rows."""
    card = _Surface(SYS_BG_PRIMARY, radius=8)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(16, 10, 16, 4)
    lay.setSpacing(0)
    hdr = QLabel(title)
    hdr.setStyleSheet(
        f"color:{SYS_ACTION_PRIMARY};font-size:9px;font-weight:700;"
        "letter-spacing:1px;background:transparent;"
    )
    lay.addWidget(hdr)
    lay.addWidget(_hdivider())
    for i, w in enumerate(widgets):
        lay.addWidget(w)
        if i < len(widgets) - 1:
            lay.addWidget(_hdivider())
    return card


def _section_scroll(cards: list) -> QScrollArea:
    """Wraps a list of card widgets in a scrollable SYS_BG_SECONDARY page."""
    inner = _Surface(SYS_BG_SECONDARY)
    lay = QVBoxLayout(inner)
    lay.setContentsMargins(12, 0, 12, 12)
    lay.setSpacing(8)
    for c in cards:
        lay.addWidget(c)
    lay.addStretch()

    # No QScrollArea background of its own — this widget fills content_stack
    # (and therefore content_col) exactly, with zero inset, so its own QSS
    # background would just be a second independently-rendered fill stacked
    # at the same boundary content_stack's removed background used to sit
    # at. `inner`, below, already covers the entire viewport via
    # setWidgetResizable(True) — that's the one fill this page actually needs.
    scroll = QScrollArea()
    scroll.setWidget(inner)
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setStyleSheet("QScrollArea { border: none; }")
    scroll.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
    return scroll


# ── Main view ─────────────────────────────────────────────────────────────────


class OptionsView(QWidget):
    settings_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._data = cfg.load()
        self._update_thread: _UpdateThread | None = None
        self._build_ui()
        self._populate()
        # Autosave signals are connected only after the initial populate() pass
        # above has finished setting widget values — connecting earlier would
        # fire a save on every programmatic setChecked()/setCurrentIndex() call.
        self._wire_autosave()

    # No paintEvent override here on purpose. Nav and content_col (see
    # _build_ui) are both _Surface widgets that paint their own correctly
    # -nested rounded shapes and together tile this entire view with zero
    # gaps — there is nothing left for a square fillRect to cover, and
    # adding one back would just reintroduce the square-corner problem
    # _Surface exists to avoid. See pyqt6-frameless-window.

    # ── Build ──────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._make_nav())

        # Rounded on the right (outer edge) only — square on the left, where it
        # meets the nav column, exactly mirroring help_window.py's column1/
        # column2 split. content_stack (below) is an opaque square fill of its
        # own, so it needs clearance >= _CONTENT_RADIUS on every side that's
        # actually rounded here (right and bottom) or its square corner just
        # paints over — and hides — the curve instead of respecting it.
        content_col = _Surface(
            SYS_BG_SECONDARY, radius=_CONTENT_RADIUS, corners=(False, True, True, False)
        )
        ccl = QVBoxLayout(content_col)
        ccl.setContentsMargins(8, 4, _CONTENT_RADIUS, _CONTENT_RADIUS)
        ccl.setSpacing(4)

        # Thin top row, empty unless a host window injects something into it
        # (e.g. OptionsWindow's close button) via add_header_widget(). Collapses
        # to ~0 height on its own, so the embedded nav-page instance loses nothing.
        self._content_header = QWidget()
        self._content_header.setStyleSheet("background:transparent;")
        self._content_header_lay = QHBoxLayout(self._content_header)
        self._content_header_lay.setContentsMargins(0, 0, 0, 0)
        self._content_header_lay.addStretch()
        ccl.addWidget(self._content_header)

        # No background styling here — content_col's own _Surface fill (same
        # SYS_BG_SECONDARY) already shows through underneath. Painting the
        # same colour again via QSS stacked another independently-sized fill
        # exactly at content_col's clearance boundary; under real DPI-scaled
        # compositing that produced a visible 1px seam where this widget's
        # QSS-rendered edge and content_col's painted edge rounded to
        # slightly different device pixels (invisible in software-rendered
        # grab() testing, visible on a real screen).
        self._content_stack = QStackedWidget()
        ccl.addWidget(self._content_stack, 1)

        root.addWidget(content_col, 1)

        for page in [
            self._make_general_page(),
            self._make_llm_page(),
            self._make_analyzers_page(),
            self._make_mcp_page(),
            self._make_clipboard_page(),
            self._make_folders_page(),
            self._make_skill_defaults_page(),
            self._make_updates_page(),
        ]:
            self._content_stack.addWidget(page)

    def add_header_widget(self, widget: QWidget) -> None:
        """Let a host window (e.g. OptionsWindow's close button) sit in the thin
        row above the content stack, beside the full-height nav rather than above it."""
        self._content_header_lay.addWidget(widget)

    _NAV_PAGES = [
        ("General", ICON_OPTIONS),
        ("LLM", ICON_AI_USAGE),
        ("Analyzers", ICON_SECURITY),
        ("MCP Scanner", ICON_INTEGRATION),
        ("Clipboard", ICON_PASTE),
        ("Watched Folders", ICON_FOLDERS),
        ("Skill Defaults", ICON_NEW_SKILL),
        ("Software Updates", ICON_UPDATES),
    ]

    def _make_nav(self) -> _Surface:
        # Square on the right (internal seam against the content pane), rounded
        # on the left (outer edge, following the window's own rounded corners).
        nav = _Surface(SYS_BG_PRIMARY, radius=8, corners=(True, False, False, True))
        nav.setFixedWidth(180)
        lay = QVBoxLayout(nav)
        # Top/left clearance must exceed the HOST WINDOW's own corner radius
        # (12px, see options_window.py's round_corners() mask) plus its 2px
        # margin — otherwise the window's rounded mask slices straight through
        # this search pill's own corner curve instead of framing it cleanly.
        lay.setContentsMargins(12, 12, 8, 8)
        lay.setSpacing(6)

        search_row = QWidget()
        search_row.setStyleSheet(f"background:{SYS_TXT_MUTED};border-radius:10px;")
        sl = QHBoxLayout(search_row)
        sl.setContentsMargins(10, 0, 10, 0)
        sl.setSpacing(6)
        search_icon = QLabel(ICON_SEARCH)
        search_icon.setFont(fa(10))
        search_icon.setStyleSheet(f"color:{SYS_BG_PRIMARY};background:transparent;")
        sl.addWidget(search_icon)
        self._nav_search = QLineEdit()
        self._nav_search.setPlaceholderText("Search")
        self._nav_search.setStyleSheet(
            f"QLineEdit{{background:transparent;border:none;color:{SYS_BG_PRIMARY};"
            f"font-size:11px;padding:6px 0;selection-background-color:{SYS_ACTION_PRIMARY};}}"
        )
        self._nav_search.textChanged.connect(self._filter_nav)
        sl.addWidget(self._nav_search, 1)
        lay.addWidget(search_row)

        self._nav_list = QListWidget()
        self._nav_list.setStyleSheet(f"""
            QListWidget {{
                background: transparent;
                border: none;
                outline: none;
                font-size: 12px;
            }}
            QListWidget::item {{
                margin: 0;
                border-radius: 6px;
            }}
            QListWidget::item:selected {{
                background: {SYS_BG_SECONDARY};
                border-radius: 6px;
            }}
            QListWidget::item:hover:!selected {{
                background: {SYS_BG_SECONDARY}88;
            }}
        """)
        self._nav_list.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        # Row content (icon + label) can be a hair wider than the list at this
        # fixed width — without this, Qt falls back to its unstyled native
        # horizontal scrollbar rather than just letting the row clip.
        self._nav_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self._nav_rows: list[_NavRow] = []
        for name, icon in self._NAV_PAGES:
            item = QListWidgetItem()
            row = _NavRow(icon, name)
            item.setSizeHint(row.sizeHint())
            self._nav_list.addItem(item)
            self._nav_list.setItemWidget(item, row)
            self._nav_rows.append(row)

        self._nav_list.setCurrentRow(0)
        self._nav_rows[0].set_selected(True)
        self._nav_list.currentRowChanged.connect(self._on_nav_row_changed)
        lay.addWidget(self._nav_list)
        return nav

    def _on_nav_row_changed(self, row: int) -> None:
        for i, nav_row in enumerate(self._nav_rows):
            nav_row.set_selected(i == row)
        if row >= 0:
            self._content_stack.setCurrentIndex(row)

    def _filter_nav(self, text: str) -> None:
        text = text.strip().lower()
        for i in range(self._nav_list.count()):
            item = self._nav_list.item(i)
            name = self._NAV_PAGES[i][0]
            item.setHidden(bool(text) and text not in name.lower())

    # ── Pages ──────────────────────────────────────────────────────────────

    def _make_general_page(self) -> QScrollArea:
        self._chk_login = _ToggleSwitch()
        self._chk_folder_tooltip = _ToggleSwitch()

        return _section_scroll(
            [
                _card_wrap(
                    [
                        _setting_row(
                            "Launch at login",
                            "Start SkillScan minimised to the system tray on Windows startup.",
                            self._chk_login,
                        ),
                        _setting_row(
                            "Show full folder path in tooltip",
                            "Display the complete path when hovering over a folder name.",
                            self._chk_folder_tooltip,
                        ),
                    ]
                )
            ]
        )

    def _make_llm_page(self) -> QScrollArea:
        _providers = ["anthropic", "openai", "ollama", "openai (local)"]

        def _combo() -> QComboBox:
            c = QComboBox()
            c.addItems(_providers)
            c.setStyleSheet(_COMBO_STYLE)
            c.setFixedWidth(160)
            return c

        def _key_field(placeholder: str = "sk-…") -> QLineEdit:
            f = QLineEdit()
            f.setEchoMode(QLineEdit.EchoMode.Password)
            f.setPlaceholderText(placeholder)
            f.setStyleSheet(_FIELD_STYLE)
            f.setFixedWidth(220)
            return f

        def _text_field(placeholder: str = "") -> QLineEdit:
            f = QLineEdit()
            f.setPlaceholderText(placeholder)
            f.setStyleSheet(_FIELD_STYLE)
            f.setFixedWidth(220)
            return f

        # Active provider selectors
        self._inapp_llm_provider = _combo()
        self._scanner_llm_provider = _combo()

        # Per-provider credential fields
        self._anthropic_api_key = _key_field()
        self._anthropic_model = _text_field("anthropic/claude-sonnet-4-6")
        self._openai_api_key = _key_field()
        self._openai_model = _text_field("openai/gpt-4o")
        self._ollama_base_url = _text_field("http://localhost:11434")
        self._ollama_model = _text_field("ollama/llama3.2")
        self._openai_local_base_url = _text_field("http://localhost:1234/v1")
        self._openai_local_model = _text_field("openai/local-model")
        self._openai_local_api_key = _key_field("optional")

        # Third-party integration keys
        self._virustotal_key = _key_field("optional")
        self._ai_defense_key = _key_field("optional")

        return _section_scroll(
            [
                _card_wrap(
                    [
                        _setting_row(
                            "Skill Studio",
                            "Provider for Optimize, AI Review & Security Evaluation.",
                            self._inapp_llm_provider,
                        ),
                        _setting_row(
                            "Scanner LLM Step",
                            "Provider for skill-scanner --use-llm and MCP LLM judge.",
                            self._scanner_llm_provider,
                        ),
                    ]
                ),
                _provider_card(
                    "ANTHROPIC",
                    [
                        _setting_row(
                            "API Key",
                            "Your Anthropic API key.",
                            self._anthropic_api_key,
                        ),
                        _setting_row(
                            "Model",
                            "e.g. anthropic/claude-sonnet-4-6",
                            self._anthropic_model,
                        ),
                    ],
                ),
                _provider_card(
                    "OPENAI",
                    [
                        _setting_row(
                            "API Key", "Your OpenAI API key.", self._openai_api_key
                        ),
                        _setting_row("Model", "e.g. openai/gpt-4o", self._openai_model),
                    ],
                ),
                _provider_card(
                    "OLLAMA  —  local, no API key required",
                    [
                        _setting_row(
                            "Base URL",
                            "Ollama server address. Must be installed and running separately.",
                            self._ollama_base_url,
                        ),
                        _setting_row(
                            "Model", "e.g. ollama/llama3.1:8b", self._ollama_model
                        ),
                    ],
                ),
                _provider_card(
                    "OPENAI (LOCAL)  —  LM Studio, vLLM, LocalAI",
                    [
                        _setting_row(
                            "Base URL",
                            "OpenAI-compatible server address.",
                            self._openai_local_base_url,
                        ),
                        _setting_row(
                            "Model", "e.g. openai/local-model", self._openai_local_model
                        ),
                        _setting_row(
                            "API Key",
                            "Optional — some local servers require a key.",
                            self._openai_local_api_key,
                        ),
                    ],
                ),
                _card_wrap(
                    [
                        _setting_row(
                            "VirusTotal API Key",
                            "Optional — enables binary threat scanning.",
                            self._virustotal_key,
                        ),
                        _setting_row(
                            "Cisco AI Defense API Key",
                            "Optional — enables AI Defense cloud analysis.",
                            self._ai_defense_key,
                        ),
                    ]
                ),
            ]
        )

    def _make_analyzers_page(self) -> QScrollArea:
        self._chk_behavioral = _ToggleSwitch()
        self._chk_llm = _ToggleSwitch()
        self._chk_trigger = _ToggleSwitch()
        self._chk_aidefense = _ToggleSwitch()
        self._chk_virustotal = _ToggleSwitch()
        self._chk_detailed = _ToggleSwitch()

        self._policy = QComboBox()
        self._policy.addItems(["permissive", "strict"])
        self._policy.setStyleSheet(_COMBO_STYLE)
        self._policy.setFixedWidth(140)

        self._fail_on = QComboBox()
        self._fail_on.addItems(["(none)", "low", "medium", "high", "critical"])
        self._fail_on.setStyleSheet(_COMBO_STYLE)
        self._fail_on.setFixedWidth(140)

        return _section_scroll(
            [
                _card_wrap(
                    [
                        _setting_row(
                            "Behavioral",
                            "Run behavioral pattern analysis (--use-behavioral).",
                            self._chk_behavioral,
                        ),
                        _setting_row(
                            "LLM-based",
                            "Use LLM to reason over skill content (--use-llm).",
                            self._chk_llm,
                        ),
                        _setting_row(
                            "Trigger detection",
                            "Detect prompt injection triggers (--use-trigger).",
                            self._chk_trigger,
                        ),
                        _setting_row(
                            "Cisco AI Defense",
                            "Cloud-based AI threat analysis (--use-aidefense).",
                            self._chk_aidefense,
                        ),
                        _setting_row(
                            "VirusTotal",
                            "Binary threat scan via VirusTotal (--use-virustotal).",
                            self._chk_virustotal,
                        ),
                        _setting_row(
                            "Detailed output",
                            "Include full detail in scan output (--detailed).",
                            self._chk_detailed,
                        ),
                    ]
                ),
                _card_wrap(
                    [
                        _setting_row(
                            "Sensitivity",
                            "How aggressively to flag potential issues.",
                            self._policy,
                        ),
                        _setting_row(
                            "Fail on severity",
                            "Exit with failure if this severity level is found.",
                            self._fail_on,
                        ),
                    ]
                ),
            ]
        )

    def _make_mcp_page(self) -> QScrollArea:
        self._mcp_api_key = QLineEdit()
        self._mcp_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self._mcp_api_key.setPlaceholderText("optional")
        self._mcp_api_key.setStyleSheet(_FIELD_STYLE)
        self._mcp_api_key.setFixedWidth(220)

        yara = _ToggleSwitch(checked=True)
        yara.setEnabled(False)

        self._chk_mcp_use_llm = _ToggleSwitch()

        self._chk_mcp_use_api = _ToggleSwitch()
        self._chk_mcp_use_api.toggled.connect(
            lambda on: self._mcp_api_key.setEnabled(on)
        )

        return _section_scroll(
            [
                _card_wrap(
                    [
                        _setting_row(
                            "Cisco AI Defense Key",
                            "Scoped to the MCP Scanner service (MCP_SCANNER_API_KEY).",
                            self._mcp_api_key,
                        ),
                    ]
                ),
                _card_wrap(
                    [
                        _setting_row(
                            "YARA rules",
                            "Always active — offline, no key required.",
                            yara,
                        ),
                        _setting_row(
                            "LLM-as-judge",
                            "Requires LLM API Key from the LLM section.",
                            self._chk_mcp_use_llm,
                        ),
                        _setting_row(
                            "Cisco AI Defense",
                            "Requires Cisco AI Defense Key above.",
                            self._chk_mcp_use_api,
                        ),
                    ]
                ),
            ]
        )

    def _make_clipboard_page(self) -> QScrollArea:
        self._cb_watch_enabled = _ToggleSwitch()
        self._cb_watch_enabled.toggled.connect(self._update_clipboard_fields)

        self._cb_interval = QComboBox()
        for secs in (3, 5, 10, 15, 30):
            self._cb_interval.addItem(f"{secs} s", secs)
        self._cb_interval.setStyleSheet(_COMBO_STYLE)
        self._cb_interval.setFixedWidth(90)

        self._cb_min_chars = QComboBox()
        for chars in (250, 500, 1000):
            self._cb_min_chars.addItem(f"{chars} chars", chars)
        self._cb_min_chars.setStyleSheet(_COMBO_STYLE)
        self._cb_min_chars.setFixedWidth(110)

        return _section_scroll(
            [
                _card_wrap(
                    [
                        _setting_row(
                            "Enable automatic clipboard scanning",
                            "Periodically check the clipboard and scan if content changed.",
                            self._cb_watch_enabled,
                        ),
                        _setting_row(
                            "Check interval",
                            "How often to poll the clipboard.",
                            self._cb_interval,
                        ),
                        _setting_row(
                            "Minimum characters",
                            "Ignore clipboard content shorter than this threshold.",
                            self._cb_min_chars,
                        ),
                    ]
                )
            ]
        )

    def _make_folders_page(self) -> QScrollArea:
        info = QLabel(
            "Folders registered here are auto-scanned when a SKILL.md file changes."
        )
        info.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:10px;")
        info.setWordWrap(True)

        self._chk_watch_notify = _ToggleSwitch()
        self._chk_suppress_scan_windows = _ToggleSwitch()

        self._folder_list = QListWidget()
        self._folder_list.setFixedHeight(150)
        self._folder_list.setStyleSheet(
            f"QListWidget{{background:{SYS_BG_SECONDARY};color:{SYS_TXT_PRIMARY};"
            f"border:none;border-radius:5px;font-size:11px;padding:4px;outline:0;}}"
            f"QListWidget::item{{border:none;padding:2px 4px;border-radius:3px;}}"
            f"QListWidget::item:selected{{background:rgba(13,148,136,35);"
            f"color:{SYS_TXT_PRIMARY};border:none;outline:0;}}"
            f"QListWidget::item:hover:!selected{{background:rgba(13,148,136,18);}}"
        )
        self._folder_list.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        self._folder_list.currentItemChanged.connect(self._on_folder_selection_changed)

        add_btn = _action_btn("+ Add Folder")
        add_btn.clicked.connect(self._add_folder)
        self._rem_btn = _ghost_btn("Remove Selected")
        self._rem_btn.setEnabled(False)
        self._rem_btn.clicked.connect(self._remove_folder)

        btn_row = QWidget()
        bl = QHBoxLayout(btn_row)
        bl.setContentsMargins(0, 6, 0, 0)
        bl.setSpacing(8)
        bl.addWidget(add_btn)
        bl.addWidget(self._rem_btn)
        bl.addStretch()

        card = _Surface(SYS_BG_PRIMARY, radius=8)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)
        lay.addWidget(info)
        lay.addWidget(self._folder_list)
        lay.addWidget(btn_row)

        # Notification / window behaviour card
        notify_card = _card_wrap(
            [
                _setting_row(
                    "Show notification on auto-scan",
                    "Display a Windows tray notification when a watched skill changes "
                    "and a scan starts automatically. Scanning still runs either way.",
                    self._chk_watch_notify,
                ),
                _setting_row(
                    "Suppress scan result windows",
                    "Never open a scan progress window. Results are still written to "
                    "the activity log and the tray notification shows the outcome.",
                    self._chk_suppress_scan_windows,
                ),
            ]
        )

        # AI tooling detection card
        detect_card = _Surface(SYS_BG_PRIMARY, radius=8)
        dl = QVBoxLayout(detect_card)
        dl.setContentsMargins(16, 14, 16, 14)
        dl.setSpacing(6)

        detect_info = QLabel(
            "Scan for installed AI development tools and automatically add their skill "
            "folders to the watched list above."
        )
        detect_info.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:10px;")
        detect_info.setWordWrap(True)
        dl.addWidget(detect_info)

        detect_btn = _action_btn("Detect AI Tooling…")
        detect_btn.setFixedWidth(160)
        detect_btn.clicked.connect(self._detect_tooling)
        detect_btn_row = QWidget()
        dbr = QHBoxLayout(detect_btn_row)
        dbr.setContentsMargins(0, 4, 0, 0)
        dbr.addWidget(detect_btn)
        dbr.addStretch()
        dl.addWidget(detect_btn_row)

        return _section_scroll([card, notify_card, detect_card])

    def _make_skill_defaults_page(self) -> QScrollArea:
        """Default frontmatter values pre-filled into new Skill Manager packages."""
        license_title = QLabel("License")
        license_title.setStyleSheet(
            f"color:{SYS_ACTION_PRIMARY};font-size:12px;font-weight:600;"
        )
        license_desc = QLabel(
            "Applied to new skill packages unless overridden per-skill."
        )
        license_desc.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:10px;")
        license_desc.setWordWrap(True)

        self._default_license = LicensePicker()

        license_card = _Surface(SYS_BG_PRIMARY, radius=8)
        lic_lay = QVBoxLayout(license_card)
        lic_lay.setContentsMargins(16, 14, 16, 14)
        lic_lay.setSpacing(6)
        lic_lay.addWidget(license_title)
        lic_lay.addWidget(license_desc)
        lic_lay.addWidget(self._default_license)

        self._default_compatibility = QLineEdit()
        self._default_compatibility.setPlaceholderText(
            "Leave blank unless this skill needs specific environment requirements"
        )
        self._default_compatibility.setStyleSheet(_FIELD_STYLE)
        self._default_compatibility.setFixedWidth(280)

        self._default_allowed_tools = QLineEdit()
        self._default_allowed_tools.setPlaceholderText("e.g. Bash(git:*) Read")
        self._default_allowed_tools.setStyleSheet(_FIELD_STYLE)
        self._default_allowed_tools.setFixedWidth(220)

        info_card = _card_wrap(
            [
                _setting_row(
                    "Compatibility",
                    "Optional — most skills do not need this field (agentskills.io spec).",
                    self._default_compatibility,
                ),
                _setting_row(
                    "Allowed tools",
                    "Space-separated, pre-approved tools. Experimental - see the "
                    f'<a href="https://agentskills.io/specification#allowed-tools-field" '
                    f'style="color:{SYS_BORDER_WARNING};">License Advice</a>.',
                    self._default_allowed_tools,
                ),
            ]
        )

        # Metadata key/value table
        meta_info = QLabel(
            "Arbitrary key/value pairs merged into every new package's metadata "
            "field. Author and version are pre-filled as good-practice suggestions, "
            "not requirements - edit, fill in, or remove either."
        )
        meta_info.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:10px;")
        meta_info.setWordWrap(True)

        self._meta_table = QTableWidget(0, 2)
        self._meta_table.setHorizontalHeaderLabels(["Key", "Value"])
        self._meta_table.setFixedHeight(130)
        self._meta_table.verticalHeader().hide()
        self._meta_table.setEditTriggers(
            QTableWidget.EditTrigger.DoubleClicked
            | QTableWidget.EditTrigger.SelectedClicked
        )
        self._meta_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._meta_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._meta_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self._meta_table.setStyleSheet(
            f"QTableWidget{{background:{SYS_BG_SECONDARY};color:{SYS_TXT_PRIMARY};"
            f"border:none;border-radius:5px;font-size:11px;gridline-color:{SYS_STROKE_SUBTLE};}}"
            f"QTableWidget::item:selected{{background:{SYS_ACTION_PRIMARY}55;}}"
            f"QHeaderView::section{{background:{SYS_BG_PRIMARY};color:{SYS_TXT_MUTED};"
            f"border:none;padding:4px 8px;font-size:10px;}}"
        )
        self._meta_table.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)
        round_corners(self._meta_table, 5)

        meta_add_btn = _action_btn("+ Add Row")
        meta_add_btn.clicked.connect(self._add_metadata_row)
        meta_rem_btn = _ghost_btn("Remove Selected")
        meta_rem_btn.clicked.connect(self._remove_metadata_row)

        meta_btn_row = QWidget()
        mbl = QHBoxLayout(meta_btn_row)
        mbl.setContentsMargins(0, 6, 0, 0)
        mbl.setSpacing(8)
        mbl.addWidget(meta_add_btn)
        mbl.addWidget(meta_rem_btn)
        mbl.addStretch()

        meta_card = _Surface(SYS_BG_PRIMARY, radius=8)
        mc_lay = QVBoxLayout(meta_card)
        mc_lay.setContentsMargins(16, 14, 16, 14)
        mc_lay.setSpacing(8)
        mc_lay.addWidget(meta_info)
        mc_lay.addWidget(self._meta_table)
        mc_lay.addWidget(meta_btn_row)

        return _section_scroll([license_card, info_card, meta_card])

    def _add_metadata_row(self) -> None:
        row = self._meta_table.rowCount()
        self._meta_table.insertRow(row)
        self._meta_table.setItem(row, 0, QTableWidgetItem(""))
        self._meta_table.setItem(row, 1, QTableWidgetItem(""))
        self._save()

    def _remove_metadata_row(self) -> None:
        for index in sorted(
            {i.row() for i in self._meta_table.selectedIndexes()}, reverse=True
        ):
            self._meta_table.removeRow(index)
        self._save()

    def _make_updates_page(self) -> QScrollArea:
        self._skill_ver_lbl = QLabel()
        self._mcp_ver_lbl = QLabel()
        self._refresh_scanner_versions()

        ver_card = _Surface(SYS_BG_PRIMARY, radius=8)
        vlay = QVBoxLayout(ver_card)
        vlay.setContentsMargins(16, 12, 16, 12)
        vlay.setSpacing(4)

        ver_title = QLabel("Scanner Versions")
        ver_title.setStyleSheet(
            f"color:{SYS_ACTION_PRIMARY};font-size:12px;font-weight:600;"
        )
        vlay.addWidget(ver_title)
        vlay.addWidget(_hdivider())

        for label, val_w in [
            ("Skill Scanner  (cisco-ai-skill-scanner)", self._skill_ver_lbl),
            ("MCP Scanner  (cisco-ai-mcp-scanner)", self._mcp_ver_lbl),
        ]:
            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 2, 0, 2)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:11px;")
            val_w.setStyleSheet(
                f"color:{SYS_TXT_PRIMARY};font-size:11px;font-weight:600;"
            )
            rl.addWidget(lbl)
            rl.addStretch()
            rl.addWidget(val_w)
            vlay.addWidget(row)

        upd_card = _Surface(SYS_BG_PRIMARY, radius=8)
        ulay = QVBoxLayout(upd_card)
        ulay.setContentsMargins(16, 14, 16, 14)
        ulay.setSpacing(8)

        hint = QLabel(
            "Downloads the latest versions of both scanners from PyPI "
            "using the same Python environment as SkillScan."
        )
        hint.setStyleSheet(f"color:{SYS_TXT_MUTED};font-size:10px;")
        hint.setWordWrap(True)
        ulay.addWidget(hint)

        self._update_btn = _action_btn("Update Scanners")
        self._update_btn.clicked.connect(self._run_scanner_update)
        btn_row = QWidget()
        bl = QHBoxLayout(btn_row)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.addWidget(self._update_btn)
        bl.addStretch()
        ulay.addWidget(btn_row)

        self._update_output = QPlainTextEdit()
        self._update_output.setReadOnly(True)
        self._update_output.setFixedHeight(130)
        self._update_output.setStyleSheet(f"""
            QPlainTextEdit {{
                background: {SYS_BG_SECONDARY};
                color: {SYS_TXT_MUTED};
                border: none; border-radius: 5px;
                padding: 6px; font-size: 10px;
                font-family: Consolas, monospace;
            }}
        """)
        self._update_output.hide()
        ulay.addWidget(self._update_output)

        return _section_scroll([ver_card, upd_card])

    # ── Helpers ────────────────────────────────────────────────────────────

    def _update_clipboard_fields(self, enabled: bool) -> None:
        self._cb_interval.setEnabled(enabled)
        self._cb_min_chars.setEnabled(enabled)

    def _on_folder_selection_changed(self, current, _previous) -> None:
        self._rem_btn.setEnabled(current is not None)

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select folder to watch")
        if folder:
            folder = str(Path(folder).resolve())
            existing = {
                str(Path(self._folder_list.item(i).text()).resolve())
                for i in range(self._folder_list.count())
            }
            if folder not in existing:
                self._folder_list.addItem(QListWidgetItem(folder))
                self._save()

    def _remove_folder(self) -> None:
        for item in self._folder_list.selectedItems():
            self._folder_list.takeItem(self._folder_list.row(item))
        self._save()

    def _detect_tooling(self) -> None:
        from ..detect_tooling_dialog import DetectToolingDialog

        dlg = DetectToolingDialog(self)
        if dlg.exec() and dlg.get_paths():
            existing = {
                str(Path(self._folder_list.item(i).text()).resolve())
                for i in range(self._folder_list.count())
            }
            added = False
            for path in dlg.get_paths():
                normalised = str(Path(path).resolve())
                if normalised not in existing:
                    self._folder_list.addItem(QListWidgetItem(normalised))
                    existing.add(normalised)
                    added = True
            if added:
                self._save()

    def _refresh_scanner_versions(self) -> None:
        self._skill_ver_lbl.setText(f"v{_pkg_version(_SKILL_PKG)}")
        self._mcp_ver_lbl.setText(f"v{_pkg_version(_MCP_PKG)}")

    def _run_scanner_update(self) -> None:
        self._update_btn.setEnabled(False)
        self._update_btn.setText("Updating…")
        self._update_output.clear()
        self._update_output.show()
        self._update_thread = _UpdateThread()
        self._update_thread.line.connect(self._update_output.appendPlainText)
        self._update_thread.finished.connect(self._on_scanner_update_done)
        self._update_thread.start()

    def _on_scanner_update_done(self, success: bool) -> None:
        self._update_btn.setEnabled(True)
        self._update_btn.setText("Update Scanners")
        if success:
            self._update_output.appendPlainText("\n✓ Scanners updated successfully.")
            self._refresh_scanner_versions()
        else:
            self._update_output.appendPlainText("\n✗ Update failed — see output above.")

    # ── Populate / save ────────────────────────────────────────────────────

    def _populate(self) -> None:
        d = self._data

        def _set_combo(combo: QComboBox, key: str, default: str) -> None:
            idx = combo.findText(d.get(key, default))
            combo.setCurrentIndex(max(0, idx))

        _set_combo(self._inapp_llm_provider, "inapp_llm_provider", "anthropic")
        _set_combo(self._scanner_llm_provider, "scanner_llm_provider", "anthropic")

        self._anthropic_api_key.setText(d.get("anthropic_api_key", ""))
        self._anthropic_model.setText(d.get("anthropic_model", ""))
        self._openai_api_key.setText(d.get("openai_api_key", ""))
        self._openai_model.setText(d.get("openai_model", ""))
        self._ollama_base_url.setText(d.get("ollama_base_url", ""))
        self._ollama_model.setText(d.get("ollama_model", ""))
        self._openai_local_base_url.setText(d.get("openai_local_base_url", ""))
        self._openai_local_model.setText(d.get("openai_local_model", ""))
        self._openai_local_api_key.setText(d.get("openai_local_api_key", ""))
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
        self._fail_on.setCurrentIndex(max(0, self._fail_on.findText(fail_on)))

        self._chk_login.setChecked(_get_login_enabled())
        self._chk_folder_tooltip.setChecked(d.get("show_folder_tooltip", True))

        for folder in d.get("watched_folders", []):
            self._folder_list.addItem(QListWidgetItem(folder))
        self._chk_watch_notify.setChecked(d.get("watched_folder_notify", True))
        self._chk_suppress_scan_windows.setChecked(
            d.get("suppress_scan_windows", False)
        )

        self._cb_watch_enabled.setChecked(d.get("clipboard_watch_enabled", False))
        interval_idx = self._cb_interval.findData(
            d.get("clipboard_watch_interval_secs", 30)
        )
        self._cb_interval.setCurrentIndex(max(0, interval_idx))
        chars_idx = self._cb_min_chars.findData(d.get("clipboard_min_chars", 250))
        self._cb_min_chars.setCurrentIndex(max(0, chars_idx))
        self._update_clipboard_fields(d.get("clipboard_watch_enabled", False))
        self._mcp_api_key.setText(d.get("mcp_api_key", ""))
        self._chk_mcp_use_llm.setChecked(d.get("mcp_use_llm", False))
        self._chk_mcp_use_api.setChecked(d.get("mcp_use_api", False))
        self._mcp_api_key.setEnabled(d.get("mcp_use_api", False))

        self._default_license.set_value(d.get("default_license", ""))
        self._default_compatibility.setText(d.get("default_compatibility", ""))
        self._default_allowed_tools.setText(d.get("default_allowed_tools", ""))
        self._meta_table.setRowCount(0)
        saved_metadata = d.get("default_metadata", {})
        # Nothing saved yet — seed with suggested starter rows (not mandatory,
        # just good practice). User can edit, fill in, or remove either one.
        rows = saved_metadata.items() if saved_metadata else _METADATA_SUGGESTIONS
        for key, value in rows:
            row = self._meta_table.rowCount()
            self._meta_table.insertRow(row)
            self._meta_table.setItem(row, 0, QTableWidgetItem(str(key)))
            self._meta_table.setItem(row, 1, QTableWidgetItem(str(value)))

    def _save(self) -> None:
        old = dict(self._data)  # snapshot before mutations for audit diff
        d = self._data
        d["inapp_llm_provider"] = self._inapp_llm_provider.currentText()
        d["scanner_llm_provider"] = self._scanner_llm_provider.currentText()
        d["anthropic_api_key"] = self._anthropic_api_key.text().strip()
        d["anthropic_model"] = self._anthropic_model.text().strip()
        d["openai_api_key"] = self._openai_api_key.text().strip()
        d["openai_model"] = self._openai_model.text().strip()
        d["ollama_base_url"] = self._ollama_base_url.text().strip()
        d["ollama_model"] = self._ollama_model.text().strip()
        d["openai_local_base_url"] = self._openai_local_base_url.text().strip()
        d["openai_local_model"] = self._openai_local_model.text().strip()
        d["openai_local_api_key"] = self._openai_local_api_key.text().strip()
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
            self._folder_list.item(i).text() for i in range(self._folder_list.count())
        ]
        d["watched_folder_notify"] = self._chk_watch_notify.isChecked()
        d["suppress_scan_windows"] = self._chk_suppress_scan_windows.isChecked()

        d["clipboard_watch_enabled"] = self._cb_watch_enabled.isChecked()
        d["clipboard_watch_interval_secs"] = self._cb_interval.currentData()
        d["clipboard_min_chars"] = self._cb_min_chars.currentData()

        d["mcp_api_key"] = self._mcp_api_key.text().strip()
        d["mcp_use_llm"] = self._chk_mcp_use_llm.isChecked()
        d["mcp_use_api"] = self._chk_mcp_use_api.isChecked()

        _set_login_enabled(self._chk_login.isChecked())
        d["show_folder_tooltip"] = self._chk_folder_tooltip.isChecked()

        d["default_license"] = self._default_license.value()
        d["default_compatibility"] = self._default_compatibility.text().strip()
        d["default_allowed_tools"] = self._default_allowed_tools.text().strip()
        metadata = {}
        for row in range(self._meta_table.rowCount()):
            key_item = self._meta_table.item(row, 0)
            val_item = self._meta_table.item(row, 1)
            key = key_item.text().strip() if key_item else ""
            if key:
                metadata[key] = val_item.text().strip() if val_item else ""
        d["default_metadata"] = metadata

        cfg.save(d)
        _log_config_changes(old, d)
        self.settings_changed.emit()

    def save_now(self) -> None:
        """Public alias for the host window to call as a closeEvent safety net."""
        self._save()

    def _wire_autosave(self) -> None:
        """Connect every setting control's discrete commit signal to autosave.

        Text fields use editingFinished (commits on Enter/focus-out) rather than
        textChanged, so typing doesn't write to disk on every keystroke; a field
        edited then immediately closed without committing is still caught by the
        save_now() safety net the host window calls from its closeEvent.
        """
        for toggle in (
            self._chk_login,
            self._chk_folder_tooltip,
            self._chk_behavioral,
            self._chk_llm,
            self._chk_trigger,
            self._chk_aidefense,
            self._chk_virustotal,
            self._chk_detailed,
            self._chk_mcp_use_llm,
            self._chk_mcp_use_api,
            self._cb_watch_enabled,
            self._chk_watch_notify,
            self._chk_suppress_scan_windows,
        ):
            toggle.toggled.connect(self._save)

        for combo in (
            self._inapp_llm_provider,
            self._scanner_llm_provider,
            self._policy,
            self._fail_on,
            self._cb_interval,
            self._cb_min_chars,
        ):
            combo.currentIndexChanged.connect(self._save)

        for field in (
            self._anthropic_api_key,
            self._anthropic_model,
            self._openai_api_key,
            self._openai_model,
            self._ollama_base_url,
            self._ollama_model,
            self._openai_local_base_url,
            self._openai_local_model,
            self._openai_local_api_key,
            self._virustotal_key,
            self._ai_defense_key,
            self._mcp_api_key,
            self._default_compatibility,
            self._default_allowed_tools,
        ):
            field.editingFinished.connect(self._save)

        self._default_license.changed.connect(self._save)
        self._meta_table.itemChanged.connect(self._save)
