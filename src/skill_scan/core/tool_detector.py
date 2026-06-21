"""Detect installed AI development tools from the tool registry."""

import glob
import json
import os
from pathlib import Path

_REGISTRY_PATH = Path(__file__).parent.parent / "data" / "tool_registry.json"


def _expand(p: str) -> str:
    return os.path.expandvars(p)


def _hint_exists(hint: str) -> bool:
    expanded = _expand(hint)
    if any(c in hint for c in "*?["):
        return bool(glob.glob(expanded))
    return Path(expanded).exists()


def _resolve_dir(p: str) -> str:
    """Expand env vars; if the path is a file, return its parent directory."""
    expanded = _expand(p)
    path = Path(expanded)
    return str(path.parent) if path.suffix else expanded


def load_registry() -> list[dict]:
    with open(_REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def detect_tools() -> list[dict]:
    """Load registry and annotate each entry with detection result and resolved paths."""
    results = []
    for tool in load_registry():
        unverified = tool.get("status") == "unverified"
        hints = tool.get("install_hints", [])
        detected = not unverified and any(_hint_exists(h) for h in hints)

        resolved: dict[str, list[str]] = {}
        for fmt, paths in tool.get("watch_paths", {}).items():
            resolved[fmt] = [_resolve_dir(p) for p in paths if p]

        results.append({**tool, "detected": detected, "resolved_paths": resolved})
    return results


def collect_watch_dirs(tools: list[dict], fmt: str = "skill") -> list[str]:
    """Return unique existing watch directories for the given format from a tool list."""
    seen: set[str] = set()
    dirs: list[str] = []
    for tool in tools:
        for p in tool.get("resolved_paths", {}).get(fmt, []):
            expanded = _expand(p)
            if expanded not in seen and Path(expanded).exists():
                seen.add(expanded)
                dirs.append(expanded)
    return dirs
