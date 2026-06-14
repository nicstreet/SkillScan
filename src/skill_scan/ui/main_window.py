"""SkillScan v2 main window — frameless, nav rail, QStackedWidget views."""

from PyQt6.QtCore import QPoint, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..core import config as cfg
from ._palette import (
    ACCENT,
    ANCHOR,
    CRITICAL_ACCENT,
    DEEP_SURFACE,
    DIVIDER,
    LIGHT_CANVAS,
    MEDIUM_ACCENT,
    MUTED_TEXT,
    SAFE_ACCENT,
)
from .nav_rail import NavRail

# ── Window chrome helpers ────────────────────────────────────────────────────


class _MainPanel(QWidget):
    """Draws the rounded ANCHOR-coloured panel that acts as the window background."""

    def paintEvent(self, _e) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(0, 0, self.width(), self.height(), 12, 12)
        p.fillPath(path, QColor(ANCHOR))
        p.end()


class _TitleBar(QWidget):
    """Custom frameless title bar — SKILLSCAN wordmark, back, minimise, close."""

    back_requested = pyqtSignal()
    minimise_requested = pyqtSignal()
    close_requested = pyqtSignal()

    _BTN_BASE = (
        "QPushButton{{"
        "  color:{fg};background:transparent;border:none;border-radius:5px;"
        "  font-family:'Segoe Fluent Icons';font-size:10px;"
        "}}"
        "QPushButton:hover{{background:{hover};color:{hover_fg};}}"
        "QPushButton:pressed{{background:{press};color:{hover_fg};}}"
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self._drag_pos: QPoint | None = None
        self.setStyleSheet(f"background: {DEEP_SURFACE};")
        self._build()

    def _build(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 6, 0)
        layout.setSpacing(4)

        # Back button (hidden until history is non-empty)
        self._back_btn = QPushButton("")  # ChevronLeft / Back
        self._back_btn.setFont(QFont("Segoe Fluent Icons", 10))
        self._back_btn.setFixedSize(30, 30)
        self._back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._back_btn.setToolTip("Back")
        self._back_btn.setStyleSheet(
            self._BTN_BASE.format(
                fg=MUTED_TEXT,
                hover=ACCENT,
                hover_fg=LIGHT_CANVAS,
                press=ACCENT,
            )
        )
        self._back_btn.setVisible(False)
        self._back_btn.clicked.connect(self.back_requested)
        layout.addWidget(self._back_btn)

        # SKILLSCAN two-colour wordmark
        wordmark = QLabel(
            f"<span style='color:{LIGHT_CANVAS};font-weight:700;"
            f"letter-spacing:2px;font-size:13px;'>SKILL</span>"
            f"<span style='color:{ACCENT};font-weight:700;"
            f"letter-spacing:2px;font-size:13px;'>SCAN</span>"
        )
        wordmark.setStyleSheet("background:transparent;")
        layout.addWidget(wordmark)
        layout.addStretch()

        # Minimise button
        min_btn = QPushButton("")  # ChromeMinimize
        min_btn.setFont(QFont("Segoe Fluent Icons", 9))
        min_btn.setFixedSize(34, 34)
        min_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        min_btn.setToolTip("Minimise")
        min_btn.setStyleSheet(
            self._BTN_BASE.format(
                fg=MUTED_TEXT,
                hover=DEEP_SURFACE,
                hover_fg=LIGHT_CANVAS,
                press="#263347",
            )
        )
        min_btn.clicked.connect(self.minimise_requested)
        layout.addWidget(min_btn)

        # Close button — hides to tray
        close_btn = QPushButton("")  # Cancel / ChromeClose
        close_btn.setFont(QFont("Segoe Fluent Icons", 9))
        close_btn.setFixedSize(34, 34)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setToolTip("Hide to tray")
        close_btn.setStyleSheet(
            self._BTN_BASE.format(
                fg=MUTED_TEXT,
                hover=CRITICAL_ACCENT,
                hover_fg=LIGHT_CANVAS,
                press="#b91c1c",
            )
        )
        close_btn.clicked.connect(self.close_requested)
        layout.addWidget(close_btn)

    def set_back_visible(self, visible: bool) -> None:
        self._back_btn.setVisible(visible)

    # Drag ─────────────────────────────────────────────────────────────────
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


class _StatusBar(QWidget):
    """24px status strip — state dot + message on left, model + version on right."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(24)
        self.setStyleSheet(f"background: {DEEP_SURFACE};")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(6)

        self._dot = QLabel("●")
        self._dot.setStyleSheet(
            f"color:{SAFE_ACCENT};font-size:8px;background:transparent;"
        )
        layout.addWidget(self._dot)

        self._msg = QLabel("Ready")
        self._msg.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:11px;background:transparent;"
        )
        layout.addWidget(self._msg)
        layout.addStretch()

        self._counts_lbl = QLabel("")
        self._counts_lbl.setStyleSheet(
            f"color:{MUTED_TEXT};font-size:11px;background:transparent;"
        )
        layout.addWidget(self._counts_lbl)

        sep = QLabel("  ·  ")
        sep.setStyleSheet(f"color:{MUTED_TEXT};font-size:11px;background:transparent;")
        layout.addWidget(sep)

        c = cfg.load()
        model = c.get("llm_model", "") or "no model configured"
        info = QLabel(f"{model}  ·  v{__version__}")
        info.setStyleSheet(f"color:{MUTED_TEXT};font-size:11px;background:transparent;")
        layout.addWidget(info)

    def set_state(self, message: str, dot_color: str = SAFE_ACCENT) -> None:
        self._dot.setStyleSheet(
            f"color:{dot_color};font-size:8px;background:transparent;"
        )
        self._msg.setText(message)

    def set_counts(self, text: str) -> None:
        self._counts_lbl.setText(text)


# ── Main window ──────────────────────────────────────────────────────────────


class MainWindow(QWidget):
    """Primary SkillScan window — frameless, nav rail, stacked views."""

    def __init__(self, tray_app=None, parent=None):
        super().__init__(parent)
        self._tray_app = tray_app  # reference for quit / reload config
        self._history: list[int] = []  # back-navigation stack

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(1000, 640)
        self.resize(1240, 760)

        self._discovery_workers: list = []  # keep refs so threads aren't GC'd

        self._build_ui()
        self._register_views()
        self._center_on_screen()

        # Deferred startup check — show warning in status bar if scanner missing
        QTimer.singleShot(600, self._check_scanner)
        # Startup folder discovery
        QTimer.singleShot(800, self._start_discovery)

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Outer layout adds margins so the drop shadow isn't clipped
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 8, 14, 22)
        outer.setSpacing(0)

        # Rounded panel with drop shadow
        self._panel = _MainPanel(self)
        shadow = QGraphicsDropShadowEffect(self._panel)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 6)
        self._panel.setGraphicsEffect(shadow)
        outer.addWidget(self._panel)

        panel_vbox = QVBoxLayout(self._panel)
        panel_vbox.setContentsMargins(0, 0, 0, 0)
        panel_vbox.setSpacing(0)

        # Title bar
        self._title_bar = _TitleBar(self)
        self._title_bar.back_requested.connect(self._navigate_back)
        self._title_bar.minimise_requested.connect(self.showMinimized)
        self._title_bar.close_requested.connect(self.hide)
        panel_vbox.addWidget(self._title_bar)

        # Thin divider under title bar
        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setFixedHeight(1)
        div.setStyleSheet(f"background:{DIVIDER};border:none;")
        panel_vbox.addWidget(div)

        # Content row: nav rail | vertical divider | stacked views
        content = QWidget()
        content.setStyleSheet(f"background:{ANCHOR};")
        content_hbox = QHBoxLayout(content)
        content_hbox.setContentsMargins(0, 0, 0, 0)
        content_hbox.setSpacing(0)

        self._nav = NavRail(self)
        self._nav.page_changed.connect(self._on_nav_changed)
        self._nav.exit_requested.connect(self._quit)
        content_hbox.addWidget(self._nav)

        nav_div = QFrame()
        nav_div.setFrameShape(QFrame.Shape.VLine)
        nav_div.setFixedWidth(1)
        nav_div.setStyleSheet(f"background:{DIVIDER};border:none;")
        content_hbox.addWidget(nav_div)

        self._stack = QStackedWidget(self)
        self._stack.setStyleSheet(f"background:{ANCHOR};")
        content_hbox.addWidget(self._stack, 1)

        panel_vbox.addWidget(content, 1)

        # Status bar
        self._status = _StatusBar(self)
        panel_vbox.addWidget(self._status)

    def _register_views(self) -> None:
        from .views.folders_view import FoldersView
        from .views.inventory_view import InventoryView
        from .views.skill_creator_view import SkillCreatorView
        from .views.testing_view import TestingView
        from .views.options_view import OptionsView
        from .views.about_view import AboutView
        from .views.skill_detail_view import SkillDetailView

        views = [
            FoldersView(),  # 0 — Folders
            InventoryView(),  # 1 — Inventory
            SkillCreatorView(),  # 2 — Create
            TestingView(),  # 3 — Testing
            OptionsView(),  # 4 — Options
            AboutView(),  # 5 — About
            SkillDetailView(),  # 6 — Skill Detail (navigated to, not in nav rail)
        ]
        for view in views:
            self._stack.addWidget(view)

        # Wire options save → reload tray config
        options_view = self._stack.widget(4)
        if hasattr(options_view, "settings_changed"):
            options_view.settings_changed.connect(self._on_settings_changed)

        # Wire folders view → skill detail navigation + status bar counts
        folders_view = self._stack.widget(0)
        if hasattr(folders_view, "skill_detail_requested"):
            folders_view.skill_detail_requested.connect(self._on_skill_detail_requested)
        if hasattr(folders_view, "tile_counts_changed"):
            folders_view.tile_counts_changed.connect(self._status.set_counts)

    # ── Navigation ───────────────────────────────────────────────────────────

    def _on_nav_changed(self, index: int) -> None:
        self._history.clear()
        self._title_bar.set_back_visible(False)
        self._stack.setCurrentIndex(index)

    def navigate_to(self, index: int) -> None:
        """Push current view and navigate (used by skill tiles → skill detail)."""
        self._history.append(self._stack.currentIndex())
        self._title_bar.set_back_visible(True)
        self._stack.setCurrentIndex(index)

    def _navigate_back(self) -> None:
        if self._history:
            index = self._history.pop()
            self._stack.setCurrentIndex(index)
            self._nav.set_current(index)
            self._title_bar.set_back_visible(bool(self._history))

    # ── Public interface (called by TrayApp) ─────────────────────────────────

    def show_window(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _center_on_screen(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2,
            )

    def _start_discovery(self) -> None:
        """Discover skills in all watch-enabled folders on startup."""
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

        self._status.set_state("Discovering skills…", MEDIUM_ACCENT)

        total_done = [0]
        total = len(watched)

        def _on_finished(result, folder_id=None):
            total_done[0] += 1
            if total_done[0] >= total:
                added = result.added
                revoked = result.trust_revoked
                if revoked:
                    self._status.set_state(
                        f"Discovery complete — {revoked} trust revocation(s)",
                        MEDIUM_ACCENT,
                    )
                else:
                    self._status.set_state(
                        f"Ready  ·  {added} new skill(s) found" if added else "Ready",
                        SAFE_ACCENT,
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
            self._status.set_state(
                "cisco-ai-skill-scanner not found — run: pip install cisco-ai-skill-scanner[all]",
                MEDIUM_ACCENT,
            )

    def _on_skill_detail_requested(self, skill_id: int) -> None:
        detail_view = self._stack.widget(6)
        if detail_view is not None:
            detail_view.load(skill_id)
            self.navigate_to(6)

    def _on_settings_changed(self) -> None:
        if self._tray_app is not None:
            self._tray_app.reload_config()

    def _quit(self) -> None:
        if self._tray_app is not None:
            self._tray_app._quit()
        else:
            QApplication.quit()
