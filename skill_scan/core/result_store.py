"""Persists scan results to APPDATA and provides a bounded in-memory list."""
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

_RESULTS_FILE = Path(os.environ.get("APPDATA", "~")) / "SkillScan" / "results.json"
_MAX_HISTORY = 100


@dataclass
class ScanResult:
    path: str
    timestamp: str
    returncode: int
    stdout: str
    stderr: str
    parsed: Optional[list | dict] = None  # parsed JSON findings when --format json used

    @property
    def is_clean(self) -> bool:
        """True when the scan found no issues."""
        if isinstance(self.parsed, dict):
            return self.parsed.get("is_safe", False) is True
        return self.returncode == 0

    @property
    def severity_label(self) -> str:
        if isinstance(self.parsed, dict):
            # cisco-ai-skill-scanner: top-level max_severity + is_safe
            if self.parsed.get("is_safe") is True:
                return "pass"
            sev = self.parsed.get("max_severity", "").lower()
            if sev in ("critical", "high", "medium", "low"):
                return sev
            # Fallback: scan findings array
            findings = self.parsed.get("findings", [])
            severities = {f.get("severity", "").lower() for f in findings if isinstance(f, dict)}
            for level in ("critical", "high", "medium", "low"):
                if level in severities:
                    return level
        if isinstance(self.parsed, list):
            severities = {f.get("severity", "").lower() for f in self.parsed if isinstance(f, dict)}
            for level in ("critical", "high", "medium", "low"):
                if level in severities:
                    return level
        if self.returncode == 0:
            return "pass"
        return "unknown"

    @property
    def short_path(self) -> str:
        p = Path(self.path)
        return p.name if p.name else self.path


_history: list[ScanResult] = []


def _load_from_disk() -> list[ScanResult]:
    if not _RESULTS_FILE.exists():
        return []
    try:
        with open(_RESULTS_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        return [ScanResult(**r) for r in raw[-_MAX_HISTORY:]]
    except Exception:
        return []


def get_history() -> list[ScanResult]:
    global _history
    if not _history:
        _history = _load_from_disk()
    return list(reversed(_history))


def add(result: ScanResult) -> None:
    global _history
    if not _history:
        _history = _load_from_disk()
    _history.append(result)
    if len(_history) > _MAX_HISTORY:
        _history = _history[-_MAX_HISTORY:]
    _RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in _history], f, indent=2)
