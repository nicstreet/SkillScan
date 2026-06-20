"""Tests for core/intent_parser.py.

LLM calls are mocked (the external dependency, per testing.md) - these tests
exercise the parsing/validation logic around the LLM, not the model's actual
output quality, which was instead validated manually against the real local
skill corpus (see .claude/architecture/todo.md, "Project Setup & Skill Supply
Chain" -> Validation protocol, and the manual test run 2026-06-20).
"""

import json

import pytest

from skill_scan.core.intent_parser import (
    IntentParserError,
    IntentResult,
    ProcessStage,
    match_local_skills,
    parse_intent,
)


def test_parse_intent_returns_structured_result(monkeypatch):
    response = json.dumps(
        {
            "project_type": "PyQt6 desktop app",
            "stack": "Python 3.13, PyQt6",
            "summary": "A small desktop tool.",
            "stages": [
                {
                    "name": "Setup",
                    "goal": "Scaffold the project.",
                    "skills_needed": ["PyQt6 GUI design"],
                }
            ],
        }
    )
    monkeypatch.setattr(
        "skill_scan.core.intent_parser.call_llm_sync", lambda *a, **k: response
    )
    result = parse_intent("a rough idea")
    assert result.project_type == "PyQt6 desktop app"
    assert len(result.stages) == 1
    assert result.stages[0].skills_needed == ["PyQt6 GUI design"]


def test_parse_intent_raises_on_unparseable_response(monkeypatch):
    monkeypatch.setattr(
        "skill_scan.core.intent_parser.call_llm_sync",
        lambda *a, **k: "not json at all",
    )
    with pytest.raises(IntentParserError):
        parse_intent("a rough idea")


def test_intent_result_all_skills_needed_deduplicates_across_stages():
    intent = IntentResult(
        project_type="x",
        stack="x",
        summary="x",
        stages=[
            ProcessStage("Setup", "goal", ["PyQt6 GUI design", "Python scripting"]),
            ProcessStage("Build", "goal", ["Python scripting", "Database setup"]),
        ],
    )
    assert intent.all_skills_needed() == [
        "PyQt6 GUI design",
        "Python scripting",
        "Database setup",
    ]


def _intent_with_one_need(need: str) -> IntentResult:
    return IntentResult(
        project_type="x",
        stack="x",
        summary="x",
        stages=[ProcessStage("Setup", "goal", [need])],
    )


def test_match_local_skills_filters_out_hallucinated_names(monkeypatch):
    """Regression: the local model returned 'pyqt6-layout-management' as a
    match for 'PyQt6 layout management' - a plausible-sounding name that does
    not exist in the real corpus, despite the prompt saying 'exact names as
    given'. The code must validate against the actual candidate pool, not
    trust the LLM's output."""
    response = json.dumps(
        {"PyQt6 layout management": ["pyqt6-layout-management", "pyqt6-toolbar"]}
    )
    monkeypatch.setattr(
        "skill_scan.core.intent_parser.call_llm_sync", lambda *a, **k: response
    )
    local_skills = {
        "pyqt6-toolbar": (
            "Build PyQt6 toolbars with icon buttons, separators, and "
            "overflow menus for frameless application windows."
        ),
        "pyqt6-menus": (
            "Build hover-triggered PyQt6 menus that open on mouse-enter "
            "and close automatically when the cursor leaves both the "
            "trigger button and the menu."
        ),
    }
    intent = _intent_with_one_need("PyQt6 layout management")
    matches = match_local_skills(intent, local_skills)
    # pyqt6-toolbar kept (real candidate); pyqt6-layout-management dropped
    # (hallucinated - never offered as a candidate).
    assert matches["PyQt6 layout management"] == ["pyqt6-toolbar"]


def test_match_local_skills_excludes_thin_description_skills_from_candidates(
    monkeypatch,
):
    """Regression: template-skill's unfilled placeholder description matched
    against nearly every capability need during manual testing. Thin-
    description skills must never reach the LLM as candidates at all."""
    calls: list[str] = []

    def fake_call(prompt: str, **kwargs):
        calls.append(prompt)
        return json.dumps({"writing tests": []})

    monkeypatch.setattr("skill_scan.core.intent_parser.call_llm_sync", fake_call)
    local_skills = {
        "template-skill": "Replace with description of the skill and when Claude should use it.",
        "webapp-testing": "Write and run automated browser-driven end-to-end tests.",
    }
    intent = _intent_with_one_need("writing tests")
    match_local_skills(intent, local_skills)
    assert "template-skill" not in calls[0]
    assert "webapp-testing" in calls[0]


def test_match_local_skills_returns_empty_for_every_need_with_no_local_skills():
    intent = _intent_with_one_need("anything")
    assert match_local_skills(intent, {}) == {"anything": []}
