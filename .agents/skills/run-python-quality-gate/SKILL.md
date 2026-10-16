---
name: run-python-quality-gate
description: Run the full local Python quality gate with formatting, linting, type checking, and tests before handoff or a pull request.
metadata:
  version: "2.1.2"
  last-verified: "2026-09-30T20:31:51+02:00"
---

# Run Python Quality Gate

Use this skill to run the full local quality gate for a Python project, including formatting, linting, type checking, and automated tests.

## Prerequisites

- `uv` is installed and configured for the project.
- `ruff`, `mypy`, and `pytest` are installed as development dependencies and configured in `pyproject.toml`.
- The same skill root provides `format-python-code`, `lint-python-code`, and `run-python-tests`.

## Steps

### 1. Auto-fix and format code

Use the `format-python-code` skill to apply auto-fixes and format the codebase.

### 2. Lint and type check code

Use the `lint-python-code` skill to perform linting and type checking.

### 3. Run automated tests

Use the `run-python-tests` skill to execute all automated tests.

### 4. Verify and report the result

After resolving any failures, run the complete quality gate again. Report the
commands and targets used, whether each check passed, and any check that could not
run with the reason.

## When a step fails

- If any step fails, stop and fix the underlying issue before proceeding to the next step.
- Do not bypass `pyproject.toml`-backed tool configuration with ad hoc flags in the final validation run.
- Run the full quality gate before handoff, even if only a single file changed.
- Pre-commit hooks provide helpful fast feedback, but they do not replace the full local quality gate.
