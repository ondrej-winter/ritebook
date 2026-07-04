---
name: local-using-agent-skills
description: Discovers Python hexagonal architecture skills that extend the shared using-agent-skills catalog. Use when starting a session in a Python hexagonal ruleset or when you need to discover local Python-specific skills.
metadata:
  version: "1.0.0"
  dependencies:
    tools: []
    skills:
      - name: add-hexagonal-feature
        purpose: Route end-to-end feature work in Python hexagonal vertical-slice projects.
        required: false
      - name: bootstrap-python-app
        purpose: Route new Python app initialization with uv, tooling, and hexagonal layout.
        required: false
      - name: format-python-code
        purpose: Route Python formatting and safe Ruff auto-fix work.
        required: false
      - name: lint-python-code
        purpose: Route Python linting, static analysis, and type checking work.
        required: false
      - name: python-add-adapter
        purpose: Route inbound or outbound adapter implementation in a Python hexagonal project.
        required: false
      - name: python-add-env-settings-adapter
        purpose: Route environment-backed settings adapter work for Python applications.
        required: false
      - name: python-add-port
        purpose: Route technology-agnostic application port creation in Python hexagonal projects.
        required: false
      - name: run-python-tests
        purpose: Route Python pytest execution work.
        required: false
      - name: split-python-module
        purpose: Route Python module or package splitting while preserving boundaries.
        required: false
      - name: write-pytest-tests
        purpose: Route pytest test creation and refactoring.
        required: false
      - name: write-python-docstrings
        purpose: Route Python docstring and explanatory comment work.
        required: false
---

# Local Using Agent Skills

Use this skill when starting a session in a Python hexagonal architecture
ruleset or when you need to discover local Python-specific skills. It lists
local skills that extend the shared skill catalog with Python-specific and
hexagonal-architecture-specific routing.

## Steps

1. Load this skill at session start when working in a Python hexagonal ruleset.
2. Use `using-agent-skills` alongside this skill for shared workflow routing.
3. Check the local routing guide below before choosing implementation,
   validation, or documentation skills.
4. Prefer the most specific matching skill. Use shared skills for general
   workflow guidance and local skills for Python hexagonal mechanics.

Use this local routing guide:

```text
Python hexagonal task arrives
- Starting a new Python application: bootstrap-python-app
- Adding an end-to-end hexagonal feature: add-hexagonal-feature
- Adding an application boundary: python-add-port
- Adding infrastructure, HTTP, CLI, event, or persistence integration: python-add-adapter
- Adding environment-backed configuration: python-add-env-settings-adapter
- Splitting a growing Python module or package: split-python-module
- Writing or refactoring Python tests: write-pytest-tests
- Running Python tests: run-python-tests
- Formatting Python code: format-python-code
- Linting or type checking Python code: lint-python-code
- Adding Python docstrings or useful comments: write-python-docstrings
```

## Skill selection notes

- Use `add-hexagonal-feature` when the change spans domain, application,
  adapters, and tests for one feature slice.
- Use `python-add-port` before `python-add-adapter` when the application-layer
  boundary does not already exist.
- Use `python-add-env-settings-adapter` for configuration sourced from
  environment variables, `.env` files, or runtime settings objects.
- Use `write-pytest-tests` for test design and structure, then
  `run-python-tests` for execution.
- Use `format-python-code` before `lint-python-code` when both are needed.
