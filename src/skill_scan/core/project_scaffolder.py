"""Project Scaffolder — second piece of the "process chain from prompt
onwards" (see .claude/architecture/project-setup-flow.md). Takes an
IntentResult (core/intent_parser.py) plus a target directory and writes the
actual starting files to disk.

Greenfield only in this v1 - refuses to scaffold into a directory that
already looks like a project (retrofit - diffing against an existing
project and proposing a patch via the Remediate dialog's pattern - is a
meaningfully bigger feature with its own UX, deliberately deferred).

Also deliberately NOT included in this v1: CI config, a real test suite
(just the skeleton directory), LICENSE selection (ui/_license_picker.py
exists and should be wired in by the eventual UI, not duplicated here), and
named templates. AI instructions via Prompt Builder are not built either -
CLAUDE.md generation below already produces a real, useful first version
directly from the IntentResult with no extra LLM call, which covers a
reasonable amount of that need without Prompt Builder existing yet.
"""

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from .intent_parser import IntentResult

_SKELETON_DIRS = [
    "src",
    "tests",
    "docs",
    ".claude/skills",
    ".claude/commands",
    ".claude/rules",
]

# Universal, stack-agnostic - security-conscious defaults regardless of what
# gets built. Trimmed from this repo's own .gitignore (kept the
# generically-useful sections, dropped the SkillScan-specific ones).
_GITIGNORE_CORE = """\
# Environment & Secrets
.env
.env.*
!.env.example

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Logs (critical: never commit)
logs/
*.log
*.log.*

# Cache & temp
.cache/
*.cache
temp/
tmp/
*.tmp

# OS
.DS_Store
Thumbs.db

# Credentials & Config (even if accidentally added)
*.key
*.pem
*.p12
*.pfx
credentials.json
secrets.json
config-prod.json

# Claude Code — personal overrides (never commit)
.claude/settings.local.json
CLAUDE.local.md
"""

_GITIGNORE_PYTHON = """
# Python
__pycache__/
*.py[cod]
.venv/
venv/
env/
*.egg-info/
.pytest_cache/
.coverage
htmlcov/
"""

_CLAUDEIGNORE_DEFAULT = """\
.env
.env.*
*.key
*.pem
secrets/
logs/
"""

_ENV_EXAMPLE_DEFAULT = """\
# Copy to .env and fill in real values. Never commit .env itself.
"""

# Stack-agnostic permission denylist - safe regardless of what gets built.
# No PostToolUse/Stop hooks here (this repo's own settings.json has them, but
# they call SkillScan-specific PowerShell scripts, not generically reusable).
_SETTINGS_JSON_DEFAULT: dict = {
    "$schema": "https://json.schemastore.org/claude-code-settings.json",
    "permissions": {
        "deny": [
            "Read(./.env)",
            "Read(./.env.*)",
            "Read(./secrets/**)",
            "Bash(git push *)",
            "Bash(git reset *)",
            "Bash(git clean *)",
        ]
    },
}


class ScaffoldError(RuntimeError):
    """Raised when the target directory isn't safe to scaffold into."""


def slugify_project_name(project_type: str) -> str:
    """Derive a folder name from the inferred project type, e.g. "Photo
    Collection Organizer" -> "photo-collection-organizer". Lets the user
    pick a parent directory upfront without having to invent a project name
    before they know what's actually being built."""
    slug = re.sub(r"[^a-z0-9]+", "-", project_type.lower()).strip("-")
    return slug or "new-project"


def resolve_target_dir(parent_dir: Path, project_type: str) -> Path:
    """Derive a non-colliding target directory from project_type, trying
    slug, slug-2, slug-3, ... rather than failing outright - found necessary
    2026-06-20 when two similarly-vague prompts ("stock price tracker",
    "invoice tracker") both got inferred as generic project types that
    slugified to the same folder name. The user never typed this name
    themselves (it's auto-derived from an LLM guess), so a clash shouldn't
    need their intervention to resolve - same instinct as how Windows/macOS
    handle "this name already exists" when creating a new folder.
    """
    slug = slugify_project_name(project_type)
    candidate = parent_dir / slug
    n = 2
    while _looks_like_existing_project(candidate):
        candidate = parent_dir / f"{slug}-{n}"
        n += 1
    return candidate


@dataclass
class ScaffoldResult:
    target_dir: Path
    created_dirs: list[Path] = field(default_factory=list)
    created_files: list[Path] = field(default_factory=list)
    wired_skills: list[str] = field(default_factory=list)


def _looks_like_existing_project(target_dir: Path) -> bool:
    if not target_dir.exists():
        return False
    markers = ["CLAUDE.md", ".git", "src", ".claude", "pyproject.toml", "package.json"]
    return any((target_dir / m).exists() for m in markers)


def _is_python_stack(stack: str) -> bool:
    return "python" in stack.lower()


def _render_claude_md(intent: IntentResult, wired_skills: list[str]) -> str:
    lines = [
        f"# {intent.project_type}",
        "",
        intent.summary,
        "",
        "## Stack",
        "",
        intent.stack,
        "",
        "## Build Plan",
        "",
    ]
    for stage in intent.stages:
        lines.append(f"### {stage.name}")
        lines.append("")
        lines.append(stage.goal)
        if stage.skills_needed:
            lines.append("")
            lines.append(f"Needs: {', '.join(stage.skills_needed)}")
        lines.append("")
    if wired_skills:
        lines.append("## Skills")
        lines.append("")
        lines.append(
            "The following skills were matched from your local skill library "
            "and wired into `.claude/skills/`:"
        )
        lines.append("")
        for name in wired_skills:
            lines.append(f"- `{name}`")
        lines.append("")
    return "\n".join(lines)


def _render_readme(intent: IntentResult) -> str:
    return (
        f"# {intent.project_type}\n\n{intent.summary}\n\n## Stack\n\n{intent.stack}\n"
    )


def scaffold_project(
    target_dir: Path,
    intent: IntentResult,
    matched_skill_paths: dict[str, Path] | None = None,
) -> ScaffoldResult:
    """Write the starting project to target_dir. target_dir must not already
    exist, or must be empty - refuses to scaffold over an existing project.

    matched_skill_paths: {skill_name: path to that skill's SKILL.md file} -
    flattened, de-duplicated set of every skill matched by
    intent_parser.match_local_skills() across all stages. The caller resolves
    capability->name matches into name->path before calling this; that keeps
    this module decoupled from core/skill_audit.py's data model.
    """
    if _looks_like_existing_project(target_dir):
        raise ScaffoldError(
            f"{target_dir} already looks like a project - refusing to "
            "scaffold over it. Retrofit (diff + patch) isn't built yet."
        )

    matched_skill_paths = matched_skill_paths or {}
    result = ScaffoldResult(target_dir=target_dir)

    target_dir.mkdir(parents=True, exist_ok=True)
    result.created_dirs.append(target_dir)
    for rel in _SKELETON_DIRS:
        d = target_dir / rel
        d.mkdir(parents=True, exist_ok=True)
        result.created_dirs.append(d)

    gitignore = _GITIGNORE_CORE
    if _is_python_stack(intent.stack):
        gitignore += _GITIGNORE_PYTHON
    _write(target_dir / ".gitignore", gitignore, result)
    _write(target_dir / ".claudeignore", _CLAUDEIGNORE_DEFAULT, result)
    _write(target_dir / ".env.example", _ENV_EXAMPLE_DEFAULT, result)
    _write(
        target_dir / ".claude" / "settings.json",
        json.dumps(_SETTINGS_JSON_DEFAULT, indent=2) + "\n",
        result,
    )
    _write(target_dir / "README.md", _render_readme(intent), result)

    wired = _wire_skills(target_dir, matched_skill_paths, result)
    result.wired_skills = wired
    _write(target_dir / "CLAUDE.md", _render_claude_md(intent, wired), result)

    return result


def _write(path: Path, content: str, result: ScaffoldResult) -> None:
    path.write_text(content, encoding="utf-8")
    result.created_files.append(path)


def _wire_skills(
    target_dir: Path, matched_skill_paths: dict[str, Path], result: ScaffoldResult
) -> list[str]:
    wired: list[str] = []
    skills_dir = target_dir / ".claude" / "skills"
    for name, skill_md_path in matched_skill_paths.items():
        source_folder = skill_md_path.parent
        if not source_folder.is_dir():
            continue
        dest_folder = skills_dir / name
        shutil.copytree(source_folder, dest_folder, dirs_exist_ok=True)
        result.created_dirs.append(dest_folder)
        wired.append(name)
    return wired
