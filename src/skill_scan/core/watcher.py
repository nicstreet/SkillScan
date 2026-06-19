"""watchdog-based folder watcher; emits a Qt signal when a skill changes."""

import hashlib
import threading
import time
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .db import Skill, session

_DEBOUNCE_SECS = 60  # minimum gap between scans of the same skill folder


def _sha256(path: Path) -> str:
    """Matches skill_discovery._sha256 so results are directly comparable."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def _known_hash(path: str) -> str | None:
    """Last file_hash recorded for this SKILL.md by discovery/trust, if any."""
    try:
        with session() as s:
            skill = s.query(Skill).filter_by(path=str(Path(path))).first()
            return skill.file_hash if skill else None
    except Exception:
        return None


class _Handler(FileSystemEventHandler):
    def __init__(self, callback):
        super().__init__()
        self._callback = callback
        self._last: dict[str, float] = {}
        self._hashes: dict[str, str] = {}
        self._seeded: set[str] = set()

    def on_modified(self, event):
        self._maybe_fire(event.src_path)

    def on_created(self, event):
        self._maybe_fire(event.src_path)

    def _maybe_fire(self, path: str):
        # Only react to SKILL.md — ignore all other files in the watched tree.
        if Path(path).name != "SKILL.md":
            return

        # Guard against OS events fired for reads or metadata-only touches:
        # only proceed if the file content has actually changed.
        digest = _sha256(Path(path))
        if not digest:
            return

        skill_root = str(Path(path).parent)

        # First sighting this session — seed against the DB's last-recorded
        # hash so a mere filesystem touch (sync/indexer/AV, no real content
        # change) right after app start doesn't read as a "change".
        if skill_root not in self._seeded:
            self._seeded.add(skill_root)
            known = _known_hash(path)
            if known:
                self._hashes[skill_root] = known

        if self._hashes.get(skill_root) == digest:
            return  # content unchanged — spurious event, skip
        self._hashes[skill_root] = digest

        now = time.monotonic()
        if now - self._last.get(skill_root, 0) < _DEBOUNCE_SECS:
            return
        self._last[skill_root] = now
        self._callback(skill_root)


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
