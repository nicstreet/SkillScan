"""Download and manage the cisco-ai-defense/skill-scanner eval test skills."""

import io
import json
import os
import shutil
import subprocess
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

_APPDATA = Path(os.environ.get("APPDATA", "~"))
TEST_SKILLS_DIR = _APPDATA / "SkillScan" / "test_skills"

# Bundled MCP manifest eval fixtures (ships with the package in skills/mcp-evals/)
MCP_EVALS_DIR = Path(__file__).parent.parent.parent / "skills" / "mcp-evals"

_ZIP_URL = (
    "https://github.com/cisco-ai-defense/skill-scanner/archive/refs/heads/main.zip"
)
_INNER_PREFIX = "skill-scanner-main/evals/skills/"


def is_downloaded() -> bool:
    return TEST_SKILLS_DIR.exists() and any(TEST_SKILLS_DIR.iterdir())


def skill_count() -> int:
    if not is_downloaded():
        return 0
    return sum(1 for p in TEST_SKILLS_DIR.iterdir() if p.is_dir())


def open_folder() -> None:
    subprocess.Popen(["explorer", str(TEST_SKILLS_DIR)])


def open_guide() -> None:
    guide = TEST_SKILLS_DIR / "GUIDE.md"
    if guide.exists():
        subprocess.Popen(["notepad.exe", str(guide)])


# ── MCP eval fixtures ────────────────────────────────────────────────────────


@dataclass
class McpEval:
    name: str
    path: Path  # path to the manifest JSON file
    expected_safe: bool
    expected_severity: str  # CLEAN / MEDIUM / HIGH / CRITICAL
    notes: str


def mcp_eval_list() -> list[McpEval]:
    """Return all MCP eval fixtures from the bundled skills/mcp-evals/ directory."""
    if not MCP_EVALS_DIR.exists():
        return []
    evals: list[McpEval] = []
    for d in sorted(MCP_EVALS_DIR.iterdir()):
        if not d.is_dir():
            continue
        json_file: Path | None = None
        for fname in ("mcp.json", "agent.json", "manifest.json"):
            candidate = d / fname
            if candidate.exists():
                json_file = candidate
                break
        if json_file is None:
            continue
        expected_file = d / "_expected.json"
        if not expected_file.exists():
            continue
        try:
            exp = json.loads(expected_file.read_text(encoding="utf-8"))
        except Exception:
            continue
        evals.append(
            McpEval(
                name=d.name,
                path=json_file,
                expected_safe=exp.get("expected_safe", True),
                expected_severity=exp.get("expected_severity", "CLEAN"),
                notes=exp.get("notes", ""),
            )
        )
    return evals


def mcp_eval_count() -> int:
    return len(mcp_eval_list())


def open_mcp_evals_folder() -> None:
    subprocess.Popen(["explorer", str(MCP_EVALS_DIR)])


class DownloadThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, str)  # success, message

    def run(self):
        try:
            self.progress.emit("Connecting to GitHub…")
            req = urllib.request.Request(
                _ZIP_URL,
                headers={"User-Agent": "SkillScan/1.0"},
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                self.progress.emit("Downloading archive…")
                data = resp.read()

            self.progress.emit("Extracting eval skills…")
            if TEST_SKILLS_DIR.exists():
                shutil.rmtree(TEST_SKILLS_DIR)
            TEST_SKILLS_DIR.mkdir(parents=True, exist_ok=True)

            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                skill_files = [
                    n
                    for n in zf.namelist()
                    if n.startswith(_INNER_PREFIX) and not n.endswith("/")
                ]
                for name in skill_files:
                    rel = name[len(_INNER_PREFIX) :]
                    if not rel:
                        continue
                    dest = TEST_SKILLS_DIR / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(zf.read(name))

            _write_guide()
            count = skill_count()
            self.finished.emit(
                True, f"Downloaded {count} skill{'s' if count != 1 else ''}."
            )
        except Exception as exc:
            self.finished.emit(False, str(exc))


def _write_guide() -> None:
    (TEST_SKILLS_DIR / "GUIDE.md").write_text(_GUIDE_CONTENT, encoding="utf-8")


_GUIDE_CONTENT = """\
# SkillScan — Testing Guide

Test skills sourced from [cisco-ai-defense/skill-scanner](https://github.com/cisco-ai-defense/skill-scanner)
(Apache 2.0) © 2026 Cisco Systems, Inc.

---

## About the Test Skills

Each subfolder here is a self-contained AI skill.  Every skill ships with an
`_expected.json` file that describes the ground-truth result:

```json
{
  "name": "example-skill",
  "safe": false,
  "severity": "high",
  "findings": [
    { "category": "prompt_injection", "severity": "high", "description": "…" }
  ]
}
```

- `"safe": true`  — scan should complete clean (no findings)
- `"safe": false` — scan should produce findings at the stated severity

Use `_expected.json` to verify the scanner fired correctly after each test below.

---

## 1 · Manual Folder Scan (tray menu)

**Tests:** right-click tray → Scan Skill Folder…

1. Right-click the SkillScan tray icon.
2. Choose **Scan Skill Folder…**
3. Navigate to this folder and select any skill subfolder.
4. The scan progress dialog opens and streams live output.
5. When complete, a tray notification shows the severity label.
6. Compare the severity against the skill's `_expected.json`.

**Try first:** pick a skill whose `"safe": false` to confirm findings are detected,
then pick one with `"safe": true` to confirm a clean result.

---

## 2 · Drag & Drop (taskbar dock)

**Tests:** Drop Zone toggle + TaskbarDock

1. Right-click the tray icon → enable **Drop Zone** in the Features section.
2. A thin accent-coloured strip appears flush against the Windows taskbar.
3. Open File Explorer, navigate to this folder.
4. Drag any skill subfolder onto the strip — it expands and shows "Drop Skill Folder".
5. Release — scan starts immediately.
6. Tray notification confirms completion.

---

## 3 · Clipboard Scan (manual)

**Tests:** tray menu → Scan Clipboard

1. Open any `SKILL.md` inside a skill subfolder with Notepad.
2. Select all (Ctrl+A) and copy (Ctrl+C).
3. Right-click the tray icon → **Scan Clipboard**.
4. SkillScan writes the clipboard text to a temporary `SKILL.md` and scans it.
5. A tray notification confirms the scan ran.

> **Tip:** choose a malicious skill's `SKILL.md` to see findings; choose a safe
> one to confirm a clean result.

---

## 4 · Background Clipboard Monitor

**Tests:** Clipboard Auto-Scan toggle + ClipboardWatcher

1. Open **Settings → Clipboard**.
2. Enable **Automatic clipboard scanning**.
3. Set **Minimum characters** to a low value (e.g. 50) so short skill files trigger it.
4. Set **Check interval** to 10 seconds for a quick test.
5. Save and enable the **Clipboard Auto-Scan** toggle in the tray menu.
6. Open a malicious skill's `SKILL.md` in Notepad, select all, copy.
7. Wait up to 10 seconds — a silent background scan fires.
8. Tray notification shows the result (no progress dialog — silent mode).
9. Restore the interval and min-chars settings when done.

---

## 5 · Folder Watching

**Tests:** Folder Watching toggle + FolderWatcher + watchdog

1. Open **Settings → Watched Folders**.
2. Click **Add Folder…** and select any skill subfolder from this directory.
3. Save and enable the **Folder Watching** toggle in the tray menu.
4. Open any file inside that skill folder (e.g. `SKILL.md`) in Notepad.
5. Add a space anywhere, save the file.
6. Within 5 seconds SkillScan detects the change and auto-scans the skill.
7. Tray notification: "Auto-scanning — Change detected in `<skill-name>`".
8. Remove the watched folder from Settings when done.

---

## 6 · Results Window

**Tests:** result_store persistence + ResultsWindow

1. Run several scans using any of the methods above.
2. Double-click the tray icon (or right-click → **View Results**).
3. The Results window shows all past scans with path, severity, and timestamp.
4. Results persist between app restarts (stored in `%APPDATA%\\SkillScan\\results.json`).

---

## Severity Reference

| Label    | Meaning                                      |
|----------|----------------------------------------------|
| clean    | No findings — skill passed all checks        |
| low      | Minor issues; unlikely to cause harm         |
| medium   | Moderate risk; review recommended            |
| high     | Significant threat; do not deploy            |
| critical | Severe / confirmed malicious payload         |
| unknown  | Scanner returned no parseable JSON output    |

---

## Troubleshooting

**Scanner not found** — ensure `cisco-ai-skill-scanner` is installed in the same
venv as SkillScan: `.venv\\Scripts\\pip install cisco-ai-skill-scanner`

**Clean result on a malicious skill** — check Settings → Analyzers; the LLM and
behavioral analyzers need an API key configured to detect some threat categories.
The static analyzer runs without a key and catches a broad range of issues.

**No tray notification** — Windows Focus Assist may be suppressing notifications.
Check Action Centre (Win+A) for queued messages.

---

## 7 · MCP Manifest Evals

**Tests:** router type detection for MCP manifests

Four sample MCP manifest JSON files ship bundled with SkillScan in `skills/mcp-evals/`.
These test that the scanner correctly identifies and labels MCP server definitions.

Each subfolder contains a `mcp.json` manifest and an `_expected.json` ground-truth file:

```json
{
  "name": "...",
  "expected_safe": false,
  "expected_severity": "CRITICAL",
  "expected_type": "mcp",
  "expected_findings": [
    { "category": "prompt_injection", "severity": "critical", "description": "..." }
  ],
  "notes": "..."
}
```

### Bundled eval manifests

| Folder | Expected severity | Pattern tested |
|--------|-------------------|----------------|
| `clean-calculator-mcp` | CLEAN | Four arithmetic tools — no suspicious instructions |
| `suspicious-unrestricted-fs-mcp` | MEDIUM | Advertises unrestricted filesystem access with no path scoping |
| `malicious-data-exfil-mcp` | HIGH | Tool description covertly instructs credential file upload |
| `malicious-prompt-injection-mcp` | CRITICAL | Full SYSTEM OVERRIDE injection with credential harvest directive |

### Running the MCP detection eval

1. Open **Testing → MCP Manifest Evals** in the SkillScan UI.
2. Click **Detect All** — each manifest is passed through the router.
3. A ✓ confirms the file was identified as `MCP_MANIFEST` type.
4. Compare the expected severity badge against your scanner output when Phase 7 (MCP scanning) is available.

> **Note:** Full LLM-based severity analysis for MCP manifests is planned for Phase 7.
> Detection testing (router labelling) is available now.
"""
