# Spec: Skill Linter

> **Status:** Active
> **Owner:** Ritebook maintainers
> **Spec version:** 1.2
> **Last reviewed:** 2026-09-29
> **Implementation state:** Implemented
> **Dependencies:** [Shared Catalog Contract](shared-catalog-contract-spec.md)
> **Associated ADRs:** None

## Objective

Ritebook provides a validation-only workflow for skill authors, maintainers, CI,
and the publisher slice. It discovers catalog candidates, validates each
`SKILL.md` header, and emits deterministic path-scoped diagnostics without
modifying publisher or consumer state.

## Current context

- The linter is implemented as the `src/ritebook/features/skill_linter/` vertical slice.
- The `skills lint` command exposes the validation use case directly.
- The publisher calls the linter through an application boundary as a hard
  precondition for index generation.
- Filesystem discovery and YAML parsing remain in outbound adapters.
- The application validator accepts the minimal two-field Agent Skills header,
  validates all supported optional fields, and rejects unknown or invalid fields
  without exposing source contents.
- Filesystem discovery reports the raw candidate count and translates per-file
  parse, read, and UTF-8 failures into deterministic path-scoped issues while root
  inspection failures remain command-level errors.
- Standalone lint, publisher prechecks, and contribution validation reuse the same
  linter application boundary.

## Assumptions

- Ritebook supports Python 3.13 or newer and uses `uv` for command execution.
- The shared catalog contract remains the source of truth for identifiers and
  catalog paths.
- The [Agent Skills specification](https://agentskills.io/specification) and its
  [`skills-ref` reference validator](https://github.com/agentskills/agentskills/tree/main/skills-ref)
  define the external header compatibility baseline reviewed on 2026-09-29.
- Ritebook catalog path constraints remain separate from header compatibility and
  may be stricter where the shared catalog contract requires canonical ASCII
  identifiers.
- Unresolved assumptions: None.

## Desired behavior

```bash
uv run ritebook skills lint --root <path>
```

- Require an explicit `--root`.
- Discover candidate skill directories using the catalog structure defined by the
  shared catalog contract.
- Validate every discovered `SKILL.md` against the Agent Skills-compliant header.
- Count every visible, non-symlinked `SKILL.md` returned by raw filesystem
  discovery, including candidates that later fail catalog-path, read, parse, or
  header validation.
- Accept the minimal standard header containing only `name` and `description`.
- Validate standard optional fields when they are present without requiring
  Ritebook-specific metadata.
- Emit deterministic, path-scoped validation output suitable for CI logs.
- Exit with status code `0` only when every discovered skill is valid.
- Exit non-zero when a skill is invalid or the skills root cannot be inspected.
- Do not write or update `ritebook-index.json` or consumer state.
- Expose the same validation behavior to the publisher so lint and publication
  rules cannot drift.

## Skill header contract

Every discovered `SKILL.md` must begin with YAML frontmatter. The minimal Agent
Skills-compliant header is:

```yaml
---
name: conventional-commits
description: Write, review, and validate Conventional Commits messages. Use when creating or checking commit messages.
---
```

A header may also use the standard optional fields:

```yaml
---
name: conventional-commits
description: Write, review, and validate Conventional Commits messages. Use when creating or checking commit messages.
license: MIT
compatibility: Requires Git.
metadata:
  author: ritebook
  version: "1.0.1"
allowed-tools: Bash(git:*) Read
---
```

Validation requirements:

- Frontmatter starts on the first line with `---` and has a closing `---` before
  the Markdown body.
- The bounded frontmatter block parses with `yaml.safe_load()` to a mapping.
- Only `name`, `description`, `license`, `compatibility`, `metadata`, and
  `allowed-tools` are accepted as top-level frontmatter fields.
- `name` is required and is a non-empty string of at most 64 characters.
- `name` contains only lowercase alphanumeric characters and hyphens, does not
  start or end with a hyphen, does not contain consecutive hyphens, and matches
  the parent skill directory name.
- The shared catalog contract separately requires Ritebook catalog path segments
  to be canonical ASCII identifiers.
- `description` is required, is a non-whitespace string of at most 1024
  characters, and explains both what the skill does and when to use it.
- `description` contains no C0, DEL, or C1 control characters. Ordinary Unicode
  text remains valid and is preserved.
- `license` is optional. When present, it is a string naming the license or a
  bundled license file.
- `compatibility` is optional. When present, it is a non-empty string of at most
  500 characters describing meaningful environment requirements.
- `metadata` is optional. When present, it is a flat mapping from string keys to
  string values. Numeric, boolean, null, sequence, and nested mapping values are
  invalid.
- Values such as versions that YAML could interpret as another scalar type must
  be quoted to remain strings.
- Structured tool and environment requirements belong in `compatibility`.
  Related-skill guidance belongs in the Markdown body rather than `metadata`.
- `allowed-tools` is optional. When present, it is a space-separated string of
  pre-approved tools. Support remains agent-dependent because the field is
  experimental in the Agent Skills specification.
- Ritebook-specific nested values such as `metadata.dependencies` are not part of
  the Agent Skills header schema and must not be required for a skill to pass.
- The Markdown body after the frontmatter is outside the header schema and has no
  additional format restrictions.

## Diagnostics

- Validation output identifies the skill file path and violated rule without
  printing the file contents.
- Multiple findings are ordered deterministically.
- Control characters reaching the CLI are rendered as visible deterministic ASCII
  escapes such as `\\n`, `\\t`, or `\\x1b`.
- Missing or unreadable roots and malformed frontmatter produce concise
  user-facing errors at the adapter boundary.
- Malformed YAML produces the exact path-scoped message
  `frontmatter must be valid YAML.`.
- A discovered file that cannot be read as UTF-8 text produces the exact
  path-scoped message `skill file must be readable UTF-8 text.`.
- Successful standalone lint reports `Checked N skill(s)`, where `N` is the raw
  discovery count defined above.

Example:

```text
conventional-commits/SKILL.md: metadata values must be strings.
```

## Commands and validation

- Test: `uv run pytest tests/unit/features/skill_linter`
- Lint and static checks: `uv run ruff check . && uv run ty check src/ritebook`
- Manual verification: `uv run ritebook skills lint --root <path>`

## Project structure

- `src/ritebook/features/skill_linter/application/`: validation use cases, DTOs, ports,
  and application errors.
- `src/ritebook/features/skill_linter/adapters/inbound/`: CLI integration.
- `src/ritebook/features/skill_linter/adapters/outbound/`: discovery and frontmatter
  adapters.
- `tests/unit/features/skill_linter/`: focused application and adapter tests.
- `LintSkillsResult.discovered_skill_count` is the raw discovery count.
  `SkillValidationReport.validated_skill_count` remains the parsed-header count
  passed to field validation, and publisher prechecks map the raw count to their
  existing `checked_skill_count` field.

## Conventions

- Keep filesystem and YAML parsing in outbound adapters and CLI rendering in the
  inbound adapter.
- Render diagnostics deterministically without raw skill-file contents or terminal
  control bytes.

## Testing strategy

- Application tests cover the minimal two-field header, every supported optional
  field, missing or malformed frontmatter, unexpected top-level fields, invalid
  names, name/path mismatches, whitespace-only and overlong descriptions,
  overlong compatibility text, non-string metadata keys or values, nested legacy
  metadata, deterministic finding order, and adapter failures.
- Adapter tests cover root and collection child discovery, ignored non-skill
  directories, over-deep paths, mixed nodes, hidden directories, unreadable paths,
  and path-scoped parse failures.
- CLI tests cover argument mapping, success and failure exit behavior, visible
  control-character escapes, and concise diagnostics.
- Tests use temporary directories and do not depend on global state or network
  access.

## Boundaries

### Always

- Keep YAML parsing and filesystem traversal in adapters.
- Keep validation orchestration independent of the publisher and CLI.
- Share the linter through an application port; do not import adapter internals
  across slices.
- Do not mutate skill files, publisher indexes, registry state, or install state.
- Do not log or print raw skill contents.
- Changes to catalog depth, identifiers, or path semantics belong in the shared
  catalog contract.

### Ask first

- Expanding the accepted header beyond fields defined by the Agent Skills
  specification or changing the catalog path model.
- Adding mutation behavior to the validation-only workflow.

### Never

- Mutate skill files, publisher indexes, registry state, or install state.
- Log or print raw skill contents.

## Success criteria

- Authors and CI can validate an explicit skills root without generating an index.
- The minimal Agent Skills header with only `name` and `description` passes.
- Standard optional header fields pass when their values satisfy the Agent Skills
  specification.
- Unknown top-level fields, invalid optional-field values, and nested metadata
  values fail with deterministic path-scoped diagnostics.
- Ritebook does not require non-standard metadata for header validity.
- Catalog identifier and path checks remain enforced independently through the
  shared catalog contract.
- Publisher index generation uses the same validation use case and cannot write an
  index after validation failure.
- Unit tests cover application, adapter, and CLI behavior.

## Open questions

None for the current specification version.
