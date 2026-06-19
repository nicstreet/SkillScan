"""Static checks for scripts/ files against agentskills.io's scripting guidance.

https://agentskills.io/skill-creation/using-scripts

Scripts can't be safely executed by a scanner, so these are heuristic warnings
based on source text patterns — not hard pass/fail validation.
"""

import re
from pathlib import Path

_INTERACTIVE_PY = re.compile(r"\b(input|raw_input)\s*\(")
_INTERACTIVE_GETPASS = re.compile(r"\bgetpass\s*\(")
_INTERACTIVE_BASH_READ = re.compile(r"(?m)^\s*read\s+(-p\s+)?\S")
_HELP_HINT = re.compile(r"--help|argparse|ArgumentParser|click\.command")
_EXIT_CODE_HINT = re.compile(r"sys\.exit\(|exit\(\d|return\s+\d+\s*$", re.MULTILINE)


def lint_script(path: str | Path) -> list[str]:
    """Return heuristic warnings for a single script file. Empty list = clean."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return [f"could not read file: {path.name}"]

    warnings: list[str] = []
    suffix = path.suffix.lower()

    if suffix == ".py":
        if _INTERACTIVE_PY.search(text):
            warnings.append(
                "uses input()/raw_input() — agents run in non-interactive shells "
                "and will hang waiting for a response"
            )
        if _INTERACTIVE_GETPASS.search(text):
            warnings.append("uses getpass() — will block waiting for a TTY prompt")
        if not _EXIT_CODE_HINT.search(text):
            warnings.append(
                "no explicit exit code found — use distinct codes per failure type"
            )
    elif suffix in (".sh", ".bash"):
        if _INTERACTIVE_BASH_READ.search(text):
            warnings.append("uses `read` — likely waits for interactive input")

    if not _HELP_HINT.search(text):
        warnings.append(
            "no --help/usage handling found — agents rely on --help to learn "
            "the script's interface"
        )

    return warnings


def lint_scripts(paths: list[str | Path]) -> dict[str, list[str]]:
    """Lint multiple scripts. Returns {filename: [warnings]} — clean files omitted."""
    results: dict[str, list[str]] = {}
    for p in paths:
        p = Path(p)
        warnings = lint_script(p)
        if warnings:
            results[p.name] = warnings
    return results
