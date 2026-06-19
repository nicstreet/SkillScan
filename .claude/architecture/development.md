# SkillScan v2 — Development Roadmap

> Canonical roadmap for SkillScan v2 — the Skill Security Environment.
> Supersedes the original v1 tray-app roadmap (historical; no longer in the repo).
> Architecture reference: [architecture.md](architecture.md)
> Quick-reference Known Fixes + condensed pointers: [todo.md](todo.md)
> Last synced against the codebase: 2026-06-19 — Phases 1–5 confirmed complete (see todo.md for the detailed Phase 5 breakdown, kept live there since it changes faster than this file). This session's work was UI polish (Options window de-masking/seam fix) and documentation (`specification.md`), not new phase work — see `change_history.md` and `handover.md` for detail.

---

## Skills Library — superseded, see below

**This section is stale and the underlying concept it describes no longer exists.** The `skills/` directory (containing `pyqt6-ui-designer`, `color-palette-builder`, `cisco-ai-defense-integrator`, `environment-setup` as hand-built sample SKILL.md packages to scan) was deleted from the working tree (uncommitted, see `handover.md`) and replaced by `evals/` — downloaded eval *fixtures* for SkillScan's own Testing view (`core/test_skills.py`), not a library of sample skills maintained in this repo. None of the "📝 Planned" rows that used to follow (`ui-text`, `ui-design-elements`, `ui-window-elements`, `ui-about-dialog`, `ui-options-dialog`) describe planned work in *this* concept anymore either.

That said, the underlying need — reusable PyQt6 UI engineering knowledge — was actually built this session, just as a different kind of artefact in a different location: seven **Claude Code skills** at `~/.claude/skills/` (`pyqt6-frameless-window`, `pyqt6-icons-buttons-text`, `pyqt6-scrollbars`, `pyqt6-menus`, `pyqt6-help-window`, `pyqt6-naming-conventions`, `pyqt6-options-pane`). These assist *building* SkillScan's UI in future sessions — they are not SKILL.md content for SkillScan to scan, and they don't live in this repository at all. See `reference_global_skills.md` in Claude's memory store for what each one covers.

---

## What Carries Forward from v1

All of the following v1 work is **retained unchanged** in v2:

| Module | Status |
|---|---|
| `core/config.py` — `load()` / `save()` | ✅ Retained |
| `core/scanner.py` — `ScanJob` / `QProcess` | ✅ Retained |
| `core/result_store.py` — JSON history (migrates to DB) | ✅ Retained, then superseded |
| `core/clipboard_watcher.py` | ✅ Retained |
| `core/watcher.py` — `FolderWatcher` | ✅ Retained |
| `core/test_skills.py` + Testing Guide | ✅ Retained |
| `ui/_palette.py` — colour tokens | ✅ Retained |
| `ui/_widgets.py` — `RoundedCard`, `TitleBar` | ✅ Retained |
| `ui/scan_progress.py` — frameless scan dialog | ✅ Retained |
| `ui/result_formatter.py` — HTML findings report | ✅ Retained |
| `ui/toggle_row.py` — pill toggle | ✅ Retained |
| `ui/tray.py` — simplified to satellite | ✅ Retained (simplified) |
| `windows/taskbar_dock.py` | ✅ Retained |
| `windows/context_menu.py` | ✅ Retained (optional install) |
| `resources/logo_no_bg.png` | ✅ Retained |

---

## Open Carries (from v1 Known Fixes)

Items from v1 that are resolved by v2 architecture, or must be fixed before/during migration:

- [x] **Scan output is raw JSON** — resolved by `result_formatter.py` (v1 Phase 5)
- [x] **`skill-scanner` not installed** — `_check_scanner()` in `main_window.py` shows install hint in status bar on startup
- [x] **`fail_on_severity` not wired** — `scanner.py` reads `fail_on_severity` from config and passes `--fail-on-severity` flag
- [x] **Drop Zone toggle not persisted** — N/A; Drop Zone removed entirely (see below)
- [x] **`drop_zone.py` still present** — file no longer exists in codebase
- [ ] **Results window empty stub** — superseded by v2 Inventory view (Phase 9, not yet started)
- [x] **No startup registration** — Options → General "Launch at login" checkbox writes to registry

---

## Known Fixes

Live list moved to [todo.md](todo.md) → "Known Fixes (do first)" — kept there since it's updated every session. As of 2026-06-18 every item tracked there is fixed, most recently the Skill Detail title-bar band removal.

---

## Actions (Planned Feature Area)

What to do with skills once a discovery is made — needs its own design pass before implementation. Likely surfaced from the Skill Detail view action bar and/or tile context menus.

- [ ] **Permanent Delete** — remove the skill file from disk with confirmation prompt; update DB and Folders view immediately; log action to activity log
- [ ] **Quarantine** — move the skill file to a designated quarantine folder (configurable in Options); consider whether to apply a filesystem-level lock (read-only attribute or ACL) to prevent the file being re-executed while quarantined; quarantined skills should be visually distinct in the Folders view (separate section or badge) and excluded from Scan All; support un-quarantine (restore to original path)
- [ ] **Options: Quarantine folder path** — add a setting under a new Actions tab in Options for users to specify the quarantine destination; default to `%APPDATA%\SkillScan\Quarantine\`

---

## Governance (Planned Feature Area — Research First)

*How do we apply governance to AI skills — not just at the personal or enterprise level, but across third-party suppliers, national jurisdictions, and established regulatory/standards frameworks?*

This is a major open design question before any implementation. SkillScan currently operates as a security scanner; governance would extend it into a **compliance and policy enforcement layer**. The scope is deliberately broad — the research phase should determine what is realistic to implement and what SkillScan should surface vs. defer to external tooling.

### Governance layers to consider

| Layer | Question | Examples |
|---|---|---|
| **Personal** | Does this skill meet my own standards? | Trust model, scan threshold, quarantine |
| **Enterprise** | Does this skill comply with org policy? | Org-provisioned allowlist, banned permission types, mandatory scan before trust |
| **Third-party** | What are suppliers accountable for? | Partner skill SLAs, community plugin review process, provenance attestation |
| **Jurisdiction / national** | What does local law require or prohibit? | UK NCSC guidance, US Executive Order on AI, EU AI Act obligations |
| **International standards** | How does this map to recognised frameworks? | NIST AI RMF, NCSC LLM guidance, ISO/IEC 42001, SOC 2 AI controls |

### Research tasks

- [ ] **Research: NIST AI Risk Management Framework (AI RMF)** — review [https://www.nist.gov/system/files/documents/2023/01/26/AI%20RMF%201.0.pdf](https://www.nist.gov/system/files/documents/2023/01/26/AI%20RMF%201.0.pdf) and the four core functions (GOVERN, MAP, MEASURE, MANAGE); determine which SkillScan findings and metadata map to AI RMF controls; assess whether SkillScan could generate an AI RMF-aligned risk report per skill or per folder

- [ ] **Research: NCSC LLM / AI security guidance** — review NCSC's published guidance on LLM security and AI system risks (https://www.ncsc.gov.uk/collection/ai-security); identify any controls or recommendations that translate directly into SkillScan detection rules or reporting fields; note whether NCSC guidance is specific to UK organisations or applicable more broadly

- [ ] **Research: EU AI Act implications** — assess how the EU AI Act's risk classification (unacceptable / high / limited / minimal) might apply to AI skills; skills used in high-risk domains (healthcare, legal, HR) could carry different obligations; determine whether SkillScan should flag a skill's declared domain/use-case against EU AI Act risk categories

- [ ] **Research: Third-party supplier governance** — what accountability mechanisms exist for partner skills and community plugins? Anthropic's own disclaimer states they "cannot verify plugins will work as intended or won't change" — is there an emerging standard for skill provenance attestation, SBOMs for AI components, or supplier security questionnaires that SkillScan could surface or integrate with?

- [ ] **Research: Jurisdiction detection and applicability** — can SkillScan infer or allow the user to declare their jurisdiction, and then surface only the relevant regulatory requirements? E.g. a UK user sees NCSC + UK AI governance obligations; a US user sees NIST + state AI laws; an EU user sees EU AI Act. Determine whether a jurisdiction-aware compliance mode is feasible without becoming a legal product (which SkillScan is not)

- [ ] **Research: ISO/IEC 42001 (AI Management Systems)** — review the standard's requirements for AI system governance, risk assessment, and documentation; identify whether SkillScan's existing scan output + compliance tab data could form part of an ISO 42001 evidence trail

### Implementation ideas (post-research)

- [ ] **Governance profile selector** — Options setting for user to declare their governance context (Personal / Enterprise / Regulated industry); adjusts scan sensitivity, required fields, and report format accordingly
- [ ] **Framework mapping in Compliance tab** — alongside the spec score, show which NIST/NCSC controls this skill's scan results are relevant to; links to the relevant control documentation
- [ ] **Policy enforcement rules** — enterprise admins can define rules (e.g. "any skill with `permissions: filesystem` must be CRITICAL before flagging"; "no untrusted skills in the `production/` folder"); rules evaluated at scan time; violations surface as governance findings distinct from security findings
- [ ] **Governance report export** — generate a structured report (JSON or PDF) mapping each scanned skill's findings to a chosen governance framework; intended for compliance audits, security reviews, or board-level reporting

---

## System Setup (Planned Feature Area)

*Goal: analyse the user's AI development environment and score its readiness — because a well-structured base is a prerequisite for skills working effectively.*

A dedicated nav item ("Setup" or "Environment") that scans the local machine and scores the configuration across several categories, with colour-coded results and actionable recommendations. Surfaces problems the user may not know they have before they start adding skills.

### What to analyse

**Claude / AI agent config**
- [ ] `CLAUDE.md` present and populated — checks for key sections: Stack, Directory Structure, Commands, Conventions, Important; scores completeness and flags empty or placeholder sections
- [ ] `.claude/` directory structure — checks for `settings.json`, `skills/`, `commands/`, `rules/` subdirectories; validates `settings.json` schema (permissions, allowed tools, hook configs)
- [ ] `.claudeignore` present — checks for common patterns (secrets, build artefacts, large binaries)
- [ ] `settings.json` quality — scans for overly permissive tool grants, missing hook configs, no denied patterns
- [ ] MCP servers configured — detects any configured MCP servers; checks for known-insecure configurations

**Project structure**
- [ ] Stack declaration — `CLAUDE.md` or equivalent contains Language, Framework, Database, Styling, Testing declarations
- [ ] Directory structure documented — key directories (`src/`, `tests/`, `docs/`, etc.) are listed with descriptions
- [ ] Commands documented — at least dev, build, test, lint commands declared
- [ ] Conventions documented — at least one naming/export/API convention declared
- [ ] Important constraints documented — at least one hard constraint (never-modify, always-run, etc.) declared

**Skills**
- [ ] Cross-reference installed skills count against detected AI tooling (e.g. Claude Desktop, Cursor) — surface ratio of tooling used vs skills scanned
- [ ] Highlight any unscanned or untrusted skills as a readiness risk

**Environment**
- [ ] Detect installed AI tooling (Claude Desktop, Cursor, Copilot, Continue, etc.) — same mechanism as Options → Watched Folders installer detection
- [ ] Check for `.env` or secrets files that are not in `.gitignore` / `.claudeignore`
- [ ] Python venv / Node `node_modules` not inadvertently exposed to AI context

### Scoring model
- Each category (Agent Config, Project Structure, Skills, Environment) scores 0–100
- Overall score is a weighted average; displayed as a top-level gauge with per-category breakdown
- Each failed check shows: what is missing, why it matters, and a one-click or copy-paste fix
- Score thresholds: ≥80 = Healthy (green), 50–79 = Needs Attention (amber), <50 = At Risk (red)

### UI
- [ ] New nav rail item "Setup" (between Testing and the separator before Options)
- [ ] Top section: overall score gauge + per-category score chips
- [ ] Scrollable list of checks grouped by category — each row: icon, check name, status badge, recommendation text
- [ ] "Re-scan Environment" button — re-runs all checks and refreshes scores
- [ ] "Export Report" — saves a markdown summary to disk

---

## CLI (Planned Feature Area)

*Goal: expose key SkillScan functionality via command line so it can be used in CI pipelines, pre-commit hooks, scripts, and headless environments — without launching the GUI.*

Needs a design pass to determine scope and flag format before implementation. Entry point would likely be `python -m skill_scan [command] [options]` (or a `skillscan` console script registered in `setup.cfg` / `pyproject.toml`).

### Commands to consider

- [ ] **`scan <path>`** — scan a single skill file or directory; print findings to stdout; exit code reflects severity (0 = clean, 1 = findings, 2 = error); supports `--format json|text` and `--fail-on-severity <level>`
- [ ] **`discover <folder>`** — walk a folder, register discovered skills in the DB, print a summary; equivalent to the GUI "Add Folder" + discovery pass
- [ ] **`list`** — print all tracked skills with their current severity, trust status, and spec score; supports `--format json|table`
- [ ] **`trust <path>`** — grant or revoke trust on a skill file from the CLI; flags: `--revoke`
- [ ] **`report <path>`** — print the last scan result for a given skill; useful for CI artefact capture
- [ ] **`setup`** — run the System Setup environment analysis and print the scored report (headless version of the Setup nav view)

### Design considerations

- [ ] Determine whether CLI commands share the same SQLite DB as the GUI, or operate independently
- [ ] Define exit code conventions (important for CI `--fail-on-severity` use case)
- [ ] Decide whether `scan` spawns `cisco-ai-skill-scanner` as a subprocess (same as GUI) or calls the Python API directly
- [ ] Stdout/stderr separation — findings to stdout, progress/debug to stderr
- [ ] `--quiet` flag to suppress all output except exit code (for scripting)
- [ ] Consider a `--watch` flag for `scan` that monitors a file and re-scans on change (headless equivalent of the folder watcher)

---

## Skill Source Classification (Planned Feature Area)

*Informed by: [What are Skills? — Anthropic Support](https://support.claude.com/en/articles/12512176-what-are-skills)*

Anthropic defines four distinct skill source types, each with a different trust profile and attack surface. SkillScan currently treats all skills as equivalent — adding source awareness would allow more nuanced risk scoring and UI presentation.

| Source | Description | Risk profile |
|---|---|---|
| **Anthropic** | Pre-built by Anthropic; auto-invoke on relevance | Lowest risk — but spoofing an Anthropic skill name is a viable attack |
| **Custom** | User/org created; Markdown + optional scripts | Standard risk — primary SkillScan target today |
| **Org-provisioned** | Distributed org-wide by Organisation Owner (Team/Enterprise) | Highest multiplied risk — one compromised skill reaches all members |
| **Partner** | Third-party (Notion, Figma, Atlassian) via MCP connectors | Third-party supply chain risk |

### Tasks

- [ ] `[P1]` **Skill source field** — add a `source` field to the `skills` DB table (`anthropic` / `custom` / `org` / `partner` / `unknown`); detect from path conventions, manifest metadata, or MCP connector origin where possible. *Research item: see Integration Reviews → "Skill source detection"*
- [ ] `[P1]` **Source badge in Skill Detail header** — display source type alongside the existing SKILL/MCP/A2A type badge; use distinct colour (e.g. partner = teal outline, org = amber outline) to signal trust tier at a glance
- [ ] `[P1]` **Executable attachment detection** — skills can include executable scripts alongside SKILL.md; detect any non-Markdown files in the skill folder (`.py`, `.sh`, `.ps1`, `.exe`, `.bat`, `.js`, etc.) and flag them as elevated risk in the scan report and tile badge; the presence of an executable should be a required finding category, not optional. *Research item: see Integration Reviews → "Executable attachment risk"*
- [ ] `[P2]` **Auto-invoke flag** — Anthropic skills and some partner skills trigger automatically when Claude deems them relevant (no explicit user invocation); detect skills that declare auto-invoke behaviour in their metadata and surface this as a risk dimension — auto-invoke skills have a larger attack surface than manually-triggered ones. *Research item: see Integration Reviews → "Auto-invoke detection"*
- [ ] `[P2]` **Org-provisioned supply chain risk** — org-distributed skills reach all organisation members automatically; add a dedicated finding category "ORG_SCOPE_DISTRIBUTION" that triggers when a skill is identified as org-provisioned; severity should be elevated (minimum MEDIUM) regardless of content findings, because the blast radius of a compromise is multiplied. *Research item: see Integration Reviews → "Org-provisioned supply chain"*
- [ ] `[P1]` **Anthropic skill name spoofing detection** — flag any custom skill whose name closely matches a known Anthropic built-in skill name (e.g. "Excel Helper", "Document Creator"); similarity check using edit distance or keyword matching; finding category "ANTHROPIC_NAME_SPOOF". *Research item: see Integration Reviews → "Anthropic name spoofing"*

---

## Claude Plugin Format (Planned Feature Area)

*Informed by: [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official), [anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community)*

Claude Code plugins are a **superset** of skills — a single plugin can bundle SKILL.md files, MCP server config, slash commands, and agent definitions together in one folder. This is a 4th detection target for SkillScan beyond the existing SKILL.md / MCP manifest / A2A agent card types.

### Plugin folder structure

```
plugin-name/
├── .claude-plugin/
│   └── plugin.json      ← primary detection signal
├── .mcp.json            ← optional MCP server config
├── commands/            ← slash command definitions
├── agents/              ← agent definitions
├── skills/              ← SKILL.md bundles
└── README.md
```

### Tasks

- [ ] **Plugin detection** — add `plugin` as a 5th `spec_type` in the router; detect by presence of `.claude-plugin/plugin.json`; display as "PLUGIN" badge (distinct colour from SKILL/MCP/A2A) in tile and detail header
- [ ] **`plugin.json` schema validation** — parse `plugin.json` and validate required fields; surface missing fields in the Compliance tab; understand what constitutes a well-formed plugin manifest
- [ ] **`strict: false` flag** — plugins can declare `"strict": false` to skip full schema enforcement; flag this in findings as a weakened validation posture (`PLUGIN_STRICT_MODE_DISABLED`)
- [ ] **Git-sourced plugin supply chain** — `plugin.json` can declare a `source.url` pointing to an external git repo (the actual skill content is fetched from there at install time); flag any external `source.url` as a supply chain risk finding (`PLUGIN_EXTERNAL_GIT_SOURCE`) — the installed content may differ from what was reviewed
- [ ] **Bundle scope analysis** — a plugin that bundles MCP servers AND skills AND agents in one install is a wider attack surface than a SKILL.md alone; calculate a "bundle scope score" and surface in the Compliance tab
- [ ] **Known-good corpus — Anthropic official skills** — download and cache the manifest from [anthropics/skills](https://github.com/anthropics/skills) and [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official); use as an allowlist for the Anthropic name-spoof detection and as a reference set for the scan pipeline; refresh periodically (Options setting for cache TTL)
- [ ] **Community plugin allowlist** — [anthropics/claude-plugins-community](https://github.com/anthropics/claude-plugins-community) syncs nightly from Anthropic's internal review pipeline; plugins in this list have passed automated security scanning; SkillScan could cross-reference local plugins against this list and display a "In community registry" indicator — neither a trust grant nor a finding, just provenance information
- [ ] **Executable files: context-aware risk** — Anthropic's own skills repo is 84% Python; executable files alongside SKILL.md are expected and normal. SkillScan's executable detection (see Skill Source Classification) should be smarter than a simple flag: look for obfuscation patterns, unexpected binary formats, scripts that reach outside the skill folder, or executables in plugins not declaring code execution in their manifest

---

## Integration Reviews (Research Items)

Items requiring research before implementation — read the referenced specs/docs, identify gaps, then convert findings into concrete Known Fixes or phase tasks.

- [ ] **OWASP Agentic Skills Top 10 — scanner integration review** — read [https://owasp.org/www-project-agentic-skills-top-10/skill-scanner-integration](https://owasp.org/www-project-agentic-skills-top-10/skill-scanner-integration) and cross-reference against what `cisco-ai-skill-scanner` currently detects; identify any OWASP Top 10 categories not covered by the existing analyzers; document gaps and raise new Known Fixes or Phase 6+ tasks for each missing detection category

- [ ] **agentskills.io specification — workflow integration review** — read [https://agentskills.io/specification](https://agentskills.io/specification) end-to-end; determine how the spec should feed into: (a) the Compliance tab scoring model in Skill Detail (currently uses a hardcoded required-fields list — should it derive from the live spec?), (b) the Skill Creator validator (Phase 5), (c) the Inventory view spec score column (Phase 9); identify whether the spec schema can be downloaded and cached, and what a spec-version mismatch would look like in the UI

- [ ] **Landscape research — what are other researchers building in this space?** — survey open-source projects, papers, and tooling addressing AI skill / MCP security to identify: (a) detection techniques or attack patterns not yet covered by SkillScan, (b) complementary tools worth integrating or referencing, (c) community standards or emerging conventions that should influence the roadmap. Starting points: [HutCh1E/Skills-check](https://github.com/HutCh1E/Skills-check). Add further links as discovered. Convert findings into Known Fixes or new phase tasks.

- [ ] **Research: Anthropic name spoofing** `[P1]` — before implementing `ANTHROPIC_NAME_SPOOF` detection, research: (a) compile a complete list of known Anthropic built-in skill names from [anthropics/skills](https://github.com/anthropics/skills) and the official plugin directory; (b) evaluate fuzzy-matching approaches used in analogous domains (npm typosquatting detection, DNS lookalike detection, PyPI name confusion) — edit distance alone has high false-positive rates; (c) determine a threshold that catches genuine spoofs (e.g. "ExceI Helper" with capital I) without flagging legitimate custom skills with similar names; (d) decide whether to maintain a local hardcoded list or fetch live from the Anthropic corpus cache

- [ ] **Research: Skill source detection** `[P1]` — before implementing the `source` DB field, research: (a) what file-system or metadata signatures reliably distinguish Anthropic / org / partner / custom skills — do Anthropic skills ship to a known path? do org skills carry an org identifier in frontmatter?; (b) review the agentskills.io spec and `anthropics/skills` spec folder for any `source` or `provenance` metadata fields; (c) establish a detection confidence model (definite vs inferred vs unknown) so the UI can communicate uncertainty rather than asserting incorrect provenance

- [ ] **Research: Executable attachment risk** `[P1]` — before implementing executable detection, research: (a) what are the legitimate patterns in the wild? Anthropic's own skills repo is 84% Python — understand what scripts are expected, what they do, and where they legitimately reach; (b) survey obfuscation detection approaches for Python and Shell (e.g. base64-encoded payloads, `eval`/`exec` chains, encoded strings); (c) identify indicators that a script reaches outside its skill folder (absolute paths, `os.environ` scraping, network calls, subprocess spawning); (d) decide what constitutes "suspicious executable" vs "expected executable" — the finding should be `SUSPICIOUS_EXECUTABLE_ATTACHMENT`, not just `HAS_EXECUTABLE`

- [ ] **Research: Auto-invoke detection** `[P2]` — before implementing the auto-invoke flag, research: (a) is auto-invoke behaviour declared in SKILL.md frontmatter, `plugin.json`, or only implicit (Anthropic skills invoke based on description relevance)?; (b) check the agentskills.io spec for any `trigger`, `auto_invoke`, or `activation` field; (c) determine whether auto-invoke can be inferred from the skill description pattern ("This skill activates when…") using keyword or regex matching; (d) assess whether auto-invoke is a binary flag or a spectrum (always-on vs conditional)

- [ ] **Research: Org-provisioned supply chain** `[P2]` — before implementing `ORG_SCOPE_DISTRIBUTION` detection, research: (a) how are org-provisioned skills actually delivered to member machines — is there a known install path, a config file, or a registry entry that identifies org-distributed skills?; (b) what Claude Team/Enterprise documentation exists about skill distribution mechanics?; (c) understand whether org skills are distinguishable from personal skills at the file-system level; (d) determine whether the finding should be informational (provenance context) or a severity modifier (multiplied blast radius elevates base severity)

- [ ] **Anthropic GitHub — remaining repos review** — [github.com/anthropics](https://github.com/anthropics) has 90 public repositories; only a subset has been reviewed. Repos already actioned: `skills` (reference corpus + spec redirect), `claude-plugins-official` (plugin format), `claude-plugins-community` (community allowlist). Repos still to review: `knowledge-work-plugins` (role-specific knowledge-work plugins — likely scan targets), `claude-agent-sdk-python` / `claude-agent-sdk-typescript` (understand how agents consume skills, which may surface new detection angles), and any others surfaced by browsing [/orgs/anthropics/repositories](https://github.com/orgs/anthropics/repositories). Focus: new file formats, new attack surfaces, reference corpora, and tooling that could complement or integrate with SkillScan.

---

## Phase 1 — Main Window Shell ✅ Complete

*Goal: replace the tray-first entry point with a primary windowed application. All existing functionality continues to work; no features removed.*

### 1.1 Window infrastructure

- [x] `ui/main_window.py` — `MainWindow(QMainWindow)` with `FramelessWindowHint` + `WA_TranslucentBackground`
- [x] Custom title bar: SKILLSCAN wordmark, draggable, minimise + close only (Segoe Fluent Icons)
- [x] `QPainterPath` rounded rect `paintEvent`, `QGraphicsDropShadowEffect` (blur=28, offset=0,6)
- [x] `mousePressEvent` / `mouseMoveEvent` drag on title bar
- [x] Window minimum size 1000×640; resizable
- [x] Status bar: scanner state dot, unscanned count, LLM model name, version string

### 1.2 Nav rail

- [x] `ui/nav_rail.py` — `NavRail(QWidget)` with `NavItem` buttons
- [x] Items: Folders, Inventory, Create, (spacer), Options, About, Exit
- [x] Active item: `ACCENT` colour, 3px left border, `rgba(ACCENT, 0.12)` bg
- [x] Hover state: `DEEP_SURFACE` bg, `MUTED_TEXT` → `LIGHT_CANVAS` transition
- [x] `page_changed(int)` signal wired to `QStackedWidget.setCurrentIndex()`
- [x] Back button in title bar area: hidden by default, shown when `_history` stack non-empty

### 1.3 View stubs

- [x] `ui/views/folders_view.py` — stub (populated Phase 3)
- [x] `ui/views/inventory_view.py` — stub (populated Phase 4)
- [x] `ui/views/skill_creator_view.py` — stub (populated Phase 5)
- [x] `ui/views/testing_view.py` — **migrated** from `settings_dialog._make_testing_tab()`
- [x] `ui/views/options_view.py` — **migrated** from `SettingsDialog` (all tabs)
- [x] `ui/views/about_view.py` — **migrated** from `AboutDialog`

### 1.4 Entry point + tray simplification

- [x] `__main__.py` updated: create `MainWindow` as primary; `TrayApp` as satellite
- [x] Tray menu simplified: keep scan triggers, feature toggles, notifications; remove Settings/About (→ main window)
- [x] `MainWindow.show()` on tray double-click or "Open SkillScan" menu item
- [x] Window close hides to tray (does not quit); Exit nav item quits

### 1.5 Carry-forward fixes

- [x] Startup check for `cisco-ai-skill-scanner` — show install-hint dialog if not found
- [x] Wire `fail_on_severity` → `--fail-on-severity <level>` CLI arg in `scanner.py`
- [x] Persist Drop Zone toggle state to `config.json`
- [x] Delete `ui/drop_zone.py`

---

## Phase 2 — SQLite Database + Skill Discovery ✅ Complete

*Goal: replace flat JSON result store with a relational database; populate it by scanning watched folders on startup.*

### 2.1 Database layer (`core/db.py`)

- [x] SQLAlchemy declarative models: `Folder`, `Skill`, `ScanResult`, `BomSnapshot`
- [x] Schema as defined in `architecture.md` §Database Schema
- [x] `session()` context manager for short-lived reads
- [x] Migration on startup: import existing `results.json` into `scan_results` (one-time, then delete JSON)
- [x] Database at `%APPDATA%\SkillScan\skillscan.db`

### 2.2 Skill discovery (`core/skill_discovery.py`)

- [x] `discover(folder: Folder, session) -> DiscoveryResult` — walks folder tree, finds SKILL.md, MCP manifests, A2A cards
- [x] File type detection: `core/router.py` — `detect_type(path) -> SpecType`
- [x] SHA-256 hash each file; compare to DB; insert new, update changed, mark missing as deleted
- [x] Trust invalidation: if `file_hash` changed and `skill.trusted`, set `trusted=False`, clear `trust_signed_at`
- [x] `DiscoveryWorker(QThread)` — runs discovery without blocking UI; emits `progress(int, int)` and `finished()`
- [x] Auto-discovery on startup for all `watch_enabled` folders
- [x] Manual "Refresh" per folder in Folders view toolbar

### 2.3 Windows integration — startup at login

- [x] "Launch at login" checkbox in Options → General
- [x] Writes/removes `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\SkillScan`

---

## Phase 3 — Folders View + Skill Tile Grid ✅ Complete

*Goal: the primary working view — browse folders, see all skills as tiles with severity badges, trigger scans.*

### 3.1 Folder pane (`views/folders_view.py` — FolderPane)

- [x] `QListWidget` of tracked folders loaded from DB
- [x] Each row: folder name, skill count badge, issues count badge (amber if any non-clean)
- [x] "Add Folder…" button — `QFileDialog`, inserts into DB, runs discovery
- [x] Right-click context menu: Remove Folder, Scan All, Open in Explorer
- [x] Selection emits `folder_selected(folder_id)` → loads tile grid

### 3.2 Skill tile grid (`views/folders_view.py` — SkillTileGrid)

- [x] `QScrollArea` with `QFlowLayout` of `SkillTile` widgets
- [x] `SkillTile(QFrame)`: skill name, description (truncated), spec type icon, severity badge, trust badge, last-scanned age
- [x] Tile border colour reflects severity (`CRITICAL_ACCENT`, `HIGH_ACCENT`, `MEDIUM_ACCENT`, `SAFE_ACCENT`, `DIVIDER` for unscanned)
- [x] Unscanned tiles: dashed border; hover shows "▶ Scan now" overlay
- [x] Trusted skills: secondary `✓ TRUST` badge in `ACCENT`
- [x] Click tile → push `SkillDetailView` onto stack, show back button
- [x] Right-click tile: Scan, Open Folder, Copy Path, Trust / Revoke Trust
- [x] Toolbar: path breadcrumb, skill count, Filter dropdown (by severity / type / trust), "Scan All" button

### 3.3 Scan integration

- [x] "Scan All" queues all unscanned (or all) skills in folder; runs `ScanJob` sequentially
- [x] Progress shown in status bar: "Scanning 3 / 8…"
- [x] On completion: tile badges refresh from DB; tray notification summarises worst severity
- [x] Single tile scan: right-click → Scan, opens `ScanProgressDialog`

---

## Phase 4 — Skill Detail View ✅ Complete

*Goal: single-skill deep-dive — spec compliance, full scan report, history sparkline.*

### 4.1 Layout (`views/skill_detail_view.py`)

- [x] Back button in title bar (uses `_history` stack from Phase 1)
- [x] Header: skill name + type badge + path; severity badge + trust badge
- [x] Spec compliance section: score bar (0–100), list of missing required fields, warnings — Compliance tab; score persisted to `skill.spec_score`
- [x] Scan report section: reuses `result_formatter.py` HTML output in `QTextBrowser`
- [x] "Show Raw Output" toggle — implemented as Raw Output tab
- [x] Scan history section: table of past scans (timestamp, severity, duration, analyzers used)
- [x] History sparkline: small `QPainter`-drawn severity timeline across last N scans
- [x] Action buttons: "Scan Now", "Trust" / "Revoke Trust", "Open File", "Open in Creator"

### 4.2 Trust workflow

- [x] "Trust" button enabled only when latest scan is `clean`
- [x] On click: sets `skill.trusted = True`, `trust_signed_at = now()`, stores current `file_hash`
- [x] If file changes on disk (watcher detects): `trusted` cleared automatically — `QFileSystemWatcher` in `SkillDetailView`; auto-revokes and logs if hash changed
- [x] "Revoke Trust": sets `trusted = False` without rescanning

---

## Phase 5 — Skill Studio ✅ Builder UI v1 complete (renamed from "Skill Creator" 2026-06-16)

*Goal: write and validate new skills without leaving SkillScan.*

Built as `views/skill_manager_view.py` (not `skill_creator_view.py` — file renamed alongside the view). Actual layout is a left/right two-panel split rather than the originally-planned top/bottom split: left = Metadata card (Name, Description with Optimize Description, License via shared `LicensePicker`, Compatibility, Allowed Tools, Additional Metadata key/value editor) + Structure card (scripts/references/assets file boxes with live Script Lint); right = SKILL.md body editor + AI Review card (diff/revert/save-review) + Specification Compliance card (live score, reuses `core/spec_compliance.py` — the same engine as Skill Detail's Compliance tab, not a separate `agentskills_spec.py` validator). AI Review returns structured XML tags (`<ISSUES>`/`<CHANGES_MADE>`/`<REVISED_DESCRIPTION>`/`<REVISED_BODY>`), not the originally-planned JSON findings array.

See [todo.md](todo.md) → "Phase 5 — Skill Manager" for the live, item-level checklist (kept there since it changes faster than this file) — Builder UI v1, Options → Default Info, and the foundational `spec_compliance.py` extraction are all done; **Own-skill audit** (batch-scanning `~/.claude/skills/`) has not been started.

---

## Phase 6 — DefenseClaw Integration

*Goal: add Cisco AI Defense DefenseClaw as a second primary analyzer.*

- [ ] `integrations/defenseclaw.py` — `DefenseclawJob(QObject)` wrapping `QProcess`
- [ ] Auto-detect `defenseclaw` executable from venv (`Path(sys.executable).parent / "defenseclaw"`)
- [ ] If not found: disable silently; show install hint in Options → Analyzers
- [ ] Parse DefenseClaw JSON output → normalise to shared `Finding` schema
- [ ] Merge findings with `cisco-ai-skill-scanner` output in `scanner.py`; deduplicate by (category, line) where possible
- [ ] Tag each finding with `source: defenseclaw` vs `source: skill-scanner`
- [ ] Enable/disable checkbox: Options → Analyzers → "DefenseClaw"
- [ ] Update `result_formatter.py`: show source tag in findings table "Analyzer" column

---

## Phase 7 — MCP + A2A File Type Support

*Goal: extend scan coverage beyond SKILL.md to MCP manifests and A2A agent cards.*

### 7.1 File type router (`core/router.py`)

- [ ] `detect_type(path: Path) -> SpecType` enum: `SKILL_MD`, `MCP_MANIFEST`, `A2A_CARD`, `UNKNOWN`
- [ ] SKILL.md: filename match
- [ ] MCP: JSON with `"mcpVersion"` key or `"tools"` array at root
- [ ] A2A: JSON at `agent.json` or `.well-known/agent.json` with `"capabilities"` key
- [ ] `SkillDiscovery` updated to find all three types in folder walks

### 7.2 MCP / A2A scan adapter (`integrations/mcp_a2a.py`)

- [ ] Extract tool descriptions / capability declarations as text
- [ ] Assemble synthetic skill context string
- [ ] Route to LLM Analyzer + Trigger Detector only (not `cisco-ai-skill-scanner`)
- [ ] Tag all findings with `source: mcp` or `source: a2a`
- [ ] Return standard `ScanResult`

### 7.3 UI changes

- [ ] Tile type icon: `SKILL.md` = skill icon, `MCP` = plug icon, `A2A` = agent icon
- [ ] Filter dropdown in tile grid: filter by spec type
- [ ] Skill detail header: show spec type badge

### 7.4 Testing view

- [ ] **"Open Testing Guide for Manifests"** button in MCP Manifest Evals section (Testing view) → opens section 7 of Testing Guide (`GUIDE.md#7--mcp-manifest-evals` or dedicated `MCP_GUIDE.md`)

---

## Phase 8 — AI BOM Generation + Export

*Goal: generate machine-readable AI Bills of Materials from the skill inventory.*

### 8.1 BOM generator (`integrations/aibom.py`)

- [ ] `generate_component(skill: Skill, latest_result: ScanResult) -> dict` — single CycloneDX component
- [ ] `generate_bom(skills: list[Skill], ...) -> dict` — full CycloneDX 1.6 document
- [ ] Properties per component: `skillscan:spec_type`, `skillscan:scan_severity`, `skillscan:scan_timestamp`, `skillscan:trusted`, `skillscan:spec_score`
- [ ] Export formats: `cyclonedx-json`, `cyclonedx-xml` (via `json` + `xml.etree`; no external library required for initial pass)
- [ ] Save snapshot to `bom_snapshots` table after each export

### 8.2 BOM export UI

- [ ] "Export AI BOM" button in Folders view toolbar (folder-scoped)
- [ ] "Export Library BOM" button in Inventory view (all tracked skills)
- [ ] `QFileDialog.getSaveFileName()` — defaults to `SkillScan-BOM-{date}.cdx.json`
- [ ] Success toast notification via tray `showMessage`

### 8.3 BOM diff

- [ ] "Compare Snapshots…" in Inventory view — picker for two `bom_snapshots` by date
- [ ] `diff_bom(snap_a, snap_b) -> BomDiff(added, removed, changed)` — compare by component name+version
- [ ] Diff shown in modal dialog: three sections (added green, removed red, changed amber) as tables

---

## Phase 9 — agentskills.io Spec Compliance + Inventory View

*Goal: validate skills against the agentskills.io specification and surface compliance across the full library.*

### 9.1 Spec validator (`integrations/agentskills_spec.py`)

- [ ] Download JSON Schema from agentskills.io on first use; cache to `%APPDATA%\SkillScan\spec_cache\`
- [ ] `validate(skill_path: Path) -> SpecResult(score: int, missing: list[str], warnings: list[str])`
- [ ] Score: 100 minus deductions per missing required field (−10) and warning (−3)
- [ ] `SpecWorker(QThread)` — runs validation without blocking UI
- [ ] Store `spec_score` in `skills` table; refresh on each scan

### 9.2 Inventory view (`views/inventory_view.py`)

- [ ] `QTableView` backed by `SkillTableModel(QAbstractTableModel)`
- [ ] Columns: Name, Type, Folder, Severity, Spec Score, Trusted, Last Scanned, Version, Authors
- [ ] Sortable by any column
- [ ] Filter bar: severity, type, trusted state, folder
- [ ] Row click → navigate to Skill Detail view
- [ ] "Export AI BOM" button (library-scoped)
- [ ] "Compare Snapshots…" button
- [ ] Spec Score shown as a coloured bar (red 0–40, amber 41–74, green 75–100)

---

## Phase 10 — Registry Browser + Trust Store

*Goal: discover and import community skills; formalise the trust workflow.*

### 10.1 Registry Browser (new nav item between Inventory and Create)

- [ ] Browse agentskills.io registry (or GitHub search fallback) for published skills
- [ ] Results shown as tiles: name, author, version, description, published date
- [ ] "Import" button: downloads SKILL.md to chosen folder → auto-runs Phase 7 discovery → opens Skill Detail
- [ ] "Scan before import": scan is triggered immediately; import only completes after result shown
- [ ] Community vs Local label on tiles

### 10.2 Trust Store enhancements

- [ ] Trust history: log each grant/revoke with timestamp and scan_result_id
- [ ] "Trust All Clean" bulk action in Inventory view
- [ ] Export trusted skill list as signed manifest (JSON with SHA-256 hashes) for team sharing
- [ ] Import trust manifest: marks matching skills as trusted if hashes match

---

## Phase 11 — Advanced Features

*Goal: power-user and team features that round out the environment.*

### 11.1 Batch reports

- [ ] "Generate Report" in Folders view toolbar — produces a timestamped HTML report for all skills in folder
- [ ] Report template: summary table (counts by severity), then per-skill findings sections
- [ ] Opens in default browser after generation; also saved to `%APPDATA%\SkillScan\reports\`

### 11.2 Multiple concurrent scans

- [ ] `ScanQueue` — manages a list of active `ScanJob` instances
- [ ] Status bar shows: "Scanning 2 / 5…" with a progress indicator
- [ ] Each queued scan is a row in a compact "Scan Queue" panel that slides up from the status bar

### 11.3 Scan scheduling

- [ ] Per-folder option: "Auto-scan on change" (existing) + "Scheduled: daily / weekly"
- [ ] Uses `QTimer` with persisted next-run timestamp in config
- [ ] Silent mode: no progress dialog; tray notification on completion

### 11.4 Policy profiles

- [ ] Named presets: "Strict" (all analyzers, fail on medium+), "Quick" (static + trigger only), "Offline" (no LLM/VT)
- [ ] Selectable per-scan in `ScanProgressDialog` override, or set as default in Options

### 11.5 Portable mode

- [ ] Config and DB stored adjacent to the executable when `--portable` flag passed
- [ ] Allows USB/shared-drive deployment without `%APPDATA%` dependency

---

## Future / Ideas

- **Prompt / Context Engineering Builder** — standalone interface + AI assistant for building AI-ready project context: system prompts, conversation starters, knowledge capsules, and project briefs. Goal: give an LLM everything it needs to hit the ground running without the user having to re-explain background on every session. Potential integration point: SkillScan could generate a context capsule for any skill folder (metadata, scan history, trust status, BOM snapshot) that drops straight into an LLM context window.

- **GitHub Actions integration** — `skillscan-action` that scans SKILL.md in a PR and posts findings as review comments
- **VS Code companion extension** — trigger scans from the editor sidebar; inline severity annotations
- **Team config sync** — shared `config.json` fetched from a URL for org-wide defaults (API keys, policy, analyzer flags)
- **Webhook on finding** — POST scan result JSON to a configured URL (Slack, Teams, Splunk, SIEM)
- **SKILL.md syntax highlighting** — VS Code / Notepad++ language extension for frontmatter + body sections
- **Dependency graph** — visualise skill-to-skill dependencies (if declared in metadata) as a DAG
- **A2A live scan** — connect to a running A2A agent endpoint and scan the live agent card from the network
- **MCP server live scan** — connect to a running MCP server and introspect tool descriptions at runtime
