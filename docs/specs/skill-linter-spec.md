# Specification: Skill Linter

## Status

- State: Active
- Revision: 1.3
- Acceptance basis: Existing Active repository contract; format normalized under the user's October 2, 2026 instruction without changing normative behavior.
- Accepted by / on: Original accepting person and date were not recorded.
- Owner: Ritebook maintainers
- Last reviewed: 2026-10-02
- Implementation state: Implemented
- Dependencies: [Shared Catalog Contract](shared-catalog-contract-spec.md)
- Associated ADRs: [ADR 0002](../adr/0002-adopt-agent-skills-as-canonical-skill-schema.md)
- Supersedes: None

## Objective and Context

Ritebook provides a validation-only workflow for skill authors, maintainers, CI,
and the publisher slice. It discovers catalog candidates, validates each
`SKILL.md` header, and emits deterministic path-scoped diagnostics without
modifying publisher or consumer state.

### Current-state evidence

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

## Scope

- In scope: Explicit-root skill discovery, Agent Skills-compatible header
  validation, deterministic diagnostics and exit behavior, and reuse of the same
  validation application boundary by publisher and contribution workflows.
- Out of scope: Mutating skill files or consumer state, changing catalog path
  semantics, and accepting header fields outside the adopted Agent Skills schema.

## Requirements

The following requirement groups preserve the normative linter contract of revision 1.3.

### R1 — Validation workflow

**Basis:** Existing active Ritebook contract, the Shared Catalog Contract, and ADR 0002.

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
- Accept compatible profiles and extensions only when they remain valid under the
  canonical Agent Skills schema.
- Emit deterministic, path-scoped validation output suitable for CI logs.
- Exit with status code `0` only when every discovered skill is valid.
- Exit non-zero when a skill is invalid or the skills root cannot be inspected.
- Do not write or update `ritebook-index.json` or consumer state.
- Expose the same validation behavior to the publisher so lint and publication
  rules cannot drift.

### R2 — Skill header contract

**Basis:** Existing active Ritebook contract and ADR 0002.

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
- Compatible local metadata keys, including reasonably unique or namespaced keys,
  are accepted when their values are strings. Ritebook treats them as opaque
  metadata and does not require them for portable validity.
- Values such as versions that YAML could interpret as another scalar type must
  be quoted to remain strings.
- Structured tool and environment requirements belong in `compatibility`.
  Related-skill guidance belongs in the Markdown body rather than `metadata`.
- `allowed-tools` is optional. When present, it is a space-separated string of
  pre-approved tools. Support remains agent-dependent because the field is
  experimental in the Agent Skills specification.
- Ritebook-specific nested values such as `metadata.dependencies` are not part of
  the Agent Skills header schema and are invalid.
- Compatible extensions use canonical optional fields, Markdown body content, or
  optional supporting files. Ritebook does not add custom top-level fields.
- Upstream specification changes require a reviewed specification and test update;
  remote documentation changes do not silently alter released behavior.
- The Markdown body after the frontmatter is outside the header schema and has no
  additional format restrictions.

### R3 — Diagnostics

**Basis:** Existing active Ritebook contract and the dependencies recorded in the Status section.

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

## Implementation and Verification Evidence

### Commands and validation

- Test: `uv run pytest tests/unit/features/skill_linter`
- Lint and static checks: `uv run ruff check . && uv run ty check src/ritebook`
- Manual verification: `uv run ritebook skills lint --root <path>`

### Project structure

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

### Conventions

- Keep filesystem and YAML parsing in outbound adapters and CLI rendering in the
  inbound adapter.
- Render diagnostics deterministically without raw skill-file contents or terminal
  control bytes.

### Testing strategy

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

## Constraints and Execution Boundaries

### Binding constraints

- Keep YAML parsing and filesystem traversal in adapters.
- Keep validation orchestration independent of the publisher and CLI.
- Share the linter through an application port; do not import adapter internals
  across slices.
- Do not mutate skill files, publisher indexes, registry state, or install state.
- Do not log or print raw skill contents.
- Changes to catalog depth, identifiers, or path semantics belong in the shared
  catalog contract.

### Changes requiring specification approval

- Expanding the accepted header beyond fields defined by the Agent Skills
  specification or changing the catalog path model.
- Adding mutation behavior to the validation-only workflow.

### Exclusions and prohibited behavior

- Mutate skill files, publisher indexes, registry state, or install state.
- Log or print raw skill contents.

## Acceptance Checks

| ID | Requirement | Conditions and action | Expected observable result | Verification method |
| --- | --- | --- | --- | --- |
| AC1 | R1 | Run `skills lint` with an explicit valid, invalid, or unreadable root. | Every visible non-symlinked candidate is counted; valid roots exit `0`; invalid candidates or root inspection failures exit non-zero; no publisher or consumer state is written. | Application, discovery-adapter, and CLI tests. |
| AC2 | R2 | Validate minimal headers, supported optional fields, flat string metadata, unknown fields, malformed values, and catalog/path mismatches. | Agent Skills-compatible values pass without Ritebook-only metadata; unsupported, malformed, nested, or mismatched values fail with path-scoped findings. | Header-validator and frontmatter-adapter tests. |
| AC3 | R3 | Render multiple validation, parse, read, UTF-8, and control-character failures. | Findings use stable path/code/message ordering, controls are visible ASCII escapes, ordinary Unicode is preserved, and raw skill contents are not emitted. | Application ordering and CLI rendering tests. |
| AC4 | R1, R2 | Publisher or contribution validation invokes the linter application boundary and receives a failure. | The same validation rules apply and the caller cannot publish or commit invalid skill content. | Publisher and contribution adapter tests. |
| AC5 | R1-R3 | Execute the focused linter unit suite. | Application, adapter, and CLI behaviors represented by this specification pass without live network or global-state dependencies. | `uv run pytest tests/unit/features/skill_linter`. |

## Assumptions

- Ritebook supports Python 3.13 or newer and uses `uv` for command execution.
- The shared catalog contract remains the source of truth for identifiers and
  catalog paths.
- The [Agent Skills specification](https://agentskills.io/specification) and its
  [`skills-ref` reference validator](https://github.com/agentskills/agentskills/tree/main/skills-ref)
  define the canonical external header compatibility baseline reviewed on
  2026-10-02.
- Ritebook catalog path constraints remain separate from header compatibility and
  may be stricter where the shared catalog contract requires canonical ASCII
  identifiers.
- Material unresolved assumptions: None.

## Open Questions

None.

## Revision and Handoff Notes

- October 2, 2026: Reformatted revision 1.3 to the current
  spec-driven-development template under the user's instruction. Requirement
  meaning, lifecycle state, and revision number were preserved.
- Next authorized step: Treat this Active revision as canonical. Changes to the
  adopted header schema or catalog model require specification and ADR review as
  described above.
