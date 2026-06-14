---
paths:
  - "tests/**/*.py"
  - "src/**/*.py"
---

# Testing Rules

## Requirements

- Unit tests mandatory for every module
- Use pytest
- Tests live in `tests/` mirroring `src/` structure
- Run tests before every commit

```bash
pytest tests/ -v
pytest --cov=src --cov-report=html
```

## Structure

```
tests/
├─ test_skill_parser.py    (mirrors src/scanners/skill_scanner.py)
├─ test_mcp_scanner.py     (mirrors src/scanners/mcp_scanner.py)
└─ test_ui_models.py       (mirrors src/models/)
```

## Conventions

```python
def test_scan_mcp_returns_skills_on_success():
    """Descriptive name: what it does when condition is met."""
    mock_response = {"skills": ["search", "write"]}
    result = scan_mcp("test-mcp", mock_response)
    assert result.skills == ["search", "write"]

def test_scan_mcp_raises_on_empty_response():
    with pytest.raises(ValueError, match="Empty MCP response"):
        scan_mcp("test-mcp", {})
```

**Rules:**
- Test names describe behaviour: `test_{what}_{when}_{expected}`
- Mock external dependencies (API calls, file system), not internal modules
- Clean up side effects in `teardown` or use `tmp_path` fixture
- One assertion per test where possible
- Test edge cases: empty responses, timeouts, malformed data
