"""Wraps skill-scanner and mcp-scanner CLIs via QProcess, streaming output live.

Routing: MCP manifests (router.SpecType.MCP_MANIFEST) are dispatched to
`mcp-scanner static --tools <path>`.  All other types use `skill-scanner scan`.
"""

import json
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from .router import SpecType, detect_type

from PyQt6.QtCore import QObject, QProcess, QTimer, pyqtSignal

from .config import get_llm_creds, load as load_cfg
from .result_store import ScanResult, add as store_result

_MCP_SEV_RANK: dict[str, int] = {
    "CRITICAL": 4,
    "HIGH": 3,
    "MEDIUM": 2,
    "LOW": 1,
    "SAFE": 0,
    "INFO": 0,
}
_MCP_SEV_MAP: dict[int, str] = {
    4: "critical",
    3: "high",
    2: "medium",
    1: "low",
    0: "clean",
}


def _normalize_mcp_result(raw: dict) -> dict:
    """Convert mcp-scanner output to the standard SkillScan findings format.

    mcp-scanner returns per-tool scan_results with nested analyzer dicts.
    This flattens them to the same {is_safe, max_severity, findings, analyzers_used}
    shape that skill-scanner produces and that the rest of the UI expects.
    """
    scan_results = raw.get("scan_results") or []
    findings: list[dict] = []
    max_rank = 0

    for sr in scan_results:
        tool_name = sr.get("tool_name") or ""
        tool_desc = sr.get("tool_description") or ""
        for analyzer_key, adata in (sr.get("findings") or {}).items():
            sev_str = (adata.get("severity") or "INFO").upper()
            rank = _MCP_SEV_RANK.get(sev_str, 0)
            if rank > max_rank:
                max_rank = rank
            taxonomies = adata.get("mcp_taxonomies") or []
            for threat in adata.get("threat_names") or []:
                tx = taxonomies[0] if taxonomies else {}
                findings.append(
                    {
                        "severity": sev_str,
                        "category": tx.get("scanner_category") or threat,
                        "title": f"{tool_name}: {threat}",
                        "description": tool_desc,
                        "remediation": tx.get("description") or "",
                        "analyzer": analyzer_key.replace("_analyzer", ""),
                        "rule_id": threat.replace(" ", "_"),
                    }
                )

    is_safe = len(findings) == 0
    return {
        "is_safe": is_safe,
        "max_severity": _MCP_SEV_MAP.get(max_rank, "clean"),
        "findings": findings,
        "findings_count": len(findings),
        "analyzers_used": raw.get("requested_analyzers") or [],
        "scan_duration_seconds": 0,
    }


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
        self._spec_type = detect_type(Path(path))
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

    @staticmethod
    def _find_mcp_scanner() -> str | None:
        """Prefer the exe next to the running Python (venv Scripts), fall back to PATH."""
        import sys

        scripts_dir = Path(sys.executable).parent
        for name in ("mcp-scanner.exe", "mcp-scanner"):
            candidate = scripts_dir / name
            if candidate.exists():
                return str(candidate)
        return shutil.which("mcp-scanner")

    def start(self) -> None:
        if self._spec_type == SpecType.MCP_MANIFEST:
            self._start_mcp()
        else:
            self._start_skill()

    def _start_skill(self) -> None:
        exe = self._find_skill_scanner()
        if exe is None:
            self.error.emit(
                "skill-scanner not found.\n"
                "Run: pip install cisco-ai-skill-scanner[all]"
            )
            return
        self._launch(exe, self._build_args(), self._build_env())

    def _start_mcp(self) -> None:
        exe = self._find_mcp_scanner()
        if exe is None:
            self.error.emit(
                "mcp-scanner not found.\n" "Run: pip install cisco-ai-mcp-scanner"
            )
            return
        self._launch(exe, self._build_mcp_args(), self._build_mcp_env())

    def _launch(self, exe: str, args: list[str], env: dict[str, str]) -> None:
        from PyQt6.QtCore import QProcessEnvironment

        pe = QProcessEnvironment.systemEnvironment()
        for k, v in env.items():
            pe.insert(k, v)
        self._process.setProcessEnvironment(pe)

        self._process.start(exe, args)
        if not self._process.waitForStarted(3000):
            self.error.emit(f"Failed to start scanner: {self._process.errorString()}")

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
        creds = get_llm_creds(c, "scanner")
        env: dict[str, str] = {}
        env["SKILL_SCANNER_LLM_API_KEY"] = creds["api_key"] or "local"
        if creds["model"]:
            env["SKILL_SCANNER_LLM_MODEL"] = creds["model"]
        if creds["provider"]:
            env["SKILL_SCANNER_LLM_PROVIDER"] = creds["provider"]
        if creds["base_url"]:
            env["SKILL_SCANNER_LLM_BASE_URL"] = creds["base_url"]
            env["OPENAI_API_BASE"] = creds["base_url"]
        if c.get("virustotal_api_key"):
            env["VIRUSTOTAL_API_KEY"] = c["virustotal_api_key"]
        if c.get("ai_defense_api_key"):
            env["AI_DEFENSE_API_KEY"] = c["ai_defense_api_key"]
        return env

    def _build_mcp_args(self) -> list[str]:
        c = self._cfg
        analyzers = ["yara"]  # always included — offline, no key required
        if c.get("mcp_use_llm") and (
            get_llm_creds(c, "scanner")["api_key"]
            or get_llm_creds(c, "scanner")["is_local"]
        ):
            analyzers.append("llm")
        if c.get("mcp_use_api") and c.get("mcp_api_key"):
            analyzers.append("api")
        if c.get("use_virustotal") and c.get("virustotal_api_key"):
            analyzers.append("virustotal")
        return [
            "--analyzers",
            ",".join(analyzers),
            "--format",
            "raw",
            "static",
            "--tools",
            self._path,
        ]

    def _build_mcp_env(self) -> dict[str, str]:
        c = self._cfg
        creds = get_llm_creds(c, "scanner")
        env: dict[str, str] = {}
        env["MCP_SCANNER_LLM_API_KEY"] = creds["api_key"] or "local"
        if creds["model"]:
            env["MCP_SCANNER_LLM_MODEL"] = creds["model"]
        if creds["provider"]:
            env["MCP_SCANNER_LLM_PROVIDER"] = creds["provider"]
        if creds["base_url"]:
            env["MCP_SCANNER_LLM_BASE_URL"] = creds["base_url"]
            env["OPENAI_API_BASE"] = creds["base_url"]
        if c.get("mcp_api_key"):
            env["MCP_SCANNER_API_KEY"] = c["mcp_api_key"]
        if c.get("virustotal_api_key"):
            env["VIRUSTOTAL_API_KEY"] = c["virustotal_api_key"]
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

        raw_parsed = _extract_json(self._stdout_buf)
        if self._spec_type == SpecType.MCP_MANIFEST and isinstance(raw_parsed, dict):
            parsed = _normalize_mcp_result(raw_parsed)
        else:
            parsed = raw_parsed

        result = ScanResult(
            path=self._path,
            timestamp=datetime.now().isoformat(timespec="seconds"),
            returncode=self._exit_code,
            stdout=self._stdout_buf,
            stderr=self._stderr_buf,
            parsed=parsed,
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
