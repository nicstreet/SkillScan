"""Claude Code's available_skills character budget — an informational risk
check, not part of the formal agentskills.io spec that core/spec_compliance.py
validates against.

Community-reverse-engineered from GitHub issues filed against
anthropics/claude-code (it isn't officially documented) and already a moving
target: the per-skill display cap was raised from 250 to 1536 characters
between Claude Code versions 2.1.86 and 2.1.105. Treat these numbers as
"worth checking", not certain — see .claude/architecture/url.md for sources.

Deliberately NOT factored into spec_compliance.score(): unlike that module's
documented agentskills.io rules, these are unofficial, version-dependent, and
have already changed once. Surfaced as risk information only.
"""

from dataclasses import dataclass, field

PER_SKILL_CAP_LEGACY = 250  # Claude Code <= 2.1.86 per-entry display truncation
PER_SKILL_CAP_CURRENT = 1536  # Claude Code >= 2.1.105 per-entry display truncation
OVERHEAD_PER_SKILL = 109  # estimated non-description chars per available_skills entry
FALLBACK_SHARED_BUDGET = (
    8000  # total available_skills budget when context window is unknown
)


@dataclass
class SkillBudgetStatus:
    description_length: int
    over_legacy_cap: bool
    over_current_cap: bool


def check_description_length(description: str) -> SkillBudgetStatus:
    """Per-skill check against the known per-entry display truncation caps."""
    n = len(description or "")
    return SkillBudgetStatus(
        description_length=n,
        over_legacy_cap=n > PER_SKILL_CAP_LEGACY,
        over_current_cap=n > PER_SKILL_CAP_CURRENT,
    )


@dataclass
class AggregateBudgetReport:
    skill_count: int
    total_description_chars: int
    estimated_total_with_overhead: int
    fallback_budget: int
    budget_used_fraction: float
    over_legacy_cap: list[tuple[str, int]] = field(default_factory=list)
    over_current_cap: list[tuple[str, int]] = field(default_factory=list)


def aggregate_budget_report(descriptions: dict[str, str]) -> AggregateBudgetReport:
    """descriptions: {skill_name: description_text} for skills sharing one budget."""
    total_desc = 0
    total_with_overhead = 0
    over_legacy: list[tuple[str, int]] = []
    over_current: list[tuple[str, int]] = []
    for name, desc in descriptions.items():
        n = len(desc or "")
        total_desc += n
        total_with_overhead += n + OVERHEAD_PER_SKILL
        if n > PER_SKILL_CAP_LEGACY:
            over_legacy.append((name, n))
        if n > PER_SKILL_CAP_CURRENT:
            over_current.append((name, n))
    return AggregateBudgetReport(
        skill_count=len(descriptions),
        total_description_chars=total_desc,
        estimated_total_with_overhead=total_with_overhead,
        fallback_budget=FALLBACK_SHARED_BUDGET,
        budget_used_fraction=(
            total_with_overhead / FALLBACK_SHARED_BUDGET
            if FALLBACK_SHARED_BUDGET
            else 0.0
        ),
        over_legacy_cap=sorted(over_legacy, key=lambda x: -x[1]),
        over_current_cap=over_current,
    )
