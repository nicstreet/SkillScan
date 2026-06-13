---
name: cisco-ai-defense-integrator
description: Integrate Cisco AI Defense security components into Python projects — cisco-ai-skill-scanner, DefenseClaw, AI BOM generation (CycloneDX), and agentskills.io spec compliance validation
version: "1.0.0"
authors:
  - name: SkillScan Project
license: MIT
tags: [security, cisco, ai-defense, skill-scanner, defenseclaw, aibom, cyclonedx, devsecops, python]
allowed-tools: [Python, Bash, Read, Write, Edit]
---

# Cisco AI Defense Integrator

You are a security engineer specialising in AI supply chain security using the Cisco AI Defense toolchain. When this skill is active, you integrate, configure, and interpret the Cisco AI Defense suite of tools accurately and safely. You follow the principle of least privilege: tools should only be granted the access they genuinely need.

---

## Toolchain Overview

| Tool | Purpose | Install |
|---|---|---|
| `cisco-ai-skill-scanner` | Static + LLM + behavioral analysis of SKILL.md files | `pip install cisco-ai-skill-scanner` |
| `DefenseClaw` | Deep AI component analysis — prompt injection, exfiltration, autonomy abuse | `pip install defenseclaw` |
| `aibom` | AI Bill of Materials generation (CycloneDX 1.6) | `pip install aibom` |
| agentskills.io spec | JSON Schema for validating SKILL.md metadata completeness | Schema at `https://agentskills.io/specification` |

All tools should be installed in the same virtual environment as the host application. Never install globally.

---

## cisco-ai-skill-scanner

### Installation and version check

```bash
pip install cisco-ai-skill-scanner
skill-scanner --version
```

### Basic scan

```bash
skill-scanner scan <path-to-skill-folder> --format json
```

`<path-to-skill-folder>` must be a directory containing a `SKILL.md` file. The scanner inspects all files in the directory.

### Full analyzer flags

```bash
skill-scanner scan <path> \
  --format json \
  --use-llm \
  --use-behavioral \
  --use-trigger \
  --use-aidefense \
  --use-virustotal \
  --detailed \
  --policy permissive \
  --fail-on-severity high
```

| Flag | Description | Requires |
|---|---|---|
| `--use-llm` | LLM-based semantic analysis | `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` env var |
| `--use-behavioral` | Heuristic behavioural pattern matching | Nothing |
| `--use-trigger` | Explicit trigger / payload detection | Nothing |
| `--use-aidefense` | Cisco AI Defense API analysis | `AI_DEFENSE_API_KEY` env var |
| `--use-virustotal` | VirusTotal hash lookup for attached binaries | `VT_API_KEY` env var |
| `--detailed` | Include full description and remediation in output | Nothing |
| `--policy` | `permissive` (default) or `strict` | Nothing |
| `--fail-on-severity` | Exit non-zero if any finding meets or exceeds level | Nothing |

### Injecting API keys safely

Always inject secrets via environment variables, never as CLI arguments:

```python
import os
from PyQt6.QtCore import QProcess, QProcessEnvironment

env = QProcessEnvironment.systemEnvironment()
env.insert("ANTHROPIC_API_KEY", cfg.get("llm_api_key", ""))
env.insert("AI_DEFENSE_API_KEY", cfg.get("ai_defense_api_key", ""))
proc.setProcessEnvironment(env)
```

### Parsing JSON output

The scanner outputs a JSON object to stdout. Mixed output (e.g. LiteLLM progress lines before JSON) requires extraction:

```python
import json

def extract_json(text: str) -> dict | None:
    decoder = json.JSONDecoder()
    for i, ch in enumerate(text):
        if ch in ('{', '['):
            try:
                obj, _ = decoder.raw_decode(text, i)
                if isinstance(obj, dict) and ("is_safe" in obj or "findings" in obj):
                    return obj
            except json.JSONDecodeError:
                continue
    return None
```

### Output schema

```json
{
  "skill_name": "my-skill",
  "is_safe": false,
  "max_severity": "HIGH",
  "findings": [
    {
      "category": "data_exfiltration",
      "severity": "HIGH",
      "title": "HTTP POST to external endpoint",
      "description": "...",
      "remediation": "...",
      "analyzer": "behavioral",
      "line": 42
    }
  ],
  "analyzers_run": ["behavioral", "llm", "trigger"],
  "scan_duration_ms": 3420
}
```

---

## DefenseClaw

### Installation

```bash
pip install defenseclaw
defenseclaw --version
```

### Basic scan

```bash
defenseclaw scan <path> --format json
```

DefenseClaw performs deeper semantic analysis than `skill-scanner` and is particularly effective at detecting:
- Indirect prompt injection embedded in tool descriptions
- Exfiltration channels hidden in benign-looking instructions
- Autonomy abuse patterns (self-modification, persistence mechanisms)
- Capability escalation attempts

### Running alongside cisco-ai-skill-scanner

Run both tools on the same skill directory and merge findings. Tag each finding with its source:

```python
def run_defenseclaw(path: str, env: dict) -> list[dict]:
    import subprocess, json
    result = subprocess.run(
        ["defenseclaw", "scan", path, "--format", "json"],
        capture_output=True, text=True,
        env={**os.environ, **env}
    )
    if result.returncode not in (0, 1):  # 1 = findings detected (not an error)
        return []
    try:
        data = json.loads(result.stdout)
        findings = data.get("findings", [])
        for f in findings:
            f["source"] = "defenseclaw"
        return findings
    except json.JSONDecodeError:
        return []
```

### Deduplication when merging

Two findings from different analyzers are considered duplicates if they share the same `(category, line)` within a tolerance of ±2 lines. Keep the higher-severity finding; discard the lower:

```python
def merge_findings(a: list[dict], b: list[dict]) -> list[dict]:
    SEV = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    merged = {(f["category"], f.get("line", 0)): f for f in a}
    for f in b:
        key = (f["category"], f.get("line", 0))
        existing = merged.get(key)
        if not existing or SEV.get(f["severity"], 0) > SEV.get(existing["severity"], 0):
            merged[key] = f
    return list(merged.values())
```

---

## AI BOM Generation (CycloneDX)

### What is an AI BOM?

An AI Bill of Materials is a machine-readable inventory of every AI component in a system — skills, models, datasets, plugins, agent cards. It is the AI equivalent of a Software BOM (SBOM) and uses the CycloneDX 1.6 ML BOM extension.

An AI BOM answers: *what AI components do we have, where did they come from, and what is their risk classification?*

### Using the aibom tool

```bash
# Generate BOM for a skill directory
aibom generate <path> --format cyclonedx-json --output bom.cdx.json

# Generate for multiple directories
aibom generate <path1> <path2> --format cyclonedx-json --output org-bom.cdx.json
```

### Building CycloneDX BOM programmatically

When `aibom` is not available or custom metadata enrichment is needed, build the document directly:

```python
import json
from datetime import datetime, timezone

def build_cyclonedx_bom(components: list[dict]) -> dict:
    """
    components: list of dicts with keys:
      name, version, description, authors, license,
      spec_type (skill|mcp|a2a), scan_severity, scan_timestamp,
      trusted (bool), spec_score (int 0-100), file_hash
    """
    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "version": 1,
        "serialNumber": f"urn:uuid:{_new_uuid()}",
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tools": [{"name": "SkillScan", "version": "2.0.0"}],
        },
        "components": [_make_component(c) for c in components],
    }

def _make_component(c: dict) -> dict:
    return {
        "type": "machine-learning-model",
        "bom-ref": c["name"],
        "name": c["name"],
        "version": c.get("version", ""),
        "description": c.get("description", ""),
        "authors": [{"name": a} for a in c.get("authors", [])],
        "licenses": [{"license": {"id": c["license"]}}] if c.get("license") else [],
        "hashes": [{"alg": "SHA-256", "content": c["file_hash"]}] if c.get("file_hash") else [],
        "properties": [
            {"name": "skillscan:spec_type",       "value": c.get("spec_type", "skill")},
            {"name": "skillscan:scan_severity",   "value": c.get("scan_severity", "unknown")},
            {"name": "skillscan:scan_timestamp",  "value": c.get("scan_timestamp", "")},
            {"name": "skillscan:trusted",         "value": str(c.get("trusted", False)).lower()},
            {"name": "skillscan:spec_score",      "value": str(c.get("spec_score", 0))},
        ],
    }
```

### Exporting

```python
bom = build_cyclonedx_bom(skill_components)
path = f"SkillScan-BOM-{datetime.now().strftime('%Y%m%d')}.cdx.json"
with open(path, "w", encoding="utf-8") as f:
    json.dump(bom, f, indent=2)
```

---

## agentskills.io Spec Validation

The agentskills.io specification defines the required and optional fields for a valid SKILL.md frontmatter. Validate before publishing or deploying a skill.

### Required fields

| Field | Type | Description |
|---|---|---|
| `name` | string | Unique kebab-case identifier |
| `description` | string | One-sentence description of what the skill does |
| `version` | string | Semantic version (e.g. `"1.0.0"`) |
| `license` | string | SPDX license identifier (e.g. `"MIT"`, `"Apache-2.0"`) |
| `allowed-tools` | list | Tools the skill may invoke |

### Recommended fields

| Field | Description |
|---|---|
| `authors` | List of `{name: string}` objects |
| `tags` | List of strings for categorisation |
| `schema_version` | Version of the SKILL.md spec being followed |

### Python validation

```python
import yaml, re
from pathlib import Path

REQUIRED = {"name", "description", "version", "license", "allowed-tools"}
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

def validate_skill(skill_path: Path) -> dict:
    text = (skill_path / "SKILL.md").read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {"score": 0, "missing": list(REQUIRED), "warnings": ["No YAML frontmatter found"]}

    _, fm_raw, _ = text.split("---", 2)
    meta = yaml.safe_load(fm_raw) or {}

    missing = [f for f in REQUIRED if f not in meta]
    warnings = []

    if meta.get("version") and not SEMVER_RE.match(str(meta["version"])):
        warnings.append("version should follow semver (MAJOR.MINOR.PATCH)")
    if not meta.get("authors"):
        warnings.append("authors field is recommended")
    if not meta.get("tags"):
        warnings.append("tags field aids discoverability")
    if len(meta.get("description", "")) > 200:
        warnings.append("description should be under 200 characters")

    score = 100 - (len(missing) * 10) - (len(warnings) * 3)
    return {"score": max(0, score), "missing": missing, "warnings": warnings}
```

---

## CI/CD Integration

### GitHub Actions workflow

```yaml
# .github/workflows/skill-scan.yml
name: Skill Security Scan
on:
  pull_request:
    paths: ["skills/**"]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with: { python-version: "3.12" }

      - name: Install scanners
        run: pip install cisco-ai-skill-scanner defenseclaw

      - name: Scan all changed skills
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          for dir in skills/*/; do
            echo "Scanning $dir"
            skill-scanner scan "$dir" \
              --format json \
              --use-llm \
              --use-behavioral \
              --use-trigger \
              --fail-on-severity high \
              --detailed
          done

      - name: Generate AI BOM
        run: aibom generate skills/ --format cyclonedx-json --output ai-bom.cdx.json

      - name: Upload BOM artifact
        uses: actions/upload-artifact@v4
        with:
          name: ai-bom
          path: ai-bom.cdx.json
```

---

## Interpreting Results

### Severity levels

| Level | Meaning | Action |
|---|---|---|
| `CLEAN` | No findings | Safe to deploy |
| `LOW` | Minor style or policy issues | Review before production |
| `MEDIUM` | Elevated risk — potential misuse | Investigate and remediate |
| `HIGH` | Significant threat — do not deploy without review | Block deployment |
| `CRITICAL` | Confirmed malicious payload | Reject and quarantine |

### Finding categories

| Category | Description |
|---|---|
| `data_exfiltration` | Instructions to send data to external endpoints |
| `prompt_injection` | Payloads designed to override system instructions |
| `autonomy_abuse` | Self-modification, persistence, or unsanctioned delegation |
| `credential_theft` | Collection of API keys, tokens, or passwords |
| `tool_chaining_abuse` | Exploiting tool composition to exceed granted permissions |
| `capability_escalation` | Requesting more permissions than declared |
| `obfuscation` | Encoding or hiding instructions to evade analysis |
| `policy_violation` | Undeclared data collection or tool use |
| `unauthorized_tool_use` | Using tools not listed in `allowed-tools` |

### Remediation workflow

1. Read the `remediation` field on each finding — the scanner provides specific guidance.
2. Address `CRITICAL` and `HIGH` findings first.
3. For `LLM_ANALYSIS_FAILED` pseudo-findings: the LLM could not analyse the skill (API key missing or malformed output). Re-run with `--use-llm` and a valid key.
4. After remediation, re-run the full scan to confirm findings are resolved.
5. Only grant Trust status after a clean re-scan confirms zero findings.

---

## Constraints

- Never disable security analyzers without a documented reason. The minimum acceptable scan is `--use-behavioral --use-trigger`.
- Never commit API keys to source control. Always use environment variables or a secrets manager.
- Never mark a skill as trusted if the scan returned findings, even LOW severity.
- Do not run `skill-scanner` or `defenseclaw` on network paths or untrusted shares — scan local copies only.
- If `is_safe` is `false` in scanner output, the skill must not be deployed regardless of `max_severity` — some scanners return `is_safe: false` even when individual findings appear low severity due to combination risk.
- AI BOM snapshots are point-in-time documents. Regenerate after any skill modification.
