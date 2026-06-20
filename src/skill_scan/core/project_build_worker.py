"""Background QThread orchestrating the "process chain from prompt onwards"
(see .claude/architecture/project-setup-flow.md) - Intent Parser -> local
skill matching -> Project Scaffolder. Lives in core/ alongside the other
QThread workers wrapping core logic (core/skill_discovery.py's
DiscoveryWorker, core/skill_audit.py's SkillAuditWorker), not in ui/.

Deliberately NOT included: Gap Detection or the background Skill Supply
Chain (external sourcing/vetting) - this only uses what's already installed
locally, the same v1 boundary core/intent_parser.py and
core/project_scaffolder.py already draw.
"""

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from .intent_parser import IntentResult, match_local_skills, parse_intent
from .project_scaffolder import scaffold_project, slugify_project_name
from .skill_audit import DEFAULT_AUDIT_ROOT, audit_roots


class ProjectBuildWorker(QThread):
    """Runs the full prompt -> scaffold chain off the UI thread."""

    progress = pyqtSignal(str)
    finished = pyqtSignal(object, object)  # (IntentResult, ScaffoldResult)
    error = pyqtSignal(str)

    def __init__(self, rough_idea: str, parent_dir: Path, parent=None):
        super().__init__(parent)
        self._rough_idea = rough_idea
        self._parent_dir = parent_dir

    def run(self) -> None:
        try:
            self.progress.emit("Understanding your idea…")
            intent = parse_intent(self._rough_idea)

            self.progress.emit("Checking your local skills…")
            matched_paths = self._match_local_skills(intent)

            self.progress.emit("Building your project…")
            target_dir = self._parent_dir / slugify_project_name(intent.project_type)
            result = scaffold_project(target_dir, intent, matched_paths)

            self.finished.emit(intent, result)
        except Exception as exc:
            self.error.emit(str(exc))

    @staticmethod
    def _match_local_skills(intent: IntentResult) -> dict[str, Path]:
        entries = audit_roots([DEFAULT_AUDIT_ROOT])
        local_skills = {e.name: str(e.meta.get("description") or "") for e in entries}
        name_to_path = {e.name: e.path for e in entries}

        matches = match_local_skills(intent, local_skills)
        matched_paths: dict[str, Path] = {}
        for names in matches.values():
            for name in names:
                if name in name_to_path:
                    matched_paths[name] = name_to_path[name]
        return matched_paths
