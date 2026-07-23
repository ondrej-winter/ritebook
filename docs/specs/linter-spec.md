# Spec: Skill Linter

> **Status:** Active
> **Owner:** Ritebook maintainers
> **Spec version:** 1.0
> **Last reviewed:** 2026-07-23
> **Implementation state:** Implemented
> **Dependencies:** [Shared Catalog Contract](shared-catalog-contract-spec.md)
> **Associated ADRs:** None

## Objective

Ritebook provides a validation-only workflow for skill authors, maintainers, CI,
and the publisher slice. It discovers catalog candidates, validates each
`SKILL.md` header, and emits deterministic path-scoped diagnostics without
modifying publisher or consumer state.

## Implementation status

- The linter is implemented as the `src/ritebook/features/linter/` vertical slice.
- The `lint-skills` command exposes the validation use case directly.
- The publisher calls the linter through an application boundary as a hard
  precondition for index generation.
- Filesystem discovery and YAML parsing remain in outbound adapters.

## Desired behavior

```bash
uv run ritebook lint-skills --skills-root <path>
```

- Require an explicit `--skills-root`.
- Discover candidate skill directories using the catalog structure defined by the
  shared catalog contract.
- Validate every discovered `SKILL.md` against the required Agent Skill header.
- Emit deterministic, path-scoped validation output suitable for CI logs.
- Exit with status code `0` only when every discovered skill is valid.
- Exit non-zero when a skill is invalid or the skills root cannot be inspected.
- Do not write or update `ritebook-index.json` or consumer state.
- Expose the same validation behavior to the publisher so lint and publication
  rules cannot drift.

## Skill header contract

Every discovered `SKILL.md` must begin with YAML frontmatter shaped like:

```yaml
---
name: conventional-commits
description: Write, review, and validate Conventional Commits messages.
metadata:
  version: "1.0.1"
  dependencies:
    tools:
      - name: git
        purpose: Inspect repository state.
        required: false
    skills:
      - name: git-workflow-and-versioning
        purpose: Apply repository-safe Git workflow practices.
        required: false
---
```

Validation requirements:

- Frontmatter starts on the first line with `---` and has a closing `---` before
  the Markdown body.
- The bounded frontmatter block parses with `yaml.safe_load()` to a mapping.
- `name` is required, is a canonical Ritebook identifier, and matches the parent
  skill directory name.
- `description` is a non-empty string of at most 1024 characters.
- `description` contains no C0, DEL, or C1 control characters. Ordinary Unicode
  text remains valid and is preserved.
- `metadata` is a required mapping.
- `metadata.version` is a required string.
- `metadata.dependencies` is a required mapping.
- `metadata.dependencies.tools` and `metadata.dependencies.skills` are required
  lists.
- Every dependency item is a mapping with non-empty string `name` and `purpose`
  fields and a boolean `required` field. Plain strings are invalid.

## Diagnostics

- Validation output identifies the skill file path and violated rule without
  printing the file contents.
- Multiple findings are ordered deterministically.
- Control characters reaching the CLI are rendered as visible deterministic ASCII
  escapes such as `\\n`, `\\t`, or `\\x1b`.
- Missing or unreadable roots and malformed frontmatter produce concise
  user-facing errors at the adapter boundary.

Example:

```text
conventional-commits/SKILL.md: metadata.dependencies.skills must be a list.
```

## Project structure

- `src/ritebook/features/linter/application/`: validation use cases, DTOs, ports,
  and application errors.
- `src/ritebook/features/linter/adapters/inbound/`: CLI integration.
- `src/ritebook/features/linter/adapters/outbound/`: discovery and frontmatter
  adapters.
- `tests/unit/features/linter/`: focused application and adapter tests.

## Testing strategy

- Application tests cover valid metadata, missing frontmatter, malformed YAML,
  invalid names, name/path mismatches, missing required metadata, malformed
  dependencies, deterministic finding order, and adapter failures.
- Adapter tests cover root and collection child discovery, ignored non-skill
  directories, over-deep paths, mixed nodes, hidden directories, unreadable paths,
  and path-scoped parse failures.
- CLI tests cover argument mapping, success and failure exit behavior, visible
  control-character escapes, and concise diagnostics.
- Tests use temporary directories and do not depend on global state or network
  access.

## Boundaries

- Keep YAML parsing and filesystem traversal in adapters.
- Keep validation orchestration independent of the publisher and CLI.
- Share the linter through an application port; do not import adapter internals
  across slices.
- Do not mutate skill files, publisher indexes, registry state, or install state.
- Do not log or print raw skill contents.
- Changes to catalog depth, identifiers, or path semantics belong in the shared
  catalog contract.

## Success criteria

- Authors and CI can validate an explicit skills root without generating an index.
- Every discovered skill is checked against one deterministic header contract.
- Invalid skills produce path-scoped diagnostics and a non-zero exit status.
- Publisher index generation uses the same validation use case and cannot write an
  index after validation failure.
- Unit tests cover application, adapter, and CLI behavior.
