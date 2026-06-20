"""In-app LLM call helper — used by Skill Manager (Optimize Description, AI Review).

Uses the 'inapp' feature credentials from config (Options → LLM → Skill Studio provider).
Falls back to ANTHROPIC_API_KEY environment variable when no API key is configured.
"""

import json
import logging
import os

from PyQt6.QtCore import QObject, QThread, pyqtSignal

from . import config as cfg
from .config import get_llm_creds

logger = logging.getLogger(__name__)

_FALLBACK_MODEL = "anthropic/claude-sonnet-4-6"

_STALE_MODELS: dict[str, str] = {
    "anthropic/claude-sonnet-4-20250514": "anthropic/claude-sonnet-4-6",
    "claude-sonnet-4-20250514": "anthropic/claude-sonnet-4-6",
}


def _env_fallback_key() -> str:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass
    return os.getenv("ANTHROPIC_API_KEY", "")


class LLMError(RuntimeError):
    """Raised by call_llm_sync() — same message text the GUI shows via LLMJob.error."""


def extract_json_object(text: str | None) -> dict | None:
    """Pull the first JSON object out of LLM/subprocess output, tolerating any
    leading/trailing prose despite instructions to respond with JSON only.

    Extracted from skill_detail_view.py once a second caller (core/intent_parser.py)
    needed the identical logic - see python-style.md's DRY rule.
    """
    if not text:
        return None
    try:
        result = json.loads(text.strip())
        if isinstance(result, dict):
            return result
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch == "{":
            try:
                obj, _ = decoder.raw_decode(text, i)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue
    return None


def call_llm_sync(
    prompt: str,
    system: str = "",
    feature: str = "inapp",
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> str:
    """Blocking LLM call - no Qt required. Shared by LLMJob and standalone scripts.

    feature: 'inapp' (Skill Studio) or 'scanner' (Skill Scanner / MCP LLM judge),
    see core.config.get_llm_creds. temperature/max_tokens are left at the
    provider's default (None) unless a caller needs short, low-variance
    output (e.g. benchmark harnesses parsing a single answer token).
    """
    d = cfg.load()
    creds = get_llm_creds(d, feature)

    api_key = creds["api_key"].strip() or _env_fallback_key()
    base_url = creds["base_url"].strip() or None
    is_local = creds["is_local"]

    if not api_key and not is_local:
        raise LLMError(
            "No API key found.\n\n"
            "Set an API key in Options → LLM, or add ANTHROPIC_API_KEY to your .env file.\n"
            "For local providers (Ollama, OpenAI Local) no key is required."
        )

    raw_model = (creds["model"] or _FALLBACK_MODEL).strip()
    model = _STALE_MODELS.get(raw_model, raw_model)

    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    logger.info(
        "LLM call: provider=%s model=%s prompt_chars=%d local=%s",
        creds["provider"],
        model,
        len(prompt),
        is_local,
    )
    import litellm

    kwargs: dict = {"model": model, "messages": messages}
    # Local providers (Ollama, LM Studio) don't need a real key, but
    # litellm's OpenAI client layer requires api_key to be non-empty.
    kwargs["api_key"] = api_key if api_key else "local"
    if base_url:
        kwargs["api_base"] = base_url
    if temperature is not None:
        kwargs["temperature"] = temperature
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    response = litellm.completion(**kwargs)
    result: str = response.choices[0].message.content or ""
    logger.info("LLM call complete: %d chars returned", len(result))
    return result


class LLMJob(QObject):
    """Non-blocking LLM call. Connect signals, then call start()."""

    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, prompt: str, system: str = "", parent=None):
        super().__init__(parent)
        self._prompt = prompt
        self._system = system
        self._thread = QThread()
        self.moveToThread(self._thread)
        self._thread.started.connect(self.run)
        self.finished.connect(self._thread.quit)
        self.error.connect(self._thread.quit)

    def start(self) -> None:
        self._thread.start()

    def run(self) -> None:
        try:
            result = call_llm_sync(self._prompt, self._system, feature="inapp")
            self.finished.emit(result)
        except Exception as exc:
            logger.error("LLM call failed: %s", exc, exc_info=True)
            self.error.emit(str(exc))
