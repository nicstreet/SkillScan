# SkillScan — TODO

> Canonical roadmap: `docs/DevelopmentV2.md`  
> This file is a quick-reference view of all outstanding work.  
> Last updated: 2026-06-13

---

## Known Fixes (do first)

These are confirmed bugs in the current v2 build. Address before marking any new phase complete.

| # | Issue | File(s) | Notes |
|---|---|---|---|
| 1 | **Watched folders not in folder list** | `folders_view.py` | Folders marked `watch_enabled=True` in DB (populated via discovery) do not appear in the left pane list — require manual "Add Folder…" to show. Fix: seed folder list from all DB folders with `watch_enabled=True` on startup, not just from user-added ones. |
| 2 | **Activity Log nav item** | `nav_rail.py`, new `views/activity_log_view.py` | Nav item on sidebar needs a view. Backend already writes timestamped entries to `%APPDATA%\SkillScan\activity.log` (scan start/complete, trust granted/revoked). View: scrollable log with severity colour coding and "Clear Log" action. |
| 3 | **Options → Watched Folders: AI tooling detection** | `options_view.py` | Add mechanism to declare installed AI tooling (Claude Desktop, Cursor, Copilot, Continue, etc.); use known install paths to auto-populate watched folders list. |

---

## Phase 5 — Skill Creator (next major phase)

`views/skill_creator_view.py` is a stub. Full spec in `docs/DevelopmentV2.md §Phase 5`.

- [ ] Metadata form: Name, Version, Description, Authors, License, Tags, Permissions
- [ ] Live spec compliance badge (updates as fields filled)
- [ ] `QPlainTextEdit` SKILL.md editor (monospace, line numbers)
- [ ] **Validate Spec** button → agentskills.io validator
- [ ] **AI Review** button → LLM security review with structured JSON findings
- [ ] **Scan Now** button → runs full scan pipeline
- [ ] **Save** / **Load** buttons

---

## Planned Feature Areas

### Actions
- [ ] Permanent Delete (with confirmation; update DB + Folders view; log to activity)
- [ ] Quarantine (move to configurable path; read-only lock; quarantine section in Folders view)
- [ ] Options: quarantine folder path (default `%APPDATA%\SkillScan\Quarantine\`)

### System Setup (new nav item "Setup")
- [ ] `CLAUDE.md` completeness check
- [ ] `.claude/` directory structure check
- [ ] `.claudeignore` presence check
- [ ] `settings.json` quality check
- [ ] MCP server config detection
- [ ] Stack / directory / commands / conventions declaration checks
- [ ] Installed AI tooling detection (Claude Desktop, Cursor, Copilot, Continue)
- [ ] Secrets files not in `.gitignore` / `.claudeignore`
- [ ] Scoring model: 0–100 per category; weighted overall; colour-coded gauge
- [ ] "Re-scan Environment" button
- [ ] "Export Report" (markdown)
- [ ] Nav: insert "Setup" between Testing and separator before Options

> **Memory reminder:** When System Setup work begins, ask user to share ChatGPT / Gemini / Copilot platform-specific config outputs they have ready.

### Governance (research first — see Research TODOs below)
- [ ] Governance profile selector (Personal / Enterprise / Regulated)
- [ ] Framework mapping in Compliance tab (NIST / NCSC controls)
- [ ] Policy enforcement rules
- [ ] Governance report export (JSON / PDF)

### CLI
- [ ] `scan <path>` — print findings, exit code reflects severity
- [ ] `discover <folder>` — walk + register in DB
- [ ] `list` — all tracked skills (json/table)
- [ ] `trust <path>` — grant/revoke
- [ ] `report <path>` — last scan result
- [ ] `setup` — headless env analysis
- [ ] Design: shared DB or independent? exit code conventions? stdout/stderr separation?

### Skill Source Classification
- [ ] `[P1]` Skill `source` DB field (anthropic / custom / org / partner / unknown)
- [ ] `[P1]` Source badge in Skill Detail header
- [ ] `[P1]` Executable attachment detection (`SUSPICIOUS_EXECUTABLE_ATTACHMENT` finding)
- [ ] `[P1]` Anthropic skill name spoofing detection (`ANTHROPIC_NAME_SPOOF` finding)
- [ ] `[P2]` Auto-invoke flag detection
- [ ] `[P2]` Org-provisioned supply chain finding (`ORG_SCOPE_DISTRIBUTION`)

### Claude Plugin Format (5th spec type)
- [ ] Plugin detection (`spec_type = "plugin"` via `.claude-plugin/plugin.json`)
- [ ] `plugin.json` schema validation
- [ ] `strict: false` finding (`PLUGIN_STRICT_MODE_DISABLED`)
- [ ] External `source.url` finding (`PLUGIN_EXTERNAL_GIT_SOURCE`)
- [ ] Bundle scope score
- [ ] Known-good corpus from `anthropics/skills` + `anthropics/claude-plugins-official`
- [ ] Community plugin cross-reference (`anthropics/claude-plugins-community`)

---

## Later Phases

### Phase 6 — DefenseClaw Integration
- [ ] `integrations/defenseclaw.py` — subprocess wrapper + result parser
- [ ] Merge findings with cisco-ai-skill-scanner output; deduplicate; tag by source
- [ ] Options toggle; result_formatter source column

### Phase 7 — MCP + A2A File Type Support
- [ ] `integrations/mcp_a2a.py` — synthetic SKILL.md context adapter
- [ ] Router updates for MCP/A2A file detection
- [ ] Tile type icons; filter for spec type

### Phase 8 — AI BOM Generation + Export
- [ ] `integrations/aibom.py` — CycloneDX 1.6 ML BOM
- [ ] Export button (folder-scoped + library-scoped)
- [ ] BOM diff (two snapshot comparison)

### Phase 9 — agentskills.io Spec + Inventory View
- [ ] `integrations/agentskills_spec.py` — download/cache JSON Schema; validator; `SpecWorker`
- [ ] `inventory_view.py` — full `QTableView` with sort/filter, spec score bar, BOM export

### Phase 10 — Registry Browser + Trust Store
- [ ] Registry browser (agentskills.io / GitHub search fallback)
- [ ] Scan-before-import flow
- [ ] Trust history log; "Trust All Clean" bulk action; export/import trust manifest

### Phase 11 — Advanced
- [ ] Batch HTML reports
- [ ] Multiple concurrent scans with `ScanQueue`
- [ ] Per-folder scan scheduling
- [ ] Policy profiles (Strict / Quick / Offline)
- [ ] Portable mode (`--portable`)

---

## Research TODOs

| Item | Priority | Notes |
|---|---|---|
| OWASP Agentic Skills Top 10 — scanner integration review | P1 | Cross-reference vs cisco-ai-skill-scanner; identify gap categories |
| agentskills.io specification — workflow integration review | P1 | How to feed into Compliance tab, Skill Creator validator, Inventory spec score |
| Landscape research — what are others building? | P1 | Starting point: HutCh1E/Skills-check; identify complementary tools and detection techniques |
| NIST AI RMF — map SkillScan findings to AI RMF controls | P1 | Four functions: GOVERN, MAP, MEASURE, MANAGE |
| NCSC LLM / AI security guidance review | P1 | Identify controls translating to SkillScan detection rules |
| EU AI Act risk classification — applicability to skills | P2 | High-risk domain detection? |
| Third-party supplier governance mechanisms | P2 | Provenance attestation, SBOMs, supplier questionnaires |
| Jurisdiction detection feasibility | P2 | UK/US/EU jurisdiction-aware compliance mode |
| ISO/IEC 42001 — evidence trail feasibility | P2 | Can SkillScan output contribute to ISO 42001 audit trail? |
| Anthropic name spoofing — detection approach | P1 | Compile known Anthropic skill names; evaluate fuzzy-match thresholds |
| Skill source detection — file-system signatures | P1 | What distinguishes Anthropic / org / partner / custom at the filesystem level? |
| Executable attachment risk — legitimate patterns | P1 | Anthropic skills repo is 84% Python; define `SUSPICIOUS_EXECUTABLE_ATTACHMENT` boundary |
| Auto-invoke detection — frontmatter or implicit? | P2 | Is it declared in SKILL.md / plugin.json or inferred from description? |
| Org-provisioned skills — delivery mechanism | P2 | Known install paths? Config file? Registry entry? |
| Anthropic GitHub — remaining 87 repos | P2 | Browse /orgs/anthropics/repositories; focus on knowledge-work-plugins, agent SDKs |

---

## Skills Library (planned additions)

| Skill | Status |
|---|---|
| `ui-text` | Planned — UI copy conventions |
| `ui-design-elements` | Planned — colour tokens, typography, spacing, iconography |
| `ui-window-elements` | Planned — window chrome patterns |
| `ui-about-dialog` | Planned — About dialog conventions |
| `ui-options-dialog` | Planned — Options dialog structure |
