"""Detect AI Tooling dialog — select installed tools, auto-add their skill paths."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from ..core.tool_detector import collect_watch_dirs, detect_tools
from ._icons import fa, ICON_CLOSE
from ._palette import (
    SYS_ACTION_PRIMARY,
    SYS_ACTION_HOVER,
    SYS_BG_PRIMARY,
    SYS_BG_SECONDARY,
    SYS_BADGE_SAFE,
    SYS_BORDER_ADVISORY,
    SYS_CONTROL_BG_CRITICAL_PRESSED,
    SYS_BADGE_UNSAFE,
    SYS_STROKE_DIVIDER,
    SYS_STROKE_SUBTLE,
    SYS_TXT_PRIMARY,
    SYS_TXT_MUTED,
)
from ._widgets import SCROLLBAR_STYLE

# Format badge colours
_FMT_STYLE = {
    "skill": f"background:{SYS_ACTION_PRIMARY};color:{SYS_TXT_PRIMARY};",
    "mcp": f"background:{SYS_BORDER_ADVISORY};color:{SYS_TXT_PRIMARY};",
    "a2a": f"background:#7C3AED;color:{SYS_TXT_PRIMARY};",
}
_BADGE_BASE = "font-size:9px;font-weight:600;padding:1px 5px;border-radius:3px;letter-spacing:0.5px;"

_STATUS_DETECTED = (SYS_BADGE_SAFE, "● Detected")
_STATUS_NOT_FOUND = (SYS_TXT_MUTED, "○ Not found")
_STATUS_UNVERIFIED = (SYS_BORDER_ADVISORY, "? Unverified")

_CLOSE_BTN_CSS = (
    "QPushButton{{color:{fg};background:transparent;border:none;border-radius:5px;"
    "font-family:'Font Awesome 6 Free';font-weight:900;font-size:10px;}}"
    "QPushButton:hover{{background:{hover};color:{hover_fg};}}"
    "QPushButton:pressed{{background:{press};color:{hover_fg};}}"
)


# ── Surfaces ──────────────────────────────────────────────────────────────────


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
                0, 0, self.width(), self.height(), self._radius, self._radius
            )
            p.fillPath(path, self._color)
        else:
            p.fillRect(self.rect(), self._color)
        p.end()


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
        self.setChecked(not self._checked)

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        track = QColor(SYS_ACTION_PRIMARY if self._checked else SYS_STROKE_SUBTLE)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(track)
        p.drawRoundedRect(0, 2, 24, 12, 6, 6)
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(14 if self._checked else 2, 4, 8, 8)
        p.end()


class _Card(_Surface):
    """Rounded card with drop shadow."""

    def __init__(self, parent=None):
        super().__init__(SYS_BG_SECONDARY, radius=14, parent=parent)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 140))
        shadow.setOffset(0, 6)
        self.setGraphicsEffect(shadow)


# ── Title bar ────────────────────────────────────────────────────────────────


class _TitleBar(QWidget):
    """32 px title bar — SKILLSCAN wordmark + close button, draggable."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(32)
        self.setStyleSheet("background:transparent;")
        self._drag_pos = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 0, 6, 0)
        lay.setSpacing(4)

        wordmark = QLabel(
            f"<span style='color:{SYS_TXT_PRIMARY};font-weight:700;"
            f"letter-spacing:2px;font-size:13px;'>SKILL</span>"
            f"<span style='color:{SYS_ACTION_PRIMARY};font-weight:700;"
            f"letter-spacing:2px;font-size:13px;'>SCAN</span>"
        )
        wordmark.setStyleSheet("background:transparent;")
        lay.addWidget(wordmark)
        lay.addStretch()

        close_btn = QPushButton(ICON_CLOSE)  # xmark
        close_btn.setFont(fa(9))
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("Close")
        close_btn.setStyleSheet(
            _CLOSE_BTN_CSS.format(
                fg=SYS_TXT_MUTED,
                hover=SYS_BADGE_UNSAFE,
                hover_fg=SYS_TXT_PRIMARY,
                press=SYS_CONTROL_BG_CRITICAL_PRESSED,
            )
        )
        close_btn.clicked.connect(self.window().reject)
        lay.addWidget(close_btn)

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                e.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, e) -> None:
        if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
            self.window().move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, _e) -> None:
        self._drag_pos = None


# ── Tool row ─────────────────────────────────────────────────────────────────


class _ToolRow(QWidget):
    """Single tool row: checkbox | name + vendor | format badges | status."""

    def __init__(self, tool: dict, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.tool = tool
        self._build(tool)

    def _build(self, tool: dict) -> None:
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 8)
        lay.setSpacing(10)

        self._check = _ToggleSwitch(checked=tool.get("detected", False))
        lay.addWidget(self._check, 0, Qt.AlignmentFlag.AlignVCenter)

        name_col = QVBoxLayout()
        name_col.setSpacing(1)
        name_lbl = QLabel(tool["name"])
        name_lbl.setStyleSheet(
            f"color:{SYS_TXT_PRIMARY};font-size:12px;font-weight:500;background:transparent;"
        )
        vendor_lbl = QLabel(tool.get("vendor", ""))
        vendor_lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:10px;background:transparent;"
        )
        name_col.addWidget(name_lbl)
        name_col.addWidget(vendor_lbl)
        lay.addLayout(name_col, 1)

        badges = QHBoxLayout()
        badges.setSpacing(4)
        for fmt in tool.get("formats", []):
            style = _FMT_STYLE.get(
                fmt, f"background:{SYS_TXT_MUTED};color:{SYS_TXT_PRIMARY};"
            )
            b = QLabel(fmt.upper())
            b.setStyleSheet(f"{_BADGE_BASE}{style}")
            badges.addWidget(b)
        badges.addStretch()
        lay.addLayout(badges)

        if tool.get("status") == "unverified":
            colour, text = _STATUS_UNVERIFIED
        elif tool.get("detected"):
            colour, text = _STATUS_DETECTED
        else:
            colour, text = _STATUS_NOT_FOUND

        status_lbl = QLabel(text)
        status_lbl.setFixedWidth(90)
        status_lbl.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        status_lbl.setStyleSheet(
            f"color:{colour};font-size:10px;font-weight:500;background:transparent;"
        )
        resolved = tool.get("resolved_paths", {}).get("skill", [])
        if resolved:
            status_lbl.setToolTip("Skill paths:\n" + "\n".join(resolved))
        lay.addWidget(status_lbl)

    def is_checked(self) -> bool:
        return self._check.isChecked()


# ── Dialog ───────────────────────────────────────────────────────────────────


class DetectToolingDialog(QDialog):
    """Select installed AI tools; returns verified skill paths to add to watched folders."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setMinimumSize(720, 580)
        self.resize(740, 600)

        self._tools = detect_tools()
        self._rows: list[_ToolRow] = []
        self._result_paths: list[str] = []
        self._build_ui()

    def get_paths(self) -> list[str]:
        return self._result_paths

    def _build_ui(self) -> None:
        # Outer layout — margins leave room for drop shadow
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 22)

        card = _Card(self)
        card_lay = QVBoxLayout(card)
        card_lay.setContentsMargins(0, 0, 0, 0)
        card_lay.setSpacing(0)

        # Title bar
        title_bar = _TitleBar(card)
        card_lay.addWidget(title_bar)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{SYS_STROKE_DIVIDER};border:none;")
        card_lay.addWidget(div)

        # Body
        body = QWidget()
        body.setStyleSheet("background:transparent;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(16, 14, 16, 14)
        body_lay.setSpacing(10)

        # Detection summary banner
        detected_count = sum(1 for t in self._tools if t.get("detected"))
        total = len(self._tools)

        banner = _Surface(SYS_BG_PRIMARY, radius=6)
        bl = QVBoxLayout(banner)
        bl.setContentsMargins(14, 10, 14, 10)
        bl.setSpacing(4)

        sub = QLabel(
            "Select the tools you have installed. SkillScan will verify their skill paths "
            "and add them to your watched folders list."
        )
        sub.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:11px;background:transparent;"
        )
        sub.setWordWrap(True)

        detection_lbl = QLabel(
            f"<span style='color:{SYS_BADGE_SAFE};font-weight:600;'>{detected_count}</span>"
            f"<span style='color:{SYS_TXT_MUTED};'> of {total} tools detected on this machine</span>"
        )
        detection_lbl.setStyleSheet("background:transparent;font-size:11px;")
        bl.addWidget(sub)
        bl.addWidget(detection_lbl)
        body_lay.addWidget(banner)

        # Filter buttons
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        sel_all = QPushButton("Select All")
        sel_detected = QPushButton("Select Detected")
        sel_none = QPushButton("Clear")
        for btn in (sel_all, sel_detected, sel_none):
            btn.setFixedHeight(22)
            btn.setStyleSheet(
                f"QPushButton{{background:transparent;color:{SYS_TXT_MUTED};"
                f"border:1px solid {SYS_STROKE_SUBTLE};border-radius:4px;"
                f"font-size:10px;padding:1px 10px;}}"
                f"QPushButton:hover{{color:{SYS_TXT_PRIMARY};border-color:{SYS_ACTION_PRIMARY};}}"
            )
        sel_all.clicked.connect(lambda: self._set_all(True))
        sel_detected.clicked.connect(self._select_detected)
        sel_none.clicked.connect(lambda: self._set_all(False))
        filter_row.addWidget(sel_all)
        filter_row.addWidget(sel_detected)
        filter_row.addWidget(sel_none)
        filter_row.addStretch()
        body_lay.addLayout(filter_row)

        # Tool list card — plain QWidget inside so it doesn't paint over rounded corners
        list_card = _Surface(SYS_BG_SECONDARY, radius=8)
        list_lay = QVBoxLayout(list_card)
        list_lay.setContentsMargins(1, 1, 1, 1)
        list_lay.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea{background:transparent;border:none;}"
            "QScrollArea > QWidget > QWidget{background:transparent;}"
        )
        scroll.verticalScrollBar().setStyleSheet(SCROLLBAR_STYLE)

        inner = QWidget()
        inner.setStyleSheet("background:transparent;")
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(0, 0, 0, 0)
        inner_lay.setSpacing(0)

        for i, tool in enumerate(self._tools):
            row = _ToolRow(tool, inner)
            bg = SYS_BG_SECONDARY if i % 2 else SYS_BG_PRIMARY
            row.setStyleSheet(f"background:{bg};")
            self._rows.append(row)
            inner_lay.addWidget(row)
            if i < len(self._tools) - 1:
                d = QFrame()
                d.setFrameShape(QFrame.Shape.HLine)
                d.setFixedHeight(1)
                d.setStyleSheet(f"background:{SYS_STROKE_DIVIDER};border:none;")
                inner_lay.addWidget(d)

        inner_lay.addStretch()
        scroll.setWidget(inner)
        list_lay.addWidget(scroll)
        body_lay.addWidget(list_card, 1)

        # Summary + buttons — summary sits left, buttons right, same row height
        self._summary_lbl = QLabel()
        self._summary_lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:10px;background:transparent;"
        )
        for row in self._rows:
            row._check.toggled.connect(lambda _checked: self._update_summary())

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        btn_row.addWidget(self._summary_lbl, 0, Qt.AlignmentFlag.AlignVCenter)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet(
            f"QPushButton{{background:transparent;color:{SYS_TXT_MUTED};"
            f"border:1px solid {SYS_STROKE_SUBTLE};border-radius:5px;"
            f"padding:4px 16px;font-size:12px;}}"
            f"QPushButton:hover{{color:{SYS_TXT_PRIMARY};border-color:{SYS_TXT_PRIMARY};}}"
        )
        cancel_btn.clicked.connect(self.reject)

        self._add_btn = QPushButton("Add to Watched Folders")
        self._add_btn.setFixedHeight(28)
        self._add_btn.setStyleSheet(
            f"QPushButton{{background:{SYS_ACTION_PRIMARY};color:{SYS_TXT_PRIMARY};"
            f"border:none;border-radius:5px;padding:4px 16px;"
            f"font-size:12px;font-weight:600;}}"
            f"QPushButton:hover{{background:{SYS_ACTION_HOVER};}}"
            f"QPushButton:disabled{{background:{SYS_STROKE_SUBTLE};color:{SYS_TXT_MUTED};}}"
        )
        self._add_btn.clicked.connect(self._accept)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self._add_btn)
        body_lay.addLayout(btn_row)

        card_lay.addWidget(body, 1)
        outer.addWidget(card)

        self._update_summary()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _selected_tools(self) -> list[dict]:
        return [row.tool for row in self._rows if row.is_checked()]

    def _update_summary(self) -> None:
        paths = collect_watch_dirs(self._selected_tools(), "skill")
        n = len(paths)
        if n == 0:
            self._summary_lbl.setText("No valid skill paths found for selected tools.")
            self._add_btn.setEnabled(False)
        else:
            self._summary_lbl.setText(
                f"{n} skill path{'s' if n != 1 else ''} will be added to watched folders."
            )
            self._add_btn.setEnabled(True)

    def _set_all(self, checked: bool) -> None:
        for row in self._rows:
            row._check.setChecked(checked)

    def _select_detected(self) -> None:
        for row in self._rows:
            row._check.setChecked(row.tool.get("detected", False))

    def _accept(self) -> None:
        self._result_paths = collect_watch_dirs(self._selected_tools(), "skill")
        self.accept()
