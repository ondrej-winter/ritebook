---
name: using-python-software-development-skills
description: Discover and invoke Python software development skills. Use when starting Python work or deciding which Python-specific implementation, validation, testing, or documentation skill applies.
metadata:
  version: "2.1.2"
  last-verified: "2026-09-30T20:31:51+02:00"
---

# Using Python Software Development Skills

Use this collection catalog when starting Python software development work or
when you need to discover Python-specific skills. It complements
`using-agnostic-software-development-skills`, which routes technology-independent
engineering workflows.

## Steps

1. Load this skill at session start when working on a Python project.
2. Use `using-agnostic-software-development-skills` alongside this skill for
   shared workflow routing.
3. Check the Python routing guide below before choosing implementation,
   validation, or documentation skills.
4. Prefer the most specific matching skill. Use shared skills for general
   workflow guidance and this collection for Python mechanics.

Use this Python routing guide:

```text
Python task arrives
- Starting a new Python application: bootstrap-python-app
- Adding an end-to-end hexagonal feature: add-hexagonal-feature
- Adding an application boundary: python-add-port
- Adding infrastructure, HTTP, CLI, event, or persistence integration: python-add-adapter
- Building or refactoring an extensible multi-feature product CLI: python-build-extensible-cli
- Adding environment-backed configuration: python-add-env-settings-adapter
- Splitting a growing Python module or package: split-python-module
- Writing or refactoring Python tests: write-pytest-tests
- Running Python tests: run-python-tests
- Formatting Python code: format-python-code
- Linting or type checking Python code: lint-python-code
- Running the complete Python quality gate: run-python-quality-gate
- Adding Python docstrings or useful comments: write-python-docstrings
```

## Skill selection notes

- Use `add-hexagonal-feature` when the change spans domain, application,
  adapters, and tests for one feature slice.
- Use `python-add-port` before `python-add-adapter` when the application-layer
  boundary does not already exist.
- Use `python-build-extensible-cli` when a shared product CLI shell needs
  multiple feature-owned command contributions; use `python-add-adapter` for an
  individual CLI adapter.
- Use `python-add-env-settings-adapter` for configuration sourced from
  environment variables, `.env` files, or runtime settings objects.
- Use `write-pytest-tests` for test design and structure, then
  `run-python-tests` for execution.
- Use `run-python-quality-gate` for the complete pre-handoff validation sequence.
- Use `format-python-code` before `lint-python-code` when both are needed.
