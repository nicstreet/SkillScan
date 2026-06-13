"""SQLAlchemy database layer — models, session factory, and JSON history migration."""
import json
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer, Text, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

_DB_DIR = Path(os.environ.get("APPDATA", "~")) / "SkillScan"
_DB_PATH = _DB_DIR / "skillscan.db"
_RESULTS_JSON = _DB_DIR / "results.json"

_engine = None
_SessionFactory = None


class Base(DeclarativeBase):
    pass


class Folder(Base):
    __tablename__ = "folders"

    id           = Column(Integer, primary_key=True)
    path         = Column(Text, unique=True, nullable=False)
    watch_enabled = Column(Boolean, default=False)
    last_scanned = Column(DateTime, nullable=True)
    added_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    skills       = relationship("Skill", back_populates="folder",
                                cascade="all, delete-orphan")
    bom_snapshots = relationship("BomSnapshot", back_populates="folder",
                                 cascade="all, delete-orphan")


class Skill(Base):
    __tablename__ = "skills"

    id             = Column(Integer, primary_key=True)
    folder_id      = Column(Integer, ForeignKey("folders.id"), nullable=False)
    path           = Column(Text, unique=True, nullable=False)
    name           = Column(Text, nullable=False)
    spec_type      = Column(Text, default="skill")   # skill / mcp / a2a / unknown
    version        = Column(Text, nullable=True)
    authors        = Column(Text, default="[]")      # JSON array string
    license        = Column(Text, nullable=True)
    description    = Column(Text, nullable=True)
    file_hash      = Column(Text, nullable=True)
    trusted        = Column(Boolean, default=False)
    trust_signed_at = Column(DateTime, nullable=True)
    spec_score     = Column(Integer, nullable=True)
    created_at     = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    modified_at    = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    folder         = relationship("Folder", back_populates="skills")
    scan_results   = relationship("ScanResult", back_populates="skill",
                                  cascade="all, delete-orphan")


class ScanResult(Base):
    __tablename__ = "scan_results"

    id             = Column(Integer, primary_key=True)
    skill_id       = Column(Integer, ForeignKey("skills.id"), nullable=True)
    timestamp      = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    severity       = Column(Text, default="unknown")
    is_safe        = Column(Boolean, default=False)
    raw_json       = Column(Text, nullable=True)
    findings_json  = Column(Text, nullable=True)
    duration_ms    = Column(Integer, nullable=True)
    analyzers_used = Column(Text, default="[]")      # JSON array string
    returncode     = Column(Integer, default=0)

    skill          = relationship("Skill", back_populates="scan_results")


class BomSnapshot(Base):
    __tablename__ = "bom_snapshots"

    id         = Column(Integer, primary_key=True)
    folder_id  = Column(Integer, ForeignKey("folders.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    format     = Column(Text, default="cyclonedx-json")
    content    = Column(Text, nullable=False)

    folder     = relationship("Folder", back_populates="bom_snapshots")


def init_db() -> None:
    """Create tables and run one-time JSON history migration."""
    global _engine, _SessionFactory
    if _engine is not None:
        return
    _DB_DIR.mkdir(parents=True, exist_ok=True)
    _engine = create_engine(f"sqlite:///{_DB_PATH}", echo=False)
    Base.metadata.create_all(_engine)
    _SessionFactory = sessionmaker(bind=_engine)
    _migrate_json_history()


def _migrate_json_history() -> None:
    """Import results.json into scan_results on first run, then rename the file."""
    if not _RESULTS_JSON.exists():
        return
    migrated_flag = _DB_DIR / ".results_migrated"
    if migrated_flag.exists():
        return
    try:
        raw = json.loads(_RESULTS_JSON.read_text(encoding="utf-8"))
    except Exception:
        migrated_flag.touch()
        return

    with session() as s:
        for entry in raw:
            parsed = entry.get("parsed")
            severity = "unknown"
            is_safe = False
            findings_json = None
            if isinstance(parsed, dict):
                is_safe = bool(parsed.get("is_safe", False))
                severity = parsed.get("max_severity", "unknown") if not is_safe else "clean"
                findings = parsed.get("findings")
                if findings:
                    findings_json = json.dumps(findings)
            ts_str = entry.get("timestamp", "")
            try:
                ts = datetime.fromisoformat(ts_str)
            except Exception:
                ts = datetime.now(timezone.utc)
            row = ScanResult(
                skill_id=None,
                timestamp=ts,
                severity=severity,
                is_safe=is_safe,
                raw_json=entry.get("stdout"),
                findings_json=findings_json,
                returncode=entry.get("returncode", 0),
            )
            s.add(row)
        s.commit()

    migrated_flag.touch()


@contextmanager
def session() -> Generator[Session, None, None]:
    """Short-lived session context manager for DB reads/writes."""
    if _SessionFactory is None:
        init_db()
    s: Session = _SessionFactory()
    try:
        yield s
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_or_create_folder(path: str, watch_enabled: bool = False) -> int:
    """Return folder id, inserting a new row if not present."""
    with session() as s:
        folder = s.query(Folder).filter_by(path=path).first()
        if folder is None:
            folder = Folder(
                path=path,
                watch_enabled=watch_enabled,
                added_at=datetime.now(timezone.utc),
            )
            s.add(folder)
            s.commit()
            s.refresh(folder)
        return folder.id
