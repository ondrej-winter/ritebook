# Implementation Plan: Agent Skills–Compliant Skill Linter

## Overview

Bring Ritebook's skill linter into conformance with
[`skill-linter-spec.md`](../specs/skill-linter-spec.md) version 1.2. Replace the
legacy required `metadata.version` and nested `metadata.dependencies` contract
with the standard Agent Skills header, harden content-safe diagnostics, and prove
that standalone linting, publisher prechecks, and contribution validation continue
to share one application boundary.

**Readiness:** Ready

**Plan status:** Complete

**Prepared:** 2026-09-29

**Validation status:** All local formatting, linting, type, architecture, unit,
integration, local E2E, build, manual conformance, and isolated Docker E2E checks
pass.

**Owning specification:**
`/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/docs/specs/skill-linter-spec.md`

## Initial-State Findings

- The linter vertical slice, `skills lint` CLI command, publisher precheck, and
  contribution integration already exist.
- Catalog discovery, shared-kernel path validation, deterministic issue sorting,
  CLI control-character escaping, and publisher write prevention are already
  implemented.
- At planning time, the main contract mismatch was in
  `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/src/ritebook/features/skill_linter/application/use_cases/validate_skill_headers/validators.py`.
  It required `metadata`, `metadata.version`, and nested
  `metadata.dependencies`.
- Existing integration and end-to-end fixtures encoded the legacy metadata shape,
  so they did not prove that the minimal two-field Agent Skills header was accepted.
- The shared YAML parser included the underlying PyYAML exception text
  in malformed-YAML diagnostics. That text can contain source-derived snippets and
  conflicts with the concise, content-safe diagnostic requirement.
- A discovered file that could not be read or decoded raised
  `SkillFileReadError` outside the linter's translated application-error path.
- No dependency addition is required. Keep PyYAML and do not add `skills-ref` as a
  runtime dependency.
- The local active specification is authoritative. The upstream Agent Skills
  specification and reference validator are compatibility evidence, not a
  replacement source of requirements.

## Scope

### In Scope

- Replace the legacy metadata/dependency rules with the six accepted Agent Skills
  frontmatter fields.
- Accept a minimal header containing only `name` and `description`.
- Validate all optional fields defined by the active specification.
- Reject unknown top-level fields and non-string top-level keys.
- Preserve separate catalog path validation through the shared kernel.
- Produce deterministic, path-scoped, content-safe diagnostics.
- Preserve linter reuse by publisher and contribution workflows.
- Update tests and fixtures to demonstrate the new contract.
- Update concise user documentation and specification implementation-state
  metadata after validation succeeds.

### Out of Scope

- Changes to schema-v1 catalog depth, path semantics, or canonical catalog
  identifiers.
- Validation of Markdown body structure or content.
- Heuristic or natural-language enforcement that a description semantically
  explains both what the skill does and when to use it. Enforce only the objective
  requirements: string type, non-whitespace content, length, and control-character
  safety.
- Duplicate YAML-key detection, YAML schema changes, or replacement of PyYAML.
- Adding `skills-ref` as a project dependency.
- Mutation, automatic fixes, index schema changes, or consumer-state changes.
- Refactoring the publisher's existing discovery workflow beyond changes needed to
  preserve linter conformance.
- Backward-compatibility shims for the legacy nested metadata format.

## Assumptions and Decisions

- The active local specification takes precedence if the upstream reference
  implementation is less strict or behaves differently.
- A present optional field with YAML `null` is invalid because it does not satisfy
  the field's required type; an absent optional field is valid.
- `license` and `allowed-tools` must be strings when present, but the specification
  does not require them to be non-empty.
- `compatibility` must be a non-whitespace string of at most 500 characters when
  present.
- `metadata` may be an empty mapping, but every present key and value must be a
  string. Nested mappings, sequences, numbers, booleans, and null values are
  invalid.
- Per-file read failures should become path-scoped findings so other discovered
  candidates can still be reported. Root inspection and directory traversal
  failures remain command-level application errors.
- Raw discovery count is the number of visible, non-symlinked `SKILL.md` files
  returned by filesystem discovery before catalog-path validation, file reading,
  YAML parsing, or application validation. Every such candidate contributes to
  the lint result count, including invalid candidates.
- `SkillHeaderDiscoveryResult` and `LintSkillsResult` expose that count as
  `discovered_skill_count`. `SkillValidationReport.validated_skill_count` retains
  its narrower meaning: parsed headers passed to application validation.
- Successful standalone lint output is `Checked N skill(s)`. Publisher prechecks
  map the same raw discovery count to their existing `checked_skill_count` field.
- Malformed YAML uses the exact issue message `frontmatter must be valid YAML.`.
  File read or UTF-8 decode failures use the exact issue message
  `skill file must be readable UTF-8 text.`. The relative issue path supplies file
  context; neither message includes source, parser, absolute-path, OS-error, or
  invalid-byte details.
- No ADR is required because the architecture, dependencies, persistence formats,
  and public command structure remain unchanged.
- Open questions: None.

## Dependency and Sequencing Graph

```text
Specification v1.2
  └── Parsed frontmatter boundary types
       └── Agent Skills application validation
            ├── Standalone lint result
            ├── Publisher precheck mapping
            └── Contribution validation mapping
       └── Filesystem/YAML error translation
            └── CLI-safe diagnostics
                 └── Integration and E2E workflows
                      └── Documentation and implementation-state closure
```

Catalog discovery and shared-kernel path validation are existing prerequisites
and must remain unchanged.

## Progress Tracking

This dashboard mirrors every task, acceptance criterion, verification item, and
checkpoint below. Update both copies of an item together during implementation.

- [x] **T1** Lock the validation contract with application tests.
  - [x] **T1-A1** Minimal and optional-field acceptance cases pass.
  - [x] **T1-A2** Required and optional-field rejection cases are covered.
  - [x] **T1-A3** Deterministic multi-finding behavior is covered.
  - [x] **T1-V1** Focused application tests pass.
- [x] **CP1** Application contract checkpoint.
- [x] **T2** Implement the Agent Skills header validator.
  - [x] **T2-A1** Legacy metadata requirements are removed.
  - [x] **T2-A2** The six-field allowlist and field-specific rules are enforced.
  - [x] **T2-A3** Diagnostics do not interpolate untrusted YAML values.
  - [x] **T2-V1** Validator tests, Ruff, and ty checks pass.
- [x] **T3** Harden filesystem and frontmatter error translation.
  - [x] **T3-A1** Malformed YAML produces a concise content-safe issue.
  - [x] **T3-A2** Discovered unreadable files produce path-scoped issues.
  - [x] **T3-A3** Root discovery failures remain command-level application errors.
  - [x] **T3-V1** Shared and linter adapter tests pass.
- [x] **CP2** Linter slice checkpoint.
- [x] **T4** Verify CLI, publisher, and contribution reuse.
  - [x] **T4-A1** CLI exit and rendering behavior remains conformant.
  - [x] **T4-A2** Publisher refuses to write after any new validation failure.
  - [x] **T4-A3** Contribution validation continues using the linter port safely.
  - [x] **T4-V1** Cross-boundary unit tests pass.
- [x] **T5** Migrate integration and E2E fixtures to the minimal contract.
  - [x] **T5-A1** Shared valid fixtures contain only required fields by default.
  - [x] **T5-A2** At least one real workflow covers all optional fields.
  - [x] **T5-A3** No maintained fixture treats legacy dependencies as required.
  - [x] **T5-V1** Integration and E2E tests pass.
- [x] **CP3** End-to-end behavior checkpoint.
- [x] **T6** Align documentation and specification state.
  - [x] **T6-A1** README guidance describes minimal and optional header support.
  - [x] **T6-A2** The specification's current context reflects the implementation.
  - [x] **T6-A3** Both specification metadata locations say `Implemented`.
  - [x] **T6-V1** Documentation is reviewed against observed CLI behavior.
- [x] **T7** Run the full project quality gate.
  - [x] **T7-A1** Formatting, linting, typing, architecture, tests, and build pass.
  - [x] **T7-A2** Docker E2E passes without network access at runtime.
  - [x] **T7-A3** The final diff contains no unrelated changes.
  - [x] **T7-V1** Manual valid- and invalid-header lint checks pass.
- [x] **CP4** Final handoff checkpoint.

## Detailed Tasks

### T1 — Lock the New Application Contract with Focused Tests

- [x] **T1** Replace legacy dependency-oriented test cases with a contract matrix
  derived from specification version 1.2.

**Likely file:**

- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/tests/unit/features/skill_linter/application/test_skill_validation.py`

#### Accepted Headers

- Minimal `name` and `description`.
- Each optional field independently.
- All optional fields together:
  - `license: MIT`
  - non-empty `compatibility`
  - flat string-to-string `metadata`
  - string `allowed-tools`
- Empty metadata mapping.
- Empty string metadata keys or values, because the contract requires strings but
  does not impose non-empty metadata entries.
- Ordinary Unicode descriptions.
- Markdown body content remains irrelevant at the application validation layer.

#### Rejected Top-Level Shape

- Frontmatter is `None`, a sequence, or a scalar.
- Unknown top-level string field.
- Non-string top-level key.
- Multiple unknown fields produce deterministic output without echoing arbitrary
  field values.

#### Required Fields

- Missing `name`.
- `name: null`.
- Non-string name.
- Empty, whitespace-only, uppercase, underscored, overlong, leading-hyphen,
  trailing-hyphen, and consecutive-hyphen names.
- Name and directory mismatch.
- Missing `description`.
- `description: null`.
- Non-string, empty, whitespace-only, overlong, and control-containing
  descriptions.

#### Optional Fields

- `license` present with null or a non-string value.
- `compatibility` present with null, a non-string value, an empty or
  whitespace-only value, or more than 500 characters.
- `metadata` present with null or a non-mapping value.
- Non-string metadata key.
- Numeric, boolean, null, sequence, or nested mapping metadata value.
- `allowed-tools` present with null or a non-string value.

Do not add a non-empty requirement for `license` or `allowed-tools` because the
active specification does not define one.

#### Determinism

- Multiple findings from one header are sorted deterministically.
- Findings across multiple skill paths are sorted by path and then message.
- Messages identify the field and violated rule without embedding rejected YAML
  values.

#### Acceptance Criteria

- [x] **T1-A1** Minimal and optional-field acceptance cases pass.
- [x] **T1-A2** Required and optional-field rejection cases are covered.
- [x] **T1-A3** Deterministic multi-finding behavior is covered.

#### Verification

- [x] **T1-V1** Run:

  ```bash
  uv run pytest tests/unit/features/skill_linter/application/test_skill_validation.py -q
  ```

  During test-first implementation, new cases should fail against the legacy
  validator before T2 and pass after T2.

### CP1 — Application Contract Checkpoint

- [x] **CP1** Confirm that the tests encode only objective specification rules and
  do not introduce semantic description heuristics, catalog path changes, legacy
  compatibility behavior, or stricter optional-field rules than the active
  specification.

### T2 — Replace Legacy Validation with the Agent Skills Schema

- [x] **T2** Implement the new validation contract without moving YAML or
  filesystem concerns into the application layer.

**Likely files:**

- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/src/ritebook/features/skill_linter/application/use_cases/validate_skill_headers/validators.py`
- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/src/ritebook/features/skill_linter/application/dtos/skill_validation.py`

#### Implementation Details

1. Define a linter-owned allowlist containing `name`, `description`, `license`,
   `compatibility`, `metadata`, and `allowed-tools`.
2. Remove all validation that requires `metadata`, `metadata.version`,
   `metadata.dependencies`, or dependency tool/skill entries.
3. Preserve linter-owned name validation rather than coupling it directly to the
   shared catalog identifier helper. Header compatibility and catalog path policy
   are separate contracts, even though the current ASCII constraints coincide.
4. Use key membership rather than `.get()` where absence and explicit YAML `null`
   have different meanings.
5. Generalize the parsed mapping boundary so raw YAML mappings with non-string
   keys can be represented and validated honestly. The current
   `Mapping[str, object]` alias must not hide non-string YAML keys.
6. Add small, field-specific validators for the top-level allowlist, name,
   description, license, compatibility, metadata, and allowed tools.
7. Keep diagnostics stable and content-safe: name the known field and violated
   rule, but do not embed rejected values, YAML snippets, or arbitrary unknown
   keys.
8. Retain immutable DTOs, `SkillValidationIssue`, `SkillValidationReport`, current
   application orchestration, and the absence of filesystem/YAML imports in the
   application layer.

#### Acceptance Criteria

- [x] **T2-A1** A two-field header succeeds and legacy metadata is no longer
  required.
- [x] **T2-A2** Only the six allowed fields are accepted, with all specification
  constraints enforced.
- [x] **T2-A3** Validation messages do not expose rejected values or raw source
  fragments.

#### Verification

- [x] **T2-V1** Run:

  ```bash
  uv run pytest tests/unit/features/skill_linter/application -q
  uv run ruff check src/ritebook/features/skill_linter tests/unit/features/skill_linter
  uv run ty check src/ritebook
  ```

### T3 — Harden Frontmatter and Filesystem Error Translation

- [x] **T3** Make malformed and unreadable skill files produce deterministic,
  content-safe diagnostics at the correct boundary.

**Likely files:**

- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/src/ritebook/adapters/outbound/filesystem/frontmatter.py`
- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/src/ritebook/features/skill_linter/adapters/outbound/filesystem/frontmatter.py`
- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/src/ritebook/features/skill_linter/adapters/outbound/filesystem/adapter.py`
- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/tests/unit/adapters/outbound/test_filesystem_frontmatter.py`
- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/tests/unit/features/skill_linter/adapters/outbound/test_filesystem_skill_headers.py`

#### Implementation Details

1. Keep the existing bounded, first-line-delimited `yaml.safe_load()` parser.
2. Replace malformed-YAML messages containing `str(yaml.YAMLError)` with the exact
   message `frontmatter must be valid YAML.`. Do not include source
   snippets, line contents, or parser implementation details.
3. Preserve distinct errors for a missing opening delimiter and a missing closing
   delimiter. Non-mapping parsed frontmatter remains application validation.
4. Handle per-file read or UTF-8 decoding failures inside
   `FilesystemSkillHeaderDiscovery`: convert them into a
   `SkillValidationIssue` scoped to the known relative `SKILL.md` path and continue
   processing other candidates. Use the exact message
   `skill file must be readable UTF-8 text.`.
5. Keep missing roots, non-directory roots, root inspection failures, and
   directory traversal failures as `LintSkillsDiscoveryError` command failures.
6. Add `discovered_skill_count` to `SkillHeaderDiscoveryResult`, set it from the
   raw `discover_named_files()` result before path validation, and propagate it as
   `LintSkillsResult.discovered_skill_count`.
7. Add deterministic tests for malformed YAML without source snippets, invalid
   UTF-8, simulated file-read errors, simulated unreadable roots/directories, and
   one bad file not preventing findings for other candidates.

#### Acceptance Criteria

- [x] **T3-A1** Malformed YAML produces a concise, stable, path-scoped issue
  without parser or source excerpts.
- [x] **T3-A2** A discovered unreadable file becomes a path-scoped finding while
  other candidates remain inspectable.
- [x] **T3-A3** Root and traversal failures remain concise command-level errors
  translated through `LinterError`.

#### Verification

- [x] **T3-V1** Run:

  ```bash
  uv run pytest tests/unit/adapters/outbound/test_filesystem_frontmatter.py -q
  uv run pytest tests/unit/features/skill_linter/adapters/outbound/test_filesystem_skill_headers.py -q
  uv run pytest tests/unit/features/skill_linter -q
  ```

### CP2 — Linter Slice Checkpoint

- [x] **CP2** Confirm dependency direction: application validation imports no
  adapter or YAML types; the filesystem adapter maps external failures into
  application DTOs/errors; shared-kernel catalog validation remains unchanged; and
  no new cross-slice private imports exist.

### T4 — Verify CLI, Publisher, and Contribution Reuse

- [x] **T4** Preserve all callers of the linter application boundary and add
  regression evidence for the new validation failures.

**Likely files:**

- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/tests/unit/adapters/inbound/cli/test_adapter.py`
- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/tests/unit/features/skill_linter/application/test_lint_skills.py`
- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/tests/unit/features/skill_linter/adapters/outbound/test_publisher_precheck.py`
- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/tests/unit/features/publisher/application/test_publish_index.py`
- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/tests/unit/features/skill_contribution/adapters/outbound/test_validation_adapter.py`

#### Implementation Details

1. Simplify application fake headers to use the minimal two-field form.
2. Preserve standalone CLI behavior: status `0` only without issues; status `1`
   for invalid skills or inspection errors; findings on stderr; success count on
   stdout as `Checked N skill(s)`; and visible control-character escaping.
3. Add or adjust a CLI test for concise malformed-YAML or file-read diagnostics.
4. Preserve publisher behavior: the linter remains the hard precheck, failed
   prechecks prevent discovery and index writes, and mapped issue ordering remains
   deterministic.
5. Preserve contribution behavior: it continues calling the linter application
   port, reports only the issue count at its public boundary, and does not expose
   detailed findings or source contents.
6. Avoid changing port signatures unless implementation evidence proves it
   necessary. The current linter port and publisher/contribution mapping contracts
   are expected to remain sufficient. Rename only the lint result count from
   `validated_skill_count` to `discovered_skill_count`; retain the publisher's
   existing `checked_skill_count` field.

#### Acceptance Criteria

- [x] **T4-A1** CLI mapping, exit codes, streams, and control escaping remain
  correct.
- [x] **T4-A2** Publisher tests prove no index write occurs after an unknown field,
  invalid optional field, or nested metadata failure.
- [x] **T4-A3** Contribution tests prove validation reuse without leaking finding
  details.

#### Verification

- [x] **T4-V1** Run:

  ```bash
  uv run pytest tests/unit/adapters/inbound/cli/test_adapter.py -q
  uv run pytest tests/unit/features/skill_linter/adapters/outbound/test_publisher_precheck.py -q
  uv run pytest tests/unit/features/publisher/application/test_publish_index.py -q
  uv run pytest tests/unit/features/skill_contribution/adapters/outbound/test_validation_adapter.py -q
  ```

### T5 — Migrate Integration and E2E Fixtures

- [x] **T5** Make broad workflows prove the minimal standard header while retaining
  targeted coverage for optional fields and invalid nested metadata.

**Likely files:**

- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/tests/integration/conftest.py`
- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/tests/e2e/conftest.py`
- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/tests/e2e/test_cli_workflows.py`
- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/tests/integration/test_adapter_integrations.py`
- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/tests/e2e/test_skill_contribution_workflow.py`

This task spans shared test fixtures and the workflows that consume them. Keep the
change atomic because splitting fixture migration from its consumers would create
an intermediate suite whose broad tests still encode the obsolete contract.

#### Implementation Details

1. Change default valid-skill builders to emit only `name` and `description` in
   frontmatter.
2. Remove legacy nested metadata from integration fixtures, E2E fixtures, local
   `_valid_skill_content()` helpers, linter adapter fixtures, and publisher adapter
   fixtures unless a test specifically exercises optional metadata.
3. Keep invalid fixtures focused on their intended failure. A missing-description
   fixture must not contain an unrelated invalid legacy field.
4. Add one real filesystem or CLI scenario with all supported optional fields so
   YAML parsing and application validation are exercised together.
5. Add a real failure scenario where a nested metadata mapping is rejected with a
   path-scoped metadata string-value issue and publisher output is not written.
6. Ensure publish, register, list, install, sync, and contribute workflows continue
   operating with minimal Agent Skills headers.

#### Acceptance Criteria

- [x] **T5-A1** Default valid fixtures contain only `name` and `description`.
- [x] **T5-A2** At least one integration or E2E path proves all optional fields are
  accepted.
- [x] **T5-A3** Maintained tests no longer imply that `metadata.version` or
  `metadata.dependencies` are required.

#### Verification

- [x] **T5-V1** Run:

  ```bash
  uv run pytest tests/integration -q
  uv run pytest tests/e2e -q
  ```

### CP3 — End-to-End Behavior Checkpoint

- [x] **CP3** Confirm from observed behavior that standalone lint accepts a minimal
  header, optional fields are accepted, invalid optional fields fail, publisher
  validation prevents index writes, contribution still uses the shared linter,
  and `skills lint` writes no state.

### T6 — Align Documentation and Specification State

- [x] **T6** Update derived guidance and close the specification's partial
  implementation state only after behavior and tests are complete.

**Likely files:**

- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/README.md`
- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/docs/specs/skill-linter-spec.md`
- `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/docs/specs/README.md`

#### Implementation Details

1. Update the README's lint description to state concisely that `name` and
   `description` form the minimal accepted header, standard optional Agent Skills
   fields are supported, Ritebook-specific nested metadata is not required, and
   the owning specification contains detailed rules.
2. Preserve the staged specification's normative content. Do not rewrite or revert
   its version 1.2 requirements.
3. Once implementation and focused validation pass, replace the stale current
   context that says the validator still requires legacy metadata, set the skill
   linter's `Implementation state` to `Implemented`, and update the matching
   specification catalog entry.
4. Keep `Last reviewed: 2026-09-29`, the date of the specification/code comparison.

#### Acceptance Criteria

- [x] **T6-A1** README guidance matches the supported command without duplicating
  the full schema.
- [x] **T6-A2** The specification's current-context section no longer describes
  removed legacy behavior.
- [x] **T6-A3** Both specification metadata locations report `Implemented`, but
  only after implementation evidence exists.

#### Verification

- [x] **T6-V1** Compare documentation examples with a successful manual CLI run,
  then search for stale legacy requirements:

  ```bash
  rg -n "metadata\.version|metadata\.dependencies|metadata is required" README.md docs src tests
  ```

  Remaining matches must be limited to intentional history or rejection examples
  in the version 1.2 specification and tests.

### T7 — Full Quality Gate and Manual Conformance Checks

- [x] **T7** Run the complete project-defined handoff validation after all code,
  tests, fixtures, and documentation are aligned.

#### Manual Conformance Cases

Use temporary fixtures outside maintained source files and verify:

1. A minimal valid header exits `0`.
2. A header with all optional fields exits `0`.
3. An unknown top-level field exits `1`.
4. A nested metadata value exits `1`.
5. A whitespace-only description exits `1`.
6. Invalid UTF-8 or malformed YAML exits `1` with concise output and no source
   contents.
7. Publishing an invalid skill does not create or overwrite
   `ritebook-index.json`.

#### Acceptance Criteria

- [x] **T7-A1** Formatting, linting, type checking, architecture validation,
  non-E2E tests, and package build pass:

  ```bash
  uv run ruff format --check .
  uv run ruff check .
  uv run ty check src/ritebook
  uv run lint-imports
  uv run pytest -m "not e2e"
  uv build
  ```

- [x] **T7-A2** The isolated Docker E2E gate passes:

  ```bash
  docker build -f Dockerfile.e2e -t ritebook-e2e .
  docker run --rm --network none ritebook-e2e
  ```

  Passed on 2026-09-29 with Docker Desktop 4.92.0. The image built successfully,
  and the network-isolated container run completed with 22 passing E2E tests.

- [x] **T7-A3** The final diff contains no unrelated changes:

  ```bash
  git --no-pager status --short
  git --no-pager diff --check
  git --no-pager diff --stat
  git --no-pager diff
  ```

#### Verification

- [x] **T7-V1** Record the exact manual commands, exit codes, and representative
  sanitized output in the implementation handoff.

### CP4 — Final Handoff Checkpoint

- [x] **CP4** Mark the plan complete only when every required acceptance and
  verification item is checked, the specification state is updated, focused and
  full validation pass, Docker E2E passes, no unrelated files are changed, and any
  deviation from this plan is recorded.

## Risks and Mitigations

| Risk | Mitigation |
| --- | --- |
| Optional `null` values are treated as absent. | Use explicit key membership before type validation. |
| PyYAML accepts non-string mapping keys. | Represent parsed mappings as `Mapping[object, object]` and validate keys explicitly. |
| Malformed-YAML output exposes source lines. | Replace parser exception text with a fixed concise diagnostic. |
| Unknown fields or values inject terminal controls. | Do not interpolate arbitrary YAML values; retain CLI escaping as defense in depth. |
| Shared catalog and Agent Skills name rules become coupled. | Keep header validation linter-owned and leave shared-kernel path policy unchanged. |
| Broad tests pass only because fixtures include legacy metadata. | Make minimal two-field headers the default integration and E2E fixture. |
| Publisher behavior drifts from standalone lint. | Preserve `LinterPublisherPrecheck` and add a publication-blocking regression case for a version 1.2 failure. |
| Unreadable files escape the linter boundary. | Convert per-file failures into path-scoped findings; reserve application errors for root or traversal failure. |
| Existing staged specification edits are overwritten. | Treat them as user-owned and make only narrow implementation-state/current-context updates after validation. |

## Parallelization Opportunities

- T1 and analysis for T3 can proceed in parallel, but T2 must use T1 as its
  executable contract.
- T3 can be implemented independently of the field validators once its diagnostic
  wording is fixed.
- T4 caller tests can be updated after T2's issue contract stabilizes.
- T5 fixture migration should remain one coordinated task because its consumers
  share the same builders.
- T6 implementation-state closure and T7 are sequential finalization tasks.

## Plan Maintenance During Implementation

Treat this document as a living plan:

1. Update both the detailed checkbox and its matching Progress Tracking checkbox
   after each completed item.
2. Record brief status notes, blockers, deviations, changed sequencing, and newly
   discovered work when they affect the remaining plan.
3. Leave unknown, deferred, failed, or unverified items unchecked.
4. Mark a parent task complete only when all required acceptance and verification
   items are resolved.
5. Do not silently expand the work into catalog-path, index-schema, dependency, or
   Markdown-body validation changes.

## Implementation Handoff

- Implement tasks in dependency order from T1 through T7, pausing at each
  checkpoint.
- Preserve the staged changes to
  `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/docs/specs/skill-linter-spec.md`
  and
  `/Users/owinter/Documents/Projects/ondrej-winter.nosync/ritebook/docs/specs/README.md`.
- Use the narrowest relevant checks while iterating, then run the full quality gate
  before marking the specification implemented.
- Report assumptions, changed files, test evidence, Docker E2E evidence, and any
  deferred work in the final handoff.
