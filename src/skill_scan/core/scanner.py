"""Wraps the skill-scanner CLI via QProcess, streaming output live."""

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal

from .config import load as load_cfg
from .result_store import ScanResult, add as store_result


def _extract_json(text: str) -> list | dict | None:
    """Parse JSON from scanner output that may contain non-JSON lines mixed in.

    The cisco-ai-skill-scanner prefixes stdout with LiteLLM info/feedback lines
    before the JSON payload.  json.JSONDecoder.raw_decode() starts at a given
    position and stops at the matching closing bracket — the only reliable way
    to extract a JSON value from mixed text without caring about trailing data.
    """
    if not text.strip():
        return None
    # Fast path: whole buffer is clean JSON
    try:
        result = json.loads(text)
        if isinstance(result, (list, dict)):
            return result
    except json.JSONDecodeError:
        pass
    # Scan for the first { or [ and decode from there
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch in ("{", "["):
            try:
                result, _ = decoder.raw_decode(text, i)
                if isinstance(result, (list, dict)):
                    return result
            except json.JSONDecodeError:
                pass
    return None


class ScanJob(QObject):
    output_line = pyqtSignal(str)  # stdout/stderr line as it arrives
    finished = pyqtSignal(ScanResult)  # emitted when process exits
    error = pyqtSignal(str)  # emitted on launch failure

    def __init__(self, path: str, cfg: Optional[dict] = None, parent=None):
        super().__init__(parent)
        self._path = path
        self._cfg = cfg or load_cfg()
        self._process = QProcess(self)
        self._stdout_buf = ""
        self._stderr_buf = ""
        self._exit_code = 0
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.readyReadStandardError.connect(self._on_stderr)
        self._process.finished.connect(self._on_finished)

    # ------------------------------------------------------------------
    @staticmethod
    def _find_skill_scanner() -> str | None:
        """Prefer the exe next to the running Python (venv Scripts), fall back to PATH."""
        import sys

        scripts_dir = Path(sys.executable).parent
        for name in ("skill-scanner.exe", "skill-scanner"):
            candidate = scripts_dir / name
            if candidate.exists():
                return str(candidate)
        return shutil.which("skill-scanner")

    def start(self) -> None:
        exe = self._find_skill_scanner()
        if exe is None:
            self.error.emit(
                "skill-scanner not found.\n"
                "Run: pip install cisco-ai-skill-scanner[all]"
            )
            return

        args = self._build_args()
        env = self._build_env()

        from PyQt6.QtCore import QProcessEnvironment

        pe = QProcessEnvironment.systemEnvironment()
        for k, v in env.items():
            pe.insert(k, v)
        self._process.setProcessEnvironment(pe)

        self._process.start(exe, args)
        if not self._process.waitForStarted(3000):
            self.error.emit(
                f"Failed to start skill-scanner: {self._process.errorString()}"
            )

    def cancel(self) -> None:
        if self._process.state() != QProcess.ProcessState.NotRunning:
            self._process.kill()

    # ------------------------------------------------------------------
    def _build_args(self) -> list[str]:
        c = self._cfg
        args = ["scan", self._path, "--format", "json"]
        if c.get("use_behavioral"):
            args.append("--use-behavioral")
        if c.get("use_llm"):
            args.append("--use-llm")
        if c.get("use_trigger"):
            args.append("--use-trigger")
        if c.get("use_aidefense"):
            args.append("--use-aidefense")
        if c.get("use_virustotal"):
            args.append("--use-virustotal")
        if c.get("detailed"):
            args.append("--detailed")
        policy = c.get("policy", "")
        if policy in ("strict", "permissive"):
            args += ["--policy", policy]
        fail_on = c.get("fail_on_severity", "")
        if fail_on:
            args += ["--fail-on-severity", fail_on]
        args.append("--lenient")
        return args

    def _build_env(self) -> dict[str, str]:
        c = self._cfg
        env: dict[str, str] = {}
        if c.get("llm_api_key"):
            env["SKILL_SCANNER_LLM_API_KEY"] = c["llm_api_key"]
        if c.get("llm_model"):
            env["SKILL_SCANNER_LLM_MODEL"] = c["llm_model"]
        provider = c.get("llm_provider", "")
        if provider:
            env["SKILL_SCANNER_LLM_PROVIDER"] = provider
        if c.get("virustotal_api_key"):
            env["VIRUSTOTAL_API_KEY"] = c["virustotal_api_key"]
        if c.get("ai_defense_api_key"):
            env["AI_DEFENSE_API_KEY"] = c["ai_defense_api_key"]
        return env

    # ------------------------------------------------------------------
    def _on_stdout(self) -> None:
        data = bytes(self._process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        self._stdout_buf += data
        for line in data.splitlines():
            self.output_line.emit(line)

    def _on_stderr(self) -> None:
        data = bytes(self._process.readAllStandardError()).decode(
            "utf-8", errors="replace"
        )
        self._stderr_buf += data
        for line in data.splitlines():
            self.output_line.emit(f"[stderr] {line}")

    def _on_finished(self, exit_code: int, _exit_status) -> None:
        # Store exit code and delay completion: on Windows the pipe may not be
        # fully flushed by the time the finished signal fires, so give the OS
        # 200 ms to deliver any remaining readyRead events before we finalise.
        self._exit_code = exit_code
        QTimer.singleShot(200, self._finalise)

    def _finalise(self) -> None:
        # Flush any output still sitting in the QProcess buffer
        remaining_out = bytes(self._process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        if remaining_out:
            self._stdout_buf += remaining_out
            for line in remaining_out.splitlines():
                self.output_line.emit(line)

        remaining_err = bytes(self._process.readAllStandardError()).decode(
            "utf-8", errors="replace"
        )
        if remaining_err:
            self._stderr_buf += remaining_err
            for line in remaining_err.splitlines():
                self.output_line.emit(f"[stderr] {line}")

        result = ScanResult(
            path=self._path,
            timestamp=datetime.now().isoformat(timespec="seconds"),
            returncode=self._exit_code,
            stdout=self._stdout_buf,
            stderr=self._stderr_buf,
            parsed=_extract_json(self._stdout_buf),
        )
        store_result(result)
        self.finished.emit(result)


# ---------------------------------------------------------------------------
# Clipboard scanning helpers
# ---------------------------------------------------------------------------


def clipboard_path_or_temp(text: str) -> tuple[str, bool]:
    """
    Given clipboard text, return (path_to_scan, is_temp).
    If text looks like an existing path, return it directly (is_temp=False).
    Otherwise write it to a temp SKILL.md and return that dir (is_temp=True).
    """
    candidate = text.strip().strip('"').strip("'")
    if Path(candidate).exists():
        return candidate, False

    tmp = tempfile.mkdtemp(prefix="skillscan_")
    skill_md = Path(tmp) / "SKILL.md"
    skill_md.write_text(text, encoding="utf-8")
    return tmp, True
