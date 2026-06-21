# SkillScan — Product & Technical Specification

> Purpose of this document: a stack-agnostic blueprint of what was actually built, written so it could be implemented again — in any desktop GUI stack — and arrive at the same product. It describes *what* and *why*, not *how in this codebase*; for the existing Python/PyQt6 implementation's file-by-file detail, see `architecture.md`, `project_files.md`, and `development.md` in this same folder. Use this document alongside those, and alongside any visual/design artefacts (screenshots, colour tokens) you're pairing it with — this spec deliberately omits exact pixel/colour values.

---

## 1. Purpose & Problem Statement

AI "skills" — instruction files that tell an LLM agent what to do and what tools it may call (e.g. `SKILL.md` packages, MCP server manifests, A2A agent cards) — are themselves untrusted input once an agent can discover and load them automatically. A skill file can carry a prompt injection, an instruction to exfiltrate data, or a request for capability escalation, and it looks exactly like a normal instruction document.

**SkillScan** is a local desktop security tool that scans, audits, and governs every AI skill, MCP manifest, and A2A agent card a user has on their machine, *before* an agent is allowed to load them. It is not a cloud service: scanning, caching, and history all stay on the local machine by default.

## 2. Target Users & Use Cases

- An individual developer or power user who has accumulated skill files across multiple AI tools/agents and wants a single place to see which ones are safe.
- Someone authoring their own skills who wants spec-compliance checking and AI-assisted review before publishing or sharing a skill.
- A user who wants new skills automatically scanned the moment they appear (new file in a watched folder, a skill pasted to clipboard, a download) without manually running a CLI each time.

## 3. Domain Model (Glossary)

| Term | Meaning |
|---|---|
| **Skill** | A discovered unit to be scanned — most commonly a folder containing a `SKILL.md`, but also an MCP server manifest or an A2A agent card. Has a detected `spec_type` (`skill` / `mcp` / `a2a` / `unknown`). |
| **Folder** | A directory the user has added to the library. May contain one or more skills. Can optionally be *watched* (auto re-scan on change). |
| **Scan Result** | One run of the analyzers against one skill: a severity, a safe/unsafe verdict, structured findings, raw analyzer output, timing, and which analyzers actually ran. A skill accumulates a history of scan results over time. |
| **Trust** | A manually-asserted, per-skill state ("I have reviewed this and accept the risk") that is automatically revoked the moment the skill's on-disk content changes (detected via content hash), so trust can never silently survive a file edit. |
| **Severity** | One of CLEAN / LOW / MEDIUM / HIGH / CRITICAL, the worst finding across all analyzers in a scan. |
| **BOM (Bill of Materials)** | A point-in-time CycloneDX-format snapshot of everything discovered in a folder, for audit/compliance export. |
| **Analyzer** | One independent scanning technique (see §8.1) whose findings are merged into a single scan result. |

## 4. Functional Requirements

### 4.1 Dashboard

A glanceable overview, not a workflow. A grid of independent summary widgets (target: a dozen-plus), each showing one slice of state:

- Headline metrics (skills scanned, issues found, trend)
- Per-feature AI provider/credential health (is a key configured, is it valid, which provider is active)
- Overall security posture (proportion safe vs. flagged)
- An actionable list of items needing attention (untrusted-but-changed skills, failed scans, missing keys)
- Recent scan activity feed
- Scan throughput/velocity over time
- Library composition (by type, by source folder)
- BOM/AI-asset inventory summary
- Trust health (how many skills are trusted, how many trust grants were auto-revoked by a content change)
- Local environment/setup status
- Quick actions (jump straight to common tasks)

The grid must support per-widget show/hide, reordering (drag-and-drop), variable widget sizing (span), and persist that layout across restarts. A safe, conservative auto-refresh interval (on the order of a minute) keeps it current without hammering anything.

### 4.2 Folder & Skill Library Management

- Add a folder to the library (manually, or by dropping it onto a persistent "drop target" UI element for instant scan-on-drop).
- Browse all discovered skills as a visual grid of cards/tiles, each showing: name, type, severity (colour-coded), trust state, and a compact summary of findings.
- Support at least two density modes (e.g. compact vs. detailed tile) and at least one alternate layout (e.g. a flat list).
- Filter (by severity, type, trust state, folder) and sort (by name, date, severity) the grid live as the user types/selects.
- Queue and show progress for multiple in-flight scans without blocking the UI.
- Mark a folder as *watched* — any future change under it triggers an automatic re-scan (see §4.9).

### 4.3 Skill Studio (Authoring/Build)

A guided builder for someone *creating* a new skill, not just scanning an existing one:

- Metadata form (name, version, authors, license — with a license picker backed by a known-license registry, description, compatibility, allowed tools, free-form additional metadata).
- Direct editing of the skill's primary instruction document.
- Spec-compliance scoring against the public skill specification, with actionable per-rule feedback.
- AI-assisted description optimisation and a full AI review pass (summary + findings), gated behind whichever LLM provider is configured for this feature (see §8.2) — and skippable entirely if no provider is configured.
- A "scan now" action that runs the same analyzer pipeline used everywhere else, so the author sees exactly what an end user would see.
- Lint/validate any embedded scripts.
- Package and save the finished skill back to its source location, or build a distributable package.

### 4.4 Skill Detail / Inspection

Per-skill deep dive, reached from a tile or from a notification:

- Spec-compliance breakdown (same scoring engine as Skill Studio).
- The full human-readable scan report, plus raw analyzer output for power users.
- Scan history over time with a severity trend visualisation.
- Trust workflow: grant trust, see when it was granted, see it auto-revoked with the reason (content changed) the moment the underlying file's content hash no longer matches what was trusted.

### 4.5 Testing / Eval Fixtures

A way for the user to verify their own setup works correctly: download a maintained set of known-malicious and known-safe sample skills/manifests/agent cards (across attack categories) and run them through the pipeline to confirm expected verdicts come back. This is testing *of the tool*, not a library of real skills to keep around.

### 4.6 Activity Log

A filterable, severity-coloured chronological feed of everything that happened: scans run, trust granted/revoked, errors. Must support filtering by severity/type and searching by skill name.

### 4.7 Options / Settings

Grouped settings pages, reachable as both an embedded page and a separate floating window (same content, two entry points). At minimum:

- **General** — startup behaviour, minor UX toggles.
- **AI / LLM** — see §8.2; independent provider selection per feature.
- **Analyzers** — enable/disable each analyzer category (see §8.1), policy strictness, severity threshold that should fail a scan.
- **External scanner config** — analogous toggles for any secondary scanner (e.g. an MCP-specific scanner) that has its own analyzer set.
- **Clipboard watching** — enable/disable, polling interval, minimum content length before considering clipboard content scan-worthy, dedup so the same content isn't rescanned repeatedly.
- **Watched folders** — add/remove, per-folder watch toggle, notification behaviour.
- **Skill authoring defaults** — default license/compatibility/metadata used when starting a new skill in Skill Studio.
- **Software updates** — check/notify.

Settings must **autosave on every discrete change** (toggle flipped, dropdown changed, field committed) — no manual Save button, no "did I save?" ambiguity. A safety-net save on window close catches an edit whose commit event hasn't fired yet (e.g. a text field that's still focused). The settings UI itself should be searchable (type to filter visible setting rows/pages) given the number of pages.

### 4.8 About

Version, active LLM provider per feature, credits/links.

### 4.9 System Tray & Background Scanning

The app should be usable without its main window open:

- A system tray presence with quick actions and toggles, and a way to reopen the main window.
- Native OS notifications for scan completion / issues found, with user-configurable suppression (some users will want silence; default to informative).
- Watched-folder auto-scan: a change to a skill file under a watched folder triggers a debounced automatic re-scan, without spamming a scan-per-keystroke during a save.
- Clipboard auto-scan: content copied to the clipboard that looks like skill content gets scanned automatically (configurable threshold + dedup, see §4.7).
- A configurable global hotkey to trigger an ad-hoc scan.
- Optional OS file-manager integration (e.g. a right-click "Scan with SkillScan" context menu) that does not require elevated/admin privileges to install.

### 4.10 Out of Scope / Not Yet Built (at time of writing)

These are intentionally named in the navigation as placeholders, not hidden — the product's information architecture already has a slot for them:

- **AI Prompt Builder** — a guided tool for constructing prompts (not yet specified in detail).
- **Amalgamator** — combining multiple skills/sources into one (not yet specified in detail).
- **Skill Competence Builder** — an evaluation/benchmarking tool for skill quality (not yet specified in detail).
- **Inventory** — a dedicated cross-folder asset inventory view distinct from the Folders tile grid (not yet specified in detail).
- **Governance** — formal mapping to external AI governance frameworks (e.g. a NIST/ISO-style control mapping) — research-stage only.
- **Quarantine / permanent delete actions** for flagged skills — a destructive-action workflow not yet designed.

A specification for any of these should be written as its own addendum when that work actually starts, rather than guessed here.

## 5. Information Architecture & Navigation

A single main window owns a persistent navigation affordance (a rail or menu) and a content area that swaps between full-page views. Two settings-style destinations (Options, Help) additionally open as small floating auxiliary windows so they can be reached without losing the user's place in the main window — see §6.3.

Top-level destinations, grouped:

- **Primary workflow**: Dashboard, Folders, Inventory*, Skill Studio, Testing, Activity Log
- **AI-assisted tools**: Prompt Builder*, Amalgamator*, Skill Competence Builder*
- **Utility**: Options, About

(*) not yet built — see §4.10.

A secondary, always-reachable strip surfaces: alerts, a quick way into Options, and Help — independent of which main view is currently open.

## 6. UI Architecture Patterns

These are the structural patterns that make the product feel coherent, established and validated through this build. They are framework-agnostic: any desktop GUI toolkit capable of custom-drawn, frameless windows can implement them.

### 6.1 Custom window chrome, painted not masked

The product uses entirely custom window chrome (no native title bar) with rounded corners throughout. The critical rule, learned the hard way: **a window region mask is a hard, binary, per-pixel clip — it cannot antialias, no matter how finely its boundary is sampled.** Smooth rounded corners come only from a layer painting its own rounded shape with antialiasing turned on. A region mask should be reserved for the rare case where some genuinely unavoidable square-edged native element must be clipped — never used as the default way to round a window.

The practical implication: every nested layer inside a rounded window must itself paint a correctly-sized, correctly-rounded shape (or be plain content with no background fill of its own) so that nothing square-edged is ever left exposed at an outer curve. Pick one mechanism per corner and don't mix a paint-based round with a mask-based round on the same edge.

### 6.2 Shell / Surface separation

Every top-level window is two layers: an outer, fully transparent "shell" that owns only window-manager-level properties (frameless, draggable region if any, drop-shadow suppression), and an inner "surface" widget that does 100% of the actual background painting (fill colour + border stroke, both rounded). This separation keeps "being a window" and "looking like a window" independent, which is what makes the no-mask rounding in §6.1 possible — the surface can be sized and inset precisely enough to never need clipping.

Where a window is split into multiple visual regions (e.g. a side rail next to a main content pane), each region should independently paint only the corners that are actually on the window's outer edge — a region against an internal seam stays square there. Any child content sitting inside a rounded region needs a safety margin from that region's curved edges at least as large as the region's own corner radius, or its own (typically square) background fill will simply paint over the curve and silently flatten it back to a sharp corner — a failure mode that produces no visible roughness to catch the eye, only a corner that's quietly stopped being round.

### 6.3 Floating auxiliary windows

Secondary windows (Settings/Options, Help) follow one shared pattern:

- Lazily constructed on first use, then kept alive and reused (a "singleton" reference) rather than rebuilt every time — re-showing just raises and focuses the existing instance.
- Centered over the main window on each appearance.
- The main window dims behind them while they're open (a translucent overlay), reinforcing that they're a focused sub-task, without making them a true blocking modal dialog.
- Closing clears the dim overlay and (if applicable) flushes any pending unsaved state.

### 6.4 Settings autosave pattern

Settings views wire each control's discrete "value committed" signal directly to a persistence call, but **only after the view has finished populating its initial values from storage** — wiring autosave before that point causes every value the populate step sets to register as a spurious user-initiated save. The persistence function itself must be safe to call from either an embedded context (settings-as-a-page) or a standalone context (settings-as-a-window) without knowing which one it's in — it shouldn't decide whether to close any window; the host window's own close handling does that, calling the settings view's save routine as a last-chance safety net.

### 6.5 Layered navigation

A persistent navigation rail/menu selects among a set of full-page views held in a single swappable content container (only one page is ever visually present at a time, but constructing pages once and keeping them resident avoids rebuild cost on every navigation). Floating auxiliary windows (§6.3) sit outside this container entirely — they're a different navigational layer, not one more page in the stack.

### 6.6 Background work & responsiveness

Anything that shells out to an external process (an analyzer CLI) or does meaningful I/O (file discovery, hashing a folder tree) must run off the UI thread, reporting back through a thread-safe completion/progress signal rather than being polled. File-system watching must be debounced — a single save can produce a burst of filesystem events, and a watched-folder rescan should fire once per logical change, not once per event.

## 7. Data Architecture

### 7.1 Entities

| Entity | Key fields | Notes |
|---|---|---|
| **Folder** | path (unique), watch-enabled flag, last-scanned timestamp, added timestamp | One row per top-level folder the user has added. |
| **Skill** | path (unique), folder reference, name, spec type (skill/mcp/a2a/unknown), version, authors, license, description, content hash, trusted flag + trust-granted timestamp, spec-compliance score, created/modified timestamps | One row per discovered skill. Content hash is what trust-revocation compares against on every scan. |
| **Scan Result** | skill reference (nullable, for results migrated from a pre-database history), timestamp, severity, safe/unsafe flag, raw analyzer output, structured findings, duration, which analyzers ran, process return code | Append-only history; a skill accumulates many over its lifetime. |
| **BOM Snapshot** | folder reference, created timestamp, format identifier, content blob | Point-in-time export, kept for audit trail. |

Relationships: a Folder has many Skills and many BOM Snapshots; a Skill has many Scan Results. Deleting a Folder cascades to its Skills and BOM Snapshots; deleting a Skill cascades to its Scan Results.

### 7.2 Persistence locations

Everything lives locally, under a per-user application-data directory:

- **Settings** — a single structured config file (human-diffable format, e.g. JSON), never committed to any source repository.
- **Library/history database** — a local relational/embedded database file. A one-time migration path should exist for importing any pre-database flat-file history (e.g. a legacy JSON results log) on first run, guarded so it only ever runs once.
- **Activity/diagnostic log** — a size-capped, rotating local log file.

No scan result, skill content, or configuration value is ever uploaded anywhere by default (see §10.1).

## 8. External Integrations

### 8.1 Analyzers

A scan result is the merge of however many of these analyzers are enabled:

- **Static skill analyzer** — purpose-built static analysis + known-trigger-phrase detection for skill instruction documents and A2A agent cards.
- **Static MCP analyzer** — equivalent static analysis for MCP server manifests specifically.
- **LLM analyzer** — sends the skill content to a configured LLM (see §8.2) for a security-focused judgment; entirely optional and must degrade gracefully (clearly marked "skipped", not silently absent) if no provider is configured.
- **Behavioral pattern matching** — heuristic/rule-based detection independent of the LLM and static analyzers.
- **Hash-reputation lookup** (optional, third-party) — check a file's hash against a known-malware database.
- **Cloud analysis** (optional, third-party) — an additional vendor security-analysis service, opt-in only.

Both static analyzers are wrapped as external command-line tools invoked as subprocesses (not reimplemented in-process), parsing their structured (e.g. JSON) output. Any credential they need is passed via environment variable into the subprocess, never as a CLI argument (arguments are visible in process listings; environment variables are not) and never logged.

### 8.2 LLM provider abstraction

The LLM analyzer and any AI-assisted authoring feature (description optimisation, full review) sit behind a provider-agnostic interface supporting, at minimum: a major hosted LLM API, a second hosted LLM API, and at least one fully local option (a local inference server reachable over HTTP, requiring no API key and no internet access). Provider selection is **per feature, independently** — e.g. the authoring assistant can run against a local model while the scan pipeline's LLM judge runs against a hosted model, simultaneously, without one setting controlling both. Credentials are stored per-provider (not one shared key), and a feature with no key/provider configured must skip gracefully rather than error.

### 8.3 Optional third-party services

Hash-reputation lookup and vendor cloud analysis (§8.1) are both off by default, require their own API key, and must be clearly distinguishable in the UI as "this analyzer sends data outside your machine" — distinct from every other analyzer, which is fully local.

## 9. Configuration Schema (representative, not exhaustive)

Grouped by the Options page that owns it (§4.7):

- Per-feature active LLM provider (authoring vs. scanner, independently)
- Per-provider credentials/endpoints/model identifiers (one block per provider)
- Per-analyzer enable/disable flags, policy strictness, severity-to-fail threshold
- Equivalent per-analyzer flags for any secondary scanner
- Dashboard layout state (hidden widgets, custom spans, custom order)
- Watched folders list + per-folder/global notification suppression flags
- A global scan hotkey binding
- An accent colour / theme preference
- Clipboard watch enable flag, poll interval, minimum-length threshold
- Skill-authoring defaults (license, compatibility, free-form metadata)

## 10. Non-Functional Requirements

### 10.1 Security & Privacy

- **No hardcoded credentials anywhere** — always loaded from local configuration/environment at runtime.
- **No telemetry without explicit opt-in.** No scan result, skill content, or usage data leaves the machine unless the user has explicitly enabled one of the optional third-party analyzers in §8.3.
- **Never log a secret value.** Logs may record *that* a credential was loaded/used; never the value itself, and never a full raw API response or raw scan payload that might embed one.
- **All cache and history stays local** — no auto-upload of scan results or skill content, ever.
- Validate and constrain any file path built from external/untrusted input before using it.
- Never deserialize untrusted data with a mechanism that can execute code as a side effect of loading it; never build a shell command from untrusted input in a way that could be reinterpreted by the shell; never evaluate untrusted input as code.
- Audit-log security-relevant operations (trust granted/revoked, analyzer credential changes) distinctly from routine activity.

### 10.2 Platform & Environment

Single-user local desktop application. No multi-user/server mode is in scope. Should run without requiring elevated/administrator privileges for any core feature (an OS context-menu integration, if offered, must use a no-admin-required installation mechanism).

### 10.3 Performance & Responsiveness

The UI must never block on a scan, a filesystem scan/hash, or a network call to an LLM provider — all of these are background work (§6.6) reporting back asynchronously. Dashboard auto-refresh and watched-folder polling should be conservative enough to be invisible in normal resource usage.

### 10.4 Reliability

- **Trust is automatically revoked, never silently stale.** A content-hash check on every relevant access compares against the hash that was trusted; any mismatch revokes trust immediately and visibly, rather than letting a user believe a changed file is still the one they reviewed.
- **Idempotent persistence.** Saving settings (or any autosaved state) twice with the same values must be safe and side-effect-free, since the autosave pattern (§6.4) may fire more than once for a single logical change.
- A scan that fails partway (one analyzer errors) should still surface whatever the other analyzers found, clearly marking which analyzer was skipped and why, rather than discarding the whole result.

## 11. Key Architecture Decisions Worth Preserving

These are decisions this build arrived at after getting them wrong first — worth stating explicitly so a re-implementation doesn't have to relearn them:

1. **Round by painting, not masking** (§6.1) — the single most consequential UI decision in the build; a mask-based rounded window will always look visibly worse than a paint-based one, with no amount of mask refinement closing the gap.
2. **A window's exact pixel dimensions can themselves cause a visible 1-pixel seam** between two independently-laid-out widgets, purely from how the OS compositor's DPI scaling rounds sub-pixel positions — invisible in an off-screen/headless render, only visible on a real screen, and fixable by adjusting the window's size rather than restructuring the layout. Check this cheaply (resize and re-check) before assuming a seam is structural.
3. **Settings persistence and "decide whether to close a window" must be two different responsibilities** — a settings view used both embedded and standalone cannot safely assume which top-level window it's inside.
4. **Trust must be derived from content, not from a path or a timestamp** — a content hash is the only thing that can't be fooled by a touch/rename that doesn't actually change the file, or missed by an edit that doesn't update an mtime in the way expected.
5. **Local LLM providers still need *something* in the credential field** even though they don't check it — several client libraries that route local-server calls through a generic provider-client code path will reject a truly empty credential, so a local provider should still send a non-empty placeholder.

## 12. Reference Implementation Notes

The existing build (this repository) implements this specification in Python, using a desktop GUI toolkit supporting custom frameless windows (PyQt6), an embedded SQL database via an ORM (SQLite via SQLAlchemy), a filesystem-watching library for the watched-folders feature, and an LLM-abstraction library for the multi-provider integration in §8.2. None of that is prescribed by this specification — it's recorded here only so the two documents can be cross-referenced. See `architecture.md` and `project_files.md` in this folder for that implementation's exact structure.

## 13. Out of Scope

- Multi-user accounts, server deployment, or any centralized/shared instance of this tool.
- Mobile or web clients.
- Automated remediation of a flagged skill (rewriting it to remove the malicious content) — today's AI-assisted features review and advise; they do not autonomously rewrite a third party's skill.
- Anything listed in §4.10.
