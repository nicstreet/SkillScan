"""Tests for core/skill_crowding.py - the domain-crowding heuristic.

Regression coverage for two real bugs caught during calibration (2026-06-20),
both the same risk class - something in a description that doesn't carry
domain signal skewing the overlap score - via two different vectors:

1. Including the skill's own *name* in keyword extraction let generic naming
   suffixes ("-builder", "-helper") both dilute genuine overlap below
   threshold and create false matches between unrelated same-suffix skills.
2. Generic skill-description *prose* ("create and edit...", "use this skill
   whenever...") produced false-positive overlap between genuinely unrelated
   domains, independent of the name issue.

Each test below maps to a specific real finding, not a hypothetical case.
"""

from skill_scan.core.skill_crowding import detect_crowding, is_thin_description


def test_detect_crowding_flags_vague_clear_twin_pair():
    """The actual empirically-validated case: evals/skill_selection/'s
    twin-pair test found pdf-helper measurably degrading pdf-builder's
    real selection accuracy (100% -> 60%) - this is the case the whole
    check exists to catch."""
    skills = {
        "pdf-builder": (
            "Create, merge, split, and fill PDF documents - extract text and "
            "tables from existing PDFs and generate new ones from structured "
            "content."
        ),
        "pdf-helper": "Helps with PDF stuff.",
    }
    pairs = detect_crowding(skills)
    assert len(pairs) == 1
    assert {pairs[0].skill_a, pairs[0].skill_b} == {"pdf-builder", "pdf-helper"}
    assert pairs[0].smaller == "pdf-helper"
    assert "pdf" in pairs[0].shared_keywords


def test_detect_crowding_ignores_generic_naming_suffix_in_skill_name():
    """Regression: '-builder'/'-helper' suffixes in the NAME must not create
    false matches between otherwise-unrelated skills (caught when mcp-builder
    and pptx-builder falsely flagged before the name was excluded from
    extraction entirely)."""
    skills = {
        "mcp-builder": (
            "Scaffold and implement Model Context Protocol (MCP) servers, "
            "including tool definitions, schemas, and transport setup."
        ),
        "pptx-builder": (
            "Build PowerPoint presentations: slide layouts, charts, speaker "
            "notes, and theme-consistent formatting."
        ),
    }
    assert detect_crowding(skills) == []


def test_detect_crowding_ignores_generic_template_phrasing_in_description():
    """Regression: generic skill-authoring prose ('create and edit...') must
    not create false matches between genuinely unrelated domains (caught when
    docx-writer and xlsx-helper falsely flagged at 30% on shared {create,
    edit, tables} - none of which actually distinguish Word from Excel)."""
    skills = {
        "docx-writer": (
            "Create and edit Word documents with headings, tables, styles, "
            "and tracked changes for review workflows."
        ),
        "xlsx-helper": (
            "Create and edit Excel spreadsheets - formulas, pivot tables, "
            "conditional formatting, and charts."
        ),
    }
    assert detect_crowding(skills) == []


def test_detect_crowding_returns_empty_for_clearly_unrelated_skills():
    skills = {
        "algorithmic-art": (
            "Generate generative and algorithmic art using code-driven "
            "visual patterns such as noise fields, flow fields, and tiling."
        ),
        "internal-comms": (
            "Draft internal company communications - announcements, memos, "
            "policy updates, and team newsletters."
        ),
    }
    assert detect_crowding(skills) == []


def test_detect_crowding_skips_skills_with_empty_or_missing_description():
    skills = {"a": "", "b": "Build PowerPoint presentations with charts."}
    assert detect_crowding(skills) == []


def test_detect_crowding_sorts_worst_overlap_first():
    skills = {
        "pdf-builder": "Create, merge, split, and fill PDF documents.",
        "pdf-helper": "Helps with PDF stuff.",
        "pdf-reader": "Helps with PDF stuff and other documents too maybe.",
    }
    pairs = detect_crowding(skills)
    assert len(pairs) >= 2
    overlaps = [p.overlap for p in pairs]
    assert overlaps == sorted(overlaps, reverse=True)


def test_detect_crowding_respects_custom_threshold():
    skills = {
        "a": "Build PowerPoint presentations with charts and themes.",
        "b": "Build interactive web demos with charts and layouts.",
    }
    # Shared: {charts} only - real but narrow overlap, won't clear the
    # default 0.3 threshold; a much lower threshold should still catch it.
    assert detect_crowding(skills, threshold=0.9) == []
    assert detect_crowding(skills, threshold=0.05) != []


def test_is_thin_description_flags_unfilled_template_boilerplate():
    """Regression: core/intent_parser.py's local-matching candidate filter
    (2026-06-20) initially missed this exact description at threshold=3 -
    it has exactly 3 non-generic keywords ({description, should, replace}),
    and the off-by-one (`< 3`) let it through. This is template-skill's
    actual, real, unfilled placeholder description, not a hypothetical."""
    assert is_thin_description(
        "Replace with description of the skill and when Claude should use it."
    )


def test_is_thin_description_does_not_flag_a_real_specific_description():
    assert not is_thin_description(
        "Create, merge, split, and fill PDF documents - extract text and "
        "tables from existing PDFs and generate new ones from structured "
        "content."
    )


def test_is_thin_description_flags_empty_string():
    assert is_thin_description("")
