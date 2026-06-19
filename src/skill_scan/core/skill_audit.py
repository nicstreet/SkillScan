"""Own-skill audit — batch spec-compliance scoring for skills already on disk.

Distinct from the Folders/Skill DB tracking (which covers arbitrary scanned
locations a user explicitly adds): this targets Claude Code's own skill
folders — ~/.claude/skills/ plus any project .claude/skills/ folders the user
adds — and scores each one against core/spec_compliance.py. Ephemeral: results
are held in memory for the session, not persisted to the DB.
"""

from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from . import spec_compliance

DEFAULT_AUDIT_ROOT = Path.home() / ".claude" / "skills"


@dataclass
class AuditEntry:
    path: Path
    name: str
    folder: str
    meta: dict
    result: spec_compliance.ComplianceResult = field(repr=False)

    @property
    def score(self) -> int:
        return self.result.score


def find_skill_files(root: Path) -> list[Path]:
    """Recursively find SKILL.md files under root."""
    if not root.is_dir():
        return []
    return sorted(root.rglob("SKILL.md"))


def audit_roots(roots: list[Path]) -> list[AuditEntry]:
    """Score every SKILL.md found under the given roots, worst score first."""
    entries: list[AuditEntry] = []
    seen: set[Path] = set()
    for root in roots:
        for path in find_skill_files(root):
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            meta = spec_compliance.parse_frontmatter(path)
            body = spec_compliance.parse_body(path)
            result = spec_compliance.score(
                meta, folder_name=path.parent.name, body=body
            )
            entries.append(
                AuditEntry(
                    path=path,
                    name=str(meta.get("name") or path.parent.name),
                    folder=str(path.parent),
                    meta=meta,
                    result=result,
                )
            )
    entries.sort(key=lambda e: e.score)
    return entries


class SkillAuditWorker(QThread):
    """Runs audit_roots on a background thread."""

    finished = pyqtSignal(object)  # list[AuditEntry]

    def __init__(self, roots: list[Path], parent=None):
        super().__init__(parent)
        self._roots = roots

    def run(self) -> None:
        try:
            entries = audit_roots(self._roots)
        except Exception:
            entries = []
        self.finished.emit(entries)
