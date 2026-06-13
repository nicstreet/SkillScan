"""watchdog-based folder watcher; emits a Qt signal when a skill changes."""
import threading
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class _Handler(FileSystemEventHandler):
    def __init__(self, callback):
        super().__init__()
        self._callback = callback
        self._last: dict[str, float] = {}

    def on_modified(self, event):
        self._maybe_fire(event.src_path)

    def on_created(self, event):
        self._maybe_fire(event.src_path)

    def _maybe_fire(self, path: str):
        import time
        now = time.monotonic()
        # debounce: only fire once per skill folder per 5 s
        skill_root = self._find_skill_root(path)
        if skill_root is None:
            return
        last = self._last.get(skill_root, 0)
        if now - last < 5.0:
            return
        self._last[skill_root] = now
        self._callback(skill_root)

    @staticmethod
    def _find_skill_root(path: str) -> str | None:
        """Walk up until we find a SKILL.md or hit the watch root."""
        p = Path(path)
        for _ in range(5):
            if (p / "SKILL.md").exists():
                return str(p)
            if p.name == "SKILL.md":
                return str(p.parent)
            p = p.parent
        return None


class FolderWatcher(QObject):
    skill_changed = pyqtSignal(str)  # emits the skill folder path

    def __init__(self, parent=None):
        super().__init__(parent)
        self._observer = Observer()
        self._watches: dict[str, object] = {}
        self._lock = threading.Lock()

    def set_folders(self, folders: list[str]) -> None:
        with self._lock:
            current = set(self._watches.keys())
            desired = set(folders)
            for f in current - desired:
                self._observer.unschedule(self._watches.pop(f))
            for f in desired - current:
                if Path(f).is_dir():
                    h = _Handler(self._on_change)
                    w = self._observer.schedule(h, f, recursive=True)
                    self._watches[f] = w

    def start(self) -> None:
        if not self._observer.is_alive():
            self._observer.start()

    def stop(self) -> None:
        if self._observer.is_alive():
            self._observer.stop()
            self._observer.join()

    def _on_change(self, skill_path: str) -> None:
        self.skill_changed.emit(skill_path)
