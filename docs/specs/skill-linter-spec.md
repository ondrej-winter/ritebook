# Specification: Skill Linter

## Status

- State: Active
- Revision: 1.5
- Acceptance basis: Existing Active repository contract plus the user's approved October 6 and October 7, 2026 validation decisions.
- Accepted by / on: User / 2026-10-07
- Owner: Ritebook maintainers
- Last reviewed: 2026-10-07
- Implementation state: Implemented
- Dependencies: [Shared Catalog Contract](shared-catalog-contract-spec.md)
- Associated ADRs: [ADR 0002](../adr/0002-adopt-agent-skills-as-canonical-skill-schema.md), [ADR 0003](../adr/0003-publish-from-validated-skill-snapshots.md), and [ADR 0005](../adr/0005-enforce-a-strict-portable-schema-v1-catalog-boundary.md)
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
- Successful lint results expose an immutable publication snapshot; failed lint
  results expose no partial snapshot.
- Standalone lint, publisher prechecks, and contribution validation reuse the same
  linter application boundary.

## Scope

- In scope: Explicit-root skill discovery, Agent Skills-compatible header
  validation, deterministic diagnostics and exit behavior, and reuse of the same
  validation application boundary by publisher and contribution workflows.
- Out of scope: Mutating skill files or consumer state, changing catalog path
  semantics, and accepting header fields outside the adopted Agent Skills schema.

## Requirements

The following requirement groups define the normative linter contract of revision 1.5.

### R1 — Validation workflow

**Basis:** Existing active Ritebook contract, the Shared Catalog Contract, and ADR 0002.

```bash
uv run ritebook skills lint --root <path>
```

- Require an explicit `--root`.
- Discover candidate skill directories using the catalog structure defined by the
  shared catalog contract.
- Validate every discovered `SKILL.md` against the Agent Skills-compliant header.
- Traverse visible directories iteratively, without following symlinks and without
  an arbitrary discovery-depth cap. Catalog depth remains a separate validation
  rule from traversal depth.
- Count every visible regular `SKILL.md` returned by raw filesystem discovery,
  including candidates that later fail catalog-path, read, parse, or header
  validation.
- Report every visible symlinked `SKILL.md` and every visible symlinked directory
  that resolves to a `SKILL.md` candidate as a path-scoped validation issue.
  Symlinked candidates are not followed and are not included in the regular-file
  discovery count.
- Treat an existing, readable root with no candidates as a valid empty catalog.
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
- The complete file must be readable UTF-8 text.
- The frontmatter block, including delimiters and line endings, must be at most
  65,536 UTF-8 bytes. The closing delimiter may occur after any number of lines
  within that byte bound; there is no line-count limit.
- The bounded frontmatter block parses with safe YAML semantics to a mapping.
- Duplicate mapping keys are invalid at every nesting level rather than being
  resolved by last-value-wins behavior.
- Only `name`, `description`, `license`, `compatibility`, `metadata`, and
  `allowed-tools` are accepted as top-level frontmatter fields.
- `name` is required and is a non-empty string of at most 64 characters.
- `name` contains only lowercase alphanumeric characters and hyphens, does not
  start or end with a hyphen, does not contain consecutive hyphens, and matches
  the parent skill directory name.
- The shared catalog contract separately requires Ritebook catalog path segments
  to be canonical ASCII identifiers.
- `description` is required and is a non-whitespace string of at most 1024
  characters after trimming leading and trailing whitespace.
- Describing both what the skill does and when to use it is authoring guidance,
  not a deterministic validity rule.
- The normalized trimmed `description` contains no C0, DEL, C1, or surrogate code
  points. Ordinary Unicode scalar text remains valid and is preserved.
- `license` is optional. When present, it is a string naming the license or a
  bundled license file.
- `compatibility` is optional. When present, it is a non-empty string of at most
  500 characters. Whether it describes meaningful environment requirements is
  authoring guidance, not a deterministic validity rule.
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
- The stable diagnostic contract is the path and message. Ritebook does not
  promise diagnostic codes that are not present in the application result.
- Control characters reaching the CLI are rendered as visible deterministic ASCII
  escapes such as `\\n`, `\\t`, or `\\x1b`.
- Missing or unreadable roots and malformed frontmatter produce concise
  user-facing errors at the adapter boundary.
- Malformed YAML produces the exact path-scoped message
  `frontmatter must be valid YAML.`.
- Duplicate YAML mapping keys produce the exact path-scoped message
  `frontmatter must not contain duplicate mapping keys.`.
- Frontmatter over the byte bound produces the exact path-scoped message
  `frontmatter must be at most 65536 UTF-8 bytes.`.
- A visible symlinked candidate produces the exact path-scoped message
  `skill candidates must not use symbolic links.`.
- A discovered file that cannot be read as UTF-8 text produces the exact
  path-scoped message `skill file must be readable UTF-8 text.`.
- Successful standalone lint reports `Checked N skill(s)`, where `N` is the raw
  discovery count defined above.

Example:

```text
conventional-commits/SKILL.md: metadata values must be strings.
```

### R4 — Validated publication snapshot

**Basis:** The user's approved October 6, 2026 decision and
[ADR 0003](../adr/0003-publish-from-validated-skill-snapshots.md).

- A completely successful lint returns one immutable `ValidatedSkill` for every
  discovered regular candidate, sorted deterministically by catalog path.
- Each snapshot contains the catalog-relative path, validated name,
  catalog-relative skill-file path, and normalized description derived from the
  same parsed header that passed validation.
- The normalized description is the trimmed value used for length, control, and
  snapshot validation.
- Any discovery, path, read, parse, or header issue causes the result to expose no
  validated snapshots; partial publication input is prohibited.
- A successful empty catalog returns an empty snapshot.
- Publisher prechecks may map this application snapshot to publisher-owned DTOs,
  but must not rediscover files or reparse frontmatter.
- The linter publishes a single-file application API that accepts one explicit
  `SKILL.md` path and expected name, applies the same parsing and portable-header
  rules, and returns either deterministic issues or the validated name and
  normalized description. It does not apply catalog discovery or path-depth rules.

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
  passed to field validation. `LintSkillsResult.validated_skills` is populated
  only on complete success, and publisher prechecks map the raw count and exact
  snapshot to their publisher-owned result.

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
  metadata, successful snapshots, snapshot suppression on failure, deterministic
  finding order, and adapter failures.
- Adapter tests cover root and collection child discovery, ignored non-skill
  directories, arbitrarily deep iterative traversal, over-deep catalog paths,
  mixed nodes, hidden directories, visible symlink candidates, unreadable paths,
  duplicate keys, the 65,536-byte boundary, and path-scoped parse failures.
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
- Expose publication snapshots only through successful application results and do
  not include filesystem paths or parser-specific objects in that boundary.
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
| AC1 | R1 | Run `skills lint` with a valid, empty, invalid, deeply nested, symlink-containing, or unreadable root. | Regular candidates are counted, empty roots succeed, traversal has no recursion cap, visible candidate symlinks fail without being followed, invalid candidates or root inspection failures exit non-zero, and no publisher or consumer state is written. | Application, discovery-adapter, and CLI tests. |
| AC2 | R2 | Validate minimal headers, supported optional fields, flat string metadata, duplicate keys, exact and over-limit frontmatter, malformed values, whitespace-padded descriptions, surrogate values, and catalog/path mismatches. | Agent Skills-compatible values pass; descriptions are trimmed before length and snapshot use; 65,536-byte frontmatter passes; over-limit, duplicate, unsupported, malformed, nested, surrogate, or mismatched values fail with path-scoped findings. | Header-validator and frontmatter-adapter tests. |
| AC3 | R3 | Render multiple validation, parse, read, UTF-8, symlink, and control-character failures. | Findings use stable path/message ordering, controls are visible ASCII escapes, ordinary Unicode is preserved, and raw skill contents are not emitted. | Application ordering and CLI rendering tests. |
| AC4 | R4 | Lint a valid, invalid, or empty catalog and pass the result through the publisher precheck. | Successful regular candidates produce the exact deterministic snapshot, failures produce no partial snapshot, empty catalogs produce an empty snapshot, and no second discovery or parse occurs. | Linter application, precheck adapter, and publisher application tests. |
| AC5 | R1-R4 | Publisher or contribution validation receives linter failure. | The same validation rules apply and the caller cannot publish or commit invalid skill content. | Publisher and contribution adapter tests. |
| AC6 | R1-R4 | Execute the focused linter unit suite. | Application, adapter, and CLI behaviors represented by this specification pass without live network or global-state dependencies. | `uv run pytest tests/unit/features/skill_linter`. |
| AC7 | R2-R4 | Validate one explicit committed `SKILL.md` through the application API. | The result uses the same header parser, name checks, normalized description, and deterministic issues as catalog linting without running catalog discovery. | Single-file linter application and adapter tests. |

## Assumptions

- Ritebook supports Python 3.13 or newer and uses `uv` for command execution.
- The shared catalog contract remains the source of truth for identifiers and
  catalog paths.
- The [Agent Skills specification](https://agentskills.io/specification) and its
  [`skills-ref` reference validator](https://github.com/agentskills/agentskills/tree/main/skills-ref)
  define the canonical external header compatibility baseline reviewed on
  2026-10-06.
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
- October 6, 2026: Revision 1.4 replaced the line-count parser bound with a
  65,536-byte UTF-8 bound, rejected duplicate keys and visible candidate
  symlinks, required iterative traversal, clarified advisory field-quality rules
  and path/message diagnostics, and added the validated publication snapshot.
- October 7, 2026: Revision 1.5 made trimmed descriptions the validated snapshot
  value, rejected surrogate code points, and added the published single-file
  validation API required by installation.
- October 7, 2026: Marked revision 1.5 implemented after normalized-description,
  surrogate-rejection, catalog-snapshot, and single-file validation tests passed.
  Changes to the adopted header schema, catalog model, or snapshot ownership
  require specification and ADR review as described above.
