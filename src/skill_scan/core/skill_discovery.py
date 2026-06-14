"""Skill discovery — walks folders, syncs Skill rows to DB, invalidates trust on hash change."""

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from .db import Folder, Skill, init_db, session
from .router import SpecType, detect_type

# ── Helpers ──────────────────────────────────────────────────────────────────


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def _parse_skill_meta(path: Path) -> dict:
    """Extract YAML frontmatter fields from a SKILL.md file."""
    try:
        import yaml

        text = path.read_text(encoding="utf-8", errors="replace")
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                return yaml.safe_load(text[3:end]) or {}
    except Exception:
        pass
    return {}


def _parse_json_meta(path: Path) -> dict:
    """Extract name/description/version from a JSON manifest."""
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
        if isinstance(data, dict):
            return {
                "name": data.get("name") or data.get("id"),
                "description": data.get("description"),
                "version": str(data.get("version", "")) or None,
            }
    except Exception:
        pass
    return {}


def discover_paths(folder_path: str) -> list[Path]:
    """Return all AI component file paths under folder_path."""
    root = Path(folder_path)
    if not root.is_dir():
        return []
    found: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and detect_type(p) != SpecType.UNKNOWN:
            found.append(p)
    return found


# ── Discovery result ─────────────────────────────────────────────────────────


@dataclass
class DiscoveryResult:
    added: int = 0
    updated: int = 0
    unchanged: int = 0
    trust_revoked: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return self.added + self.updated + self.unchanged


# ── Core sync ────────────────────────────────────────────────────────────────


def sync_folder(folder_id: int, folder_path: str) -> DiscoveryResult:
    """Walk folder, upsert Skill rows, invalidate trust on hash change."""
    result = DiscoveryResult()
    now = datetime.now(timezone.utc)

    try:
        paths = discover_paths(folder_path)
    except Exception as e:
        result.errors.append(str(e))
        return result

    with session() as s:
        for path in paths:
            try:
                _sync_one(s, folder_id, path, now, result)
            except Exception as e:
                result.errors.append(f"{path.name}: {e}")

        folder = s.query(Folder).filter_by(id=folder_id).first()
        if folder:
            folder.last_scanned = now

        s.commit()

    return result


def _sync_one(
    s, folder_id: int, path: Path, now: datetime, result: DiscoveryResult
) -> None:
    path_str = str(path)
    spec_type = detect_type(path)
    file_hash = _sha256(path)

    if spec_type == SpecType.SKILL_MD:
        meta = _parse_skill_meta(path)
        name = meta.get("name") or path.parent.name
        description = str(meta.get("description", "")) or None
        version = str(meta.get("version", "")) or None
        authors = json.dumps(meta.get("authors") or [])
        lic = str(meta.get("license", "")) or None
    else:
        meta = _parse_json_meta(path)
        name = meta.get("name") or path.stem
        description = meta.get("description")
        version = meta.get("version")
        authors = "[]"
        lic = None

    existing = s.query(Skill).filter_by(path=path_str).first()

    if existing is None:
        s.add(
            Skill(
                folder_id=folder_id,
                path=path_str,
                name=name,
                spec_type=spec_type.value,
                version=version,
                authors=authors,
                license=lic,
                description=description,
                file_hash=file_hash,
                trusted=False,
                spec_score=None,
                created_at=now,
                modified_at=now,
            )
        )
        result.added += 1
    else:
        if existing.file_hash != file_hash:
            existing.file_hash = file_hash
            existing.modified_at = now
            existing.name = name
            existing.version = version
            existing.authors = authors
            existing.license = lic
            existing.description = description
            if existing.trusted:
                existing.trusted = False
                existing.trust_signed_at = None
                result.trust_revoked += 1
            result.updated += 1
        else:
            result.unchanged += 1


# ── QThread worker ────────────────────────────────────────────────────────────


class DiscoveryWorker(QThread):
    """Runs folder discovery on a background thread."""

    progress = pyqtSignal(int, int)  # (done, total) — not yet granular
    finished = pyqtSignal(object)  # DiscoveryResult

    def __init__(self, folder_id: int, folder_path: str, parent=None):
        super().__init__(parent)
        self._folder_id = folder_id
        self._folder_path = folder_path

    def run(self) -> None:
        init_db()
        result = DiscoveryResult()
        try:
            result = sync_folder(self._folder_id, self._folder_path)
        except Exception as e:
            result.errors.append(str(e))
        self.finished.emit(result)


# ── Startup discovery ─────────────────────────────────────────────────────────


def run_startup_discovery(watched_folders: list[str]) -> list[DiscoveryWorker]:
    """
    Launch a DiscoveryWorker for each watched folder.
    Returns the list so callers can connect signals before the threads start.
    """
    from .db import get_or_create_folder

    workers: list[DiscoveryWorker] = []
    for path in watched_folders:
        folder_id = get_or_create_folder(path, watch_enabled=True)
        worker = DiscoveryWorker(folder_id, path)
        workers.append(worker)
    for w in workers:
        w.start()
    return workers
