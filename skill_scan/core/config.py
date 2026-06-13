import json
import os
from pathlib import Path
from typing import Any

_CONFIG_DIR = Path(os.environ.get("APPDATA", "~")) / "SkillScan"
_CONFIG_FILE = _CONFIG_DIR / "config.json"

_DEFAULTS: dict[str, Any] = {
    "llm_provider": "anthropic",
    "llm_api_key": "",
    "llm_model": "anthropic/claude-sonnet-4-20250514",
    "virustotal_api_key": "",
    "ai_defense_api_key": "",
    "use_behavioral": True,
    "use_llm": True,
    "use_trigger": False,
    "use_aidefense": False,
    "use_virustotal": False,
    "policy": "permissive",
    "detailed": True,
    "fail_on_severity": "",
    "watched_folders": [],
    "scan_hotkey": "Ctrl+Shift+S",
    "accent_color": "#0ea5e9",
    "clipboard_watch_enabled": False,
    "clipboard_watch_interval_secs": 30,
    "clipboard_min_chars": 200,
}


def load() -> dict[str, Any]:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not _CONFIG_FILE.exists():
        return dict(_DEFAULTS)
    try:
        with open(_CONFIG_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return {**_DEFAULTS, **data}
    except Exception:
        return dict(_DEFAULTS)


def save(cfg: dict[str, Any]) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
