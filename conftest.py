"""Adds src/ to sys.path so tests can import skill_scan without installing
it as a package - same approach used by every ad-hoc verification script in
this repo (no pyproject.toml/setup.py exists yet for an installable layout).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
