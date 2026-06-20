"""Tests for core/launch.py. subprocess.Popen and shutil.which are mocked
(the external dependencies per testing.md) - a real launch would spawn an
actual Claude Code session as a side effect, which a test must never do.
"""

from pathlib import Path

import pytest

from skill_scan.core.launch import (
    LaunchError,
    claude_code_available,
    launch_claude_code,
)


def test_claude_code_available_reflects_which_result(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/claude")
    assert claude_code_available() is True

    monkeypatch.setattr("shutil.which", lambda name: None)
    assert claude_code_available() is False


def test_launch_claude_code_raises_when_not_found(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    with pytest.raises(LaunchError):
        launch_claude_code(Path("/some/project"))


def test_launch_claude_code_strips_api_key_by_default(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-should-not-leak")
    captured = {}

    def fake_popen(args, cwd=None, env=None):
        captured["args"] = args
        captured["cwd"] = cwd
        captured["env"] = env
        return "fake-process"

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    launch_claude_code(Path("/some/project"))

    assert "ANTHROPIC_API_KEY" not in captured["env"]
    assert captured["cwd"] == "/some/project" or captured["cwd"] == str(
        Path("/some/project")
    )


def test_launch_claude_code_keeps_api_key_when_explicitly_allowed(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-explicitly-allowed")
    captured = {}

    def fake_popen(args, cwd=None, env=None):
        captured["env"] = env
        return "fake-process"

    monkeypatch.setattr("subprocess.Popen", fake_popen)
    launch_claude_code(Path("/some/project"), allow_api_billing=True)

    assert captured["env"]["ANTHROPIC_API_KEY"] == "sk-explicitly-allowed"
