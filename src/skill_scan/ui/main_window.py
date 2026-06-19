"""SkillScan main window - frameless, taskbar + floating nav panel, QStackedWidget views."""

from PyQt6.QtCore import (
    QEasingCurve,
    QEvent,
    QObject,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
    pyqtSignal,
)
from PyQt6.QtGui import QAction, QColor, QCursor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..core import config as cfg
from ._icons import (
    fa,
    fa_reg,
    ICON_BACK,
    ICON_CLOSE,
    ICON_MAXIMIZE,
    ICON_MINUS,
    ICON_RESTORE,
    ICON_MENU,
    ICON_BELL,
    ICON_INFO,
    ICON_CIRCLE_QUESTION,
    ICON_DASHBOARD,
    ICON_FOLDERS,
    ICON_INVENTORY,
    ICON_MANAGE,
    ICON_TESTING,
    ICON_ACTIVITY,
    ICON_OPTIONS,
    ICON_ABOUT,
    ICON_EXIT,
    ICON_EDIT_PEN,
    ICON_COPY,
    ICON_AI_USAGE,
    ICON_BULLHORN,
)
from ._palette import (
    SYS_ACTION_PRIMARY,
    SYS_BG_PRIMARY,
    SYS_BADGE_UNSAFE,
    SYS_BG_SECONDARY,
    SYS_BG_ROW_HOVER,
    SYS_STROKE_DIVIDER,
    SYS_TXT_PRIMARY,
    SYS_BORDER_ADVISORY,
    SYS_TXT_MUTED,
    SYS_BADGE_SAFE,
    SYS_CONTROL_BG_PRESSED,
    SYS_CONTROL_BG_CRITICAL_PRESSED,
)
from ._widgets import round_corners

# ---- Constants ---------------------------------------------------------------

RESIZE_MARGIN = 8
PANEL_W = 160

_VIEW_NAMES = [
    "Dashboard",
    "Folders",
    "Inventory",
    "Skill Studio",
    "Testing",
    "Activity",
    "Prompt Builder",
    "Amalgamator",
    "Skill Builder",
    "Options",
    "About",
]


# ---- Window panel background -------------------------------------------------


class _MainPanel(QWidget):
    """Draws the rounded SYS_BG_PRIMARY background that acts as the window surface."""

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Fill
        fill = QPainterPath()
        fill.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        p.fillPath(fill, QColor(SYS_BG_SECONDARY))
        # Border - inset by half pen width so stroke isn't clipped at widget edge
        pen = QPen(QColor(SYS_STROKE_DIVIDER))
        pen.setWidthF(1.5)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        border = QPainterPath()
        border.addRoundedRect(
            0.75, 0.75, self.width() - 1.5, self.height() - 1.5, 11.25, 11.25
        )
        p.drawPath(border)
        p.end()


# ---- Task bar ----------------------------------------------------------------


class _TaskBar(QWidget):
    """40px top bar: [menu][back][status] | [SkillScan . View] | [AI][min][max][close]."""

    nav_requested = pyqtSignal(int)
    exit_requested = pyqtSignal()
    back_requested = pyqtSignal()
    alerts_requested = pyqtSignal()
    options_requested = pyqtSignal()
    about_requested = pyqtSignal()
    help_requested = pyqtSignal()
    test_window_requested = pyqtSignal()  # TEMPORARY — diagnostic seam isolation
    minimise_requested = pyqtSignal()
    maximise_requested = pyqtSignal()
    close_requested = pyqtSignal()

    _BTN_BASE = (
        "QPushButton{{"
        "  color:{fg};background:transparent;border:none;border-radius:5px;"
        "  font-family:'Font Awesome 6 Free';font-weight:{fw};font-size:{fs};"
        "}}"
        "QPushButton:hover{{background:{hover};color:{hover_fg};}}"
        "QPushButton:pressed{{background:{press};color:{hover_fg};}}"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.setStyleSheet(f"background:{SYS_BG_PRIMARY};")
        self._drag_pos: QPoint | None = None
        self._max_btn: QPushButton | None = None
        self._dot_lbl: QLabel | None = None
        self._status_lbl: QLabel | None = None
        self._title_lbl: QLabel | None = None
        self._back_btn: QPushButton | None = None
        self._nav_menu: QMenu | None = None
        self._nav_close_timer = QTimer(self)
        self._nav_close_timer.setInterval(80)
        self._nav_close_timer.timeout.connect(self._check_nav_menu_hover)
        self._about_menu: QMenu | None = None
        self._about_close_timer = QTimer(self)
        self._about_close_timer.setInterval(80)
        self._about_close_timer.timeout.connect(self._check_about_menu_hover)
        self._build()

    def _build(self) -> None:
        # Three-section layout: [left, stretch=1] [title] [right, stretch=1]
        # Both side panes absorb spare space equally, so the title stays pinned
        # at the exact horizontal centre regardless of status text length.
        outer = QHBoxLayout(self)
        outer.setContentsMargins(6, 0, 6, 0)
        outer.setSpacing(0)

        # ── Left pane ─────────────────────────────────────────────────────────
        left = QWidget()
        left.setStyleSheet("background:transparent;")
        ll = QHBoxLayout(left)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(2)

        self._menu_btn = QPushButton(ICON_MENU)
        self._menu_btn.setFont(fa(11))
        self._menu_btn.setFixedSize(30, 30)
        self._menu_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._menu_btn.setToolTip("Navigation")
        self._menu_btn.setStyleSheet(
            self._BTN_BASE.format(
                fw="900",
                fs="11pt",
                fg=SYS_TXT_MUTED,
                hover=SYS_BG_SECONDARY,
                hover_fg=SYS_ACTION_PRIMARY,
                press=SYS_CONTROL_BG_PRESSED,
            )
        )
        self._menu_btn.enterEvent = lambda e: self._show_nav_menu()
        ll.addWidget(self._menu_btn)

        self._back_btn = QPushButton(ICON_BACK)
        self._back_btn.setFont(fa(11))
        self._back_btn.setFixedSize(26, 26)
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.setToolTip("Back")
        self._back_btn.setStyleSheet(
            self._BTN_BASE.format(
                fw="900",
                fs="11pt",
                fg=SYS_TXT_MUTED,
                hover=SYS_ACTION_PRIMARY,
                hover_fg=SYS_TXT_PRIMARY,
                press=SYS_ACTION_PRIMARY,
            )
        )
        self._back_btn.setVisible(False)
        self._back_btn.clicked.connect(self.back_requested)
        ll.addWidget(self._back_btn)

        ll.addSpacing(6)
        self._page_actions_box = QWidget()
        self._page_actions_box.setStyleSheet("background:transparent;")
        self._pa_layout = QHBoxLayout(self._page_actions_box)
        self._pa_layout.setContentsMargins(0, 0, 0, 0)
        self._pa_layout.setSpacing(4)
        self._page_actions_box.hide()
        ll.addWidget(self._page_actions_box)

        ll.addSpacing(8)

        self._dot_lbl = QLabel(ICON_BULLHORN)
        self._dot_lbl.setFont(fa(10))
        self._dot_lbl.setStyleSheet(
            f"color:{SYS_ACTION_PRIMARY};background:transparent;padding-right:8px;"
        )
        ll.addWidget(self._dot_lbl)

        self._status_lbl = QLabel("Ready")
        self._status_lbl.setMinimumWidth(160)
        self._status_lbl.setStyleSheet(
            f"color:{SYS_TXT_MUTED};font-size:12px;background:transparent;"
        )
        ll.addWidget(self._status_lbl)

        ll.addStretch()  # absorbs leftover space within the pane

        # ── Centre title ──────────────────────────────────────────────────────
        self._title_lbl = QLabel()
        self._title_lbl.setStyleSheet("background:transparent;")
        self._title_lbl.setAlignment(
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter
        )
        self.set_title("Dashboard")

        # ── Right pane ────────────────────────────────────────────────────────
        right = QWidget()
        right.setStyleSheet("background:transparent;")
        rl = QHBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(2)

        rl.addStretch()  # absorbs leftover space within the pane

        for icon, sig, tip in (
            (ICON_BELL, self.alerts_requested, "Alerts"),
            (ICON_OPTIONS, self.options_requested, "Options"),
            (ICON_CIRCLE_QUESTION, self.help_requested, "Help"),
        ):
            btn = QPushButton(icon)
            btn.setFont(fa(11))
            btn.setFixedSize(26, 26)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setToolTip(tip)
            btn.setStyleSheet(
                self._BTN_BASE.format(
                    fw="900",
                    fs="11pt",
                    fg=SYS_TXT_MUTED,
                    hover=SYS_BG_SECONDARY,
                    hover_fg=SYS_ACTION_PRIMARY,
                    press=SYS_CONTROL_BG_PRESSED,
                )
            )
            btn.clicked.connect(sig)
            rl.addWidget(btn)

        self._about_btn = QPushButton(ICON_INFO)
        self._about_btn.setFont(fa(11))
        self._about_btn.setFixedSize(26, 26)
        self._about_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._about_btn.setToolTip("About")
        self._about_btn.setStyleSheet(
            self._BTN_BASE.format(
                fw="900",
                fs="11pt",
                fg=SYS_TXT_MUTED,
                hover=SYS_BG_SECONDARY,
                hover_fg=SYS_ACTION_PRIMARY,
                press=SYS_CONTROL_BG_PRESSED,
            )
        )
        self._about_btn.clicked.connect(self._show_about_menu)
        rl.addWidget(self._about_btn)

        rl.addSpacing(6)

        vsep = QFrame()
        vsep.setFrameShape(QFrame.Shape.VLine)
        vsep.setFixedWidth(1)
        vsep.setFixedHeight(20)
        vsep.setStyleSheet(f"background:{SYS_STROKE_DIVIDER};border:none;")
        rl.addWidget(vsep)

        rl.addSpacing(4)

        min_btn = QPushButton(ICON_MINUS)
        min_btn.setFont(fa_reg(11))
        min_btn.setFixedSize(28, 28)
        min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        min_btn.setToolTip("Minimise")
        min_btn.setStyleSheet(
            self._BTN_BASE.format(
                fw="400",
                fs="11pt",
                fg=SYS_TXT_MUTED,
                hover=SYS_BG_SECONDARY,
                hover_fg=SYS_TXT_PRIMARY,
                press=SYS_CONTROL_BG_PRESSED,
            )
        )
        min_btn.clicked.connect(self.minimise_requested)
        rl.addWidget(min_btn)

        self._max_btn = QPushButton(ICON_MAXIMIZE)
        self._max_btn.setFont(fa(11))
        self._max_btn.setFixedSize(28, 28)
        self._max_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._max_btn.setToolTip("Maximise")
        self._max_btn.setStyleSheet(
            self._BTN_BASE.format(
                fw="900",
                fs="11pt",
                fg=SYS_TXT_MUTED,
                hover=SYS_BG_SECONDARY,
                hover_fg=SYS_TXT_PRIMARY,
                press=SYS_CONTROL_BG_PRESSED,
            )
        )
        self._max_btn.clicked.connect(self.maximise_requested)
        rl.addWidget(self._max_btn)

        close_btn = QPushButton(ICON_CLOSE)
        close_btn.setFont(fa_reg(11))
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("Hide to tray")
        close_btn.setStyleSheet(
            self._BTN_BASE.format(
                fw="400",
                fs="11pt",
                fg=SYS_TXT_MUTED,
                hover=SYS_BADGE_UNSAFE,
                hover_fg=SYS_TXT_PRIMARY,
                press=SYS_CONTROL_BG_CRITICAL_PRESSED,
            )
        )
        close_btn.clicked.connect(self.close_requested)
        rl.addWidget(close_btn)

        # ── Assemble: left(1) | title | right(1) ─────────────────────────────
        outer.addWidget(left, 1)
        outer.addWidget(self._title_lbl)
        outer.addWidget(right, 1)

    # -- Nav menu (hover on burger) -------------------------------------------

    _NAV_TOP = [
        (0, "Dashboard"),
        (1, "Folders"),
        (2, "Inventory"),
        (3, "Skill Studio"),
        (4, "Testing"),
        (5, "Activity"),
    ]
    _NAV_AI = [
        (6, "Prompt Builder"),
        (7, "Amalgamator"),
        (8, "Skill Builder"),
    ]
    _NAV_BOTTOM = [
        (9, "Options"),
        (10, "About"),
    ]

    def _show_nav_menu(self) -> None:
        if self._nav_menu and self._nav_menu.isVisible():
            return
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{SYS_BG_SECONDARY};color:{SYS_TXT_PRIMARY};"
            f"border:1px solid {SYS_STROKE_DIVIDER};border-radius:6px;padding:4px;}}"
            f"QMenu::item{{padding:6px 20px;border-radius:4px;}}"
            f"QMenu::item:selected{{background:{SYS_BG_ROW_HOVER};color:{SYS_ACTION_PRIMARY};}}"
            f"QMenu::separator{{height:1px;background:{SYS_STROKE_DIVIDER};margin:4px 8px;}}"
        )
        for idx, label in self._NAV_TOP:
            action = QAction(label, self)
            action.triggered.connect(
                lambda checked=False, i=idx: self.nav_requested.emit(i)
            )
            menu.addAction(action)
        menu.addSeparator()
        for idx, label in self._NAV_AI:
            action = QAction(label, self)
            action.triggered.connect(
                lambda checked=False, i=idx: self.nav_requested.emit(i)
            )
            menu.addAction(action)
        menu.addSeparator()
        for idx, label in self._NAV_BOTTOM:
            action = QAction(label, self)
            action.triggered.connect(
                lambda checked=False, i=idx: self.nav_requested.emit(i)
            )
            menu.addAction(action)
        menu.addSeparator()
        test_action = QAction(
            "Test Window", self
        )  # TEMPORARY — diagnostic seam isolation
        test_action.triggered.connect(self.test_window_requested)
        menu.addAction(test_action)
        menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.exit_requested)
        menu.addAction(exit_action)
        self._nav_menu = menu
        menu.aboutToHide.connect(self._on_nav_menu_hide)
        pos = self._menu_btn.mapToGlobal(QPoint(0, self._menu_btn.height() + 2))
        menu.popup(pos)
        self._nav_close_timer.start()

    def _on_nav_menu_hide(self) -> None:
        self._nav_close_timer.stop()
        self._nav_menu = None

    def _check_nav_menu_hover(self) -> None:
        if not self._nav_menu or not self._nav_menu.isVisible():
            self._nav_close_timer.stop()
            self._nav_menu = None
            return
        cursor = QCursor.pos()
        btn_pos = self._menu_btn.mapToGlobal(QPoint(0, 0))
        btn_rect = QRect(btn_pos, self._menu_btn.size()).adjusted(0, 0, 0, 4)
        menu_rect = QRect(self._nav_menu.pos(), self._nav_menu.size())
        if not btn_rect.contains(cursor) and not menu_rect.contains(cursor):
            self._nav_menu.close()

    # -- About submenu --------------------------------------------------------

    def _show_about_menu(self) -> None:
        if self._about_menu and self._about_menu.isVisible():
            return
        menu = QMenu(self)
        menu.setStyleSheet(
            f"QMenu{{background:{SYS_BG_SECONDARY};color:{SYS_TXT_PRIMARY};"
            f"border:1px solid {SYS_STROKE_DIVIDER};border-radius:6px;padding:4px;}}"
            f"QMenu::item{{padding:6px 16px;border-radius:4px;}}"
            f"QMenu::item:selected{{background:{SYS_BG_ROW_HOVER};color:{SYS_ACTION_PRIMARY};}}"
            f"QMenu::item:disabled{{color:{SYS_TXT_MUTED};}}"
            f"QMenu::separator{{height:1px;background:{SYS_STROKE_DIVIDER};margin:4px 8px;}}"
        )
        c = cfg.load()
        from ..core.config import get_llm_creds

        _ic = get_llm_creds(c, "inapp")
        model_raw = _ic.get("model", "")
        model_label = (
            model_raw.split("/")[-1][:24] if model_raw else "No model configured"
        )
        info = QAction(f"Model:  {model_label}", self)
        info.setEnabled(False)
        menu.addAction(info)
        ver = QAction(f"SkillScan  v{__version__}", self)
        ver.setEnabled(False)
        menu.addAction(ver)
        menu.addSeparator()
        about = QAction("About SkillScan", self)
        about.triggered.connect(self.about_requested)
        menu.addAction(about)
        self._about_menu = menu
        menu.aboutToHide.connect(self._on_about_menu_hide)
        x_offset = (self._about_btn.width() - menu.sizeHint().width()) // 2
        pos = self._about_btn.mapToGlobal(
            QPoint(x_offset, self._about_btn.height() + 2)
        )
        menu.popup(pos)
        self._about_close_timer.start()

    def _on_about_menu_hide(self) -> None:
        self._about_close_timer.stop()
        self._about_menu = None

    def _check_about_menu_hover(self) -> None:
        if not self._about_menu or not self._about_menu.isVisible():
            self._about_close_timer.stop()
            self._about_menu = None
            return
        cursor = QCursor.pos()
        btn_pos = self._about_btn.mapToGlobal(QPoint(0, 0))
        btn_rect = QRect(btn_pos, self._about_btn.size()).adjusted(0, 0, 0, 4)
        menu_rect = QRect(self._about_menu.pos(), self._about_menu.size())
        if not btn_rect.contains(cursor) and not menu_rect.contains(cursor):
            self._about_menu.close()

    # -- Public API -----------------------------------------------------------

    def set_title(self, view_name: str) -> None:
        if self._title_lbl:
            self._title_lbl.setText(
                f"<span style='color:{SYS_TXT_PRIMARY};font-weight:700;"
                f"font-size:12px;letter-spacing:1px;'>SKILL</span>"
                f"<span style='color:{SYS_ACTION_PRIMARY};font-weight:700;"
                f"font-size:12px;letter-spacing:1px;'>SCAN</span>"
                f'<span style=\'font-family:"Font Awesome 6 Free";font-weight:900;'
                f"color:{SYS_TXT_PRIMARY};font-size:12px;'>  |  </span>"
                f"<span style='color:{SYS_TXT_MUTED};font-size:11px;'>{view_name}</span>"
            )

    def set_back_visible(self, visible: bool) -> None:
        if self._back_btn:
            self._back_btn.setVisible(visible)

    def update_max_icon(self, is_maximised: bool) -> None:
        if self._max_btn:
            self._max_btn.setText(ICON_RESTORE if is_maximised else ICON_MAXIMIZE)
            self._max_btn.setToolTip("Restore" if is_maximised else "Maximise")

    def set_status(
        self,
        message: str,
        dot_color: str = SYS_ACTION_PRIMARY,
        msg_color: str = SYS_TXT_MUTED,
    ) -> None:
        if self._dot_lbl:
            self._dot_lbl.setStyleSheet(f"color:{dot_color};background:transparent;")
        if self._status_lbl:
            self._status_lbl.setText(message)
            self._status_lbl.setStyleSheet(
                f"color:{msg_color};font-size:12px;background:transparent;"
            )

    def set_page_actions(self, widget: "QWidget | None") -> None:
        while self._pa_layout.count():
            item = self._pa_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        if widget is not None:
            self._pa_layout.addWidget(widget)
            self._page_actions_box.show()
        else:
            self._page_actions_box.hide()

    # -- Drag / double-click --------------------------------------------------

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                e.globalPosition().toPoint() - self.window().frameGeometry().topLeft()
            )

    def mouseDoubleClickEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = None
            self.maximise_requested.emit()

    def mouseMoveEvent(self, e) -> None:
        if self._drag_pos and e.buttons() == Qt.MouseButton.LeftButton:
            win = self.window()
            if hasattr(win, "_maximised") and win._maximised:
                win._toggle_maximise()
                self._drag_pos = QPoint(win.width() // 2, 10)
            win.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, _e) -> None:
        self._drag_pos = None


# ---- Nav panel item ---------------------------------------------------------


class _NavItem(QWidget):
    """Single nav item: icon + label, paint-based."""

    clicked = pyqtSignal()

    def __init__(self, icon: str, label: str, parent=None):
        super().__init__(parent)
        self._icon = icon
        self._label = label
        self._active = False
        self._hover = False
        self.setFixedHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(label)

    def set_active(self, active: bool) -> None:
        if self._active != active:
            self._active = active
            self.update()

    def enterEvent(self, _e) -> None:
        self._hover = True
        self.update()

    def leaveEvent(self, _e) -> None:
        self._hover = False
        self.update()

    def mousePressEvent(self, e) -> None:
        if e.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        if self._active:
            p.fillRect(0, 0, w, h, QColor(13, 148, 136, 40))
            p.fillRect(0, 5, 3, h - 10, QColor(SYS_ACTION_PRIMARY))
        elif self._hover:
            p.fillRect(0, 0, w, h, QColor(SYS_BG_ROW_HOVER))

        color = QColor(SYS_ACTION_PRIMARY) if self._active else QColor(SYS_TXT_MUTED)
        p.setPen(color)
        p.setFont(fa(13))
        p.drawText(
            QRect(10, 0, 22, h),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignHCenter,
            self._icon,
        )

        if self._active:
            p.setPen(QColor(SYS_TXT_PRIMARY))
        p.setFont(QFont("Segoe UI", 10))
        p.drawText(
            QRect(38, 0, w - 42, h),
            Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
            self._label,
        )
        p.end()


# ---- Nav panel (floating) ---------------------------------------------------


class _NavPanel(QWidget):
    """Floating left nav panel - rounded block, collapsible via taskbar toggle."""

    page_changed = pyqtSignal(int)
    exit_requested = pyqtSignal()

    _TOP: list[tuple[str, str]] = [
        (ICON_DASHBOARD, "Dashboard"),
        (ICON_FOLDERS, "Folders"),
        (ICON_INVENTORY, "Inventory"),
        (ICON_MANAGE, "Skill Studio"),
        (ICON_TESTING, "Testing"),
        (ICON_ACTIVITY, "Activity"),
        (ICON_EDIT_PEN, "Prompt Builder"),
        (ICON_COPY, "Amalgamator"),
        (ICON_AI_USAGE, "Skill Builder"),
    ]
    _BOTTOM: list[tuple[str, str]] = [
        (ICON_OPTIONS, "Options"),
        (ICON_ABOUT, "About"),
    ]

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setFixedWidth(PANEL_W)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._anim: QPropertyAnimation | None = None
        # _NavItem children paint full-width hover/active highlights with only
        # 6px top/bottom clearance against this panel's own 8px corner radius
        # (0px side clearance) — without this mask the first/last item's
        # highlight pokes square corners past the panel's rounded card shape.
        round_corners(self, 8)

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 6, 0, 6)
        vbox.setSpacing(0)

        self._items: list[_NavItem] = []

        for i, (icon, label) in enumerate(self._TOP):
            item = _NavItem(icon, label, self)
            item.clicked.connect(lambda idx=i: self._select(idx))
            vbox.addWidget(item)
            self._items.append(item)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background:{SYS_STROKE_DIVIDER};border:none;")
        vbox.addWidget(sep)

        offset = len(self._TOP)
        for i, (icon, label) in enumerate(self._BOTTOM):
            item = _NavItem(icon, label, self)
            item.clicked.connect(lambda idx=i + offset: self._select(idx))
            vbox.addWidget(item)
            self._items.append(item)

        vbox.addStretch()

        exit_sep = QFrame()
        exit_sep.setFrameShape(QFrame.Shape.HLine)
        exit_sep.setFixedHeight(1)
        exit_sep.setStyleSheet(f"background:{SYS_STROKE_DIVIDER};border:none;")
        vbox.addWidget(exit_sep)

        exit_item = _NavItem(ICON_EXIT, "Exit", self)
        exit_item.clicked.connect(self.exit_requested)
        vbox.addWidget(exit_item)

        self._select(0, emit=False)
        self.hide()

    def _select(self, index: int, emit: bool = True) -> None:
        for i, item in enumerate(self._items):
            item.set_active(i == index)
        if emit:
            self.page_changed.emit(index)

    def set_current(self, index: int) -> None:
        self._select(index, emit=False)

    def reposition(self, parent_size: QSize) -> None:
        self.setGeometry(6, 6, PANEL_W, parent_size.height() - 12)

    def toggle_animated(self) -> None:
        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()

        parent = self.parentWidget()
        parent_h = parent.height() if parent else 600
        end_geo = QRect(6, 6, PANEL_W, parent_h - 12)
        start_geo = QRect(-PANEL_W - 10, 6, PANEL_W, parent_h - 12)

        closing = self.isVisible()
        if not closing:
            self.setGeometry(start_geo)
            self.show()
            self.raise_()
            s, e = start_geo, end_geo
        else:
            s, e = end_geo, start_geo

        self._anim = QPropertyAnimation(self, b"geometry")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.setStartValue(s)
        self._anim.setEndValue(e)
        if closing:

            def _on_hide_done():
                self.hide()
                if parent:
                    parent.repaint()

            self._anim.finished.connect(_on_hide_done)
        self._anim.start()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 8, 8)
        p.fillPath(path, QColor(SYS_BG_SECONDARY))
        p.end()


# ---- Content area -----------------------------------------------------------


class _ContentArea(QWidget):
    """Holds the view QStackedWidget plus the floating _NavPanel overlay."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stack: QStackedWidget | None = None
        self._nav: _NavPanel | None = None

    def setup(self, stack: QStackedWidget, nav: _NavPanel) -> None:
        self._stack = stack
        self._nav = nav

    def resizeEvent(self, e) -> None:
        if self._stack:
            self._stack.setGeometry(0, 0, self.width(), self.height())
        if self._nav and self._nav.isVisible():
            self._nav.reposition(QSize(self.width(), self.height()))
        super().resizeEvent(e)


# ---- Dim overlay ------------------------------------------------------------


class _DimOverlay(QWidget):
    """Semi-transparent overlay shown over the panel when a modal-ish window is open."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        clip = QPainterPath()
        clip.addRoundedRect(0, 0, float(self.width()), float(self.height()), 12, 12)
        p.setClipPath(clip)
        p.fillRect(self.rect(), QColor(0, 0, 0, 110))
        p.end()


# ---- Main window ------------------------------------------------------------


class MainWindow(QWidget):
    """Primary SkillScan window - frameless, taskbar + floating nav, stacked views."""

    def __init__(self, tray_app=None, parent=None):
        super().__init__(parent)
        self._tray_app = tray_app
        self._history: list[int] = []

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(1000, 640)
        self.resize(1920, 1024)

        self._maximised: bool = False
        self._pre_max_geo: QRect | None = None
        self._resize_dir: str = ""
        self._resize_start_pos: QPoint | None = None
        self._resize_start_geo: QRect | None = None
        self._resize_cursor_active: bool = False

        self._discovery_workers: list = []

        self._build_ui()
        QApplication.instance().installEventFilter(self)
        self._register_views()
        self._center_on_screen()
        QTimer.singleShot(0, lambda: self._on_nav_changed(0))

        QTimer.singleShot(600, self._check_scanner)
        QTimer.singleShot(800, self._start_discovery)

    # -- UI construction ------------------------------------------------------

    def _build_ui(self) -> None:
        self._outer_layout = QVBoxLayout(self)
        self._outer_layout.setContentsMargins(0, 0, 0, 0)
        self._outer_layout.setSpacing(0)

        self._panel = _MainPanel(self)
        self._panel.setAutoFillBackground(False)
        self._panel.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self._outer_layout.addWidget(self._panel)
        self._dim_overlay = _DimOverlay(self._panel)

        panel_vbox = QVBoxLayout(self._panel)
        panel_vbox.setContentsMargins(2, 0, 2, 12)
        panel_vbox.setSpacing(0)

        _border_cap = QWidget()
        _border_cap.setFixedHeight(2)
        _border_cap.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        panel_vbox.addWidget(_border_cap)

        # Task bar
        self._taskbar = _TaskBar(self)
        self._taskbar.nav_requested.connect(self._on_nav_changed)
        self._taskbar.exit_requested.connect(self._quit)
        self._taskbar.back_requested.connect(self._navigate_back)
        self._taskbar.options_requested.connect(self._show_options_window)
        self._taskbar.help_requested.connect(self._show_help_window)
        self._taskbar.test_window_requested.connect(self._show_test_window)  # TEMPORARY
        self._taskbar.minimise_requested.connect(self.showMinimized)
        self._taskbar.maximise_requested.connect(self._toggle_maximise)
        self._taskbar.close_requested.connect(self._on_close_requested)
        self._options_window = None
        self._help_window = None
        self._test_window = None  # TEMPORARY — diagnostic seam isolation
        panel_vbox.addWidget(self._taskbar)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{SYS_STROKE_DIVIDER};border:none;")
        panel_vbox.addWidget(div)

        # Content area (fills the rest)
        self._content_area = _ContentArea(self)
        self._content_area.setStyleSheet(f"background:{SYS_BG_PRIMARY};")
        panel_vbox.addWidget(self._content_area, 1)

        # Stacked views (positioned by _ContentArea.resizeEvent)
        self._stack = QStackedWidget(self._content_area)
        self._stack.setStyleSheet(f"QStackedWidget {{ background:{SYS_BG_PRIMARY}; }}")

        # Floating nav panel (child of content area, floats above the stack)
        self._nav_panel = _NavPanel(self._content_area)
        self._nav_panel.page_changed.connect(self._on_nav_changed)
        self._nav_panel.exit_requested.connect(self._quit)

        self._content_area.setup(self._stack, self._nav_panel)

    def _register_views(self) -> None:
        from .views.dashboard_view import DashboardView
        from .views.folders_view import FoldersView
        from .views.inventory_view import InventoryView
        from .views.skill_manager_view import SkillManagerView
        from .views.testing_view import TestingView
        from .views.activity_log_view import ActivityLogView
        from .views.prompt_builder_view import PromptBuilderView
        from .views.amalgamator_view import AmalgamatorView
        from .views.skill_competence_view import SkillCompetenceView
        from .views.options_view import OptionsView
        from .views.about_view import AboutView
        from .views.skill_detail_view import SkillDetailView

        views = [
            DashboardView(),  # 0
            FoldersView(),  # 1
            InventoryView(),  # 2
            SkillManagerView(),  # 3
            TestingView(),  # 4
            ActivityLogView(),  # 5
            PromptBuilderView(),  # 6
            AmalgamatorView(),  # 7
            SkillCompetenceView(),  # 8
            OptionsView(),  # 9
            AboutView(),  # 10
            SkillDetailView(),  # 11
        ]
        for view in views:
            self._stack.addWidget(view)

        options_view = self._stack.widget(9)
        if hasattr(options_view, "settings_changed"):
            options_view.settings_changed.connect(self._on_settings_changed)

        dashboard_view = self._stack.widget(0)
        if hasattr(dashboard_view, "navigate_to_folders"):
            dashboard_view.navigate_to_folders.connect(lambda: self._on_nav_changed(1))
        if hasattr(dashboard_view, "navigate_to_activity"):
            dashboard_view.navigate_to_activity.connect(lambda: self._on_nav_changed(5))
        if hasattr(dashboard_view, "navigate_to_options"):
            dashboard_view.navigate_to_options.connect(lambda: self._on_nav_changed(9))
        if hasattr(dashboard_view, "scan_all_requested"):
            dashboard_view.scan_all_requested.connect(self._on_scan_all_requested)
        if hasattr(dashboard_view, "page_actions_changed"):
            dashboard_view.page_actions_changed.connect(self._taskbar.set_page_actions)

        folders_view = self._stack.widget(1)
        if hasattr(folders_view, "skill_detail_requested"):
            folders_view.skill_detail_requested.connect(self._on_skill_detail_requested)

        skill_manager_view = self._stack.widget(3)
        if hasattr(skill_manager_view, "status_changed"):
            skill_manager_view.status_changed.connect(self._taskbar.set_status)
        if hasattr(skill_manager_view, "page_actions_changed"):
            skill_manager_view.page_actions_changed.connect(
                self._taskbar.set_page_actions
            )

    # -- Navigation -----------------------------------------------------------

    def _on_nav_changed(self, index: int) -> None:
        self._history.clear()
        self._taskbar.set_back_visible(False)
        self._taskbar.set_page_actions(None)
        self._stack.setCurrentIndex(index)
        self._nav_panel.set_current(index)
        if index < len(_VIEW_NAMES):
            self._taskbar.set_title(_VIEW_NAMES[index])
        if self._nav_panel.isVisible():
            self._nav_panel.toggle_animated()
        view = self._stack.widget(index)
        if hasattr(view, "on_activated"):
            view.on_activated()

    def navigate_to(self, index: int) -> None:
        self._history.append(self._stack.currentIndex())
        self._taskbar.set_back_visible(True)
        self._stack.setCurrentIndex(index)

    def _navigate_back(self) -> None:
        if self._history:
            index = self._history.pop()
            self._stack.setCurrentIndex(index)
            self._nav_panel.set_current(index)
            self._taskbar.set_back_visible(bool(self._history))

    # -- Public interface -----------------------------------------------------

    def show_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    # -- Internal helpers -----------------------------------------------------

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )

    def _start_discovery(self) -> None:
        try:
            from ..core.db import Folder, init_db, session
            from ..core.skill_discovery import DiscoveryWorker

            init_db()
            with session() as s:
                folders = s.query(Folder).filter_by(watch_enabled=True).all()
                watched = [(f.id, f.path) for f in folders]
        except Exception:
            return

        if not watched:
            return

        self._taskbar.set_status("Discovering skills…", SYS_BORDER_ADVISORY)

        total_done = [0]
        total = len(watched)

        def _on_finished(result):
            total_done[0] += 1
            if total_done[0] >= total:
                added = result.added
                revoked = result.trust_revoked
                if revoked:
                    self._taskbar.set_status(
                        f"Discovery complete - {revoked} trust revocation(s)",
                        SYS_BORDER_ADVISORY,
                    )
                else:
                    self._taskbar.set_status(
                        f"Ready  ·  {added} new skill(s) found" if added else "Ready",
                        SYS_BADGE_SAFE,
                    )

        for folder_id, folder_path in watched:
            worker = DiscoveryWorker(folder_id, folder_path)
            self._discovery_workers.append(worker)

            def _make_handler(w):
                def _handler(result):
                    _on_finished(result)
                    try:
                        self._discovery_workers.remove(w)
                    except ValueError:
                        pass

                return _handler

            worker.finished.connect(_make_handler(worker))
            worker.start()

    def _check_scanner(self) -> None:
        from ..core.scanner import ScanJob

        if ScanJob._find_skill_scanner() is None:
            self._taskbar.set_status(
                "cisco-ai-skill-scanner not found - pip install cisco-ai-skill-scanner[all]",
                SYS_BORDER_ADVISORY,
            )

    def _on_skill_detail_requested(self, skill_id: int) -> None:
        detail_view = self._stack.widget(11)
        if detail_view is not None:
            detail_view.load(skill_id)
            self.navigate_to(11)

    def _show_options_window(self) -> None:
        from .options_window import OptionsWindow

        if self._options_window is None:
            self._options_window = OptionsWindow(parent=None)
            self._options_window.settings_changed.connect(self._on_settings_changed)
            self._options_window.closed.connect(self._on_options_closed)
            self._options_window.destroyed.connect(
                lambda: setattr(self, "_options_window", None)
            )
        if self._options_window.isVisible():
            self._options_window.raise_()
            self._options_window.activateWindow()
        else:
            center = self.geometry().center()
            self._options_window.move(
                center.x() - self._options_window.width() // 2,
                center.y() - self._options_window.height() // 2,
            )
            self._dim_overlay.resize(self._panel.size())
            self._dim_overlay.raise_()
            self._dim_overlay.show()
            self._options_window.show()

    def _on_options_closed(self) -> None:
        self._dim_overlay.hide()

    def _show_help_window(self) -> None:
        from .help_window import HelpWindow

        if self._help_window is None:
            self._help_window = HelpWindow(parent=None)
            self._help_window.closed.connect(self._on_help_closed)
            self._help_window.destroyed.connect(
                lambda: setattr(self, "_help_window", None)
            )
        if self._help_window.isVisible():
            self._help_window.raise_()
            self._help_window.activateWindow()
        else:
            center = self.geometry().center()
            self._help_window.move(
                center.x() - self._help_window.width() // 2,
                center.y() - self._help_window.height() // 2,
            )
            self._dim_overlay.resize(self._panel.size())
            self._dim_overlay.raise_()
            self._dim_overlay.show()
            self._help_window.show()

    def _on_help_closed(self) -> None:
        self._dim_overlay.hide()

    def _show_test_window(self) -> None:
        # TEMPORARY — diagnostic seam isolation, see change_history.md.
        from .test_window import TestWindow

        if self._test_window is None:
            self._test_window = TestWindow(parent=None)
            self._test_window.closed.connect(self._on_test_window_closed)
            self._test_window.destroyed.connect(
                lambda: setattr(self, "_test_window", None)
            )
        if self._test_window.isVisible():
            self._test_window.raise_()
            self._test_window.activateWindow()
        else:
            center = self.geometry().center()
            self._test_window.move(
                center.x() - self._test_window.width() // 2,
                center.y() - self._test_window.height() // 2,
            )
            self._dim_overlay.resize(self._panel.size())
            self._dim_overlay.raise_()
            self._dim_overlay.show()
            self._test_window.show()

    def _on_test_window_closed(self) -> None:
        self._dim_overlay.hide()

    def _on_settings_changed(self) -> None:
        if self._tray_app is not None:
            self._tray_app.reload_config()
        folders_view = self._stack.widget(1)
        if hasattr(folders_view, "sync_watched_folders"):
            folders_view.sync_watched_folders()
        self._taskbar.set_status("Settings saved", SYS_BADGE_SAFE, SYS_BADGE_SAFE)
        QTimer.singleShot(3000, lambda: self._taskbar.set_status("Ready"))

    def _on_scan_all_requested(self) -> None:
        self._start_discovery()
        self._on_nav_changed(1)

    def _on_close_requested(self) -> None:
        if self._tray_app:
            self._tray_app.close_all_dialogs()
        self.hide()

    def _quit(self) -> None:
        if self._tray_app:
            self._tray_app.close_all_dialogs()
            self._tray_app.quit_app()
        else:
            QApplication.quit()

    # -- Resize / maximise ----------------------------------------------------

    def _resize_direction(self, pos: QPoint) -> str:
        if self._maximised:
            return ""
        m = RESIZE_MARGIN
        x, y, w, h = pos.x(), pos.y(), self.width(), self.height()
        left = x < m
        right = x > w - m
        top = y < m
        bottom = y > h - m
        if top and left:
            return "tl"
        if top and right:
            return "tr"
        if bottom and left:
            return "bl"
        if bottom and right:
            return "br"
        if top:
            return "t"
        if bottom:
            return "b"
        if left:
            return "l"
        if right:
            return "r"
        return ""

    def _do_resize(self, global_pos: QPoint) -> None:
        if not self._resize_start_pos or not self._resize_start_geo:
            return
        delta = global_pos - self._resize_start_pos
        geo = QRect(self._resize_start_geo)
        d = self._resize_dir
        min_w, min_h = self.minimumWidth(), self.minimumHeight()
        if "l" in d:
            new_left = geo.left() + delta.x()
            if geo.right() - new_left >= min_w:
                geo.setLeft(new_left)
        if "r" in d:
            new_right = geo.right() + delta.x()
            if new_right - geo.left() >= min_w:
                geo.setRight(new_right)
        if "t" in d:
            new_top = geo.top() + delta.y()
            if geo.bottom() - new_top >= min_h:
                geo.setTop(new_top)
        if "b" in d:
            new_bottom = geo.bottom() + delta.y()
            if new_bottom - geo.top() >= min_h:
                geo.setBottom(new_bottom)
        self.setGeometry(geo)

    def _toggle_maximise(self) -> None:
        if self._maximised:
            if self._pre_max_geo:
                self.setGeometry(self._pre_max_geo)
            self._outer_layout.setContentsMargins(0, 0, 0, 0)
            self._maximised = False
            self._taskbar.update_max_icon(False)
        else:
            self._pre_max_geo = self.geometry()
            screen = QApplication.primaryScreen()
            if screen:
                self.setGeometry(screen.availableGeometry())
            self._outer_layout.setContentsMargins(0, 0, 0, 0)
            self._maximised = True
            self._taskbar.update_max_icon(True)

    _RESIZE_CURSORS = {
        "tl": Qt.CursorShape.SizeFDiagCursor,
        "br": Qt.CursorShape.SizeFDiagCursor,
        "tr": Qt.CursorShape.SizeBDiagCursor,
        "bl": Qt.CursorShape.SizeBDiagCursor,
        "l": Qt.CursorShape.SizeHorCursor,
        "r": Qt.CursorShape.SizeHorCursor,
        "t": Qt.CursorShape.SizeVerCursor,
        "b": Qt.CursorShape.SizeVerCursor,
    }

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        from PyQt6.QtWidgets import QWidget as _QW

        if not isinstance(obj, _QW) or obj.window() is not self:
            return False
        t = event.type()
        if t == QEvent.Type.MouseMove:
            gpos = event.globalPosition().toPoint()
            lpos = self.mapFromGlobal(gpos)
            if self._resize_dir and event.buttons() & Qt.MouseButton.LeftButton:
                self._do_resize(gpos)
                return True
            d = self._resize_direction(lpos)
            if d:
                if not self._resize_cursor_active:
                    QApplication.setOverrideCursor(self._RESIZE_CURSORS[d])
                    self._resize_cursor_active = True
                else:
                    QApplication.changeOverrideCursor(self._RESIZE_CURSORS[d])
            elif self._resize_cursor_active:
                QApplication.restoreOverrideCursor()
                self._resize_cursor_active = False
            return False
        if (
            t == QEvent.Type.MouseButtonPress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            gpos = event.globalPosition().toPoint()
            lpos = self.mapFromGlobal(gpos)
            d = self._resize_direction(lpos)
            if d:
                self._resize_dir = d
                self._resize_start_pos = gpos
                self._resize_start_geo = self.geometry()
                return True
            return False
        if t == QEvent.Type.MouseButtonRelease and self._resize_dir:
            self._resize_dir = ""
            self._resize_start_pos = None
            self._resize_start_geo = None
            if self._resize_cursor_active:
                QApplication.restoreOverrideCursor()
                self._resize_cursor_active = False
            return True
        return False

    def resizeEvent(self, e) -> None:
        super().resizeEvent(e)
        if self._dim_overlay.isVisible():
            self._dim_overlay.resize(self._panel.size())
            self._dim_overlay.raise_()
