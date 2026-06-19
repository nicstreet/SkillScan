"""Curated license registry for the License picker (Options Skill Defaults, Skill Manager).

Data file: data/license_registry.json — name, category, plain-language description,
source-disclosure obligation, and a link to the canonical legal text per entry.
"""

import json
from pathlib import Path

_REGISTRY_PATH = Path(__file__).parent.parent / "data" / "license_registry.json"

_cache: list[dict] | None = None


def load_licenses() -> list[dict]:
    global _cache
    if _cache is None:
        with open(_REGISTRY_PATH, encoding="utf-8") as f:
            _cache = json.load(f)
    return _cache


def find_by_spdx(spdx: str) -> dict | None:
    """Look up a registry entry by its spdx value (empty string matches "No License")."""
    for lic in load_licenses():
        if lic["spdx"] == spdx:
            return lic
    return None
