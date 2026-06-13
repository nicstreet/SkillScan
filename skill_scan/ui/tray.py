"""System tray application entry point."""
import shutil
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QIcon, QPainter, QPixmap, QFont
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QLabel, QMenu, QSystemTrayIcon, QWidgetAction,
)

from ..core import config as cfg
from ..core.clipboard_watcher import ClipboardWatcher
from ..core.scanner import ScanJob, clipboard_path_or_temp
from ..core.watcher import FolderWatcher
from .about_dialog import AboutDialog
from .drop_zone import DropZone
from .results_window import ResultsWindow
from .scan_progress import ScanProgressDialog
from .settings_dialog import SettingsDialog
from .toggle_row import ToggleAction, ToggleRow

_RESOURCES = Path(__file__).parent.parent / "resources"


def _make_tray_icon(color: str = "#0ea5e9") -> QIcon:
    # Prefer the logo from resources/ (ICO gives best multi-DPI quality on Windows)
    for name in ("icon.ico", "logo_no_bg.png", "logo.png"):
        candidate = _RESOURCES / name
        if candidate.exists():
            return QIcon(str(candidate))
    # Fallback: programmatic coloured pill
    px = QPixmap(64, 64)
    px.fill(Qt.GlobalColor.transparent)
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(color))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(8, 4, 48, 52, 10, 10)
    font = QFont("Segoe UI", 16, QFont.Weight.Bold)
    p.setFont(font)
    p.setPen(QColor("white"))
    p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "AI")
    p.end()
    return QIcon(px)


class SkillScanMenu(QMenu):
    """QMenu that stays open when a ToggleAction row is clicked."""
    def mouseReleaseEvent(self, event):
        # actionAt() uses the actual cursor position — more reliable than
        # activeAction() which can be None for embedded QWidgetAction items.
        action = self.actionAt(event.pos())
        if isinstance(action, ToggleAction):
            event.accept()
            return
        super().mouseReleaseEvent(event)


def _section_label(text: str, menu: QMenu) -> QWidgetAction:
    """Dimmed non-interactive section header."""
    lbl = QLabel(f"  {text}")
    lbl.setStyleSheet(
        "color: #6b7280; font-size: 10px; font-weight: 600; "
        "letter-spacing: 0.8px; padding: 2px 0 1px 0; text-transform: uppercase;"
    )
    lbl.setFixedHeight(20)
    a = QWidgetAction(menu)
    a.setDefaultWidget(lbl)
    a.setEnabled(False)
    return a


class TrayApp:
    def __init__(self, app: QApplication, initial_scan: str | None = None):
        self._app = app
        self._cfg = cfg.load()
        self._active_jobs: list[ScanJob] = []
        self._temp_dirs: list[str] = []

        self._drop_zone = DropZone(color=self._cfg.get("accent_color", "#0ea5e9"))
        self._drop_zone.scan_requested.connect(self.launch_scan)

        self._results_window: ResultsWindow | None = None

        self._watcher = FolderWatcher()
        self._watcher.skill_changed.connect(self._on_watched_change)
        self._apply_watched_folders()
        self._watcher.start()

        self._clipboard_watcher = ClipboardWatcher()
        self._clipboard_watcher.scan_requested.connect(self._on_clipboard_content)
        self._apply_clipboard_watcher()

        self._pending_notifs: dict[str, QTimer] = {}

        self._tray = QSystemTrayIcon(_make_tray_icon(self._cfg.get("accent_color", "#0ea5e9")))
        self._tray.setToolTip("SkillScan")
        self._tray.activated.connect(self._on_tray_activated)
        self._build_menu()
        self._tray.setContextMenu(self._menu)
        self._tray.show()

        if initial_scan:
            QTimer.singleShot(200, lambda: self.launch_scan(initial_scan))

    # ------------------------------------------------------------------
    def _build_menu(self):
        accent = self._cfg.get("accent_color", "#0ea5e9")
        self._menu = SkillScanMenu()

        # Title
        title_lbl = QLabel("  SkillScan")
        title_lbl.setStyleSheet(
            "font-weight: 700; font-size: 13px; padding: 8px 0 4px 0; color: palette(text);"
        )
        title_lbl.setFixedHeight(30)
        title_action = QWidgetAction(self._menu)
        title_action.setDefaultWidget(title_lbl)
        title_action.setEnabled(False)
        self._menu.addAction(title_action)
        self._menu.addSeparator()

        # --- Scan actions ---
        self._menu.addAction("  Scan Skill Folder…", self._pick_and_scan)
        self._menu.addAction("  Scan Clipboard", self._scan_clipboard)
        self._menu.addSeparator()

        # --- Toggle section ---
        self._menu.addAction(_section_label("Features", self._menu))

        self._toggle_drop_zone = ToggleAction(
            "Drop Zone", checked=False, color=accent, parent=self._menu
        )
        self._toggle_drop_zone.toggled.connect(self._on_drop_zone_toggled)
        self._menu.addAction(self._toggle_drop_zone)

        self._toggle_clipboard = ToggleAction(
            "Clipboard Auto-Scan",
            checked=self._cfg.get("clipboard_watch_enabled", False),
            color=accent, parent=self._menu,
        )
        self._toggle_clipboard.toggled.connect(self._on_clipboard_watch_toggled)
        self._menu.addAction(self._toggle_clipboard)

        has_folders = bool(self._cfg.get("watched_folders"))
        self._toggle_folders = ToggleAction(
            "Folder Watching",
            checked=has_folders,
            color=accent, parent=self._menu,
        )
        self._toggle_folders.toggled.connect(self._on_folder_watch_toggled)
        if not has_folders:
            self._toggle_folders.setToolTip("Add folders in Settings → Watched Folders first")
        self._menu.addAction(self._toggle_folders)

        self._menu.addSeparator()

        # --- View / settings ---
        self._menu.addAction("  View Results", self._show_results)
        self._menu.addSeparator()
        self._menu.addAction("  Settings…", self._show_settings)
        self._menu.addAction("  About…", self._show_about)
        self._menu.addSeparator()
        self._menu.addAction("  Exit", self._quit)

    def _sync_toggle_state(self):
        accent = self._cfg.get("accent_color", "#0ea5e9")
        for toggle in (self._toggle_drop_zone, self._toggle_clipboard, self._toggle_folders):
            toggle.setOnColor(accent)
        self._drop_zone.setOnColor(accent)

        self._toggle_clipboard.setChecked(self._cfg.get("clipboard_watch_enabled", False))
        self._toggle_folders.setChecked(bool(self._cfg.get("watched_folders")))

    # ------------------------------------------------------------------
    def _notify_delayed(self, key: str, checked: bool,
                        get_state, title: str, body: str) -> None:
        """Show a tray notification only if the toggle state is unchanged after 10 s."""
        existing = self._pending_notifs.pop(key, None)
        if existing:
            existing.stop()
        t = QTimer()
        t.setSingleShot(True)
        def _fire():
            self._pending_notifs.pop(key, None)
            if get_state() == checked:
                self._tray.showMessage(
                    title, body, QSystemTrayIcon.MessageIcon.Information, 3000
                )
        t.timeout.connect(_fire)
        t.start(10_000)
        self._pending_notifs[key] = t

    # ------------------------------------------------------------------
    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_results()

    # ------------------------------------------------------------------
    def _on_drop_zone_toggled(self, checked: bool):
        if checked:
            QTimer.singleShot(150, self._drop_zone.show)
        else:
            self._drop_zone.hide()
        self._notify_delayed(
            "drop_zone", checked,
            lambda: self._toggle_drop_zone.isChecked(),
            "Drop Zone",
            "Drop Zone is now visible." if checked else "Drop Zone hidden.",
        )

    def _on_clipboard_watch_toggled(self, checked: bool):
        self._cfg = cfg.load()
        self._cfg["clipboard_watch_enabled"] = checked
        cfg.save(self._cfg)
        self._apply_clipboard_watcher()
        self._notify_delayed(
            "clipboard", checked,
            lambda: self._toggle_clipboard.isChecked(),
            "Clipboard Auto-Scan",
            "Background clipboard scanning enabled." if checked
            else "Background clipboard scanning disabled.",
        )

    def _on_folder_watch_toggled(self, checked: bool):
        if checked:
            self._apply_watched_folders()
        else:
            self._watcher.set_folders([])
        n = len(self._cfg.get("watched_folders", []))
        body = (
            f"Watching {n} folder{'s' if n != 1 else ''}." if checked
            else "Folder watching paused."
        )
        self._notify_delayed(
            "folders", checked,
            lambda: self._toggle_folders.isChecked(),
            "Folder Watching",
            body,
        )

    # ------------------------------------------------------------------
    def _pick_and_scan(self):
        folder = QFileDialog.getExistingDirectory(None, "Select Skill Folder to Scan")
        if folder:
            self.launch_scan(folder)

    def _scan_clipboard(self):
        text = self._app.clipboard().text().strip()
        if not text:
            self._tray.showMessage(
                "SkillScan", "Clipboard is empty.",
                QSystemTrayIcon.MessageIcon.Warning, 3000,
            )
            return
        path, is_temp = clipboard_path_or_temp(text)
        if is_temp:
            self._temp_dirs.append(path)
            self._tray.showMessage(
                "SkillScan", "Clipboard text written to temp SKILL.md — scanning…",
                QSystemTrayIcon.MessageIcon.Information, 3000,
            )
        else:
            self._tray.showMessage(
                "SkillScan", f"Scanning path from clipboard:\n{path}",
                QSystemTrayIcon.MessageIcon.Information, 3000,
            )
        self.launch_scan(path)

    # ------------------------------------------------------------------
    def launch_scan(self, path: str, silent: bool = False):
        self._cfg = cfg.load()
        job = ScanJob(path, self._cfg)
        self._active_jobs.append(job)

        if silent:
            job.finished.connect(lambda r, j=job: self._on_job_done(r, j, None))
            job.error.connect(lambda msg, j=job: self._on_job_error(msg, j, None))
        else:
            dlg = ScanProgressDialog(job, path)
            job.finished.connect(lambda r, j=job, d=dlg: self._on_job_done(r, j, d))
            job.error.connect(lambda msg, j=job, d=dlg: self._on_job_error(msg, j, d))
            dlg.show()

        job.start()

    def _on_job_done(self, result, job: ScanJob, dlg):
        if job in self._active_jobs:
            self._active_jobs.remove(job)
        sev = result.severity_label.upper()
        if result.is_clean:
            title = "Scan complete — Clean"
            icon = QSystemTrayIcon.MessageIcon.Information
        elif sev != "UNKNOWN":
            title = f"Findings detected — {sev}"
            icon = QSystemTrayIcon.MessageIcon.Warning
        else:
            title = f"Scan error — exit {result.returncode}"
            icon = QSystemTrayIcon.MessageIcon.Critical
        self._tray.showMessage(title, Path(result.path).name, icon, 5000)
        self._cleanup_temps()

    def _on_job_error(self, msg: str, job: ScanJob, dlg):
        if job in self._active_jobs:
            self._active_jobs.remove(job)
        self._tray.showMessage("SkillScan error", msg, QSystemTrayIcon.MessageIcon.Critical, 6000)

    # ------------------------------------------------------------------
    def _on_watched_change(self, skill_path: str):
        self._tray.showMessage(
            "Auto-scanning", f"Change detected in {Path(skill_path).name}",
            QSystemTrayIcon.MessageIcon.Information, 2000,
        )
        self.launch_scan(skill_path)

    def _apply_watched_folders(self):
        self._watcher.set_folders(self._cfg.get("watched_folders", []))

    def _apply_clipboard_watcher(self):
        self._clipboard_watcher.configure(
            enabled=self._cfg.get("clipboard_watch_enabled", False),
            interval_secs=self._cfg.get("clipboard_watch_interval_secs", 30),
            min_chars=self._cfg.get("clipboard_min_chars", 200),
        )

    def _on_clipboard_content(self, text: str):
        path, is_temp = clipboard_path_or_temp(text)
        if is_temp:
            self._temp_dirs.append(path)
        self.launch_scan(path, silent=True)

    # ------------------------------------------------------------------
    def _show_results(self):
        if self._results_window is None:
            self._results_window = ResultsWindow()
        self._results_window.show()
        self._results_window.raise_()
        self._results_window.activateWindow()

    def _show_settings(self):
        dlg = SettingsDialog()
        if dlg.exec():
            self._cfg = cfg.load()
            self._tray.setIcon(_make_tray_icon(self._cfg.get("accent_color", "#0ea5e9")))
            self._apply_watched_folders()
            self._apply_clipboard_watcher()
            self._sync_toggle_state()

    def _show_about(self):
        AboutDialog().exec()

    # ------------------------------------------------------------------
    def _cleanup_temps(self):
        still_needed = []
        for d in self._temp_dirs:
            if any(job._path == d for job in self._active_jobs):
                still_needed.append(d)
            else:
                shutil.rmtree(d, ignore_errors=True)
        self._temp_dirs = still_needed

    def _quit(self):
        for t in self._pending_notifs.values():
            t.stop()
        self._pending_notifs.clear()
        self._watcher.stop()
        self._clipboard_watcher.configure(enabled=False, interval_secs=30, min_chars=200)
        self._cleanup_temps()
        self._tray.hide()
        self._app.quit()
