"""File type router — detects whether a path is a SKILL.md, MCP manifest, A2A card, or unknown."""

import json
from enum import Enum
from pathlib import Path


class SpecType(Enum):
    SKILL_MD = "skill"
    MCP_MANIFEST = "mcp"
    A2A_CARD = "a2a"
    UNKNOWN = "unknown"


def detect_type(path: Path) -> SpecType:
    """Return the SpecType for the given file path."""
    if path.name == "SKILL.md":
        return SpecType.SKILL_MD

    if path.suffix.lower() != ".json":
        return SpecType.UNKNOWN

    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception:
        return SpecType.UNKNOWN

    if not isinstance(data, dict):
        return SpecType.UNKNOWN

    # MCP manifest: has "mcpVersion" key or "tools" array at root
    if "mcpVersion" in data or isinstance(data.get("tools"), list):
        return SpecType.MCP_MANIFEST

    # A2A agent card: "capabilities" key + filename or path convention
    if "capabilities" in data:
        name = path.name
        parent = path.parent.name
        if name == "agent.json" or parent == ".well-known":
            return SpecType.A2A_CARD

    return SpecType.UNKNOWN
