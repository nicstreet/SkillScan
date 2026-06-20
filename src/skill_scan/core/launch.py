"""Launch the real work surface as its own process - see
.claude/architecture/project-setup-flow.md, "SkillScan is the front door,
not the work surface". SkillScan hands off and steps back; it does not
embed a console widget or wait on the launched process.

Claude Code only, for now. Cowork launching is NOT implemented here - whether
it has an equivalent CLI/deep-link launcher to Claude Code's `claude` command
is unconfirmed (see todo.md's open design questions for "Project Setup &
Skill Supply Chain") - guessing at one would be worse than not having it.
"""

import os
import shutil
import subprocess
from pathlib import Path


class LaunchError(RuntimeError):
    """Raised when the target executable can't be found."""


def claude_code_available() -> bool:
    return shutil.which("claude") is not None


def launch_claude_code(
    project_dir: Path, allow_api_billing: bool = False
) -> subprocess.Popen:
    """Spawn `claude` as its own process in project_dir, then return -
    SkillScan does not wait on it or embed it.

    Strips ANTHROPIC_API_KEY from the subprocess environment unless
    allow_api_billing is explicitly True. Setting that key makes Claude Code
    silently switch from subscription billing to pay-as-you-go API billing,
    taking precedence over subscription auth - a key configured for
    SkillScan's own small internal calls (core/llm.py) must never leak into
    the launched subprocess and silently hijack the user's whole session
    onto metered billing.
    """
    claude_path = shutil.which("claude")
    if claude_path is None:
        raise LaunchError("claude CLI not found on PATH - install Claude Code first.")

    env = os.environ.copy()
    if not allow_api_billing:
        env.pop("ANTHROPIC_API_KEY", None)

    return subprocess.Popen([claude_path], cwd=str(project_dir), env=env)
