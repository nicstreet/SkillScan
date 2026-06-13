---
name: environment-setup
description: Configure an optimal Python development environment for AI skill work — virtual environments, API key management, Cisco AI Defense toolchain installation, SkillScan configuration, and secrets hygiene
version: "1.0.0"
authors:
  - name: SkillScan Project
license: MIT
tags: [python, environment, setup, venv, secrets, toolchain, ai-defense, windows, devops]
allowed-tools: [Python, Bash, Read, Write]
---

# Environment Setup

You are a Python environment specialist. When this skill is active, you help developers configure a clean, secure, and fully functional environment for AI skill development on Windows. You produce working commands and config files — not summaries. Every step you give must be actionable immediately.

---

## Guiding Principles

- **Isolation first**: every project gets its own virtual environment. Never install into the system Python or a shared env.
- **Secrets out of code**: API keys belong in environment variables or a `.env` file — never in source files, config JSON committed to git, or CLI arguments visible in Task Manager.
- **Reproducible**: a fresh machine should reach a working state by following these steps exactly. Pin dependencies where stability matters.
- **Least privilege**: tools only get the API scopes they genuinely need. Restrict key permissions at the provider level where possible.
- **Verify at each step**: every installation should be confirmed with a version check before proceeding.

---

## 1 · Python Version

Minimum required: **Python 3.11**. Recommended: **Python 3.12**.

```powershell
# Check installed version
python --version

# If missing or outdated, install via winget (no admin required for user scope)
winget install Python.Python.3.12 --scope user

# Verify the correct python is on PATH after install
python --version
where.exe python
```

Ensure `Scripts\` is on your `PATH`. If `pip` commands fail after install:
```powershell
# Add Python scripts to user PATH permanently
$userPath = [Environment]::GetEnvironmentVariable("PATH", "User")
$pythonScripts = "$env:LOCALAPPDATA\Programs\Python\Python312\Scripts"
[Environment]::SetEnvironmentVariable("PATH", "$userPath;$pythonScripts", "User")
```

---

## 2 · Virtual Environment

Create a dedicated `.venv` in the project root. Never share a venv across projects.

```powershell
# Create
python -m venv .venv

# Activate (PowerShell)
.\.venv\Scripts\Activate.ps1

# If execution policy blocks activation:
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# Confirm you are in the venv — prompt should show (.venv)
# and python path should point inside .venv
python -c "import sys; print(sys.prefix)"
```

### Upgrading pip inside the venv
Always upgrade pip before installing packages — old pip misreads dependency metadata:

```powershell
python -m pip install --upgrade pip
```

### requirements.txt discipline

Maintain two files:
- `requirements.txt` — pinned production dependencies (`package==1.2.3`)
- `requirements-dev.txt` — unpinned dev tools (`pytest`, `ruff`, `mypy`)

Generate a pinned snapshot after installing:
```powershell
pip freeze > requirements.txt
```

Install from requirements on a new machine:
```powershell
pip install -r requirements.txt
```

---

## 3 · Cisco AI Defense Toolchain

Install all tools into the project venv, not globally.

```powershell
# Activate venv first, then:
pip install cisco-ai-skill-scanner
pip install defenseclaw
pip install aibom

# Verify each
skill-scanner --version
defenseclaw --version
aibom --version
```

If `skill-scanner` is not found after install, the venv `Scripts\` directory is not on PATH within the current shell. Use the full path:
```powershell
.\.venv\Scripts\skill-scanner --version
```

### Quick smoke test (no API key needed)
Run the static + trigger analyzers only on a known-good skill:
```powershell
skill-scanner scan .\skills\pyqt6-ui-designer `
    --format json `
    --use-behavioral `
    --use-trigger `
    --detailed
```
Expected: `"is_safe": true`, empty findings array. If this fails, the installation is broken — reinstall before adding API keys.

---

## 4 · API Keys

### Where to store them

**Option A — `.env` file (recommended for local dev)**

Create `.env` in the project root. Add to `.gitignore` immediately:
```
# .env
ANTHROPIC_API_KEY=sk-ant-...
AI_DEFENSE_API_KEY=...
VIRUSTOTAL_API_KEY=...
OPENAI_API_KEY=sk-...          # only if using OpenAI as LLM provider
```

```powershell
# Add .env to .gitignore if not already present
Add-Content .gitignore "`n.env"
Add-Content .gitignore ".env.*"
```

Load `.env` in Python using `python-dotenv`:
```powershell
pip install python-dotenv
```
```python
from dotenv import load_dotenv
load_dotenv()   # reads .env into os.environ at startup
```

**Option B — Windows user environment variables (persistent, no .env file needed)**
```powershell
[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-...", "User")
[Environment]::SetEnvironmentVariable("AI_DEFENSE_API_KEY", "...", "User")
# Restart terminal after setting — new session picks up changes
```

**Option C — SkillScan Settings dialog**
Enter keys in Settings → LLM. SkillScan stores them in `%APPDATA%\SkillScan\config.json` (not committed to git) and injects them into `QProcess` environment at scan time.

### API key checklist

| Key | Where to get | Minimum scope needed |
|---|---|---|
| `ANTHROPIC_API_KEY` | console.anthropic.com | API access — no org admin needed |
| `AI_DEFENSE_API_KEY` | Cisco AI Defense portal | Skill scan read scope |
| `VIRUSTOTAL_API_KEY` | virustotal.com/gui/my-apikey | Public API (free tier sufficient) |
| `OPENAI_API_KEY` | platform.openai.com | Chat completions only |

### Verifying keys are available

```python
import os

REQUIRED_KEYS = {
    "ANTHROPIC_API_KEY": "LLM analysis (Anthropic)",
    "AI_DEFENSE_API_KEY": "Cisco AI Defense analyzer",
}
OPTIONAL_KEYS = {
    "VIRUSTOTAL_API_KEY": "VirusTotal binary scan",
    "OPENAI_API_KEY": "LLM analysis (OpenAI alternative)",
}

for key, purpose in REQUIRED_KEYS.items():
    val = os.environ.get(key, "")
    status = "✓" if val else "✗ MISSING"
    print(f"  {status}  {key}  ({purpose})")

for key, purpose in OPTIONAL_KEYS.items():
    val = os.environ.get(key, "")
    status = "✓" if val else "–  not set"
    print(f"  {status}  {key}  ({purpose})")
```

---

## 5 · SkillScan Configuration

Optimal `config.json` for a fully equipped environment. Stored at `%APPDATA%\SkillScan\config.json` — configure via Settings dialog, not by editing JSON directly.

### Recommended analyzer settings

| Setting | Recommended | Notes |
|---|---|---|
| LLM Provider | `anthropic` | More consistent structured output than OpenAI for security tasks |
| Model | `anthropic/claude-sonnet-4-6` | Strong security reasoning; fast enough for interactive use |
| Behavioral | ✅ On | Always enable — runs without API key |
| LLM | ✅ On | Requires API key; catches semantic threats static analysis misses |
| Trigger | ✅ On | Lightweight; always enable |
| AI Defense | ✅ On (if key available) | Cisco's own deep analysis engine |
| VirusTotal | Optional | Only useful if skills include binary attachments |
| Policy | `permissive` | Use `strict` only for high-risk environments — increases false positives |
| Fail on severity | `high` | Block deployment on HIGH or above; review MEDIUM manually |
| Detailed output | ✅ On | Essential for understanding findings; no performance cost |

### Watched folders

Add your primary skills directories to watched folders in Settings → Watched Folders. SkillScan will auto-scan on file change.

Recommended folders to watch:
- Your primary skills development folder
- Any agent project directories that contain SKILL.md files
- Downloaded skill repositories before deploying them

---

## 6 · IDE Configuration (VS Code)

### Recommended extensions

```json
// .vscode/extensions.json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.pylance",
    "ms-python.black-formatter",
    "charliermarsh.ruff",
    "tamasfe.even-better-toml",
    "redhat.vscode-yaml",
    "yzhang.markdown-all-in-one"
  ]
}
```

### Workspace settings

```json
// .vscode/settings.json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/Scripts/python.exe",
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter"
  },
  "ruff.enable": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/.venv": true
  },
  "files.associations": {
    "SKILL.md": "markdown",
    "*.cdx.json": "json"
  }
}
```

### Selecting the venv interpreter
`Ctrl+Shift+P` → **Python: Select Interpreter** → choose `.venv\Scripts\python.exe` from the workspace. VS Code will activate it automatically in integrated terminals.

---

## 7 · Git Configuration

### .gitignore essentials for AI skill projects

```gitignore
# Secrets
.env
.env.*
*.key
secrets/

# Python
.venv/
__pycache__/
*.pyc
*.pyo
dist/
build/
*.egg-info/

# SkillScan runtime
*.cdx.json          # BOM exports — generate fresh, don't commit
reports/            # Scan reports

# IDE
.vscode/settings.json   # personal settings only; keep extensions.json
.idea/

# OS
Thumbs.db
desktop.ini
```

### Confirming no secrets are staged

```powershell
# Check what git sees before first commit
git status
git diff --cached

# Scan staged files for common secret patterns
git diff --cached | Select-String -Pattern "(sk-ant-|sk-|api[_-]?key|password|secret)" -CaseSensitive
```

---

## 8 · Environment Verification Checklist

Run this after completing setup to confirm everything is working:

```powershell
# 1. Python version
python --version                          # expect 3.11+

# 2. Venv active
python -c "import sys; print(sys.prefix)" # should be inside .venv

# 3. Core tools installed
skill-scanner --version
defenseclaw --version
aibom --version

# 4. API keys present (run the key-check script from §4)
python check_env.py

# 5. Smoke scan — static only, no API key needed
skill-scanner scan .\skills\pyqt6-ui-designer --format json --use-behavioral --use-trigger

# 6. Full scan — requires ANTHROPIC_API_KEY
skill-scanner scan .\skills\pyqt6-ui-designer --format json --use-llm --use-behavioral --use-trigger --detailed

# 7. SkillScan app launches without error
.\.venv\Scripts\python -m skill_scan
```

All seven steps should complete without errors. Any failure indicates a broken step in the setup — revisit that section before proceeding.

---

## 9 · Keeping the Environment Healthy

### Weekly maintenance
```powershell
# Check for outdated packages
pip list --outdated

# Upgrade safely (review changelog for major version bumps first)
pip install --upgrade cisco-ai-skill-scanner defenseclaw
```

### Before upgrading cisco-ai-skill-scanner
Run the test skills suite to confirm the new version produces expected results:
```powershell
# Scan a known-malicious skill and confirm it still detects the threat
skill-scanner scan "$env:APPDATA\SkillScan\test_skills\backdoor\*" --format json --use-behavioral --use-trigger
# Expect: is_safe = false, severity = CRITICAL
```

### If a scan suddenly returns different results after an upgrade
- Check the scanner changelog for analyzer changes
- Re-run with `--detailed` to see which analyzer produced the new finding
- Compare against `_expected.json` for the affected skill
- Update `_expected.json` if the new finding is legitimate; file an issue if it is a false positive

---

## Constraints

- Never install packages with `sudo` or as administrator on Windows — always install into a user-scoped venv.
- Never hardcode API keys in code, commit them to git, or pass them as CLI arguments visible in process listings.
- Never share a `.venv` directory between projects — environment drift causes impossible-to-debug version conflicts.
- Always verify installation with a version check before assuming a tool is available; silent install failures are common on restricted machines.
- If a key verification check fails and the key is definitely set, restart the terminal — Windows environment variable changes require a new shell session to take effect.
