---
name: run-python-tests
description: Runs automated tests for a Python project using pytest.
---

# Skill: Run Python Tests

Use this skill to run automated tests for a Python project using `pytest`.

## Prerequisites

- `uv` is installed and configured for the project.
- `pytest` is installed as a development dependency and configured in `pyproject.toml`.

## Steps

### 1. Run all tests

```bash
uv run pytest
```

This command executes all tests defined in the project.

### 2. Run focused tests (optional)

```bash
uv run pytest tests/<path_to_test_file>
uv run pytest -k "<pattern>"
```

Use these commands to run a subset of tests during development.

## When tests fail

- Read the test output to identify the failing test and the assertion or exception that caused the failure.
- Fix the root cause in the source code or test rather than skipping or deleting the test.
- Use `uv run pytest -x` to stop at the first failure during iterative debugging.
- For flaky or slow tests, document the reason and mitigation in the handoff notes rather than silently ignoring them.
- After fixes, re-run the full test suite with `uv run pytest` before handoff.
