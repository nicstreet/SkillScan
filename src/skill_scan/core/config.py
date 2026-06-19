import json
import os
from pathlib import Path
from typing import Any

_CONFIG_DIR = Path(os.environ.get("APPDATA", "~")) / "SkillScan"
_CONFIG_FILE = _CONFIG_DIR / "config.json"

_DEFAULTS: dict[str, Any] = {
    # ── LLM — per-feature active provider ────────────────────────────────────
    "inapp_llm_provider": "anthropic",  # Skill Studio: Optimize, Review, Security Eval
    "scanner_llm_provider": "anthropic",  # Skill Scanner --use-llm + MCP LLM judge
    # ── LLM — per-provider credentials (all stored simultaneously) ───────────
    "anthropic_api_key": "",
    "anthropic_model": "anthropic/claude-sonnet-4-6",
    "openai_api_key": "",
    "openai_model": "openai/gpt-4o",
    "ollama_base_url": "http://localhost:11434",
    "ollama_model": "ollama/llama3.2",
    "openai_local_base_url": "http://localhost:1234/v1",
    "openai_local_model": "openai/local-model",
    "openai_local_api_key": "",
    # ── Third-party scan integrations ────────────────────────────────────────
    "virustotal_api_key": "",
    "ai_defense_api_key": "",
    # ── Skill scanner (cisco-ai-skill-scanner) ────────────────────────────────
    "use_behavioral": True,
    "use_llm": True,
    "use_trigger": False,
    "use_aidefense": False,
    "use_virustotal": False,
    "policy": "permissive",
    "detailed": True,
    "fail_on_severity": "",
    # ── MCP scanner (cisco-ai-mcp-scanner) ───────────────────────────────────
    "mcp_api_key": "",  # Cisco AI Defense key (MCP_SCANNER_API_KEY)
    "mcp_use_llm": False,  # LLM-as-judge analyzer
    "mcp_use_api": False,  # Cisco AI Defense API analyzer
    # ── Dashboard ─────────────────────────────────────────────────────────────
    "dashboard_hidden": [],
    "dashboard_spans": {},
    "dashboard_order": [],
    # ── App ───────────────────────────────────────────────────────────────────
    "watched_folders": [],
    "watched_folder_notify": True,
    "suppress_scan_windows": False,
    "suppress_error_notifications": False,
    "suppress_additional_notifications": False,
    "scan_hotkey": "Ctrl+Shift+S",
    "accent_color": "#0ea5e9",
    "clipboard_watch_enabled": False,
    "clipboard_watch_interval_secs": 30,
    "clipboard_min_chars": 250,
    # ── Skill Manager — Skill Defaults ────────────────────────────────────────
    "default_license": "",
    "default_compatibility": "",
    "default_metadata": {},
    "default_allowed_tools": "",
}

# Providers that don't require an API key
_LOCAL_PROVIDERS = {"ollama", "openai (local)"}


def get_llm_creds(cfg: dict, feature: str = "inapp") -> dict[str, str]:
    """Return {provider, api_key, model, base_url, is_local} for a feature.

    feature: 'inapp'   → Skill Studio (Optimize / Review / Security Eval)
             'scanner' → Skill Scanner --use-llm and MCP LLM judge
    """
    key = "inapp_llm_provider" if feature == "inapp" else "scanner_llm_provider"
    provider = cfg.get(key, "anthropic")
    return _creds_for(cfg, provider)


def _creds_for(cfg: dict, provider: str) -> dict[str, str]:
    if provider == "anthropic":
        return {
            "provider": provider,
            "api_key": cfg.get("anthropic_api_key", ""),
            "model": cfg.get("anthropic_model", "anthropic/claude-sonnet-4-6"),
            "base_url": "",
            "is_local": False,
        }
    if provider == "openai":
        return {
            "provider": provider,
            "api_key": cfg.get("openai_api_key", ""),
            "model": cfg.get("openai_model", "openai/gpt-4o"),
            "base_url": "",
            "is_local": False,
        }
    if provider == "ollama":
        return {
            "provider": provider,
            "api_key": "",
            "model": cfg.get("ollama_model", "ollama/llama3.2"),
            "base_url": cfg.get("ollama_base_url", "http://localhost:11434"),
            "is_local": True,
        }
    if provider == "openai (local)":
        return {
            "provider": provider,
            "api_key": cfg.get("openai_local_api_key", ""),
            "model": cfg.get("openai_local_model", "openai/local-model"),
            "base_url": cfg.get("openai_local_base_url", "http://localhost:1234/v1"),
            "is_local": True,
        }
    return {
        "provider": provider,
        "api_key": "",
        "model": "",
        "base_url": "",
        "is_local": False,
    }


def _migrate_llm(data: dict) -> None:
    """One-time migration from flat llm_* keys to per-provider + per-feature keys."""
    old_provider = data.pop("llm_provider", None)
    old_key = data.pop("llm_api_key", None)
    old_model = data.pop("llm_model", None)
    old_base_url = data.pop("llm_base_url", None)

    if not old_provider:
        return

    if not data.get("inapp_llm_provider"):
        data["inapp_llm_provider"] = old_provider
    if not data.get("scanner_llm_provider"):
        data["scanner_llm_provider"] = old_provider

    if old_key:
        if old_provider == "anthropic" and not data.get("anthropic_api_key"):
            data["anthropic_api_key"] = old_key
        elif old_provider == "openai" and not data.get("openai_api_key"):
            data["openai_api_key"] = old_key
        elif old_provider == "openai (local)" and not data.get("openai_local_api_key"):
            data["openai_local_api_key"] = old_key

    if old_model:
        if old_provider == "anthropic" and not data.get("anthropic_model"):
            data["anthropic_model"] = old_model
        elif old_provider == "openai" and not data.get("openai_model"):
            data["openai_model"] = old_model
        elif old_provider == "ollama" and not data.get("ollama_model"):
            data["ollama_model"] = old_model
        elif old_provider == "openai (local)" and not data.get("openai_local_model"):
            data["openai_local_model"] = old_model

    if old_base_url:
        if old_provider == "ollama" and not data.get("ollama_base_url"):
            data["ollama_base_url"] = old_base_url
        elif old_provider == "openai (local)" and not data.get("openai_local_base_url"):
            data["openai_local_base_url"] = old_base_url


def load() -> dict[str, Any]:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not _CONFIG_FILE.exists():
        return dict(_DEFAULTS)
    try:
        with open(_CONFIG_FILE, encoding="utf-8") as f:
            raw = json.load(f)
        data = {**_DEFAULTS, **raw}
        _migrate_llm(data)
        return data
    except Exception:
        return dict(_DEFAULTS)


def save(cfg: dict[str, Any]) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)
