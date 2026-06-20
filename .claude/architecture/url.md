# SkillScan — Reference URLs

> Links that have informed design decisions, roadmap items, or research tasks.  
> Last updated: 2026-06-20

---

## Claude Code skill-listing character budget

Informs `core/skill_budget.py` (description-length risk check, Own-skill audit). Community-reverse-engineered, not official Anthropic documentation — already changed once (per-skill display cap raised from 250 to 1536 characters between Claude Code 2.1.86 and 2.1.105), expect it to change again. See todo.md for the planned routine to re-check these numbers periodically.

| URL | Purpose |
|---|---|
| https://github.com/anthropics/claude-code/issues/13099 | "Document the available_skills character budget limit" — confirms the shared, undocumented total budget (~1% of context window, ~8,000 char fallback) |
| https://gist.github.com/alexey-pelykh/faa3c304f731d6a962efc5fa2a43abe1 | Community research on the skill budget mechanics — per-skill overhead estimate (~109 chars), shared-budget math |
| https://claudefa.st/blog/guide/mechanics/skill-listing-budget | "Claude Code's Hidden Skill Budget Setting" — `skillListingBudgetFraction` / `SLASH_COMMAND_TOOL_CHAR_BUDGET` override settings |
| https://github.com/backnotprop/plannotator/issues/412 | "Skill description exceeds new 250-character limit in Claude Code 2.1.86" — confirms the legacy per-skill display cap and its introduction version |
| https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview | Official Agent Skills docs — confirms the formal agentskills.io 1024-char spec max (distinct from the runtime budget above) |

---

## Skill hot-reload and progressive disclosure

Informs the "Task → skillset swapping" idea (todo.md, AI Features) — confirms the mechanism is technically viable today rather than waiting on a future Anthropic feature.

| URL | Purpose |
|---|---|
| https://claudelog.com/faqs/what-is-skill-hot-reload-in-claude-code/ | Confirms skill hot-reload (CLI 2.1.0+) — files added/edited/removed under an already-watched `.claude/skills/` directory take effect live, no restart |
| https://github.com/anthropics/claude-code/issues/20507 | "Feature Request: Add /reload-skills command" — context on the limitation that a brand-new top-level skills directory still needs a restart to start being watched |
| https://medium.com/@dan.avila7/claude-code-skills-progressive-disclosure-step-by-step-3ca02a4a9f60 | Confirms the three-level progressive disclosure model (frontmatter always loaded → body loaded on activation → supporting files loaded as needed) |

---

## Core dependencies

| URL | Purpose |
|---|---|
| https://github.com/cisco-ai-defense/cisco-ai-skill-scanner | Primary scanner CLI that SkillScan wraps |
| https://agentskills.io/specification | agentskills.io SKILL.md specification — feeds Compliance tab scoring and Skill Creator validator |

---

## Anthropic / Claude ecosystem

| URL | Purpose |
|---|---|
| https://support.claude.com/en/articles/12512176-what-are-skills | Anthropic definition of skill source types (Anthropic / Custom / Org / Partner) — informed Skill Source Classification feature area |
| https://github.com/anthropics/skills | Anthropic official skills repo — reference corpus for Anthropic name-spoof detection and known-good allowlist |
| https://github.com/anthropics/claude-plugins-official | Official Claude plugins — informs Claude Plugin Format feature area (5th spec type) |
| https://github.com/anthropics/claude-plugins-community | Community plugin registry (nightly sync from Anthropic review pipeline) — planned cross-reference for "In community registry" indicator |
| https://github.com/anthropics/knowledge-work-plugins | Role-specific knowledge-work plugins — planned review (likely scan targets) |
| https://github.com/orgs/anthropics/repositories | Anthropic GitHub — 90 public repos; review remaining ones for new file formats, attack surfaces, reference corpora |

---

## Security standards and frameworks

| URL | Purpose |
|---|---|
| https://www.nist.gov/system/files/documents/2023/01/26/AI%20RMF%201.0.pdf | NIST AI Risk Management Framework 1.0 — governance research; map SkillScan findings to four core functions (GOVERN, MAP, MEASURE, MANAGE) |
| https://www.ncsc.gov.uk/collection/ai-security | NCSC AI security guidance — identify controls translating to SkillScan detection rules |
| https://owasp.org/www-project-agentic-skills-top-10/skill-scanner-integration | OWASP Agentic Skills Top 10 — cross-reference vs current scanner coverage; identify detection gaps |

---

## Research and community

| URL | Purpose |
|---|---|
| https://github.com/HutCh1E/Skills-check | Community AI skill security tool — landscape research starting point |

---

## Standards (planned research)

| URL | Purpose |
|---|---|
| EU AI Act | EU AI Act risk classification — assess applicability to skills by declared domain/use-case |
| ISO/IEC 42001 | AI Management Systems standard — assess whether SkillScan output could contribute to audit trail |

> Note: EU AI Act and ISO 42001 links are formal standards documents; URLs will be sourced during the governance research phase.
