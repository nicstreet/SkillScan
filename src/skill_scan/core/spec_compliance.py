"""Shared spec-compliance validation against the agentskills.io specification.

Single source of truth for SKILL.md validation — used by both the Skill Detail
Compliance tab (scoring existing skills) and Skill Manager (validating drafts
before packaging). Do not reimplement these rules elsewhere.

Spec reference: https://agentskills.io/specification
"""

import re
from dataclasses import dataclass, field
from pathlib import Path

_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_NAME_MAX_LEN = 64
_DESCRIPTION_MAX_LEN = 1024
_COMPATIBILITY_MAX_LEN = 500

# Only name + description are required by spec — missing either means the file
# is invalid, and that's the only thing the score reflects. license/compatibility/
# metadata/allowed-tools are genuinely optional and situational per spec (e.g.
# "Most skills do not need the compatibility field") — their absence is often
# correct, not a deficiency, so they are surfaced as informational notes in the
# UI but never deducted from the score. Don't add a weight for them here.
REQUIRED_FIELDS = ["name", "description"]
RECOMMENDED_FIELDS = ["license", "compatibility", "metadata", "allowed-tools"]
REQ_WEIGHT = 50

# Progressive disclosure budget (spec recommendation) — rough token estimate
# at ~4 chars/token, good enough for a warning threshold.
MAX_BODY_LINES = 500
MAX_BODY_TOKENS = 5000


@dataclass
class ComplianceResult:
    score: int
    missing_required: list[str] = field(default_factory=list)
    missing_recommended: list[str] = field(default_factory=list)
    name_errors: list[str] = field(default_factory=list)
    description_errors: list[str] = field(default_factory=list)
    body_warnings: list[str] = field(default_factory=list)


def validate_name(name: str, folder_name: str | None = None) -> list[str]:
    """Check `name` against agentskills.io naming rules.

    Safe to call with a partial/empty string for live-typing feedback — returns
    ["name is missing"] rather than raising.
    """
    name = (name or "").strip()
    if not name:
        return ["name is missing"]
    errors = []
    if len(name) > _NAME_MAX_LEN:
        errors.append(f"exceeds {_NAME_MAX_LEN} characters")
    if "--" in name:
        errors.append("must not contain consecutive hyphens")
    elif name.startswith("-") or name.endswith("-"):
        errors.append("must not start or end with a hyphen")
    elif not _NAME_RE.match(name):
        errors.append("must be lowercase letters, numbers, and single hyphens only")
    if folder_name is not None and name != folder_name:
        errors.append(f"must match parent folder name (folder is '{folder_name}')")
    return errors


def validate_description(description: str) -> list[str]:
    """Check `description` against agentskills.io rules."""
    description = (description or "").strip()
    if not description:
        return ["description is missing"]
    if len(description) > _DESCRIPTION_MAX_LEN:
        return [f"exceeds {_DESCRIPTION_MAX_LEN} characters"]
    return []


def validate_compatibility(compatibility: str) -> list[str]:
    """Check optional `compatibility` field length, if provided."""
    if not compatibility:
        return []
    if len(compatibility) > _COMPATIBILITY_MAX_LEN:
        return [f"exceeds {_COMPATIBILITY_MAX_LEN} characters"]
    return []


def check_body_budget(body: str) -> list[str]:
    """Warn if the SKILL.md body exceeds the progressive-disclosure budget."""
    if not body:
        return []
    warnings = []
    lines = body.count("\n") + 1
    if lines > MAX_BODY_LINES:
        warnings.append(
            f"body is {lines} lines (recommended budget: {MAX_BODY_LINES}) — "
            "consider moving detail to references/"
        )
    approx_tokens = len(body) // 4
    if approx_tokens > MAX_BODY_TOKENS:
        warnings.append(
            f"body is ~{approx_tokens} tokens (recommended budget: {MAX_BODY_TOKENS}) — "
            "consider moving detail to references/"
        )
    return warnings


def score(
    meta: dict, folder_name: str | None = None, body: str = ""
) -> ComplianceResult:
    """Score a parsed SKILL.md frontmatter dict against the spec.

    The score is based solely on the two actually-required fields (name,
    description) and their structural validity. `missing_recommended` and
    `body_warnings` are still computed for the UI's informational notes, but
    deliberately do not affect the score — they're often correct to leave
    unset (see RECOMMENDED_FIELDS comment above), so penalizing them would
    contradict the spec's own guidance.
    """
    name = str(meta.get("name") or "").strip()
    description = str(meta.get("description") or "").strip()

    missing_req = [f for f in REQUIRED_FIELDS if not meta.get(f)]
    missing_rec = [f for f in RECOMMENDED_FIELDS if not meta.get(f)]

    name_errors = validate_name(name, folder_name) if name else []
    description_errors = validate_description(description) if description else []
    body_warnings = check_body_budget(body)

    deduction = len(missing_req) * REQ_WEIGHT
    if name_errors:
        deduction += REQ_WEIGHT // 2
    if description_errors:
        deduction += REQ_WEIGHT // 2

    return ComplianceResult(
        score=max(0, 100 - deduction),
        missing_required=missing_req,
        missing_recommended=missing_rec,
        name_errors=name_errors,
        description_errors=description_errors,
        body_warnings=body_warnings,
    )


def parse_frontmatter(path: str | Path) -> dict:
    """Parse YAML frontmatter from a SKILL.md file. Returns {} on any failure."""
    import yaml

    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                return yaml.safe_load(text[3:end]) or {}
    except Exception:
        pass
    return {}


def parse_body(path: str | Path) -> str:
    """Return the Markdown body following the frontmatter closing `---`."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        if text.startswith("---"):
            end = text.find("\n---", 3)
            if end != -1:
                return text[end + 4 :].lstrip("\n")
    except Exception:
        pass
    return ""


def score_file(path: str | Path) -> ComplianceResult:
    """Convenience wrapper: parse + score a SKILL.md file in one call."""
    path = Path(path)
    meta = parse_frontmatter(path)
    body = parse_body(path)
    return score(meta, folder_name=path.parent.name, body=body)
