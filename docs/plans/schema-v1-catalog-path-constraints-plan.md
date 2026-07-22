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
- Zero-segment, malformed, non-kebab-case, over-deep, and mixed-node catalogs fail
  with deterministic, actionable errors.
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

## Resolved Schema-v1 Contract Clarifications

The updated specifications use two distinct path concepts:

- `requirement` contains the catalog-relative selector after the local alias,
  such as `browser/runtime-verification`.
- `ritebook.lock.skills[].skill_path` is generated as a source-repository-relative
  checkout path that includes `skills_root`, such as
  `skills/browser/runtime-verification`.

The schema-v1 contract is resolved as follows before implementation:

- Apply catalog-depth and catalog-segment validation to the selector encoded in
  `requirement`, not to repository-relative `skill_path` or `skill_file`.
- Require every catalog segment, including both `<collection>` and `<skill>`, to
  use Ritebook's existing 1-64 character canonical kebab-case identifier rule.
- Reject a `SKILL.md` directly at `skills_root`; its relative directory is `.`, so
  it represents a zero-segment candidate rather than a valid catalog skill.
- Retain `skill_path` and `skill_file` as safe repository-relative checkout paths.
  They may contain additional segments contributed by `skills_root`.

Task 1 makes these decisions normative and aligns terminology across the affected
specifications. They clarify the existing schema-v1 contract without changing
serialized fields or requiring an ADR.

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
- Resolve requirement selectors by exact match first, but only after complete
  index validation has made mixed root-skill/collection nodes impossible.
  Collection expansion is a requirements-only fallback for one-segment selectors
  with immediate children.

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

- [x] Task 1: Align schema-v1 catalog-path and lockfile semantics
- [x] Task 2: Add a shared schema-v1 catalog-path policy

### Task 1: Align Schema-v1 Catalog-path and Lockfile Semantics

**Description:** Align the affected specifications before code changes. Define a
catalog path as one or two canonical kebab-case segments, reject a zero-segment
candidate at `skills_root`, and distinguish catalog-relative selectors from
repository-relative lockfile source paths. Apply catalog-depth validation to the
selector encoded in `requirement`, not to `skill_path` or `skill_file`.

**Acceptance criteria:**

- [x] The specifications distinguish catalog-relative selectors from
  repository-relative lockfile paths.
- [x] Root and collected selectors are limited to one or two segments.
- [x] Collection and skill segments both use the existing 1-64 character canonical
  kebab-case identifier rule.
- [x] A `SKILL.md` directly at `skills_root` is explicitly invalid as a
  zero-segment candidate.
- [x] Repository-relative lockfile paths remain valid regardless of
  `skills_root` depth, subject to existing safe-path validation.
- [x] `requirement`, `skill_path`, and `skill_file` use consistent terminology
  across specification requirements and test expectations.

**Verification:**

- [x] Compare the clarified text with lockfile generation in
  `src/ritebook/features/skill_installation/application/use_cases/install_from_requirements.py`.
- [x] Confirm examples remain consistent with the documented lockfile schema.
- [x] Check metadata updates against `docs/specs/README.md`; change `Spec version`,
  `Last reviewed`, and `Implementation state` only when their governance rules
  require it.

**Implementation note (2026-07-22):** Aligned the shared and workflow-specific
specifications around catalog selectors and repository-relative lockfile paths.
The documented lockfile semantics now match generation: `requirement` preserves
the qualified catalog selector, while `skill_path` and `skill_file` prepend the
published `skills_root`. Existing `1.1`, `2026-07-22`, and `Partially implemented`
metadata remains accurate because this clarification does not complete enforcement.

**Dependencies:** None

**Files likely touched:**

- `docs/specs/README.md`
- `docs/specs/publisher-index-generation-spec.md`
- `docs/specs/consumer-git-index-registry-spec.md`
- `docs/specs/install-skill-spec.md`
- `docs/specs/list-skills-spec.md`
- `docs/specs/upstream-skill-contributions-spec.md`

**Estimated scope:** S, terminology and normative contract alignment only

### Task 2: Add a Shared Schema-v1 Catalog-path Policy

**Description:** Add a pure shared-kernel module that validates literal
catalog-relative skill paths, classifies valid paths, and validates complete path
sets. Validate the literal string before constructing `PurePosixPath` so path
normalization cannot hide invalid input. Reuse the existing identifier policy,
require one or two canonical kebab-case segments, and reject mixed
root-skill/collection path sets.

**Acceptance criteria:**

- [x] Accepts `code-review` and `quality/code-review`.
- [x] Rejects empty, absolute, backslash, dot, parent, repeated-separator,
  trailing-separator, and three-or-more-segment paths.
- [x] Rejects non-kebab-case catalog segments consistently with existing
  application selectors.
- [x] Classifies one-segment paths as root skills and two-segment paths as
  collection children without introducing transport-specific types.
- [x] Rejects sets such as `quality` plus `quality/code-review`.
- [x] Allows duplicate skill names at distinct valid paths.
- [x] Rejects duplicate exact paths deterministically.
- [x] Distinguishes malformed paths, invalid depth, and mixed-node sets through
  technology-neutral typed failures or stable reason codes.
- [x] Reuses `shared_kernel.identifiers` rather than defining a second identifier
  regex.
- [x] Exposes a small intentional shared-kernel API; update `__init__.py` only if a
  stable package-level re-export is deliberately required.

**Verification:**

- [x] Focused shared-kernel tests cover valid, malformed, over-deep, mixed-node,
  duplicate-exact-path, and duplicate-name-at-distinct-path cases.
- [x] `uv run pytest tests/unit/shared_kernel/test_catalog_paths.py`
- [x] `uv run ruff check src/ritebook/shared_kernel tests/unit/shared_kernel`
- [x] `uv run ty check src/ritebook`

**Implementation note (2026-07-22):** Added the pure
`shared_kernel.catalog_paths` API with validated root-skill and collection-child
classifications, literal-before-normalization checks, and stable typed failure
reasons for malformed paths, invalid depth or segments, duplicates, and mixed
nodes. Complete-set validation preserves input order on success and deterministically
identifies mixed-node conflicts. The API remains module-scoped rather than adding a
package-level re-export. Focused coverage passes with 21 tests; the full gate passes
with Ruff, `ty`, and 578 tests passing with one existing skip.

**Dependencies:** Task 1

**Files likely touched:**

- `src/ritebook/shared_kernel/catalog_paths.py`
- `src/ritebook/shared_kernel/__init__.py` only if an intentional re-export is added
- `tests/unit/shared_kernel/test_catalog_paths.py`
- `tests/unit/shared_kernel/__init__.py` if required by the repository test layout

**Estimated scope:** S, two required files plus optional package initializers

### Checkpoint A: Shared Contract

- [x] Shared catalog-path tests pass.
- [x] Changed modules pass Ruff and `ty`.
- [x] Shared code contains no filesystem, JSON, CLI, or slice-specific errors.

### Phase 2: Stop Invalid Catalogs at Producer and Consumer Boundaries

- [ ] Task 3: Enforce catalog structure during lint and publisher discovery
- [ ] Task 4: Enforce the contract in the JSON index reader
- [ ] Task 5: Prove add/update failure preserves registry state

### Task 3: Enforce Catalog Structure During Lint and Publisher Discovery

**Description:** Keep recursive candidate discovery so invalid nested `SKILL.md`
files are detected rather than ignored. In both adapters, derive literal
catalog-relative parent paths for every candidate and run the shared complete-set
validator. The linter should aggregate deterministic path-scoped issues;
publisher discovery should translate the same failure reasons into actionable
discovery errors before publication. Valid skill package contents remain
unrestricted unless another nested `SKILL.md` declares a candidate skill.

Implement this as two focused changes if necessary: linter issue reporting first,
then publisher rejection using the same policy.

**Acceptance criteria:**

- [ ] Root skills and immediate collection children are discovered.
- [ ] A `SKILL.md` directly at `skills_root` is reported as an invalid
  zero-segment candidate.
- [ ] Empty, non-skill, hidden, and symlinked directories retain their current
  behavior.
- [ ] Over-deep candidates are reported with the offending path.
- [ ] Non-kebab-case collection and skill directory segments are reported with the
  offending path.
- [ ] A skill directory containing a descendant skill is rejected as a mixed
  skill/collection node.
- [ ] A collection remains implicit and produces no separate index entry.
- [ ] Structural issues are deterministic and path-scoped in `lint-skills`.
- [ ] Multiple structural failures are ordered deterministically, while publisher
  failure remains actionable without requiring linter-style aggregation.
- [ ] `publish-index` writes or replaces no index when structural validation
  fails.

**Verification:**

- [ ] Extend linter filesystem-discovery tests for root, collected, zero-segment,
  invalid segment, over-deep, mixed-node, ignored-content, and deterministic
  multi-issue cases.
- [ ] Extend publisher filesystem-discovery tests for the same path matrix.
- [ ] Prove directory-path errors remain deterministic when frontmatter also
  contains an invalid or mismatched skill name.
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

**Description:** Validate every literal schema-v1 `skills[].path`, then validate
the complete path set in the index-registry JSON adapter before metadata escapes.
Make `read_index()` and `read_skills()` share one parsing and catalog-validation
path so their contracts cannot drift. Apply it to committed indexes used by
`add-index` and `update-index`, and cached indexes used by `list-skills` and
installation.

**Acceptance criteria:**

- [ ] `read_index()` and `read_skills()` accept root and collection-child paths.
- [ ] Both methods reject over-deep and mixed-node catalogs before returning any
  metadata.
- [ ] Both methods reject non-kebab-case segments and duplicate exact paths.
- [ ] Literal non-canonical paths cannot be normalized into apparent validity by
  `PurePosixPath`.
- [ ] Adapter errors identify invalid schema-v1 catalog structure and preserve a
  machine-testable cause or stable reason.
- [ ] CLI-facing errors provide actionable reorganize-and-republish guidance.
- [ ] Duplicate skill names at distinct valid paths remain allowed.
- [ ] Existing digest and provenance behavior remains unchanged.

**Verification:**

- [ ] Extend JSON reader tests for accepted root/collected paths and rejected
  malformed, invalid-segment, duplicate, over-deep, and mixed path sets through
  both reader methods.
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
failed alias and continues. Use mutation-recording test doubles or call-order
assertions so the tests prove that mutation was never attempted rather than only
comparing final values.

**Acceptance criteria:**

- [ ] Invalid `add-index` performs no cache or registry mutation.
- [ ] Invalid forced replacement preserves the existing cache and registry entry.
- [ ] Invalid `update-index` preserves cache path, bytes, revision, digest,
  published metadata, skill count, and timestamps.
- [ ] Registry state and cached index bytes are snapshotted before failure and
  compared afterward where real filesystem state is involved.
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
parsing before catalog lookup. Keep `install-skill` exact-only and add explicit
tests proving malformed or over-deep selectors are rejected and a first-level
collection selector is not expanded. Exact-match behavior relies on the index
reader having already rejected mixed root-skill/collection catalogs.

**Acceptance criteria:**

- [ ] Direct selectors accept one- or two-segment exact skill paths only.
- [ ] Malformed, non-kebab-case, and over-deep selectors fail at the
  command/application boundary.
- [ ] A collection selector with no exact root skill is reported as unknown and is
  never expanded by `install-skill`.
- [ ] Exact root-skill behavior remains valid.
- [ ] Exact collection-child behavior remains valid.
- [ ] Cached metadata entering the slice is structurally validated by the
  index-reader boundary.

**Verification:**

- [ ] Extend selector DTO tests for one- and two-segment paths plus malformed,
  non-kebab-case, and over-deep paths.
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

**Description:** In `InstallFromRequirements`, validate selector syntax before
catalog lookup and resolve exact matches first. If no exact match exists, permit
only a one-segment selector and resolve indexed skills whose paths are exactly
`<selector>/<skill>`. Mixed root-skill/collection catalogs are impossible because
the index reader validates the complete path set first. Build and validate the
complete expanded target and lock-entry plan before source opening or filesystem
mutation. Require collection selectors to use `target`; reject collection
selectors using `target_path` during planning.

**Acceptance criteria:**

- [ ] Exact root and collection-child skills retain exact-match precedence.
- [ ] Selector syntax is validated before lookup or expansion.
- [ ] A one-segment collection expands only immediate child skills.
- [ ] Expanded skills are ordered deterministically by catalog path.
- [ ] Empty or unrelated collection selectors fail as unknown.
- [ ] Arbitrary descendant prefixes and over-deep selectors are rejected.
- [ ] A collection selector using `target_path` fails before any mutation.
- [ ] A collection selector using `target` resolves each child below the target
  base by final skill name.
- [ ] Expanded exact requirements are derived from each cached catalog path, never
  from `skills[].name`.
- [ ] Generated lock entries contain one exact requirement per resolved skill and
  retain repository-relative `skill_path` and `skill_file`.
- [ ] Duplicate, canonical, and parent-child target conflict checks run over the
  fully expanded plan before source opening or copying.

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

**Description:** Parse `ContributionSkillReference` as a local alias plus a
one- or two-segment catalog selector and remove the lockfile reader's
`skill_path == selector` fallback. Resolve by exact equality with the stored
qualified `requirement`. Continue validating repository-relative `skill_path` and
`skill_file` for safe checkout use, but do not apply catalog-depth rules to them.

**Acceptance criteria:**

- [ ] Root and collection-child exact requirements resolve one lockfile entry.
- [ ] The requested alias and catalog selector are compared as one exact qualified
  requirement, without independently resolving publisher `index.name`.
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

**Dependencies:** Task 7

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
reiterating that `install-skill` and `publish-skill-change` are exact-only. Audit
each affected specification independently against all of its normative behavior;
mark it `Implemented` only when the complete specification, not merely this plan's
subset, has implementation evidence.

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
- [ ] Each changed specification's `Implementation state` reflects its complete
  normative scope; specs with unrelated remaining work stay `Partially
  implemented` with accurate implementation-status notes.
- [ ] `Spec version` and `Last reviewed` metadata are updated only according to
  `docs/specs/README.md` governance.

**Verification:**

- [ ] `uv run ruff format .`
- [ ] `uv run ruff check .`
- [ ] `uv run ty check src/ritebook`
- [ ] `uv run pytest -m "not e2e"`
- [ ] `uv build`
- [ ] `uv run pytest tests/e2e -q`
- [ ] `docker build -f Dockerfile.e2e -t ritebook-e2e .`
- [ ] `docker run --rm --network none ritebook-e2e`
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
Schema-v1 contract alignment
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
- Task 8 follows Task 7 so contribution fixtures and exact matching use finalized,
  generated lockfile semantics.
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

- Duplicate paths remain invalid or nonsensical JSON catalog state, while duplicate
  skill names at distinct valid paths remain supported.
- Collection expansion is based solely on cached index entries; empty and
  non-skill filesystem directories are not selectable collections.
- Existing add/update sequencing should already preserve state because reader
  validation precedes cache writes; Task 5 verifies rather than assumes this.
- No new dependency or ADR is required.

## Readiness Assessment

**Phase 1 complete.** The normative path semantics and shared schema-v1 catalog
path policy are implemented and verified. Task 3 is the next sequential slice;
Task 4 may proceed independently from the same shared API. Both must preserve the
focused checkpoints and validate-before-mutation sequencing above.

## Handoff Notes

- Update this plan after every completed task and checkpoint.
- Run the narrowest relevant tests first during implementation, then the complete
  quality gate before handoff.
- Avoid unrelated refactors in shared filesystem discovery, DTO modules, or CLI
  wiring.
- Preserve public import paths unless a deliberate shared-kernel export is added.
- Import the Task 2 policy from `ritebook.shared_kernel.catalog_paths`; no
  package-level re-export was added.
- If implementation uncovers a schema change rather than a validation tightening,
  stop and record that decision through the ADR workflow before proceeding.
