# Implementation Plan: Simplify Project Sync State

## Outcome and basis

Project `skills sync` uses the selected `ritebook.lock` as its only persistent
installation record and creates no `.ritebook/` bookkeeping. Local edits remain
protected. Users serialize mutating installation commands and accept manual
repair after interrupted syncs.

**Requirements source:** [Skill Installation, revision 3.4](../specs/skill-installation-spec.md),
especially R5-R11, and [ADR 0009](../adr/0009-use-the-lockfile-as-the-only-project-sync-state.md).
Requirements were confirmed by the user on October 16, 2026.

**Readiness:** Ready — implementation is underway; no blocking decisions remain.

**Next action:** T3. The user authorized implementation and local slice commits
without pushing on October 16, 2026.

## Scope and decisions

- Keep schema-v3 lockfiles and the existing TOML and CLI options. Preserve strict
  provenance, collection resolution, referenced-index refresh, target identity,
  canonical tree hashing, no-prune behavior, and path/symlink protections.
- Make sync read ownership from the selected lockfile on every run. An index
  supplies verified candidate content, not evidence of a previous installation.
- Remove sync's local ledger, installation lock, durable journal, batch rollback,
  and automatic next-run recovery. Do not relocate them to global storage.
- Retain staging, immediate target-digest revalidation, same-filesystem target
  replacement, and atomic lockfile replacement. No lockfile compare-and-swap or
  concurrent-sync correctness guarantee is required.
- Preserve direct `skills install` state and its recoverable transaction adapter.
  Preserve index-registry locks and the existing contribution workflow. Add no
  dependencies, schema migration, push, or automatic MR feature.
- Ignore legacy `.ritebook/` data and leave it untouched. Removal is an operator
  action after checking for unfinished old recovery, not an automatic upgrade.
- Preserve the index-recovery work and all unrelated working-tree changes.
  This plan does not modify installed `.agents/skills/` copies.

## Inspected implementation and validation foundations

All paths below exist unless explicitly labeled **proposed**.

- `src/ritebook/features/skill_installation/application/use_cases/install_from_requirements.py`
  prefers a local ledger, falls back to the lockfile, enters a transaction before
  refresh, and commits both ownership and lock candidates.
- `application/ports/installation_state.py`, relative to the same slice, combines
  direct and sync state contracts. `adapters/outbound/json_installation_state/adapter.py`
  already reads strict schema-v3 lock entries, resolves portable targets, and
  renders deterministic lock bytes.
- `application/ports/installation_transaction.py` and
  `adapters/outbound/installation_transaction/adapter.py` implement the shared
  lock/journal/rollback protocol. Both use cases receive the same adapter from
  `src/ritebook/cli.py`; removing it globally would change direct install.
- `adapters/outbound/filesystem_installer/adapter.py`,
  `adapters/outbound/safe_filesystem.py`, and `adapters/outbound/tree_digest.py`
  provide existing staging, descriptor-relative filesystem operations, inspection,
  hashing, and cleanup. Atomic state persistence currently lives in the transaction
  adapter's `_atomic_write_bytes`, not the JSON state renderer.
- `adapters/inbound/cli/commands.py` renders sync issues. Current local-change
  messages preserve files but do not explain the force/contribution choice.
- `tests/integration/test_installation_process_recovery.py` exercises the shared
  transaction adapter directly. Its `.ritebook/` fixture names do not make those
  guarantees sync-only; retain coverage for the direct-install adapter.
- `tests/unit/adapters/inbound/cli/test_adapter.py` owns CLI argument, diagnostic,
  and exit-code tests; `tests/unit/test_cli.py` owns composition-root tests.
  Existing filesystem/contribution CLI workflows are Docker E2E tests. Source-CLI
  integration workflows named below are new coverage, not existing fixtures.
- `Makefile` confirms `make test`, `make architecture`, `make quality`, and
  `make verify`. Run from the repository root with the locked development
  environment installed by `make setup`. Focus a `make test` invocation with
  pytest's `PYTEST_ADDOPTS`, as listed under each task. These are planned checks,
  not results obtained during this documentation change.

## Assumptions and unresolved questions

No unresolved product or architecture decision blocks implementation. Existing
schema-v3 lock entries are sufficient for ownership reconstruction; the strict
reader and current missing-ledger fallback provide the inspected basis.

One bounded implementation choice is recorded here: use a separate sync writer
port and filesystem adapter, rather than a mode flag that disables guarantees
inside the recoverable direct-install transaction. T2 defines and verifies the
boundary. Temporary sibling artifacts and per-target best-effort restoration
are implementation details; they must not become durable recovery state.

## Requirement coverage

| Requirement | Tasks and checks |
| --- | --- |
| R1-R4: retained direct install, resolution, provenance, and digest behavior | T1-V1, T2-AC3, CP-FINAL-2 |
| R5: sole lockfile authority and missing-baseline behavior | T1-AC1, T1-AC2, T1-V1 |
| R6: declaration scope, preservation, and force | T1-AC2, T2-AC1, T3-AC1, CP-FINAL-2 |
| R7: journal-free sync, staged/atomic writes, manual repair, direct isolation | T2-AC1 through T2-AC3, T2-V1, T2-V2, T3-AC2 |
| R8: unchanged strict schema and deterministic partial lock state | T1-AC1 through T1-AC3, T2-AC2, T3-AC2 |
| R9: truthful results and actionable diagnostics | T2-AC2, T3-AC1, T3-AC2 |
| R10: contribution compatibility | T1-AC3, T3-AC1, T3-V2 |
| R11: no project state directory and legacy retirement | T2-AC1, T3-AC3, T3-V1, T3-V2 |

## Execution summary

- **Execution order:** T1 → T2 → T3 → final handoff checkpoint.
- **Parallel groups:** None. Tasks share orchestration, adapters, and fixtures;
  sequential delivery keeps the direct-install boundary reviewable.
- T1 is an intermediate implementation slice: it removes ledger authority while
  retaining the old execution adapter until T2. It does not establish conformance
  to all of revision 3.4 on its own. That adapter can still replay a legacy journal
  before baseline reading; do not release T1 as journal-free sync or claim legacy
  artifacts remain untouched until T2 passes.

## Task details

### T1: Use the selected lockfile for every sync baseline

- [x] **T1** — Make lockfile authority and missing-lock behavior executable.

**Outcome and basis:** Implement R5 and R8 without changing direct-install
ownership. This is a complete reconciliation behavior change; the remaining
transaction removal follows in T2.

**Dependencies and entry conditions:** None beyond the accepted spec and a fresh
working-tree inspection. Preserve existing staged work.

**Files or components:**

- `src/ritebook/features/skill_installation/application/use_cases/install_from_requirements.py`
- `src/ritebook/features/skill_installation/application/ports/installation_state.py`
- `src/ritebook/features/skill_installation/adapters/outbound/json_installation_state/adapter.py`
- `tests/unit/features/skill_installation/application/{fakes.py,test_reconciliation.py}`
- `tests/unit/features/skill_installation/adapters/outbound/test_json_installation_state.py`
- Affected ledger assertions in `tests/e2e/test_cli_workflows.py`.

**Estimated scope:** M — the existing lock reader supplies the conversion;
application calls and focused test expectations change together.

**Acceptance criteria:**

- [x] **T1-AC1** — Every sync reads the selected schema-v3 lockfile, including a
  custom path, and renders only a lockfile candidate. Reconciliation makes no
  ledger existence, ownership-read, or ownership-render calls; conflicting or
  malformed ledgers supply no baseline authority. Shared direct-install ownership
  methods remain available. Legacy transaction replay is removed in T2.
- [x] **T1-AC2** — With no lockfile, missing targets install while existing
  directories are skipped without force, even if they match index content. Force
  replaces only safe selected targets and establishes a verified baseline.
  Existing local edits retain their prior digest/provenance when skipped;
  undeclared directories remain outside reconciliation.
- [x] **T1-AC3** — Schema v3, strict invalid/legacy lock rejection even under
  force, ignored `desired: false` ownership, partial issues, portable path
  resolution after checkout relocation, and deterministic no-change bytes remain
  valid. No companion ledger write is needed for contribution compatibility.

**Verification:**

- [x] **T1-V1** — Add regression cases before changing orchestration. Run
  `PYTEST_ADDOPTS='tests/unit/features/skill_installation tests/unit/features/skill_contribution' make test`.
  Expect all focused cases to pass, including direct-install tests; assertions
  must distinguish lockfile authority from the current ledger-first behavior.
  The directories are confirmed existing test roots.

**Evidence and status:** Complete. Regression tests first failed on ledger
authority and duplicate state candidates. Focused installation/contribution tests
passed (275 cases); `make quality` then passed all checks and 761 default tests,
including the expanded regressions. Commands used
`UV_CACHE_DIR=/private/tmp/ritebook-uv-cache` because the sandbox blocks the default
cache. E2E ledger assertions now require no ledger. The intermediate transaction
adapter still creates lock/journal artifacts; T2 removes that dependency.

### T2: Execute staged sync writes without a recovery transaction

- [x] **T2** — Separate sync filesystem writes from direct-install transactions.

**Outcome and basis:** Implement R6/R7 and the no-bookkeeping portion of R11.
Complete staged writes retain path protection while accepting partial progress.

**Dependencies and entry conditions:** T1's lockfile-only state candidate and
baseline rules are in place. Do not remove the direct-install transaction adapter.

**Files or components:**

- **Proposed:** `src/ritebook/features/skill_installation/application/ports/sync_writer.py`
  and `adapters/outbound/filesystem_sync_writer/{__init__.py,adapter.py}` under
  the same slice, with exports in their existing package initializers.
- Existing `application/dtos/install_skill.py`, `application/ports/installation_state.py`,
  `application/use_cases/install_from_requirements.py`, and
  `adapters/outbound/json_installation_state/adapter.py` under that slice.
- Existing filesystem installer, safe-filesystem helpers, and tree digest;
  `src/ritebook/cli.py` composition wiring and `tests/unit/test_cli.py`.
- Existing reconciliation fakes/tests and filesystem/state adapter tests;
  **proposed:** `tests/unit/features/skill_installation/adapters/outbound/test_filesystem_sync_writer.py`.
- `tests/integration/test_adapter_integrations.py` and existing E2E sync assertions
  that currently require `.ritebook/` or whole-sync rollback.

**Estimated scope:** L, retained as one slice because the new port, filesystem
adapter, application caller, composition wiring, and regression tests must agree
before sync can use the new execution contract. Keep the adapter cohesive and
leave direct-install transaction internals unchanged wherever practical.

**Implementation approach:**

- Publish a sync writer port with staged-tree replacement and atomic lockfile
  writing operations using application types and primitives. It has no
  context-manager, locking, journaling, commit-all, or replay API.
- Give sync its own lockfile path DTO/contract without ownership, journal, or
  installation-lock paths; keep `InstallationOperationPaths` for direct install.
- Reuse existing staging, hashing, and descriptor-relative helpers. For a
  replacement, a uniquely named sibling may temporarily hold the prior tree.
  Remove it after successful placement rather than retaining it until batch
  commit. On a handled placement failure, attempt local restoration; if that
  fails, preserve and report the remaining path. Do not undo other completed
  targets or add a persistent manifest.
- Use a same-directory temporary file and atomic replacement for the lockfile,
  following `_atomic_write_bytes` in the existing transaction adapter. Reuse the
  pattern without importing that adapter's private helper into the new adapter;
  keep any extracted filesystem primitive adapter-owned. Translate raw I/O errors
  to application errors. Keep direct-install snapshot comparison intact; sync
  does not require it.
- Attempt cleanup for every artifact owned by this invocation even if one cleanup
  fails. Retain the primary failure and report remaining paths safely, including
  a staging failure before `stage()` returns and a lockfile temporary-file cleanup
  failure. Cleanup after successful placement must not trigger restoration of
  the previous tree or success output when cleanup failed.
- Pass the new writer only to `InstallFromRequirements` at the composition root.
  Remove sync-only ledger/path APIs and unused fakes after checking callers.

**Acceptance criteria:**

- [x] **T2-AC1** — Fresh, unchanged, force, partial, and failed syncs create no
  `.ritebook/` bookkeeping, acquire no sync installation lock, and write no
  journal anywhere. Complete staging precedes target mutation; target-digest,
  ancestry, containment, symlink, and special-file checks remain effective.
- [x] **T2-AC2** — Staging failure leaves its target unchanged. A later replacement
  or lockfile-write failure does not roll back earlier completed targets. A
  failed pre-replacement lockfile write preserves the previous whole document
  or leaves the path absent. Partial state never labels a failed target as
  materialized. Handled cleanup failures report retained artifacts and return
  nonzero, including after lockfile replacement; a complete new lockfile may
  already exist in that case. Earlier failures remain visible if cleanup also
  fails, and cleanup attempts continue for other current-invocation artifacts.
- [x] **T2-AC3** — Direct install still uses its existing registry, operation lock,
  journal, rollback, and next-run recovery. Index refresh still uses the published
  registry port and registry locks. An old held sync lock does not block sync.

**Verification:**

- [x] **T2-V1** — Write fault-injection adapter and orchestration tests, then run
  `PYTEST_ADDOPTS='tests/unit/features/skill_installation tests/unit/test_cli.py tests/integration/test_adapter_integrations.py tests/integration/test_installation_process_recovery.py' make test`.
  Expect staged/atomic writes, partial progress, no transaction calls from sync,
  and existing direct transaction/process tests to pass. Add a held legacy-lock
  fixture without claiming support for two simultaneously mutating syncs.
  Inject failures before and after directory placement, during local restoration,
  before and after lockfile replacement, and during staging/backup/temp cleanup.
  Inspect bytes and retained paths rather than only checking raised exceptions.
- [x] **T2-V2** — Run `make architecture`; expect all import contracts to pass.
  Inspect the composition root and published ports: direct install retains the
  recoverable transaction and sync receives only its writer and state contracts.

**Evidence and status:** Complete. Sync receives `SyncWriterPort` and `SyncPaths`;
direct install retains its recoverable transaction. The no-transaction and
staging-cleanup regressions failed before their fixes. Fault tests cover current
target restoration, failed restoration, backup cleanup, atomic lockfile failure,
post-placement failures, and continued staging cleanup with a primary failure.
A real held legacy lock and malformed ledger/journal remain untouched. The
focused T2 command passed 159 cases before contract cleanup; the final
`make quality` passed all checks, including architecture and 775 default tests.
Commands used the writable temporary uv cache recorded under T1. Installed-wheel
execution remains required at CP-FINAL-2.

### T3: Prove manual repair, explain skips, and retire legacy guidance

- [ ] **T3** — Finish sync diagnostics, migration guidance, and operator workflows.

**Outcome and basis:** Complete R7/R9-R11 and AC5/AC7/AC11-AC13. This slice makes
the accepted failure model observable through the real command.

**Dependencies and entry conditions:** T2's journal-free execution and atomic
lockfile writer are wired into sync. T1's preserved baseline is available for
contribution guidance.

**Files or components:**

- `src/ritebook/features/skill_installation/application/use_cases/install_from_requirements.py`
  and `adapters/inbound/cli/commands.py` under that slice; existing layer-owned
  errors/DTOs where diagnostics need them.
- Existing reconciliation tests, `tests/e2e/test_cli_workflows.py`,
  `tests/e2e/test_skill_contribution_workflow.py`, and direct-install regression
  tests. Keep the shared recovery integration helper/tests scoped to direct install.
- `tests/unit/adapters/inbound/cli/test_adapter.py` for command guidance,
  terminal-control escaping, fatal partial-progress errors, and exit codes.
- **Proposed:** `tests/integration/test_sync_interruption.py` and an explicit
  subprocess helper beside it. Use local Git/filesystem fixtures and a bounded
  readiness-marker handshake before process termination; no timing-only sleeps.
- **Proposed:** `tests/integration/test_sync_workflows.py` for source-CLI relocation,
  custom lockfile, legacy-artifact preservation, and sync/contribution workflows.
  Use isolated HOME/config/cache paths and local Git fixtures; do not import the
  wheel-only `run_cli` fixture from `tests/e2e/conftest.py`.
- `README.md`, `docs/specs/skill-installation-spec.md`, `docs/specs/README.md`,
  and the implementation-status note in ADR 0009. Preserve historical ADR text.

**Estimated scope:** M — diagnostics and documentation share the existing skip
results; the process fixture verifies the already implemented failure boundary.

**Acceptance criteria:**

- [ ] **T3-AC1** — Modified owned skills are preserved with their old baseline.
  Diagnostics explain destructive `--force` and exact `skills contribute`
  guidance. Unmanaged or missing-lock skips explain force without inventing a
  contribution baseline. No diagnostic promises automatic push or MR creation.
  Guidance includes the selected custom `--lockfile` where needed. Explain that
  sync `--force` applies to all current declarations, so users review every
  selected target before a force rerun.
- [ ] **T3-AC2** — Terminate sync after a completed replacement and before lockfile
  writing. The next normal run preserves mismatched or unmanaged content,
  reports the uncertainty, and neither rolls back nor silently adopts it. A
  reviewed force rerun repairs the installation and creates a valid lockfile.
  Cover both stale-lock and absent-lock baselines. Fatal handled errors report
  possible partial progress; success is never reported for a failed lock write.
  The stale-lock fixture must replace a previously recorded tree with a different
  verified digest; otherwise it cannot prove mismatch preservation. Kill a child
  executing the composed sync use case through the real writer, with a test-only
  pause before lockfile writing. Reruns exercise the normal CLI. Bound waits and
  reap the child in fixture cleanup; add no production pause switch.
- [ ] **T3-AC3** — Sync workflows create no `.ritebook/` and work after checkout
  relocation and with custom lockfile paths. Conflicting/malformed old
  ledgers, journals, and unrelated sentinels are ignored and remain byte-identical.
  A preserved local edit remains contributable using only schema-v3 lock state.
- [ ] **T3-AC4** — Replace the README's current transaction description and pending
  note with implemented behavior, one-command-at-a-time responsibility,
  interruption/force guidance, and manual retirement instructions. Resolve old
  pending recovery with the previous version or manual inspection before deleting
  generated artifacts; do not recommend blanket directory deletion. Keep spec
  implementation metadata partial until CP-FINAL-3 records the final evidence.

**Verification:**

- [ ] **T3-V1** — Run
  `PYTEST_ADDOPTS='tests/unit/features/skill_installation tests/unit/features/skill_contribution tests/unit/adapters/inbound/cli/test_adapter.py tests/unit/test_cli.py tests/integration' make test`.
  Expect exact diagnostics, deterministic interrupted-sync repair, untouched old
  artifacts, source-CLI filesystem/contribution workflows for T3-AC3, and retained
  direct-install/registry recovery coverage to pass.
- [ ] **T3-V2** — Review installed-wheel assertions for AC4-AC13; their execution
  gates overall completion at CP-FINAL-2. Review README/spec links and guidance
  against the actual CLI, especially contribution's local-only behavior and
  legacy cleanup.

**Evidence and status:** Pending. Do not delete the developer's actual `.ritebook/`
folder or modify a real user registry to demonstrate migration; use fixtures.

### Final handoff checkpoint

**Prerequisites:** T1-T3 and their focused checks/reviews are complete. The shared
installed-wheel execution gate follows at CP-FINAL-2.

- [ ] **CP-FINAL-1** — Inspect the complete diff and requirement mapping. Each
  installation AC1-AC13 has focused evidence or a named installed-wheel assertion
  awaiting CP-FINAL-2. Direct-install and registry guarantees remain owned, and no
  hidden sync ledger, lock, journal, or recovery protocol replaces `.ritebook/`.
  Preserve unrelated changes.
- [ ] **CP-FINAL-2** — Run `make verify` from the repository root. Require format,
  Ruff, ty, import contracts, default non-E2E tests, package builds, and the clean
  installed-wheel Docker E2E suite to pass. Docker must be available; any missing
  or failed check remains unverified and blocks claiming full completion.
- [ ] **CP-FINAL-3** — Apply `condensed-prose-refactor` to changed prose, run
  `git diff --check`, check local Markdown links, and inspect final status. Record
  actual validation evidence in the spec and this plan, then update implementation
  metadata and remove the documentation-only execution boundary before marking
  work done.

**Evidence and status:** Pending. These are implementation checks; passing tests
from the earlier index-recovery work do not prove this contract.

## Risks and fallback

- **Stale lock after failure:** T2/T3 preserve completed target changes without
  claiming they are recorded. Rerun normally to identify mismatches, inspect
  files/artifacts, then force only selected content the user accepts replacing.
  Do not regenerate ownership by comparing to the newest index.
- **Interrupted directory swap:** A target may be absent while old content remains
  in a sibling artifact. Document manual inspection; never delete an uncertain
  sibling during later syncs or replay it as a transaction.
- **Pending legacy recovery:** New sync ignores old journals. Before upgrading,
  finish recovery using the previous version or manually reconcile files and
  state. Keep uncertain backups until inspected.
- **Shared adapter regression:** T2 preserves direct-install transaction wiring
  and existing process-level coverage. Avoid broad deletion of recovery helpers
  or tests just because their fixture names contain `.ritebook/`.
- **Concurrent writers:** Unsupported by explicit user choice. Do not add global
  locks, lockfile compare-and-swap promises, or new hidden state to mitigate it.
- **Code rollback:** Restoring the old implementation does not undo target changes
  or restore deleted local metadata. The old implementation prefers a surviving
  ledger and may replay a legacy journal. Reconcile those artifacts before using
  it; only when the ledger is absent does it use schema-v3 lockfile ownership.
  Inspect mismatches before any force operation.

## Status and scope changes

- October 16, 2026: Plan prepared from the confirmed interview, current source,
  adapter tests, installed-wheel workflows, and Makefile. No implementation tasks
  or runtime verification have been performed for this change.
- Preparation review: `review-implementation-plan` checked scope, requirement
  coverage, shared-adapter isolation, dependencies, and validation. Task reviews
  finish before the final installed-wheel gate; no task depends on that gate for
  its own completion.
- Preparation validation (recorded before this review): 9 documents and 55 local
  links checked; R1-R11 and
  AC1-AC13 are present in order; all 21 plan checkbox IDs are unique and pending.
  Both staged and unstaged `git diff --check` passed. No runtime tests were run
  for this documentation-only change.
- October 16, 2026 review: Added CLI test ownership and focused checks, proposed
  source-CLI integration coverage, explicit cleanup/fault assertions, a differing
  digest for the interruption fixture, and T1/rollback legacy-recovery limits.
  Product decisions, task IDs, and pending progress are unchanged. This is a plan
  review; implementation and runtime validation remain pending.
- Review validation: All 21 pending checkbox IDs match the original plan, exactly
  one readiness label remains, and both local Markdown links resolve. Final prose
  reviewed with `condensed-prose-refactor`; `git diff --check` passes. No runtime
  tests or `make verify` were run because this review changes only the plan.
