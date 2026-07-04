---
name: format-python-code
description: Format Python code with ruff and apply safe auto-fixes when a Python project needs consistent style before linting, testing, or handoff.
metadata:
  version: "1.0.0"
---

# Skill: Format Python Code

Use this skill to format Python code and apply safe auto-fixes using `ruff` before linting, testing, or handing off changes.

## Prerequisites

- `uv` is installed and configured for the project.
- `ruff` is installed as a development dependency and configured in `pyproject.toml`.

## Steps

### 1. Apply auto-fixes and format

```bash
uv run ruff check . --fix
uv run ruff format .
```

These commands will automatically reformat Python code and apply any safe linting auto-fixes.

### 2. Review the result

Review the changed files before continuing. Confirm that formatting and auto-fixes preserved the intended behavior, then continue with the `lint-python-code` step when linting or type checking is required.

## When formatting fails

- If `ruff format .` produces unexpected changes, verify that the project's `pyproject.toml` ruff configuration is correct before overriding the formatter.
- Unfixable lint violations reported by `ruff check . --fix` will be caught and addressed during the `lint-python-code` step.
