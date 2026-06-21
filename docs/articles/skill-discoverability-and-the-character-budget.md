# Can Claude Actually Find the Right Skill? Testing SKILL.md Descriptions Empirically

SkillScan started this investigation trying to design a better prompt-building wizard.
It ended up finding a real, measurable problem in how Claude Code decides which skills
to invoke — and a concrete number for SkillScan's own maintainer's skill folder. This is
the path from one to the other, and what SkillScan actually built as a result.

## The starting question

The idea on the table was an "AI Prompt Builder" with three tiers — Beginner,
Intermediate, Pro — each asking progressively more questions to help a user arrive at a
better prompt. It's a reasonable instinct: don't overwhelm a novice with fifteen
questions, but let a power user dial in everything.

The harder question came next: **how do we know this is the right design?**
Researching comparable tools surfaced real prior art worth learning from:

- **[prompt-architect](https://github.com/ckelsoe/prompt-architect)**, a Claude Code Agent
  Skill, classifies *intent* first (create / transform / reason / critique / recover /
  clarify / agentic), then picks a matching framework (CO-STAR, RISEN, RTF, Chain-of-Thought)
  before asking questions — a different axis than skill level. Depth should probably scale
  with *task type*, not just *user experience*.
- **[Anthropic's own Console prompt generator/improver](https://www.anthropic.com/news/prompt-generator)**
  shows the adaptive alternative to a fixed question form: describe a goal, let Claude infer
  the structure, or paste a rough prompt and have it refined directly.
- **PromptLayer, LangSmith, and Vellum** (prompt management platforms) all converge on the
  same loop regardless of how they differ elsewhere: write → test against the model →
  version → compare. A "Test Now" step isn't a nice-to-have in this category; it's table
  stakes.

That research answered "what exists," but not "is this correct for SkillScan's users."
Five web searches establish plausibility, not proof. The honest answer was: nobody knows
yet, including us — and research alone wasn't going to resolve it.

## From "I think" to "let's measure"

The proposal that broke the deadlock: stop debating the wizard design in the abstract,
and instead build an empirical test of the thing the wizard is actually trying to
improve — whether Claude picks the *right* skill out of many candidates, given a task.

That test splits into two halves with very different evidentiary weight:

1. **Selection** — give an LLM a corpus of skills (name + description only, the same
   fields Claude's real relevance-matching reads) and a task prompt, and ask which skill
   it would invoke. If you label the *expected* skill for each task ahead of time, this is
   **objective**: precision/recall, no judgment calls. This directly tests "trigger
   clarity" — a check SkillScan's roadmap had already flagged as wanted but undesigned.
2. **Build + judge** — actually execute the task with the selected skill's content, then
   have a second LLM score the output. This half is genuinely subjective, and inherits all
   the known failure modes of LLM-as-judge evaluation: position bias, verbosity bias,
   self-preference bias. It needs randomized ordering, rubric scoring, and multiple judge
   calls — not a single A-vs-B verdict.

SkillScan built and ran the first half. (The second is real and useful, but a bigger lift
— it's noted as future work below.)

## The benchmark

Living at [`evals/skill_selection/`](../../evals/skill_selection/) in this repo:

- **A 17-skill corpus** — 15 well-differentiated skills spanning clearly distinct domains
  (PDF/Word/PowerPoint/Excel generation, MCP server scaffolding, generative art, internal
  comms, brand guidelines, two of SkillScan's own real PyQt6 skills, etc.), plus **2
  deliberately vague "control" skills** (`general-helper`, `assistant-tools`) designed to
  test false-positive over-triggering.
- **15 hand-labeled tasks**, each mapping unambiguously to exactly one corpus skill.
- **`run_selection_benchmark.py`** — builds a single prompt listing every skill's
  name + description, asks an LLM which one it would invoke, repeats each task N times
  (mirroring the repeated-trial pattern already used elsewhere in this repo for
  determinism testing), and reports per-task hit rate plus the control skills'
  false-positive rate.

**Result, run against a local `llama3.1:8b` model, 15 tasks × 5 repeated runs (75 trials):
100% selection accuracy, 0% false-positive rate.** Every well-written description won its
matching task every time; the two vague distractors never fired once.

**The honest gap:** every task's ground truth is a *clear* skill. None of the 15 tasks
expect a vague one to win. This benchmark proves the mechanism works — clear descriptions
get found, irrelevant ones stay silent — but it does not yet prove that vagueness *causes*
a miss on the skill that should have won. That needs a vague/clear twin-pair task (the same
underlying skill, described once clearly and once vaguely) and is recorded as the next
step in `todo.md`.

## The pivot nobody expected: length isn't the lever you'd think

Mid-discussion, a natural follow-on question came up: if a vague description is the
problem, would a *more generous* character limit help authors be more specific? Checking
the formal spec said no — 1024 characters (a few full sentences) is already generous;
vagueness is a writing-quality problem, not a length-constraint problem.

But a direct factual challenge — "I thought the accepted standard was around 220
characters?" — turned out to be onto something real that a single spec lookup had missed
entirely. There isn't one limit. There are at least three, for three different things:

| Limit | Value | Applies to |
|---|---|---|
| Formal agentskills.io spec max | **1024 characters** | What `core/spec_compliance.py` validates against |
| Claude.ai web UI "Custom Skills" upload | **~200 characters** | A separate, stricter consumer-product constraint |
| Claude Code's runtime `available_skills` listing | **Shared budget, ~8,000 chars fallback** (scales with context window) + **per-skill display cap, 250→1536 chars** (raised once already, undocumented officially) | What Claude Code actually shows the model at session start |

The third one is the one that bites in practice. It isn't in any official Anthropic
documentation — it's reverse-engineered from multiple GitHub issues filed against
`anthropics/claude-code` by users who found skills silently going invisible. The budget is
shared across *every installed skill at once*: the more skills you have, the less room
each one gets, and overflow doesn't error — it silently truncates or drops a skill from
discovery entirely, sometimes cutting off the exact trigger phrasing that made a
description good in the first place.

Full sourcing is recorded in [`url.md`](../../.claude/architecture/url.md).

## A real number, not a hypothetical

Running this check against the project maintainer's actual `~/.claude/skills/` folder
(33 installed skills):

- **Total description length: ~14,200 characters** against a documented ~8,000-character
  fallback shared budget — **≈177% of budget**.
- **21 of 33 skills** exceed the older 250-character per-skill display cap (`claude-api`
  at 1068 characters, `xlsx` at 941, `docx` at 785, several of the project's own
  `pyqt6-*` skills in the 300s).
- **0 of 33** exceed the newer 1536-character cap — so on a recent Claude Code version,
  per-skill truncation is probably not the active risk; the shared total is.

This reframed the original question. A richer, longer description doesn't just risk
*failing to help* discoverability — for a real, populated skill folder, it's actively
counterproductive: every extra character competes for a budget shared with every other
installed skill.

## What SkillScan actually built

Given the gap between "formal spec" and "what Claude Code does at runtime," this became a
new, concrete check rather than staying a discussion:

- **`core/skill_budget.py`** — the per-skill and aggregate budget math, clearly documented
  as community-sourced and explicitly *not* factored into `spec_compliance.py`'s score.
  These numbers are unofficial and have already changed once (250 → 1536); penalizing a
  skill's score against an unconfirmed, moving threshold would repeat a mistake this
  project already made once before (an earlier, incorrect hard-coded required-field list
  scored every skill against invented rules until it was caught and fixed). This is
  surfaced as risk information, not a deduction.
- **Skill Audit view** — a new "Desc. Chars" column (color-coded against both caps) and an
  aggregate budget line in the toolbar summary ("description budget: 14,200/8,000 chars
  (177%)"), so the question is answered the moment you open the view, not buried in a
  report.
- **Shared compliance renderer** — the same per-skill budget note appears in Skill Detail's
  Compliance tab too, since both views already share one rendering implementation.

## Open threads

- **The vague/clear twin-pair test** — the one piece still missing to *directly* prove
  vagueness causes a selection miss, rather than just confirming clear descriptions win
  and irrelevant ones don't.
- **A "keep the budget constants current" routine** — these thresholds are an admitted
  moving target. A periodic check (as part of SkillScan's own update process) that flags
  when the tracked sources have changed again is recorded in `todo.md`, likely to land
  alongside a planned broader "System Setup" environment-health module rather than as a
  one-off script.
- **The build + judge half of the original evaluation idea** — real, useful, and a
  meaningfully bigger lift (needs bias-aware judging, not a single LLM call) than what's
  built so far.

## Chosen approach, in one paragraph

Don't theorize about prompt-wizard design in the abstract — test the underlying mechanism
empirically, and prefer objective measurement (labeled selection accuracy) over subjective
judgment (LLM-as-judge output scoring) wherever the question allows it. That same
discipline, applied to a tangential question about character limits, surfaced a real,
sourced, currently-relevant problem with the maintainer's own skill set that a spec-only
reading would have missed entirely. The result shipped is a new, clearly-labeled-as-
informational risk check in the Skill Audit view, plus a standalone, reusable benchmark
harness for testing skill-selection accuracy going forward — not a finished prompt wizard,
but a measurement foundation that any future feature in this space should be built on top
of, rather than around.
