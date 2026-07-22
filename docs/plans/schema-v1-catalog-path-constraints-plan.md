# Implementation Plan: Schema-v1 Catalog Path Constraints

## Overview

Implement the schema-v1 catalog contract introduced by commit `9969b9d` across
publishing, registry consumption, listing, installation, and contribution
workflows. Valid catalog-relative skill paths are `<skill>` or
`<collection>/<skill>`; a first segment cannot be both a root skill and a
collection. Only requirements-file installation may expand a collection, and
then only to its immediate child skills. Invalid candidate indexes must never
replace coherent registry or cache state.

The specification commit is documentation-only. The current implementation still
permits over-deep catalog paths, mixed skill/collection nodes, arbitrary
requirements-prefix expansion, and over-deep direct selectors.

## Goals and Success Criteria

### Goal

Enforce one consistent schema-v1 catalog path policy at producer, consumer, and
command boundaries while preserving existing provenance, atomicity, and
hexagonal vertical-slice boundaries.

### Deliverables

- A shared, technology-neutral catalog-path validation policy.
- Producer-side catalog structure validation for linting and index publishing.
- Consumer-side validation for added, updated, cached, and listed indexes.
- Exact direct-install and contribution selection.
- Immediate-child collection expansion for requirements-file installation only.
- Regression, integration, CLI, and E2E coverage.
- Updated user-facing documentation and implementation-state metadata.

### Success Criteria

- Root and collected skills are accepted throughout supported workflows.
- Over-deep and mixed-node catalogs fail with deterministic, actionable errors.
- Invalid add/update candidates preserve existing cache and registry state.
- Direct installation and contribution commands never expand collections.
- Requirements installation expands only immediate collection children and
  validates the complete plan before mutation.
- The full local quality gate, package build, and Docker E2E workflow pass.

### Constraints

- Keep schema version `1`; the serialized publisher index fields do not change.
- Preserve vertical-slice ownership and inward-pointing dependencies.
- Keep framework, filesystem, JSON, and CLI details inside adapters.
- Translate shared validation failures into slice-owned errors at boundaries.
- Preserve exact relative skill paths as identity; never fall back to
  `skills[].name`.
- Keep existing valid cached state intact when candidate validation fails.
- Use `ty`, not `mypy`, for Ritebook static type validation.

## Required Specification Clarification

The updated contribution specification currently conflates two path concepts:

- `requirement` contains the catalog-relative selector after the local alias,
  such as `browser/runtime-verification`.
- `ritebook.lock.skills[].skill_path` is generated as a source-repository-relative
  checkout path that includes `skills_root`, such as
  `skills/browser/runtime-verification`.

The new text says lockfile skill paths deeper than `<collection>/<skill>` must be
rejected. Applying that rule to `skill_path` would reject valid collected skills
whenever `skills_root` is not `.`.

Implementation must first clarify the specification: enforce the one/two-segment
catalog rule on the selector encoded in `requirement`, while retaining
`skill_path` as a safe repository-relative checkout path. This clarifies the
existing lockfile schema and does not require an ADR.

## Architecture Decisions

- Add a pure shared-kernel catalog path policy because publisher, registry,
  installation, and contribution slices implement the same schema-v1 concept.
- Keep errors technology-neutral in the shared kernel and translate them into
  owning-slice errors in adapters or application boundaries.
- Continue recursive `SKILL.md` candidate discovery, then validate the complete
  candidate set. Stopping traversal at the first skill would hide invalid nested
  candidates instead of reporting them.
- Validate complete path sets at both producer and consumer boundaries. Producer
  validation prevents new invalid indexes; consumer validation rejects legacy or
  externally generated invalid schema-v1 indexes.
- Preserve the current validate-before-cache sequencing for add/update and prove
  its atomicity through regression tests.
- Resolve requirement selectors by exact match first. Collection expansion is a
  requirements-only fallback for one-segment selectors with immediate children.

## Progress Tracking

Treat this plan as a living document throughout implementation. After each
completed task or meaningful change:

- check off completed tasks, acceptance criteria, verification items, and
  checkpoints
- leave unfinished or unverified items unchecked
- add newly discovered work and update sequencing when scope or dependencies
  change
- note blockers, deviations, and decisions that affect the remaining work

Keep this section and the task list current without waiting for a progress request.

## Task List

### Phase 1: Define the Shared Contract

- [ ] Task 1: Clarify contribution selector and lockfile path semantics
- [ ] Task 2: Add a shared schema-v1 catalog-path policy

### Task 1: Clarify Contribution Selector and Lockfile Path Semantics

**Description:** Update the contribution specification so catalog-depth validation
applies to the catalog-relative selector encoded in `requirement`, not to the
repository-relative `skill_path`. Keep `skill_path` as the exact checkout path
used for source comparison and contribution preparation.

**Acceptance criteria:**

- [ ] The specification distinguishes catalog-relative selectors from
  repository-relative lockfile paths.
- [ ] Root and collected selectors are limited to one or two segments.
- [ ] Repository-relative lockfile paths remain valid regardless of
  `skills_root` depth, subject to existing safe-path validation.
- [ ] Lockfile-reader test requirements use the same terminology.

**Verification:**

- [ ] Compare the clarified text with lockfile generation in
  `src/ritebook/features/skill_installation/application/use_cases/install_from_requirements.py`.
- [ ] Confirm examples remain consistent with the documented lockfile schema.

**Dependencies:** None

**Files likely touched:**

- `docs/specs/upstream-skill-contributions-spec.md`

**Estimated scope:** XS, one file

### Task 2: Add a Shared Schema-v1 Catalog-path Policy

**Description:** Add a pure shared-kernel module that validates and classifies
catalog-relative skill paths and validates complete path sets. It must validate
canonical safe kebab-case POSIX segments, require one or two segments, and reject
mixed root-skill/collection path sets.

**Acceptance criteria:**

- [ ] Accepts `code-review` and `quality/code-review`.
- [ ] Rejects empty, absolute, backslash, dot, parent, repeated-separator,
  trailing-separator, and three-or-more-segment paths.
- [ ] Rejects non-kebab-case catalog segments consistently with existing
  application selectors.
- [ ] Classifies one-segment paths as root skills and two-segment paths as
  collection children without introducing transport-specific types.
- [ ] Rejects sets such as `quality` plus `quality/code-review`.
- [ ] Allows duplicate skill names at distinct valid paths.
- [ ] Exposes a small intentional shared-kernel API.

**Verification:**

- [ ] Focused shared-kernel tests cover valid, malformed, over-deep, mixed-node,
  and duplicate-name-at-distinct-path cases.
- [ ] `uv run pytest tests/unit/shared_kernel/test_catalog_paths.py`
- [ ] `uv run ruff check src/ritebook/shared_kernel tests/unit/shared_kernel`
- [ ] `uv run ty check src/ritebook`

**Dependencies:** Task 1

**Files likely touched:**

- `src/ritebook/shared_kernel/catalog_paths.py`
- `src/ritebook/shared_kernel/__init__.py`
- `tests/unit/shared_kernel/test_catalog_paths.py`

**Estimated scope:** S, three files

### Checkpoint A: Shared Contract

- [ ] Shared catalog-path tests pass.
- [ ] Changed modules pass Ruff and `ty`.
- [ ] Shared code contains no filesystem, JSON, CLI, or slice-specific errors.

### Phase 2: Stop Invalid Catalogs at Producer and Consumer Boundaries

- [ ] Task 3: Enforce catalog structure during lint and publisher discovery
- [ ] Task 4: Enforce the contract in the JSON index reader
- [ ] Task 5: Prove add/update failure preserves registry state

### Task 3: Enforce Catalog Structure During Lint and Publisher Discovery

**Description:** Keep recursive candidate discovery so invalid nested `SKILL.md`
files are detected rather than ignored. Validate all discovered candidate paths
as a set before publication. The linter should emit deterministic path-scoped
issues; publisher discovery should raise actionable discovery errors. Valid skill
package contents remain unrestricted unless another nested `SKILL.md` declares a
candidate skill.

Implement this as two focused changes if necessary: linter issue reporting first,
then publisher rejection using the same policy.

**Acceptance criteria:**

- [ ] Root skills and immediate collection children are discovered.
- [ ] Empty, non-skill, hidden, and symlinked directories retain their current
  behavior.
- [ ] Over-deep candidates are reported with the offending path.
- [ ] A skill directory containing a descendant skill is rejected as a mixed
  skill/collection node.
- [ ] A collection remains implicit and produces no separate index entry.
- [ ] Structural issues are deterministic and path-scoped in `lint-skills`.
- [ ] `publish-index` writes or replaces no index when structural validation
  fails.

**Verification:**

- [ ] Extend linter filesystem-discovery tests for root, collected, over-deep,
  mixed-node, ignored-content, and deterministic issue cases.
- [ ] Extend publisher filesystem-discovery tests for the same path matrix.
- [ ] Extend publish-index use-case tests to prove the writer is not called after
  structural failure.
- [ ] Run the focused linter and publisher unit suites.

**Dependencies:** Task 2

**Files likely touched:**

- `src/ritebook/features/linter/adapters/outbound/filesystem/adapter.py`
- `src/ritebook/features/publisher/adapters/outbound/filesystem/adapter.py`
- `src/ritebook/features/publisher/domain/catalog.py`
- `tests/unit/features/linter/adapters/outbound/test_filesystem_skill_headers.py`
- `tests/unit/features/publisher/adapters/outbound/test_filesystem_skill_discovery.py`
- `tests/unit/features/publisher/application/test_publish_index.py`

**Estimated scope:** M per focused sub-change; do not combine unrelated cleanup

### Task 4: Enforce the Contract in the JSON Index Reader

**Description:** Validate every schema-v1 `skills[].path`, then validate the
complete path set in the index-registry JSON adapter. Apply the same validation
path to committed indexes used by `add-index` and `update-index`, and cached
indexes used by `list-skills` and installation.

**Acceptance criteria:**

- [ ] `read_index()` and `read_skills()` accept root and collection-child paths.
- [ ] Both methods reject over-deep and mixed-node catalogs before returning any
  metadata.
- [ ] Literal non-canonical paths cannot be normalized into apparent validity by
  `PurePosixPath`.
- [ ] Errors identify invalid schema-v1 catalog structure.
- [ ] CLI-facing errors provide actionable reorganize-and-republish guidance.
- [ ] Duplicate skill names at distinct valid paths remain allowed.
- [ ] Existing digest and provenance behavior remains unchanged.

**Verification:**

- [ ] Extend JSON reader tests for accepted root/collected paths and rejected
  malformed, over-deep, and mixed path sets.
- [ ] Add list-skills tests proving invalid cached indexes fail before display.
- [ ] Add CLI adapter coverage for actionable validation messages when needed.
- [ ] Run focused index-registry adapter and list-skills tests.

**Dependencies:** Task 2

**Files likely touched:**

- `src/ritebook/features/index_registry/adapters/outbound/json_index/reader.py`
- `tests/unit/features/index_registry/adapters/outbound/test_json_index_reader.py`
- `tests/unit/features/index_registry/application/test_list_skills.py`
- `tests/unit/adapters/inbound/cli/test_adapter.py`

**Estimated scope:** M, four files

### Task 5: Prove Add/update Failure Preserves Registry State

**Description:** Add regression coverage around the existing validate-before-write
sequencing. Confirm invalid candidate indexes fail before cache writes and registry
upserts, including forced replacement and update. Confirm bulk update records the
failed alias and continues.

**Acceptance criteria:**

- [ ] Invalid `add-index` performs no cache or registry mutation.
- [ ] Invalid forced replacement preserves the existing cache and registry entry.
- [ ] Invalid `update-index` preserves cache path, bytes, revision, digest,
  published metadata, skill count, and timestamps.
- [ ] `update-index --all` records a structurally invalid alias as failed and
  continues updating other aliases.
- [ ] Implementation changes are made only if regression tests expose an atomicity
  defect.

**Verification:**

- [ ] Extend add-index application tests with invalid-reader failures and mutation
  assertions.
- [ ] Extend update-index application tests for single and bulk update behavior.
- [ ] Run focused add/update tests.

**Dependencies:** Task 4

**Files likely touched:**

- `tests/unit/features/index_registry/application/test_add_index.py`
- `tests/unit/features/index_registry/application/test_update_index.py`
- `src/ritebook/features/index_registry/application/use_cases/add_index.py` only if needed
- `src/ritebook/features/index_registry/application/use_cases/update_index.py` only if needed

**Estimated scope:** S, primarily two test files

### Checkpoint B: Producer and Consumer Boundaries

- [ ] Publisher and linter focused tests pass.
- [ ] Registry and listing focused tests pass.
- [ ] Invalid catalogs cannot be published, registered, updated, listed, or
  passed into installation.
- [ ] Failed candidate validation leaves existing registry/cache state unchanged.

### Phase 3: Implement Exact-skill and Collection-selector Semantics

- [ ] Task 6: Restrict direct installation to exact schema-v1 skill paths
- [ ] Task 7: Replace arbitrary prefix expansion with immediate collection expansion

### Task 6: Restrict Direct Installation to Exact Schema-v1 Skill Paths

**Description:** Reuse the shared catalog-path validator in installation selector
parsing. Keep `install-skill` exact-only and add explicit tests proving over-deep
selectors are rejected and a first-level collection selector is not expanded.

**Acceptance criteria:**

- [ ] Direct selectors accept one- or two-segment exact skill paths only.
- [ ] Over-deep selectors fail at the command/application boundary.
- [ ] A collection selector with no exact root skill is reported as unknown and is
  never expanded by `install-skill`.
- [ ] Exact root-skill behavior remains valid.
- [ ] Exact collection-child behavior remains valid.
- [ ] Cached metadata entering the slice is structurally validated by the
  index-reader boundary.

**Verification:**

- [ ] Extend selector DTO tests for one, two, and over-deep paths.
- [ ] Extend direct-install tests for exact root, exact collection child, and
  non-expanding collection selector behavior.
- [ ] Run focused direct-install and catalog-adapter tests.

**Dependencies:** Tasks 2 and 4

**Files likely touched:**

- `src/ritebook/features/skill_installation/application/dtos/install_skill.py`
- `tests/unit/features/skill_installation/application/test_install_skill.py`
- `tests/unit/features/skill_installation/adapters/outbound/` catalog adapter test
  if boundary mapping needs explicit coverage

**Estimated scope:** S, two or three files

### Task 7: Replace Arbitrary Prefix Expansion With Immediate Collection Expansion

**Description:** In `InstallFromRequirements`, resolve exact matches first. If no
exact match exists, permit only a one-segment selector and resolve indexed skills
whose paths are exactly `<selector>/<skill>`. Require collection selectors to use
`target`; reject collection selectors using `target_path` during planning before
source opening, target planning, copying, or lockfile writing.

**Acceptance criteria:**

- [ ] Exact root and collection-child skills retain exact-match precedence.
- [ ] A one-segment collection expands only immediate child skills.
- [ ] Expanded skills are ordered deterministically by catalog path.
- [ ] Empty or unrelated collection selectors fail as unknown.
- [ ] Arbitrary descendant prefixes and over-deep selectors are rejected.
- [ ] A collection selector using `target_path` fails before any mutation.
- [ ] A collection selector using `target` resolves each child below the target
  base by final skill name.
- [ ] Generated lock entries contain one exact requirement per resolved skill and
  retain repository-relative `skill_path` and `skill_file`.
- [ ] Duplicate, canonical, and parent-child target conflict checks run over the
  fully expanded plan before copying.

**Verification:**

- [ ] Replace the obsolete arbitrary-folder-prefix expansion test.
- [ ] Add immediate-child, deterministic-order, empty-collection, unrelated-prefix,
  `target_path`, over-deep-selector, and no-mutation tests.
- [ ] Retain exact-match and duplicate-target regression coverage.
- [ ] Run the focused requirements-install suite.

**Dependencies:** Task 6

**Files likely touched:**

- `src/ritebook/features/skill_installation/application/use_cases/install_from_requirements.py`
- `src/ritebook/features/skill_installation/application/errors.py`
- `tests/unit/features/skill_installation/application/test_install_from_requirements.py`
- requirements-reader tests only if adapter-level translation changes

**Estimated scope:** M, three primary files

### Checkpoint C: Installation Semantics

- [ ] All installation unit tests pass.
- [ ] Direct and requirements workflows have distinct, spec-compliant selector
  behavior.
- [ ] Invalid collection requests cause no target or lockfile mutation.
- [ ] Generated lockfiles preserve repository-relative source paths.

### Phase 4: Tighten Contribution Selection

- [ ] Task 8: Resolve contributions by exact catalog-relative requirement

### Task 8: Resolve Contributions by Exact Catalog-relative Requirement

**Description:** Limit `ContributionSkillReference` to one or two catalog segments
and remove the lockfile reader's `skill_path == selector` fallback. Resolve by
exact stored `requirement` and local alias. Continue validating repository-relative
`skill_path` for safe checkout use, but do not apply catalog-depth rules to it.

**Acceptance criteria:**

- [ ] Root and collection-child exact requirements resolve one lockfile entry.
- [ ] A collection-only request is never expanded and fails unless an exact root
  skill with that path exists.
- [ ] Over-deep contribution selectors fail before lockfile or checkout mutation.
- [ ] Resolution does not fall back to `skill_name` or repository-relative
  `skill_path`.
- [ ] Duplicate skill names at different catalog paths remain unambiguous.
- [ ] Lockfile fixtures reflect generated state where `skill_path` includes
  `skills_root`.
- [ ] Existing safe repository-path checks remain active for contribution checkout
  and comparison adapters.

**Verification:**

- [ ] Extend contribution reference DTO tests.
- [ ] Replace unrealistic lockfile reader fixtures with generated-schema-compatible
  repository-relative paths.
- [ ] Add exact root, exact collection child, collection-only, over-deep, and
  no-fallback lockfile-reader tests.
- [ ] Add application/CLI boundary tests proving rejection occurs before checkout
  preparation.
- [ ] Run focused contribution tests.

**Dependencies:** Tasks 1 and 2

**Files likely touched:**

- `src/ritebook/features/skill_contribution/application/dtos/publish_skill_change.py`
- `src/ritebook/features/skill_contribution/adapters/outbound/json_lockfile/reader.py`
- `tests/unit/features/skill_contribution/application/test_publish_skill_change.py`
- `tests/unit/features/skill_contribution/adapters/outbound/test_json_lockfile_reader.py`
- CLI adapter tests if error translation changes

**Estimated scope:** M, four or five files

### Checkpoint D: Contribution Semantics

- [ ] Contribution focused tests pass.
- [ ] Real generated lockfile shape is covered by fixtures.
- [ ] No prefix, skill-name, or repository-path selector fallback remains.
- [ ] Contribution checkout still receives the exact safe repository-relative
  source path.

### Phase 5: Integrate, Document, and Validate

- [ ] Task 9: Add cross-workflow CLI/E2E coverage and update documentation

### Task 9: Add Cross-workflow CLI/E2E Coverage and Update Documentation

**Description:** Cover supported catalog layouts and rejection behavior at real
CLI boundaries. Update README language that currently describes unrestricted
recursive discovery. Document collection selectors for `ritebook install`, while
reiterating that `install-skill` and `publish-skill-change` are exact-only. Return
specification implementation-state metadata to `Implemented` only after all
acceptance criteria pass.

**Acceptance criteria:**

- [ ] CLI/integration/E2E coverage includes publishing and listing root and
  collection-child skills.
- [ ] Requirements installation expands a collection through the real CLI.
- [ ] Direct installation and contribution reject collection-only selectors.
- [ ] Over-deep and mixed-node catalogs fail with clear user-facing errors.
- [ ] State preservation is covered at the highest practical boundary without
  duplicating lower-level atomicity tests.
- [ ] README documents the one/two-level catalog layout and requirements-only
  collection expansion.
- [ ] README examples use valid catalog paths and distinguish catalog-relative
  selectors from repository-relative lockfile paths.
- [ ] Changed specifications are marked `Implemented` only after all code and test
  work succeeds.

**Verification:**

- [ ] `uv run ruff format .`
- [ ] `uv run ruff check .`
- [ ] `uv run ty check src/ritebook`
- [ ] `uv run pytest -m "not e2e"`
- [ ] `uv build`
- [ ] `uv run pytest tests/e2e -q`
- [ ] Run the canonical Docker E2E command documented by the repository/specification.
- [ ] Review the final diff for architecture-boundary compliance and unrelated
  churn.

**Dependencies:** Tasks 3 through 8

**Files likely touched:**

- `README.md`
- relevant files under `tests/unit/adapters/inbound/cli/`
- `tests/integration/test_adapter_integrations.py`
- `tests/e2e/test_cli_workflows.py`
- `docs/specs/consumer-git-index-registry-spec.md`
- `docs/specs/install-skill-spec.md`
- `docs/specs/list-skills-spec.md`
- `docs/specs/publisher-index-generation-spec.md`
- `docs/specs/upstream-skill-contributions-spec.md`

**Estimated scope:** M when split into integration-tests and documentation changes

### Checkpoint E: Complete

- [ ] Every specification acceptance criterion is implemented or explicitly
  accounted for.
- [ ] All focused and full quality checks pass.
- [ ] Package build and Docker E2E pass.
- [ ] Specs and README match real behavior.
- [ ] The final change set is ready for review.

## Dependency Graph

```text
Contribution terminology clarification
              |
              v
Shared catalog-path policy
     +--------+------------------+
     |                           |
     v                           v
Publisher/linter validation   JSON index validation
     |                           |
     v                           +----------+
Publish safety                            |
                                         v
                              Add/update/list safety
                                         |
                            +------------+------------+
                            |                         |
                            v                         v
                    Direct install limits   Requirements expansion
                            |                         |
                            +------------+------------+
                                         |
                                         v
                              Contribution exactness
                                         |
                                         v
                               CLI/E2E/docs/full gate
```

## Sequencing and Parallelization

- Tasks 1 and 2 are sequential because all slices depend on the clarified shared
  contract.
- After Task 2, producer Task 3 and consumer Task 4 can be implemented in
  parallel if both use the agreed shared API.
- Task 5 follows Task 4 because its regression scenarios depend on reader
  validation failures.
- Task 6 depends on the shared validator and consumer read boundary.
- Task 7 follows Task 6 because both use the same selector contract.
- Task 8 can proceed after Tasks 1 and 2, but its integration tests should be
  reconciled with generated lockfile behavior from Task 7.
- Task 9 is last because it integrates every workflow and updates implementation
  status.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Existing schema-v1 indexes become invalid | High | Return actionable reorganize-and-republish guidance and preserve previous registry/cache state. |
| Lockfile `skill_path` is mistaken for a catalog path | High | Complete Task 1 first; validate selector depth from `requirement` and keep repository-path safety separate. |
| Shared validation leaks slice-specific concerns | Medium | Keep the shared kernel pure and translate failures at each adapter/application boundary. |
| Discovery stops early and hides nested violations | High | Recursively discover all candidates, then validate the complete path set. |
| Exact root skill and same-named collection become ambiguous | High | Reject the complete mixed path set at producer and consumer boundaries; do not rely on exact-match precedence. |
| Requirements installation mutates targets before detecting an invalid collection request | High | Complete selector expansion, target derivation, lockfile validation, and conflict checks before the first copy. |
| Existing tests preserve obsolete arbitrary-prefix behavior | Medium | Replace the obsolete test with immediate-child collection cases and explicit rejection scenarios. |
| Contribution tests use unrealistic lockfile fixtures | Medium | Use repository-relative `skill_path` values that include `skills_root` and resolve by exact `requirement`. |
| Cross-slice change becomes too large to review | Medium | Land each numbered task as a focused change and keep this plan current after each task/checkpoint. |
| Error wording diverges across commands | Low | Define stable shared concepts but keep boundary-specific actionable messages covered by CLI tests. |

## Assumptions

- Kebab-case segment validation remains the project-wide rule for catalog paths
  because current installation and contribution selectors already require it.
- A `SKILL.md` directly at `skills_root` is not a valid skill because its relative
  directory is `.`, which is not `<skill>` or `<collection>/<skill>`.
- Duplicate paths remain invalid or nonsensical JSON catalog state, while duplicate
  skill names at distinct valid paths remain supported.
- Collection expansion is based solely on cached index entries; empty and
  non-skill filesystem directories are not selectable collections.
- Existing add/update sequencing should already preserve state because reader
  validation precedes cache writes; Task 5 verifies rather than assumes this.
- No new dependency or ADR is required.

## Open Questions

- [ ] Confirm the required specification clarification: catalog-depth validation
  applies to the selector in `requirement`, while lockfile `skill_path` remains
  repository-relative.
- [ ] Confirm whether a `SKILL.md` directly at `skills_root` should be rejected as
  an invalid zero-segment skill, as implied by the new path grammar.

These questions affect precise test expectations but not the overall dependency
order. Resolve them before Task 2 is finalized.

## Handoff Notes

- Update this plan after every completed task and checkpoint.
- Run the narrowest relevant tests first during implementation, then the complete
  quality gate before handoff.
- Avoid unrelated refactors in shared filesystem discovery, DTO modules, or CLI
  wiring.
- Preserve public import paths unless a deliberate shared-kernel export is added.
- If implementation uncovers a schema change rather than a validation tightening,
  stop and record that decision through the ADR workflow before proceeding.
