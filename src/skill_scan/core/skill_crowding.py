"""Domain-crowding check - flags skills whose descriptions overlap heavily with
a neighbor in the same audited folder, even when each is individually clear.

Validated empirically by the skill-selection benchmark's vague/clear twin-pair
test (evals/skill_selection/, 2026-06-20): a vague "pdf-helper" sibling measurably
degraded a well-written "pdf-builder" neighbor's selection accuracy (100% -> 60%)
purely by existing in the same corpus - not because either description was bad
in isolation.

This is a lexical-overlap heuristic, not an LLM-based judgment - keeps Own-skill
audit fast and free of extra LLM calls per scan. It will miss overlap that uses
different words for the same concept, and may flag coincidental word overlap
that isn't real crowding. Surfaced as risk information only, same as
core/skill_budget.py - never factored into spec_compliance.score().

Uses overlap coefficient (shared / smaller set size), not Jaccard similarity -
Jaccard washes out when one description is much shorter than the other (the
exact vague/clear shape this check targets), since the union is dominated by
the longer description's vocabulary.

Two distinct word lists, not one, because they guard against two distinct
risks (caught during calibration, 2026-06-20 - see tests/core/test_skill_crowding.py):
- _STOPWORDS: ordinary English function words (the, and, with, ...) - noise
  in any text, regardless of domain.
- _GENERIC_SKILL_WORDS: words that are common specifically in skill-description
  *prose style* ("create and edit...", "use this skill whenever the user
  asks...") regardless of what the skill actually does. Confirmed by word-
  frequency analysis across the real installed corpus + the benchmark corpus
  (evals/skill_selection/) - words like "create"/"edit"/"trigger"/"whenever"
  recur across many unrelated skills' descriptions purely because that's how
  skill descriptions are conventionally phrased, not because the skills
  overlap. Without this list, e.g. "Create and edit Word documents..." vs
  "Create and edit Excel spreadsheets..." falsely flagged as crowded on
  {create, edit, tables} despite Word and Excel being unrelated domains.
  The skill's own *name* is excluded from extraction entirely (not just these
  words) for the same underlying reason: generic naming suffixes ("-builder",
  "-helper") would otherwise both dilute genuine overlap below threshold and
  create false matches between unrelated same-suffix skills.
"""

import re
from dataclasses import dataclass

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "with",
        "for",
        "to",
        "of",
        "in",
        "on",
        "using",
        "use",
        "this",
        "that",
        "is",
        "are",
        "be",
        "as",
        "at",
        "by",
        "from",
        "into",
        "your",
        "you",
        "it",
        "its",
        "their",
        "via",
        "when",
        "both",
        "plus",
        "also",
        "such",
        "any",
        "all",
        "more",
        "than",
        "new",
    }
)

# Generic skill-description prose - common across unrelated skills' write-ups,
# not domain vocabulary. See module docstring for why this is separate from
# _STOPWORDS and how it was derived (word-frequency analysis, not a guess).
_GENERIC_SKILL_WORDS = frozenset(
    {
        "skill",
        "skills",
        "claude",
        "user",
        "users",
        "trigger",
        "triggers",
        "ask",
        "asks",
        "whenever",
        "based",
        "like",
        "create",
        "creates",
        "creating",
        "edit",
        "edits",
        "editing",
        "build",
        "builds",
        "building",
        "generate",
        "generates",
        "generating",
        "helper",
        "helpers",
        "helps",
        "help",
        "tool",
        "tools",
        "utility",
        "utilities",
        "assist",
        "assists",
        "assistant",
    }
)
_MIN_TOKEN_LEN = 3
_DEFAULT_OVERLAP_THRESHOLD = 0.3


def _keywords(description: str) -> set[str]:
    """Description text only - deliberately excludes the skill's own name (see
    module docstring). Filters both ordinary English stopwords and generic
    skill-description prose words that would otherwise skew results."""
    tokens = re.findall(r"[a-z0-9]+", description.lower())
    return {
        t
        for t in tokens
        if len(t) >= _MIN_TOKEN_LEN
        and t not in _STOPWORDS
        and t not in _GENERIC_SKILL_WORDS
    }


def is_thin_description(description: str, min_keywords: int = 5) -> bool:
    """True if a description has too few non-generic keywords to be a
    reliable match candidate for anything specific (e.g. "Helps with PDF
    stuff" or a generic meta-skill like a skill-authoring template).

    Reused by core/intent_parser.py to exclude exactly this class of skill
    from local-matching candidate pools - found necessary 2026-06-20 when
    "template-skill" (a generic skill-authoring template) matched against
    nearly every unrelated capability need during testing, the same
    over-matching failure mode the crowding check above already targets.

    Threshold is 5, not the 3 first tried: "Replace with description of the
    skill and when Claude should use it." (template-skill's actual, unfilled
    placeholder description) has exactly 3 non-generic keywords and slipped
    through at that threshold - caught by re-testing against real data, not
    reasoned out in advance. That description being literal template
    boilerplate rather than a real description at all is a separate, useful
    finding - see todo.md for a planned spec_compliance.py check to detect
    unfilled placeholder text specifically, which this heuristic cannot do.
    """
    return len(_keywords(description)) < min_keywords


@dataclass
class CrowdingPair:
    skill_a: str
    skill_b: str
    overlap: float
    shared_keywords: list[str]
    smaller: str  # the skill with fewer keywords - the one more at risk


def detect_crowding(
    skills: dict[str, str], threshold: float = _DEFAULT_OVERLAP_THRESHOLD
) -> list[CrowdingPair]:
    """skills: {name: description}, all sharing one audited folder/budget.

    Returns flagged pairs, worst overlap first.
    """
    keyword_sets = {name: _keywords(desc) for name, desc in skills.items()}
    names = list(keyword_sets)
    pairs: list[CrowdingPair] = []
    for i, a in enumerate(names):
        for b in names[i + 1 :]:
            kw_a, kw_b = keyword_sets[a], keyword_sets[b]
            if not kw_a or not kw_b:
                continue
            shared = kw_a & kw_b
            if not shared:
                continue
            overlap = len(shared) / min(len(kw_a), len(kw_b))
            if overlap >= threshold:
                smaller = a if len(kw_a) <= len(kw_b) else b
                pairs.append(
                    CrowdingPair(
                        skill_a=a,
                        skill_b=b,
                        overlap=overlap,
                        shared_keywords=sorted(shared),
                        smaller=smaller,
                    )
                )
    pairs.sort(key=lambda p: -p.overlap)
    return pairs
