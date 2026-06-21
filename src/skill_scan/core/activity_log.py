"""Append-only activity log at %APPDATA%\\SkillScan\\activity.log.

Extracted from skill_detail_view.py once a second view (skill_audit_view.py)
needed the same logging - see python-style.md's DRY rule.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

LOG_PATH = Path(os.environ.get("APPDATA", "~")) / "SkillScan" / "activity.log"


def log_activity(action: str, detail: str = "") -> None:
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        line = f"[{ts}]  {action}"
        if detail:
            line += f"  —  {detail}"
        with open(LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass
