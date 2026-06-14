# SkillScan — Reference URLs

> Links that have informed design decisions, roadmap items, or research tasks.  
> Last updated: 2026-06-13

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
