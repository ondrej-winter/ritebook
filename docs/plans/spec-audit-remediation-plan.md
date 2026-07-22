# Implementation Plan: Specification Audit Remediation

## Overview

This plan addresses the findings from the July 2026 audit of every specification
under `docs/specs/`. The audit was revalidated against commit
`957379ad6bfa3ea1886140d032f1402980a3ff39`.

The work is ordered by dependency and risk. It starts with the shared provenance
contract, then closes destructive filesystem and persistence gaps, and finally
aligns terminology, specification governance, Docker E2E claims, and validation.
Each task is intended to be completed and reviewed separately so that one safety
property can be established before dependent behavior changes.

## Goal

Make the specifications authoritative, internally consistent, testable, and
aligned with safe implementation behavior across publishing, index registration,
skill installation, upstream contribution, and Docker E2E validation.

## Deliverables

- An ADR defining the publisher-to-contribution provenance and trust model.
- Updated specifications with explicit lifecycle metadata, shared terminology,
  acceptance criteria, failure behavior, and security constraints.
- Focused implementation changes for every confirmed safety or correctness gap.
- Regression tests for filesystem, persistence, provenance, output-sanitization,
  and failure-recovery behavior.
- Updated README and operational guidance where user-visible behavior changes.
- A passing project quality gate and Docker E2E suite.

## Success Criteria

- Every audit finding in the coverage matrix is closed by a completed task or an
  explicitly approved and documented exception.
- Cached metadata can never silently authorize installation of different source
  content.
- Filesystem mutations reject unsafe overlap and symlink paths and preserve prior
  valid state when replacement fails.
- Multi-artifact writes have documented and tested commit or recovery semantics.
- Stored and displayed external values cannot leak credentials or inject terminal
  control sequences.
- All six specifications use the same lifecycle metadata and vocabulary.
- The configured formatter, linter, selected type checker, test suite, package
  build, and Docker E2E suite pass.

## Constraints

- Preserve hexagonal dependency direction and vertical feature-slice ownership.
- Keep external data validation in adapters and orchestration in application use
  cases.
- Do not silently change public CLI, index, registry, requirements, or lockfile
  contracts. Version or migrate compatibility-sensitive changes explicitly,
  except where an accepted pre-release decision such as ADR 0001 explicitly
  requires rejection and regeneration.
- Keep each implementation task focused. If a task grows beyond one reviewable
  session or about five files, split it before editing.
- Use `uv` for project commands and the type checker selected in Task 16.
- Do not weaken tests or bypass lint rules to make a task pass.

## Progress Tracking

Treat this plan as a living document throughout implementation. After each task
or meaningful scope change:

- check off completed task, acceptance, verification, and checkpoint items;
- leave unverified items unchecked;
- record the completion date and relevant commit or PR in the task's status note;
- add blockers, deviations, accepted risks, and newly discovered work;
- update dependencies and the audit coverage matrix when sequencing changes;
- stop at a checkpoint when a required decision remains unresolved.

Do not mark an audit finding closed merely because a specification was edited.
Implementation-sensitive findings require code, regression tests, and synchronized
documentation unless the project explicitly accepts and records the existing risk.

## Status Summary

### Phase 1: Provenance foundation

- [x] Task 1: Decide and record the end-to-end provenance model
- [x] Task 2: Bind each cached index to validated source identity
- [x] Task 3: Install only from the source identity bound to the cached index
- [x] Task 4: Propagate verified provenance into lockfiles and contributions

### Phase 2: Destructive filesystem safety

- [x] Task 5: Reject installation source-target overlap
- [x] Task 6: Make contribution index regeneration symlink-safe
- [x] Task 7: Correct publisher output-root and `skills_root` semantics
- [x] Task 8: Make publisher index replacement atomic and symlink-safe
- [x] Task 9: Make forced installation replacement recoverable
- [x] Task 10: Canonicalize and deconflict requirements-install targets

### Phase 3: Persistence and untrusted output

- [x] Task 11: Define and implement registry-cache commit semantics
- [x] Task 12: Sanitize and safely persist Git source values
- [x] Task 13: Define terminal control-character handling
- [x] Task 14: Define recovery for post-copy generated-state failures
- [x] Task 15: Resolve local-source lockfile portability

### Phase 4: Specification and tooling governance

- [x] Task 16: Resolve the `ty` versus `mypy` policy conflict
- [x] Task 17: Add lifecycle metadata to every specification
- [ ] Task 18: Standardize published-name and local-alias terminology
- [ ] Task 19: Align Docker E2E isolation claims and behavior

### Phase 5: Final synchronization

- [ ] Task 20: Complete cross-spec review and full validation

---

## Phase 1: Provenance Foundation

## Task 1: Decide and Record the End-to-End Provenance Model

**Audit finding:** Critical 1 — cached index metadata is not bound to the source
content installed later.

**Description:** Record one authoritative architecture decision for how a
publisher index, cached index, Git source state, installed content, lockfile, and
contribution base identify the same source content. Evaluate at least immutable
Git revision pinning, a Ritebook-owned source snapshot, and content hashes. The
decision must cover managed Git URL sources and mutable user-owned local Git
repositories. Do not implement dependent behavior until this decision is
accepted.

**Acceptance criteria:**

- [x] An ADR defines the selected identity, where it is captured, where it is
  persisted, and how every downstream workflow verifies it.
- [x] The ADR defines behavior for refresh failure, detached or rewritten Git
  history, local repository drift, unavailable revisions, and schema migration.
- [x] All affected specs link to the ADR and no longer imply that independently
  mutable cached metadata and source bytes are equivalent.

**Verification:**

- [x] Review the ADR against all six specifications and the current registry,
  installation, and contribution DTOs.
- [x] Confirm the decision explicitly rejects compatibility for pre-release
  schema-v1 registry, installation-registry, and lockfile data and requires users
  to regenerate local state.
- [x] Obtain explicit architecture approval before Task 2.

**Dependencies:** None.

**Files likely touched:**

- `docs/adr/<next-number>-source-provenance-and-trust.md`
- `docs/specs/consumer-git-index-registry-spec.md`
- `docs/specs/install-skill-spec.md`
- `docs/specs/upstream-skill-contributions-spec.md`
- `docs/specs/publisher-index-generation-spec.md`

**Estimated scope:** Medium, documentation only.

**Status note:** Completed 2026-07-21. ADR 0001 was explicitly approved and
accepted. All six specifications now link to the commit-plus-index-digest
contract. Tasks 2 through 4 remain open for implementation and regression tests.

## Task 2: Bind Each Cached Index to Validated Source Identity

**Audit finding:** Critical 1.

**Description:** Implement the registry-side portion of the approved provenance
model. Capture source identity at the same point that `ritebook-index.json` is
validated and persist enough information to prove which source state the cached
index describes. Updating a managed clone must not leave an old cache silently
paired with new source content.

**Acceptance criteria:**

- [x] Added and updated registry entries persist the approved source identity for
  the exact index content that passed validation.
- [x] A failed refresh leaves a coherent previous cache/source pair or marks the
  source unusable until recovery; it never presents stale metadata as current.
- [x] Existing pre-release registry schema-v1 data without `source_revision` or
  `index_digest` is rejected with actionable guidance to regenerate registration;
  it is not inferred, migrated automatically, or accepted in compatibility mode.

**Verification:**

- [x] Focused tests cover successful add/update, validation failure after source
  refresh, unavailable source identity, and rejection of legacy registry data
  with regeneration guidance.
- [x] Run `uv run pytest tests/unit/features/index_registry`.
- [x] Run `uv run pytest tests/integration -m integration` for affected adapters.

**Dependencies:** Task 1.

**Files likely touched:**

- `src/ritebook/features/index_registry/application/dtos/index_registry.py`
- `src/ritebook/features/index_registry/application/use_cases/add_index.py`
- `src/ritebook/features/index_registry/application/use_cases/update_index.py`
- `src/ritebook/features/index_registry/adapters/outbound/filesystem_registry/adapter.py`
- `tests/unit/features/index_registry/`

**Estimated scope:** Medium; split legacy-state rejection from update orchestration
if the change exceeds five files.

**Status note:** Completed 2026-07-21. Registry add/update now selects a full Git
commit, reads and validates the root index from that committed object, hashes the
exact bytes, and persists `source_revision` plus `index_digest`. Dirty local
repositories and unavailable revisions are rejected before cache or registry
writes, legacy registry entries require regeneration, and the focused unit and
integration suites pass. Full two-artifact commit/recovery semantics remain owned
by Task 11.

## Task 3: Install Only From the Source Identity Bound to the Cached Index

**Audit finding:** Critical 1.

**Description:** Update source resolution so direct and requirements-file installs
verify that the cached index and root index at the full Git revision selected in
Task 1 both match the digest persisted in Task 2, then copy only from that commit.
Never treat a mutable checkout or working tree as the bound source state.

**Acceptance criteria:**

- [x] Installation fails before trusting metadata or copying unless the cached
  index and root index at the bound commit both match the persisted digest.
- [x] Managed Git sources install from the bound source state without implicitly
  advancing it during installation.
- [x] Local Git installs read committed objects without using or mutating working
  tree content and fail with recovery guidance when the repository or bound commit
  is unavailable.

**Verification:**

- [x] Regression tests reproduce stale-cache/new-clone, cached-index mismatch,
  bound-commit index mismatch, and unavailable local-source scenarios.
- [x] Run `uv run pytest tests/unit/features/skill_installation`.
- [x] Run the relevant publisher-to-consumer E2E workflow.

**Dependencies:** Tasks 1 and 2.

**Files likely touched:**

- `src/ritebook/features/skill_installation/application/dtos/install_skill.py`
- `src/ritebook/features/skill_installation/application/use_cases/install_skill.py`
- `src/ritebook/features/skill_installation/application/use_cases/install_from_requirements.py`
- `src/ritebook/features/skill_installation/adapters/outbound/source_repository/adapter.py`
- `tests/unit/features/skill_installation/`

**Estimated scope:** Medium; direct and requirements-file behavior should share one
source-resolution contract.

**Status note:** Completed 2026-07-21. Direct and requirements-file installs now
validate the exact cached index bytes and the root index bytes at the persisted
full Git revision against the registered digest before reading skill metadata.
Managed and local sources are materialized from committed objects into temporary
snapshots without fetch, checkout, or working-tree reads, with actionable failures
for unavailable repositories, commits, or mismatched indexes. The focused
installation suite passed with 93 tests; the affected unit and integration suites
passed with 99 tests; the full non-E2E suite passed with 451 tests and 15 deselected;
the two relevant publisher-to-consumer install E2E workflows passed; and Ruff and
`ty` checks passed. Lockfile and installation-state digest propagation remains
owned by Task 4.

## Task 4: Propagate Verified Provenance Into Lockfiles and Contributions

**Audit finding:** Critical 1.

**Description:** Ensure generated installation state records the verified identity
actually used for copying and that contribution preparation consumes the same
identity. Update the pre-release schema-v1 lockfile and installation-registry
contracts in place; reject older local files without provenance and direct users
to regenerate them.

**Acceptance criteria:**

- [x] `ritebook.lock` and `installations.json` record the verified installed source
  identity rather than whatever revision happens to be current afterward.
- [x] Contribution comparison and branch preparation use that identity as their
  locked base and fail clearly when it is unavailable.
- [x] Schema-v1 lockfile and installation-registry readers reject missing
  provenance with regeneration guidance; parser/writer tests cover rejection and
  the required fields without automatic migration or compatibility inference.

**Verification:**

- [x] Run focused lockfile writer/reader and contribution application tests.
- [x] Run `uv run pytest tests/unit/features/skill_installation`.
- [x] Run `uv run pytest tests/unit/features/skill_contribution`.

**Dependencies:** Tasks 1 through 3.

**Files likely touched:**

- `src/ritebook/features/skill_installation/application/dtos/install_skill.py`
- `src/ritebook/features/skill_installation/adapters/outbound/json_lockfile/adapter.py`
- `src/ritebook/features/skill_contribution/application/dtos/`
- `src/ritebook/features/skill_contribution/adapters/outbound/json_lockfile/reader.py`
- Corresponding installation and contribution tests

**Estimated scope:** Medium; split lockfile schema work from contribution behavior
if necessary.

**Status note:** Completed 2026-07-21. Installation now carries the exact verified
`source_revision` and `index_digest` returned by source resolution into deterministic
`ritebook.lock` and `installations.json` output. Legacy schema-v1 generated state
without either field is rejected with regeneration guidance. Contribution lockfile
parsing requires the same pair, and isolated Git workspaces verify that the locked
commit exists and its committed root index matches the digest before checkout,
cleanup, comparison, or branch preparation. Focused installation tests passed with
94 tests, focused contribution tests passed with 109 tests, integration tests passed
with 6 tests, and the contribution E2E workflow passed with 3 tests.

## Checkpoint A: Provenance Contract

- [x] ADR is accepted and linked from affected specs.
- [x] Registry cache, source resolver, generated state, and contribution workflow
  agree on one source identity.
- [x] A failed index update cannot lead to installation of different unvalidated
  source content.
- [x] Focused unit and integration suites pass.

---

## Phase 2: Destructive Filesystem Safety

## Task 5: Reject Installation Source-Target Overlap

**Audit finding:** Critical 2 — installation may delete or recursively copy its
own source.

**Description:** Validate the resolved source directory and target before any
deletion, directory creation, or copy. Reject equality and both ancestor/descendant
relationships. Apply the same rule to direct and requirements-file installation.

**Acceptance criteria:**

- [x] Target equal to the source skill directory is rejected before mutation.
- [x] Target above or inside the source skill directory is rejected before
  mutation.
- [x] Errors identify unsafe overlap without exposing file contents or sensitive
  source details.

**Verification:**

- [x] Add regression tests for equal, ancestor, descendant, and safe sibling paths.
- [x] Run `uv run pytest tests/unit/features/skill_installation/adapters/outbound/test_filesystem_installer.py`.
- [x] Confirm a rejected forced install leaves source and existing target intact.

**Dependencies:** None; coordinate with Task 9 if both modify the installer.

**Files likely touched:**

- `src/ritebook/features/skill_installation/adapters/outbound/filesystem_installer/adapter.py`
- `tests/unit/features/skill_installation/adapters/outbound/test_filesystem_installer.py`
- `docs/specs/install-skill-spec.md`

**Estimated scope:** Small.

**Status note:** Completed 2026-07-21. The filesystem installer now compares the
canonical resolved source skill directory and target before any existence check,
deletion, parent creation, or copy. Equal, ancestor, and descendant relationships
raise a content-safe overlap error for both direct and requirements-file installs,
including forced installs. Regression coverage confirms source and existing target
content remain intact and safe sibling installation still succeeds. The focused
adapter suite passed with 23 tests, the skill-installation suite passed with 98
tests, the full non-E2E suite passed with 461 tests and 15 deselected, and Ruff and
`ty` checks passed.

## Task 6: Make Contribution Index Regeneration Symlink-Safe

**Audit finding:** Critical 3 — contribution index regeneration can write through
a symlink outside its checkout.

**Description:** Treat the existing and replacement `ritebook-index.json` paths as
untrusted. Validate every path component, reject symlinks, require containment in
the Ritebook-owned checkout, and preserve external files even when a malicious
checkout contains a symlinked index.

**Acceptance criteria:**

- [x] Index reading rejects a symlinked file and symlinked ancestor paths.
- [x] Index regeneration cannot write outside the resolved contribution checkout.
- [x] Rejection occurs before publisher execution or any external file mutation.

**Verification:**

- [x] Add a regression test with `ritebook-index.json` linked to an external file.
- [x] Add a regression test for a symlinked parent path where supported.
- [x] Run `uv run pytest tests/unit/features/skill_contribution/adapters/outbound/test_index_regeneration_adapter.py`.

**Dependencies:** None; Task 8 may provide a shared safe-write primitive only if
that primitive remains adapter infrastructure without cross-slice business logic.

**Files likely touched:**

- `src/ritebook/features/skill_contribution/adapters/outbound/index_regeneration/adapter.py`
- `tests/unit/features/skill_contribution/adapters/outbound/test_index_regeneration_adapter.py`
- `docs/specs/upstream-skill-contributions-spec.md`

**Estimated scope:** Small.

**Status note:** Completed 2026-07-22. Contribution index regeneration now
preflights the Ritebook-owned checkout and root index before reading metadata,
changing directories, or invoking the publisher. It rejects any symlink component
in the checkout path, a symlinked or non-regular `ritebook-index.json`, and any
resolved index outside the checkout. Regression tests confirm publisher execution
does not begin and an external symlink target remains unchanged. The focused
adapter suite passed with 5 tests, the full contribution suite passed with 111
tests, the full non-E2E suite passed with 463 tests and 15 deselected, the package
build succeeded, and Ruff and `ty` checks passed.

## Task 7: Correct Publisher Output-Root and `skills_root` Semantics

**Audit finding:** Required 4 — absolute `--skills-root` values can produce an
unusable index.

**Description:** Define and implement one canonical relationship among invocation
working directory, repository root, skills root, output path, and serialized
`skills_root`. Do not serialize an absolute nested skills root as `.` unless the
index is written at that same root by contract.

**Acceptance criteria:**

- [x] Relative and absolute inputs that select the same directory produce the same
  portable index paths.
- [x] Every generated `skills[].path` resolves from the serialized `skills_root`
  relative to the repository containing `ritebook-index.json`.
- [x] CLI help, success output, README, and publisher spec clearly state where the
  index is written.

**Verification:**

- [x] Add test matrices for repository root, nested skills root, relative input,
  absolute input, and invocation from another directory.
- [x] Run publisher application, adapter, and CLI tests.
- [x] Generate an index in a temporary repository and install one indexed skill
  through the consumer workflow.

**Dependencies:** Task 1 if the output-root decision affects provenance identity.

**Files likely touched:**

- `src/ritebook/features/publisher/application/use_cases/publish_index.py`
- Publisher discovery or CLI adapter as selected by the contract
- `tests/unit/features/publisher/`
- `tests/e2e/test_cli_workflows.py`
- `docs/specs/publisher-index-generation-spec.md`

**Estimated scope:** Medium.

**Status note:** Completed 2026-07-22. CLI publishing now treats the invocation
directory as the repository and output root, canonicalizes relative and absolute
skills-root inputs to one resolved scan path plus a portable repository-relative
`skills_root`, and rejects roots outside the output repository before publisher
execution. Contribution regeneration supplies the same explicit pair for its
isolated checkout. Focused publisher, CLI, and contribution tests passed with 56
tests. The full non-E2E suite passed with 465 tests and 15 deselected, the full
E2E suite passed with 15 tests, the package build succeeded, and Ruff and `ty`
checks passed.

## Task 8: Make Publisher Index Replacement Atomic and Symlink-Safe

**Audit finding:** Required 5 — publisher replacement can truncate prior output or
follow a symlink.

**Description:** Replace direct `Path.write_text()` output with a checked,
same-directory temporary write and final replacement. Reject symlinked output
paths and define cleanup and prior-file preservation on every failure path.

**Acceptance criteria:**

- [x] Existing valid index content remains unchanged when serialization, temporary
  write, flush, or replacement fails.
- [x] A symlinked output file or unsafe ancestor is rejected without modifying its
  target.
- [x] Temporary files are uniquely named, permission-safe, and cleaned after
  handled failures.

**Verification:**

- [x] Add writer tests for successful replacement, write failure, replace failure,
  existing symlink, and stale temporary-file collision.
- [x] Run `uv run pytest tests/unit/features/publisher/adapters/outbound`.
- [x] Confirm generated JSON remains deterministic and two-space formatted.

**Dependencies:** Task 7.

**Files likely touched:**

- `src/ritebook/features/publisher/adapters/outbound/json_index/writer.py`
- `tests/unit/features/publisher/adapters/outbound/test_json_index_writer.py`
- `docs/specs/publisher-index-generation-spec.md`

**Estimated scope:** Small.

**Status note:** Completed 2026-07-22. The publisher JSON writer now serializes
the complete payload before filesystem mutation, rejects symlinked output files
and ancestor components, writes through a uniquely and securely created
same-directory temporary file, flushes and synchronizes it, revalidates the
destination, and atomically replaces the index. Serialization, write, sync, and
replacement failures preserve prior index content and clean the writer-owned
temporary file; stale similarly named files are not reused or removed. The
focused writer suite passed with 12 tests, the publisher adapter suite passed
with 21 tests, the publisher suite passed with 48 tests, the full non-E2E suite
passed with 473 tests and 15 deselected, the package build succeeded, and Ruff
and `ty` checks passed.

## Task 9: Make Forced Installation Replacement Recoverable

**Audit finding:** Required 9 — forced installation deletes the previous target
before replacement succeeds.

**Description:** Stage a complete replacement next to the target, validate the
staged tree, and swap it into place while retaining enough prior state to recover
from a failed replacement. Never expose a partially copied target as success.

**Acceptance criteria:**

- [x] Copy failure leaves the prior target unchanged.
- [x] Swap failure restores or preserves the prior target and reports actionable
  recovery guidance.
- [x] Success removes temporary and backup paths without deleting broader parent
  directories.

**Verification:**

- [x] Add injected-failure tests for staging, backup, swap, restore, and cleanup.
- [x] Run filesystem installer tests and relevant integration tests.
- [x] Confirm direct and requirements-file `--force` behavior remains consistent.

**Dependencies:** Task 5. Coordinate with Task 14's higher-level commit semantics.

**Files likely touched:**

- `src/ritebook/features/skill_installation/adapters/outbound/filesystem_installer/adapter.py`
- `tests/unit/features/skill_installation/adapters/outbound/test_filesystem_installer.py`
- `docs/specs/install-skill-spec.md`

**Estimated scope:** Medium.

**Status note:** Completed 2026-07-22. The shared filesystem installer now stages
each complete skill directory in a uniquely created same-parent transaction path
before changing an existing target. Forced replacement moves the prior target to
an installer-owned backup, swaps the staged directory into place, restores the
backup after swap failure, and retains it with actionable recovery guidance if
restoration or post-swap cleanup fails. Successful replacement removes only its
own staging and backup paths while preserving sibling content. Failure-injection
coverage includes staging, backup, swap, restore, and cleanup boundaries. The
focused adapter suite passed with 28 tests, the skill-installation suite passed
with 103 tests, integration tests passed with 6 tests, the full non-E2E suite
passed with 478 tests and 15 deselected, the package build succeeded, and Ruff
and `ty` checks passed. Application-level multi-target and generated-state commit
semantics remain owned by Task 14.

## Task 10: Canonicalize and Deconflict Requirements-Install Targets

**Audit finding:** Required 10 — duplicate targets are compared lexically rather
than as resolved filesystem destinations.

**Description:** Introduce a planning boundary that resolves target destinations
without mutating the filesystem, rejects dangerous ancestor symlinks, and detects
equivalent, nested, or otherwise conflicting targets before the first copy.

**Acceptance criteria:**

- [x] Lexically different paths resolving to the same destination are rejected.
- [x] Parent-child target overlaps in one plan are rejected before installation.
- [x] Target collision semantics are documented for symlinks and case-insensitive
  filesystems, including platform limitations.

**Verification:**

- [x] Add tests for `.`/`..` normalization, absolute-relative equivalence,
  symlinked ancestors, parent-child overlap, and safe siblings.
- [x] Run requirements-install application and filesystem adapter tests.
- [x] Confirm no install calls occur after a planning collision.

**Dependencies:** Task 5. Coordinate with Task 9 for target staging paths.

**Files likely touched:**

- `src/ritebook/features/skill_installation/application/ports/skill_installer.py`
- `src/ritebook/features/skill_installation/application/use_cases/install_from_requirements.py`
- `src/ritebook/features/skill_installation/adapters/outbound/filesystem_installer/adapter.py`
- Corresponding application and adapter tests
- `docs/specs/install-skill-spec.md`

**Estimated scope:** Medium.

**Status note:** Completed 2026-07-22. The skill-installer outbound port now
provides a non-mutating target-planning boundary. The filesystem adapter rejects
symlinks in the target or any existing ancestor, applies existing broad-target
safety checks, and returns the canonical destination without creating paths.
Requirements installation preflights the complete plan and rejects lexical aliases
using `.`, `..`, relative/absolute forms, equal destinations, and parent-child
overlaps before the first install call while allowing safe siblings. The spec
documents host-filesystem case semantics and the limitation for differently cased,
entirely nonexistent paths. Focused application and adapter tests passed with 49
tests, the complete skill-installation suite passed with 108 tests, integration
tests passed with 6 tests, the full non-E2E suite passed with 483 tests and 15
deselected, the package build succeeded, and Ruff and `ty` checks passed.

## Checkpoint B: Filesystem Safety

- [x] Source/target and target/target overlaps are rejected before mutation.
- [x] Publisher and contribution index writes cannot follow unsafe symlinks.
- [x] Failed forced replacement preserves prior valid content or retains an
  identified backup with recovery guidance when automatic restoration fails.
- [x] Absolute and relative publisher roots produce portable, installable indexes.
- [x] Focused filesystem and publisher suites pass.

---

## Phase 3: Persistence and Untrusted Output

## Task 11: Define and Implement Registry-Cache Commit Semantics

**Audit finding:** Required 6 — cache and registry persistence can become
inconsistent.

**Description:** Define the local transaction boundary for cached index content
and registry metadata. Implement either atomic directory generation switching,
staged writes with rollback, or another documented recovery protocol. Cover both
`add-index --force` and `update-index`.

**Acceptance criteria:**

- [x] A failure after either staged artifact write leaves the previous registry
  entry and cached index coherently usable or clearly recoverable.
- [x] Readers never observe registry metadata pointing to absent or partially
  written cache content.
- [x] Startup or next-command recovery handles abandoned staging artifacts
  deterministically.

**Verification:**

- [x] Add failure-injection tests at cache stage, registry stage, commit, rollback,
  and recovery boundaries.
- [x] Run all index registry unit and integration tests.
- [x] Inspect generated files to confirm deterministic content and cleanup.

**Dependencies:** Task 2 because source identity belongs in the committed state.

**Files likely touched:**

- `src/ritebook/features/index_registry/application/use_cases/add_index.py`
- `src/ritebook/features/index_registry/application/use_cases/update_index.py`
- `src/ritebook/features/index_registry/adapters/outbound/index_cache/adapter.py`
- `src/ritebook/features/index_registry/adapters/outbound/filesystem_registry/adapter.py`
- Corresponding registry tests

**Estimated scope:** Medium; split adapter staging from use-case commit orchestration
if needed.

**Status note:** Completed 2026-07-22. Cached indexes now use immutable
content-addressed generations, and deterministic `indexes.json` replacement is the
atomic commit pointer after the candidate file is flushed and synchronized. Failed
registry commits preserve the previous pair and best-effort discard the candidate;
the next add or update for the alias removes abandoned adapter-owned generations
and temporary files while preserving the registry-referenced generation and legacy
paths. Focused registry and integration validation passed with 119 tests. The full
gate passed Ruff formatting and linting, `ty`, 491 non-E2E tests with 15 deselected,
package build, and `git diff --check`.

## Task 12: Sanitize and Safely Persist Git Source Values

**Audit finding:** Required 7 — remembered Git sources may expose credentials.

**Description:** Define separate operational, persisted, and display forms for Git
sources. Reject or strip URL user-info and other secret-bearing forms before
persistence, render a redacted display form, sanitize Git errors, and create local
state files with private permissions where supported.

**Acceptance criteria:**

- [x] Credentials embedded in supported URL forms are rejected or removed before
  registry, lockfile, installation registry, logs, errors, and CLI output.
- [x] `list-indexes` displays a useful non-secret source identifier.
- [x] Newly created registry and installation state use documented restrictive
  permissions without breaking supported platforms.

**Verification:**

- [x] Add tests using password, token, URL-encoded user-info, SSH/scp-like syntax,
  and credential-bearing Git failures.
- [x] Search generated test artifacts and captured output for sentinel secrets.
- [x] Run index registry, installation manifest, CLI, and Git adapter tests.

**Dependencies:** Task 1 because persisted source identity may affect provenance.

**Files likely touched:**

- Index registry Git and filesystem adapters
- Index registry CLI command renderer
- Installation lockfile/registry writers
- Shared pure source-value type only if ownership is explicitly justified
- Corresponding tests and affected specs

**Estimated scope:** Medium; split parsing/redaction from file permissions if the
task exceeds five files.

**Status note:** Completed 2026-07-22. Ritebook now distinguishes operational,
safe persisted, and defensive display forms for Git sources. Standard URLs with
username-only, password/token, or percent-encoded authority user-info are rejected
before Git execution, managed-cache mutation, or generated-state persistence;
scp-like SSH sources remain supported. Registry, installation-registry, lockfile,
and contribution boundaries reject unsafe legacy or candidate values without
echoing secrets, `list-indexes` removes URL user-info defensively, and Git failures
do not surface raw subprocess output. User-owned `indexes.json` and
`installations.json` replacements receive POSIX mode `0600`, while the shareable
`ritebook.lock` rejects unsafe sources without forcing private permissions. The
focused remediation suite passed with 106 tests. The full gate passed Ruff
formatting and linting, `ty`, all 517 tests including 15 E2E tests, package build,
and `git diff --check`.

## Task 13: Define Terminal Control-Character Handling

**Audit finding:** Required 8 — untrusted descriptions and sources can inject
terminal control sequences.

**Description:** Choose one documented policy for control characters in index
names, skill paths, descriptions, source displays, and diagnostics. Prefer
rejecting invalid identity/path fields at ingestion and escaping display-only text
at the CLI boundary.

**Acceptance criteria:**

- [x] Newlines, carriage returns, tabs where disallowed, C0/C1 controls, and ANSI
  escape sequences cannot forge additional CLI lines or terminal formatting.
- [x] Valid Unicode descriptions remain readable and deterministic.
- [x] Publisher validation, consumer index validation, and CLI rendering apply one
  documented policy without contradictory transformations.

**Verification:**

- [x] Add parameterized tests for control characters and representative Unicode.
- [x] Run publisher/linter validation, JSON index reader, and CLI rendering tests.
- [x] Capture output and assert exact line count and absence of raw escape bytes.

**Dependencies:** Task 12 for source display policy.

**Files likely touched:**

- Publisher/linter validation boundary
- `src/ritebook/features/index_registry/adapters/outbound/json_index/reader.py`
- `src/ritebook/features/index_registry/adapters/inbound/cli/commands.py`
- Relevant validation and CLI tests
- Publisher, registry, and list-skills specs

**Estimated scope:** Medium.

**Status note:** Completed 2026-07-22. Publisher/linter validation, publisher
domain invariants, and consumer index validation now reject C0 controls, DEL,
and C1 controls in portable descriptions and paths. CLI source, description, and
validation-diagnostic boundaries render any remaining controls as deterministic
visible escapes after source credential redaction, while ordinary Unicode remains
unchanged. The focused remediation suite passed with 148 tests. The full gate
passed Ruff formatting and linting, `ty`, 521 non-E2E tests, all 15 E2E tests,
package build, and `git diff --check`.

## Task 14: Define Recovery for Post-Copy Generated-State Failures

**Audit finding:** Required 12 — clock, manifest, or lockfile failures after copies
are not specified.

**Description:** Define an application-level commit protocol for installed
directories plus `installations.json` or `ritebook.lock`. Move all fallible planning
and timestamp generation before mutation where possible. For unavoidable
persistence failures, either roll back copied targets or return explicit partial
state and recovery instructions.

**Acceptance criteria:**

- [x] Direct install and requirements install have documented outcomes for clock,
  manifest, and lockfile failures after staging or copying.
- [x] The CLI distinguishes pre-mutation full failure, copy failure or restored
  replacement failure, and retained partial installation state. Application-level
  cross-target rollback is intentionally not used because a completed forced copy
  may already have finalized its private backup.
- [x] Tests prove generated state is never reported as written when persistence
  failed and that recovery does not remove pre-existing user content.

**Verification:**

- [x] Add application tests for naive clock, manifest failure, lockfile failure,
  restored replacement and retained-backup failure, and multi-skill partial
  failure.
- [x] Run all skill installation application and adapter tests.
- [x] Add or update an E2E failure scenario with exact diagnostics.

**Dependencies:** Tasks 9, 10, and 11 for established staging/commit patterns.

**Files likely touched:**

- `src/ritebook/features/skill_installation/application/use_cases/install_skill.py`
- `src/ritebook/features/skill_installation/application/use_cases/install_from_requirements.py`
- Installation ports/DTOs required for staged commit or rollback
- Corresponding application tests
- `docs/specs/install-skill-spec.md`

**Estimated scope:** Medium; implement direct install and requirements install as
separate sub-tasks if their recovery protocols differ.

**Status note:** Complete on 2026-07-22. Direct and requirements workflows now
construct and validate deterministic generated-state candidates before copying,
then commit state only after successful copies. Unavoidable post-copy registry or
lockfile failures use an explicit retained-state contract with copied-target and
retry guidance; installer cleanup failures preserve the exact retained-backup
recovery path. The focused installation, CLI, and real-CLI E2E suite passed with
180 tests, including a deterministic post-copy lockfile commit failure that leaves
the copied target in place and emits exact stderr with no success output. Full
repository validation is recorded in the Task 14 handoff.

## Task 15: Resolve Local-Source Lockfile Portability

**Audit finding:** Required 11 — committed lockfile portability conflicts with
absolute local Git source provenance.

**Description:** Decide whether local-source lockfiles are machine-specific,
relocatable, disallowed for committed requirements installs, or represented by a
portable logical source plus local resolution configuration. Align contribution
support with the selected contract.

**Acceptance criteria:**

- [x] The installation and contribution specs state whether local-source lockfiles
  are portable and commit-safe.
- [x] The writer rejects or transforms machine-specific absolute paths according to
  the chosen contract.
- [x] Contribution publishing either resolves the portable source safely or fails
  with actionable guidance for unsupported local entries.

**Verification:**

- [x] Add lockfile writer/reader tests for relative, absolute, missing, and moved
  local repositories.
- [x] Add contribution tests for the supported and unsupported local-source cases.
- [x] Confirm README guidance matches the enforced behavior.

**Dependencies:** Tasks 1 and 4.

**Files likely touched:**

- Installation lockfile DTO and writer
- Contribution lockfile reader or source workspace adapter
- Corresponding tests
- `docs/specs/install-skill-spec.md`
- `docs/specs/upstream-skill-contributions-spec.md`

**Estimated scope:** Medium.

**Status note:** Completed 2026-07-22. Shared `ritebook.lock` files now accept only
portable `git_url` sources. Requirements installs backed by `local_git_repo`
registrations fail during candidate lockfile validation before any copy, while
direct `install-skill` support remains unchanged. Contribution lockfile ingestion
rejects relative, absolute, missing, and moved local repository values without
echoing the path and directs users to register a Git URL and regenerate the
lockfile. Portable local `file://` Git URL integration and E2E workflows cover
requirements installation and contribution publishing. Validation passed Ruff
formatting and linting, `ty`, 63 focused tests, 540 non-E2E tests, all 16 E2E
tests, and the package build. Docker E2E was attempted but could not start because
the local Docker daemon was unavailable.

## Checkpoint C: Persistence and Trust Boundaries

- [x] Registry/cache and installation/state writes have tested commit or recovery
  semantics.
- [ ] No supported source string or Git error leaks credential sentinels.
- [x] CLI output safely handles untrusted control characters.
- [x] Local-source lockfile behavior is explicit and enforced.
- [x] Relevant unit, integration, and failure-path E2E tests pass.

---

## Phase 4: Specification and Tooling Governance

## Task 16: Resolve the `ty` Versus `mypy` Policy Conflict

**Audit finding:** Cross-cutting 13 — project specs and CI use `ty`, while active
project rules require `mypy`.

**Description:** Make one explicit tooling decision. Either update the reusable
ruleset to permit and require `ty` for this project, or migrate dependencies,
configuration, CI, specs, and local quality-gate instructions to `mypy`. Do not
require two type checkers without a documented reason and ownership model.

**Acceptance criteria:**

- [x] `pyproject.toml`, dependency lock, CI, specs, README, and active rules name
  the same required type checker.
- [x] The selected checker covers the intended source set and passes without
  ignored unexplained failures.
- [x] Contributor commands and CI commands are identical except for explicit
  environment setup.

**Verification:**

- [x] Run the selected type-check command from a synchronized `uv` environment.
- [x] Search the repository for stale required commands naming the rejected tool.
- [x] Confirm dependency and lockfile changes are synchronized if applicable.

**Dependencies:** None; complete before final validation.

**Files likely touched:**

- `pyproject.toml`
- `uv.lock`
- `.github/workflows/ci-cd.yaml`
- `.clinerules/011-tooling-and-ci.md` or project-specific override
- Specs and README command references

**Estimated scope:** Medium, mostly configuration/documentation.

**Status note:** Completed 2026-07-22. Ritebook keeps `ty` as its only required
static type checker. A late active project rule explicitly overrides the reusable
profile's `mypy` default and requires `uv run ty check src/ritebook`, matching
`pyproject.toml`, the locked development dependency, pre-commit, CI, README, and
all six specifications. `uv sync --frozen --group dev` and the selected checker
passed across 160 source files. A repository-wide command search found no
project-required `mypy` invocation outside the intentionally superseded reusable
rules and reusable skill templates; no dependency or lockfile change was needed.

## Task 17: Add Lifecycle Metadata to Every Specification

**Audit finding:** Cross-cutting 14 — specifications mix implemented and proposed
behavior without lifecycle metadata.

**Description:** Add a uniform metadata header and lightweight governance section
to every specification. Define allowed statuses and how implementation evidence,
open questions, and supersession are maintained.

**Acceptance criteria:**

- [x] Every spec declares status, owner, spec version, last reviewed date,
  implementation state, dependencies, and associated ADRs.
- [x] Normative requirements are distinguishable from current-state notes and
  future ideas.
- [x] Superseded or deferred behavior has an owner or linked follow-up rather than
  remaining ambiguous prose.

**Verification:**

- [x] Review all six headers side by side for identical field names and semantics.
- [x] Verify every cross-spec and ADR link resolves.
- [x] Confirm dates and implementation states reflect the current tree.

**Dependencies:** Task 1 so the provenance ADR can be linked.

**Files likely touched:**

- All files under `docs/specs/`
- Optional `docs/specs/README.md` for status definitions

**Estimated scope:** Medium, documentation only; apply as a dedicated mechanical
change separate from behavioral rewrites.

**Status note:** Completed 2026-07-22. `docs/specs/README.md` now defines the
shared lifecycle contract, allowed status and implementation-state values,
content classification, and review process. All six specifications use the same
seven metadata fields, identify their dependencies and ADRs, and separate current
implementation evidence from normative requirements and uncommitted future work.
Stale provenance implementation notes were synchronized with the current tree;
the unresolved Docker isolation contract remains explicitly owned by Task 19.
A focused validation helper confirmed all seven fields in all six specs and
resolved 32 relative documentation links; `git diff --check` passed. No code,
configuration, or runtime behavior changed, so Python and Docker suites were not
rerun for this documentation-only task.

## Task 18: Standardize Published-Name and Local-Alias Terminology

**Audit finding:** Cross-cutting 15 — `published_name`, local alias, `<index-name>`,
and `index_name` are used ambiguously.

**Description:** Establish a shared glossary and update public examples, schemas,
DTO descriptions, errors, and help text. Preserve compatibility-sensitive JSON
field names unless a versioned migration is approved.

**Acceptance criteria:**

- [ ] `published_name` always means publisher-owned index metadata.
- [ ] `local_alias` always means the consumer-owned lookup namespace used in skill
  references.
- [ ] Any retained `name` or `index_name` field documents its exact semantic role
  and migration constraints.

**Verification:**

- [ ] Search specs, README, CLI help, DTOs, and errors for ambiguous index-name
  references and classify every remaining use.
- [ ] Run CLI and DTO tests if user-facing terms change.
- [ ] Confirm examples use the same vocabulary across registry, listing,
  installation, lockfile, and contribution workflows.

**Dependencies:** Tasks 1, 4, and 17.

**Files likely touched:**

- All affected files under `docs/specs/`
- `README.md`
- Application DTO docstrings or field names where safe
- CLI help/error text and tests where user-facing terminology changes

**Estimated scope:** Medium; split documentation terminology from versioned API
renaming if public fields must change.

**Status note:** Pending.

## Task 19: Align Docker E2E Isolation Claims and Behavior

**Audit finding:** Cross-cutting 16 — “clean-room” claims exceed the isolation
actually enforced.

**Description:** Decide whether Docker E2E promises only a fresh containerized
dependency environment or a stronger unprivileged, network-independent runtime.
Narrow the spec language or enforce the stronger model with a non-root user,
controlled HOME, and explicit network/permission expectations.

**Acceptance criteria:**

- [ ] The Docker spec defines exactly what state, permissions, and network access
  are isolated.
- [ ] If realistic user permissions are in scope, the image runs tests as an
  unprivileged user with a writable temporary HOME.
- [ ] CI and local commands exercise the same Docker behavior and remain independent
  of private credentials and external services.

**Verification:**

- [ ] Build with `docker build -f Dockerfile.e2e -t ritebook-e2e .`.
- [ ] Run with `docker run --rm ritebook-e2e` and, if required by the contract,
  verify the effective UID, HOME, and network assumptions in a focused test.
- [ ] Review `.dockerignore` for sensitive or developer-state exclusions.

**Dependencies:** None; complete before Task 20.

**Files likely touched:**

- `Dockerfile.e2e`
- `.dockerignore`
- `tests/e2e/conftest.py` or a focused environment assertion
- `.github/workflows/ci-cd.yaml`
- `docs/specs/docker-e2e-integration-testing-spec.md`

**Estimated scope:** Medium.

**Status note:** Pending.

## Checkpoint D: Governance Alignment

- [x] One type checker is consistently required by rules, tooling, docs, and CI.
- [x] Every spec has current lifecycle metadata and valid cross-links.
- [ ] Shared index terminology is unambiguous.
- [ ] Docker E2E claims match observable runtime behavior.

---

## Phase 5: Final Synchronization

## Task 20: Complete Cross-Spec Review and Full Validation

**Audit finding:** Closes the audit as a whole and verifies that individual fixes
did not introduce new contradictions.

**Description:** Perform a fresh review of all specifications against the final
implementation, tests, README, CLI help, schemas, and CI. Run the complete local
and Docker quality gates. Record any intentionally accepted risk with owner and
follow-up rather than leaving an unchecked item implied complete.

**Acceptance criteria:**

- [ ] Every row in the audit coverage matrix is marked closed or accepted through
  an explicit ADR/issue with owner and rationale.
- [ ] Examples, schemas, CLI options, error semantics, paths, and validation
  commands match the current implementation.
- [ ] README, specifications, tests, and generated example files describe one
  coherent publisher-to-contribution workflow.

**Verification:**

- [ ] Run `uv run ruff format --check .`.
- [ ] Run `uv run ruff check .`.
- [ ] Run the type-check command selected in Task 16.
- [ ] Run `uv run pytest -m "not e2e"`.
- [ ] Run `uv build`.
- [ ] Run `docker build -f Dockerfile.e2e -t ritebook-e2e .`.
- [ ] Run `docker run --rm ritebook-e2e`.
- [ ] Review `git --no-pager diff --check` and the final changed-file set.

**Dependencies:** Tasks 1 through 19.

**Files likely touched:**

- `docs/specs/*.md`
- `README.md`
- Any focused tests or docs found stale during final review
- This plan's completion and coverage checkboxes

**Estimated scope:** Medium, review and validation.

**Status note:** Pending.

---

## Audit Coverage Matrix

| Audit finding | Severity | Primary task(s) | Status |
| --- | --- | --- | --- |
| 1. Cached index is not bound to installed source content | Critical | 1–4 | Closed |
| 2. Installation source-target overlap | Critical | 5 | Closed |
| 3. Contribution index symlink escape | Critical | 6 | Closed |
| 4. Publisher output-root/`skills_root` mismatch | Required | 7 | Closed |
| 5. Publisher write is non-atomic and symlink-following | Required | 8 | Closed |
| 6. Registry/cache two-artifact inconsistency | Required | 11 | Closed |
| 7. Git source credential exposure | Required | 12 | Closed |
| 8. Terminal control-character injection | Required | 13 | Closed |
| 9. Destructive forced replacement | Required | 9 | Closed |
| 10. Lexical rather than canonical target collisions | Required | 10 | Closed |
| 11. Local-source lockfile portability conflict | Required | 15 | Closed |
| 12. Post-copy generated-state failure semantics | Required | 14 | Closed |
| 13. `ty` versus `mypy` governance conflict | Cross-cutting | 16 | Closed |
| 14. Missing specification lifecycle metadata | Cross-cutting | 17 | Closed |
| 15. Published-name/local-alias terminology drift | Cross-cutting | 18 | Open |
| 16. Docker “clean-room” claim exceeds enforcement | Cross-cutting | 19 | Open |
| Final cross-spec and implementation consistency | Verification | 20 | Open |

## Sequencing and Parallelization

### Must remain sequential

- Tasks 1 → 2 → 3 → 4 establish the provenance contract and its consumers.
- Tasks 5 → 9 establish overlap safety before replacement mechanics change.
- Tasks 2 → 11 ensure transactional registry work includes the new source identity.
- Tasks 9, 10, and 11 → 14 provide lower-level staging semantics before defining
  the application-level installation commit protocol.
- Tasks 1 and 4 → 15 resolve local-source portability against the final provenance
  and lockfile model.
- All tasks → 20.

### Safe to parallelize after Task 1

- Task 6 contribution index path safety.
- Tasks 7 and 8 publisher root and safe output work, with coordination on writer
  paths.
- Task 12 source sanitization and Task 13 terminal handling after their shared
  display policy is agreed.
- Tasks 16, 17, and 19 when they do not edit the same docs or CI sections.

### Coordination required

- Tasks 5, 9, and 10 all affect filesystem installation behavior.
- Tasks 2 and 11 both affect registry/cache persistence.
- Tasks 4 and 15 both affect lockfile schemas and contribution provenance.
- Tasks 12, 13, and 18 may all affect CLI output and examples.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Provenance decision changes persisted schemas | High | ADR 0001 intentionally updates pre-release schema v1 in place and requires local registry, installation-registry, and lockfile state to be regenerated. |
| “Atomic” filesystem behavior differs by platform | High | Define the supported guarantee precisely, use same-filesystem staging, and test failure recovery rather than claiming universal atomicity. |
| Rollback deletes pre-existing user content | High | Track ownership of staged/backup paths explicitly and test every rollback boundary. |
| Source redaction makes a source unusable for Git operations | High | Keep operational values ephemeral or in an approved credential mechanism; never use display strings as operational input. |
| Canonical path checks race with filesystem changes | Medium | Minimize check/use gaps, reject symlinks, stage under controlled parents, and document local-CLI threat assumptions. |
| Schema and terminology cleanup breaks existing consumers | Medium | Preserve existing fields or provide versioned migration; separate wording cleanup from API changes. |
| Plan tasks grow beyond reviewable scope | Medium | Split tasks before editing when they exceed one session or about five files; update this plan and dependencies. |
| Docker hardening adds slow or platform-fragile tests | Medium | Enforce only explicitly selected isolation properties and keep external services out of default E2E. |

## Open Questions Requiring Decisions

- [x] Which provenance strategy is authoritative: immutable revision, owned source
  snapshot, content hashes, or a documented combination? **Decision:** full Git
  commit object ID plus SHA-256 of the exact validated index bytes; see ADR 0001.
- [x] Must schema-v1 registry and lockfile files be migrated automatically, read in
  compatibility mode, or rejected with guidance? **Decision:** this pre-release
  schema v1 is updated in place; incompatible local state is rejected and
  regenerated without automatic migration.
- [x] Should local Git sources be allowed in committed `ritebook.lock` files?
  **Decision:** No. Shared lockfiles require portable `git_url` sources; local Git
  repository registrations remain supported only for browsing and direct
  `install-skill` workflows.
- [x] What durability guarantee is required for local state: process-level atomic
  replacement, crash consistency, or explicit best-effort recovery? **Decision:**
  synchronize complete same-directory candidate files, atomically replace the
  registry commit pointer, and deterministically recover abandoned adapter-owned
  artifacts on the next mutation; no stronger cross-filesystem or power-loss
  durability guarantee is claimed.
- [x] Reject C0 controls, DEL, and C1 controls in descriptions at publication and
  consumer ingestion; escape controls at CLI display boundaries as defense in
  depth without transforming valid persisted metadata.
- [x] Is `ty` the intentional project override to the reusable `mypy` rule, or
  should the project migrate to `mypy`? **Decision:** `ty` is Ritebook's sole
  required type checker; `.clinerules/014-project-tooling-override.md` explicitly
  supersedes the reusable `mypy` default for this repository.
- [ ] Does Docker E2E need unprivileged-user fidelity, or should “clean-room” be
  narrowed to dependency and developer-state isolation?

## Completion Handoff

Before declaring this plan complete, provide:

- the final audit coverage matrix;
- ADR and schema migration references;
- changed public contracts and compatibility notes;
- focused and full validation evidence;
- intentionally accepted risks with owner and follow-up;
- confirmation that this plan's checkboxes and status notes reflect actual,
  verified work.
