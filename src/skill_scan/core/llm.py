"""In-app LLM call helper — used by Skill Manager (Optimize Description, AI Review).

Uses the 'inapp' feature credentials from config (Options → LLM → Skill Studio provider).
Falls back to ANTHROPIC_API_KEY environment variable when no API key is configured.
"""

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
            d = cfg.load()
            creds = get_llm_creds(d, "inapp")

            api_key = creds["api_key"].strip() or _env_fallback_key()
            base_url = creds["base_url"].strip() or None
            is_local = creds["is_local"]

            if not api_key and not is_local:
                self.error.emit(
                    "No API key found.\n\n"
                    "Set an API key in Options → LLM, or add ANTHROPIC_API_KEY to your .env file.\n"
                    "For local providers (Ollama, OpenAI Local) no key is required."
                )
                return

            raw_model = (creds["model"] or _FALLBACK_MODEL).strip()
            model = _STALE_MODELS.get(raw_model, raw_model)

            messages: list[dict] = []
            if self._system:
                messages.append({"role": "system", "content": self._system})
            messages.append({"role": "user", "content": self._prompt})

            logger.info(
                "LLM call: provider=%s model=%s prompt_chars=%d local=%s",
                creds["provider"],
                model,
                len(self._prompt),
                is_local,
            )
            import litellm

            kwargs: dict = {"model": model, "messages": messages}
            # Local providers (Ollama, LM Studio) don't need a real key, but
            # litellm's OpenAI client layer requires api_key to be non-empty.
            kwargs["api_key"] = api_key if api_key else "local"
            if base_url:
                kwargs["api_base"] = base_url
            response = litellm.completion(**kwargs)
            result: str = response.choices[0].message.content or ""
            logger.info("LLM call complete: %d chars returned", len(result))
            self.finished.emit(result)

        except Exception as exc:
            logger.error("LLM call failed: %s", exc, exc_info=True)
            self.error.emit(str(exc))
