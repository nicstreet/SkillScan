# SkillScan

**AI Skill Security Environment** — scan, audit, and govern every AI skill, MCP manifest, and A2A agent card on your machine.

SkillScan wraps the [Cisco AI Skill Scanner](https://github.com/cisco-ai-defense/cisco-ai-skill-scanner) CLI with a Windows-native PyQt6 interface — system tray for reactive scanning, full-window environment coming in v2.

![SkillScan — Folders view showing skill tile grid with severity ratings](.claude/architecture/assets/screenshot.png)

---

## What It Does

AI skills (the instruction files that tell LLM agents what to do and what tools they can use) can contain malicious payloads: prompt injection, exfiltration instructions, or capability escalation. SkillScan surfaces these risks before a skill gets near a live agent.

Scan a skill folder and get:
- **Severity rating** — CLEAN / MEDIUM / HIGH / CRITICAL
- **Structured findings** — category, description, line reference, remediation advice
- **LLM-powered analysis** — deep reasoning via Anthropic Claude, OpenAI, or any LiteLLM-compatible model

---

## v1.0.0 Features

### Scanning
- Scan any skill folder via the tray menu or folder picker
- Scan clipboard content as a skill (configurable min-chars threshold)
- Drag a skill folder onto the taskbar strip to scan instantly
- Automatic re-scan when watched folders change (watchdog with 5s debounce)

### Analyzers
- `cisco-ai-skill-scanner` — static analysis + trigger detection
- LLM analyzer — configurable provider (Anthropic, OpenAI, Groq, etc.)
- Behavioral pattern matching
- VirusTotal hash lookup (optional)
- Trigger detection

### Results
- Live output streaming during scan
- Structured HTML findings report — severity badges, findings table, remediation
- Raw output toggle for full scanner output
- Last 100 results persisted at `%APPDATA%\SkillScan\results.json`

### Windows integration
- System tray icon with right-click scan menu
- Taskbar drop strip — 6px accent bar, expands to 56px on drag-enter
- Animated pill toggle switches for feature toggles
- Optional HKCU Explorer right-click context menu (no admin required)

### Background
- Clipboard auto-scan (QTimer poller, MD5 deduplication)
- Folder watcher (watchdog Observer, silent re-scan, tray notification)

### Settings
- LLM provider, model, and API key
- Analyzer toggles (behavioral, LLM, AI Defense, VirusTotal, trigger)
- Clipboard watch interval and min-chars threshold
- Watched folder management
- Built-in testing guide for verifying the installation

---

## Requirements

- Windows 10/11
- Python 3.11+
- [`cisco-ai-skill-scanner`](https://github.com/cisco-ai-defense/cisco-ai-skill-scanner) CLI installed
- At least one LLM API key (Anthropic recommended)

### Install dependencies

```powershell
python -m venv .venv
.venv\Scripts\pip install PyQt6 watchdog pywin32
```

### Run

```powershell
.venv\Scripts\python -m skill_scan
```

Or use the included launchers:

```powershell
.\run.ps1   # PowerShell
run.bat     # Command Prompt
```

---

## Skills Library

SkillScan ships with four reference skills in `skills/`. Each skill is a `SKILL.md` + `_expected.json` pair — scan them to verify your setup is working correctly.

| Skill | Description |
|---|---|
| `pyqt6-ui-designer` | PyQt6 UI engineering patterns — frameless windows, palette, layouts, threading |
| `color-palette-builder` | Generate a `_palette.py` from a single base colour with WCAG contrast checks |
| `cisco-ai-defense-integrator` | Integrate skill-scanner, DefenseClaw, AI BOM, and agentskills.io validation |
| `environment-setup` | Optimal Python + AI dev environment — venv, API keys, toolchain, secrets hygiene |

---

## Configuration

Settings are stored at `%APPDATA%\SkillScan\config.json` — never in the repo. Open **Settings** from the tray menu to configure API keys and analyzer options.

API keys are injected into the scanner via process environment — never passed as CLI arguments, never logged.

---

## Coming in v1.1 — The Skill Security Environment

v2 transforms SkillScan from a tray utility into a full windowed application:

**Phase 1 — Main Window Shell**
Frameless PyQt6 window with nav rail, `QStackedWidget` views, and tray demoted to satellite. Migrates Testing, Settings, and About into nav-accessible views.

**Phase 2 — SQLite + Skill Discovery**
SQLAlchemy schema (folders, skills, scan_results, bom_snapshots). Auto-discovery walks watched folders on startup; SHA-256 hashing auto-revokes trust on file change.

**Phase 3 — Folders View + Skill Tile Grid**
Primary view: folder list pane + skill tile grid with severity badge borders, trust badges, and per-tile right-click scan actions.

**Phase 4 — Skill Detail View**
Deep-dive per skill: spec compliance score, full scan report, history sparkline, trust workflow (sign off on clean scan; hash invalidates on file change).

Further phases cover Skill Creator (Phase 5), DefenseClaw integration (Phase 6), MCP + A2A file type support (Phase 7), AI BOM generation and export (Phase 8), agentskills.io spec compliance (Phase 9), Registry Browser + Trust Store (Phase 10), and batch reports + scheduling + policy profiles (Phase 11).

Full roadmap: [.claude/architecture/development.md](.claude/architecture/development.md)
Architecture: [.claude/architecture/architecture.md](.claude/architecture/architecture.md)

---

## Documentation

| Document | Contents |
|---|---|
| [.claude/architecture/architecture.md](.claude/architecture/architecture.md) | v2 windowed app — full component architecture, DB schema, integration design |
| [.claude/architecture/development.md](.claude/architecture/development.md) | v2 roadmap — 11 phases, skills library, what carries forward from v1 |

---

## License

MIT
