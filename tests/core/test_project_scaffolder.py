"""Tests for core/project_scaffolder.py.

Uses pytest's tmp_path fixture for real file I/O (per testing.md: "use
tmp_path fixture" - this module's whole job is writing files, so the
filesystem is the thing under test here, not an external dependency to mock).
"""

import pytest

from skill_scan.core.intent_parser import IntentResult, ProcessStage
from skill_scan.core.project_scaffolder import (
    ScaffoldError,
    resolve_target_dir,
    scaffold_project,
    slugify_project_name,
)


def test_slugify_project_name_converts_spaces_and_case():
    assert (
        slugify_project_name("Photo Collection Organizer")
        == "photo-collection-organizer"
    )


def test_slugify_project_name_strips_punctuation():
    assert slugify_project_name("Todo List Manager (v2)!") == "todo-list-manager-v2"


def test_slugify_project_name_falls_back_when_empty():
    assert slugify_project_name("") == "new-project"
    assert slugify_project_name("!!!") == "new-project"


def test_resolve_target_dir_returns_plain_slug_when_no_collision(tmp_path):
    result = resolve_target_dir(tmp_path, "Photo Collection Organizer")
    assert result == tmp_path / "photo-collection-organizer"


def _mark_as_existing_project(target_dir):
    target_dir.mkdir(parents=True)
    (target_dir / "CLAUDE.md").write_text("already here", encoding="utf-8")


def test_resolve_target_dir_auto_suffixes_on_collision(tmp_path):
    """Regression: two similarly-vague prompts ("stock price tracker",
    "invoice tracker") both got inferred as the same generic project type,
    colliding on the same slug and hard-failing the build. The user never
    typed this name themselves, so the clash shouldn't need their
    intervention to resolve."""
    _mark_as_existing_project(tmp_path / "photo-collection-organizer")
    result = resolve_target_dir(tmp_path, "Photo Collection Organizer")
    assert result == tmp_path / "photo-collection-organizer-2"


def test_resolve_target_dir_keeps_incrementing_past_multiple_collisions(tmp_path):
    for name in (
        "photo-collection-organizer",
        "photo-collection-organizer-2",
        "photo-collection-organizer-3",
    ):
        _mark_as_existing_project(tmp_path / name)
    result = resolve_target_dir(tmp_path, "Photo Collection Organizer")
    assert result == tmp_path / "photo-collection-organizer-4"


def test_resolve_target_dir_reuses_empty_directory_with_matching_name(tmp_path):
    (tmp_path / "photo-collection-organizer").mkdir()
    result = resolve_target_dir(tmp_path, "Photo Collection Organizer")
    assert result == tmp_path / "photo-collection-organizer"


_PYQT6_INTENT = IntentResult(
    project_type="Photo Collection Organizer",
    stack="Python 3.13, PyQt6, SQLAlchemy",
    summary="A desktop app to organize photos and find duplicates.",
    stages=[
        ProcessStage("Setup", "Scaffold the project.", ["PyQt6 GUI design"]),
        ProcessStage("Build", "Implement duplicate detection.", ["Image processing"]),
    ],
)


def test_scaffold_project_creates_skeleton_directories(tmp_path):
    target = tmp_path / "new-project"
    scaffold_project(target, _PYQT6_INTENT)
    for rel in (
        "src",
        "tests",
        "docs",
        ".claude/skills",
        ".claude/commands",
        ".claude/rules",
    ):
        assert (target / rel).is_dir()


def test_scaffold_project_writes_core_files(tmp_path):
    target = tmp_path / "new-project"
    scaffold_project(target, _PYQT6_INTENT)
    for rel in (
        ".gitignore",
        ".claudeignore",
        ".env.example",
        "README.md",
        "CLAUDE.md",
        ".claude/settings.json",
    ):
        assert (target / rel).is_file()


def test_scaffold_project_gitignore_includes_python_section_for_python_stack(tmp_path):
    target = tmp_path / "new-project"
    scaffold_project(target, _PYQT6_INTENT)
    content = (target / ".gitignore").read_text(encoding="utf-8")
    assert "__pycache__" in content
    assert ".env" in content  # universal section still present


def test_scaffold_project_gitignore_omits_python_section_for_non_python_stack(tmp_path):
    intent = IntentResult(
        project_type="Web API",
        stack="Node.js, Express",
        summary="A small REST API.",
        stages=[],
    )
    target = tmp_path / "new-project"
    scaffold_project(target, intent)
    content = (target / ".gitignore").read_text(encoding="utf-8")
    assert "__pycache__" not in content
    assert ".env" in content


def test_scaffold_project_claude_md_includes_plan_and_stack(tmp_path):
    target = tmp_path / "new-project"
    scaffold_project(target, _PYQT6_INTENT)
    content = (target / "CLAUDE.md").read_text(encoding="utf-8")
    assert "Photo Collection Organizer" in content
    assert "Python 3.13, PyQt6, SQLAlchemy" in content
    assert "PyQt6 GUI design" in content
    assert "Setup" in content and "Build" in content


def test_scaffold_project_refuses_to_overwrite_existing_project(tmp_path):
    target = tmp_path / "existing-project"
    target.mkdir()
    (target / "CLAUDE.md").write_text("already here", encoding="utf-8")
    with pytest.raises(ScaffoldError):
        scaffold_project(target, _PYQT6_INTENT)


def test_scaffold_project_wires_in_matched_local_skills(tmp_path):
    source_skill = tmp_path / "source-skills" / "pyqt6-menus"
    source_skill.mkdir(parents=True)
    (source_skill / "SKILL.md").write_text(
        "---\nname: pyqt6-menus\ndescription: test\n---\n", encoding="utf-8"
    )
    (source_skill / "references").mkdir()
    (source_skill / "references" / "example.md").write_text("ref", encoding="utf-8")

    target = tmp_path / "new-project"
    result = scaffold_project(
        target,
        _PYQT6_INTENT,
        matched_skill_paths={"pyqt6-menus": source_skill / "SKILL.md"},
    )

    assert result.wired_skills == ["pyqt6-menus"]
    wired = target / ".claude" / "skills" / "pyqt6-menus"
    assert (wired / "SKILL.md").is_file()
    assert (wired / "references" / "example.md").is_file()
    # Wired skill names show up in the generated CLAUDE.md too.
    assert "pyqt6-menus" in (target / "CLAUDE.md").read_text(encoding="utf-8")


def test_scaffold_project_skips_missing_skill_source_folder(tmp_path):
    target = tmp_path / "new-project"
    result = scaffold_project(
        target,
        _PYQT6_INTENT,
        matched_skill_paths={"ghost-skill": tmp_path / "nowhere" / "SKILL.md"},
    )
    assert result.wired_skills == []
    assert not (target / ".claude" / "skills" / "ghost-skill").exists()
