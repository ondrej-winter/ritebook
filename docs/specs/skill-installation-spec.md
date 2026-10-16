# Specification: Skill Installation

## Status

- State: Active
- Revision: 3.4
- Acceptance basis: Existing active lockfile-only sync and transactional direct-install contracts.
- Owner: Ritebook maintainers
- Last reviewed: 2026-10-16
- Implementation state: Implemented
- Dependencies: [Shared Catalog Contract](shared-catalog-contract-spec.md) and [Index Registry](index-registry-spec.md)

## Objective and Context

Ritebook installs one exact skill into an explicit target and synchronizes the
skills declared in `ritebook.toml`. Both workflows use the verified source binding
defined by the [Shared Catalog Contract](shared-catalog-contract-spec.md).

### Design rationale

The installed-tree digest records the last installed baseline. An index describes
candidate content; matching it cannot prove prior ownership or distinguish local
edits from an interrupted update.

Project sync uses only the portable lockfile to avoid duplicate ownership state.
This trades whole-sync rollback and automatic recovery for partial progress and
manual repair. Users serialize mutating installation commands. Direct install
retains its user-level ownership registry and recoverable transaction.

Sync handles current declarations only. Removing a declaration relinquishes
ownership without deleting files; destructive replacement requires explicit
`--force` and still enforces path and source safety.

## Scope

- In scope: exact direct install, declaration-scoped repository sync, referenced
  index refresh, generated lock and ownership state, content identity, default
  local-edit and unmanaged-target preservation, explicit force replacement,
  direct-install locking and recovery, sync partial completion and manual repair,
  retirement of project-local sync state, path and symlink safety, deterministic
  output, CLI behavior, and schema-v1 and schema-v2 migration rejection.
- Out of scope: unregistered live sources, default direct-install destinations,
  dependency resolution between skills, publisher signatures, cross-host shared
  ownership state, automatic deletion of undeclared targets, and force overrides
  for symlinks, special files, dangerous paths, unsafe ancestry, or invalid
  provenance. Automatic whole-sync rollback, next-run journal recovery, sync
  concurrency coordination, changes to direct-install state, and changes to
  index-registry locking are outside the sync contract.

## Requirements

### R1 — Exact direct installation

- `skills install` requires a fully qualified
  `<local-alias>/<skill-path>` reference and explicit `--target`.
- The selector is exactly one schema-v1 catalog path: `<skill>` or
  `<collection>/<skill>`. Direct install never expands collections and never
  falls back to `skills[].name`.
- Ritebook verifies the cached index bytes and the root index bytes at the bound
  `source_revision` against the registered `index_digest` before parsing or using
  skill metadata.
- Cached-index digest verification occurs before JSON decoding or parsing.
- `skill_file` must name the canonical `SKILL.md` file inside the selected skill
  directory.
- Ritebook copies the complete skill directory from the bound commit. It never
  substitutes a mutable working tree or current `HEAD`.
- Before target planning, staging, or mutation, Ritebook validates the selected
  committed `SKILL.md` through the linter's single-file API. Its validated `name`
  and normalized `description` must exactly match the selected index entry.
- A missing target may be installed. Without `--force`, any existing target is
  preserved and direct install exits nonzero.
- With `--force`, an existing normal directory is transactionally replaced even
  when it is unmanaged or differs from its last committed digest. Successful
  replacement establishes fresh ownership and the candidate tree digest.
- `--force` does not authorize replacement of symlinks, regular files, special
  files, dangerous paths, unsafe ancestry, invalid source trees, or targets that
  changed after inspection.

### R2 — Requirements and portable target identity

- `skills sync` reads `ritebook.toml` by default and accepts `--file`.
- `[targets]` maps simple nicknames to non-empty relative target-base paths.
- Every `[[skills]]` entry defines `name` and exactly one of `target` or
  `target_path`.
- Sync target paths must be portable relative paths. They resolve relative to the
  requirements-file directory; absolute, root-like, home, current-directory, and
  escaping paths are invalid.
- Exact selectors resolve one indexed skill. A single-segment selector that is
  not an exact skill may expand one first-level collection to its immediate
  indexed children in deterministic path order.
- Collection selectors require `target`; `target_path` represents one exact
  target only.
- Every resolved target receives a deterministic `target_id` computed from its
  normalized portable target path. The identifier does not contain a
  machine-specific canonical path.
- Duplicate requirements and equal, equivalent, or parent-child targets are
  rejected before refresh or target mutation.

### R3 — Referenced-index refresh and verified resolution

- Before reading installable metadata, sync refreshes every distinct registered
  local alias referenced by the parsed requirements file.
- Refresh uses the index registry's normal source validation, immutable cache,
  and registry commit protocol.
- A missing alias or any refresh failure aborts sync before target mutation and
  before lock or ownership state is changed. Sync never falls back to stale
  cached metadata after a requested refresh fails.
- After refresh, Ritebook opens and verifies the bound source snapshot before it
  parses the verified cached index and resolves skills from that snapshot.
- Every selected exact or collection-expanded skill passes committed-header
  coherence before any target or generated-state mutation begins.
- Direct install remains explicitly offline against the already registered
  binding; users choose `indexes update` when they want a newer direct-install
  source.

### R4 — Canonical installed-tree digest

- Every owned installation records `installed_tree_digest` as
  `sha256:<64-lowercase-hex>`.
- The digest input begins with a versioned Ritebook tree-hash domain marker.
- Ritebook walks the complete skill tree without following symlinks and sorts
  entries by relative POSIX path encoded as UTF-8.
- For each directory the digest includes entry type and path. For each regular
  file it includes entry type, path, executable-bit state, byte length, and exact
  file bytes.
- Timestamps, uid/gid, platform inode numbers, and non-executable permission bits
  are excluded.
- Symlinks, sockets, devices, fifos, and other special files make a source or
  managed target invalid.
- The same algorithm is used for staged candidates, installed targets, ownership
  checks, local-edit detection, and contribution baselines.

### R5 — Lockfile authority and direct-install ownership

- Repository sync reads its installation baseline only from the selected strict
  schema-v3 `ritebook.lock`, including an explicit `--lockfile` override. It
  resolves portable targets relative to the requirements-file directory and
  derives canonical machine paths in memory.
- An index supplies verified candidate content and provenance. It does not
  establish prior installation ownership or authorize replacing existing files,
  even when those files match the current candidate.
- Sync must not read, create, update, or depend on a separate installation ledger,
  journal, or sync operation-lock file, either in `.ritebook/` or elsewhere.
- Valid schema-v3 lock entries with `desired: false` remain readable but never
  establish ownership. A path represented only by such an entry is unmanaged
  when declared again.
- When the lockfile is absent, sync has no prior ownership evidence. It installs
  missing targets and skips existing directories without `--force`. It records
  the skips as issues and exits nonzero; force may establish a new baseline for
  safe replaced directories.
- Without `--force`, automatic replacement of an existing target requires
  matching ownership and a current tree digest equal to the recorded
  `installed_tree_digest`. A mismatch remains a local edit and an unlisted
  existing target remains unmanaged.
- With `--force`, prior ownership is not required. Ritebook uses the current
  inspected tree digest as a race-detection snapshot and records ownership only
  after target replacement and the lockfile write succeed. A skipped modified
  target retains its prior baseline digest and provenance; sync must not adopt
  the modified bytes as a newly installed baseline.
- Direct install stores ownership in
  `~/.config/ritebook/installations.json`, or the explicit
  `--installation-registry-path` override.
- Direct-install ownership entries are sorted by `target_id` and record the
  owning workflow, requirement, target identity, canonical target, installed tree
  digest, and verified source provenance.
- New sync lock state contains only targets selected by the current
  requirements file. Omitted prior entries are dropped from generated state
  without inspecting, modifying, or deleting their directories.
- Direct-install ownership files use schema version 3, strict root and entry
  validation, no unknown fields, atomic same-directory replacement, and POSIX
  mode `0600` where supported.
- Schema-v1 and schema-v2 direct-install registries are not
  current ownership evidence. Ritebook rejects them with instructions to inspect
  and remove or relocate legacy targets before reinstalling.

### R6 — Declaration-scoped sync and explicit force replacement

For each target resolved from the current requirements file, sync classifies the
current state against its lockfile baseline:

- **missing:** install the candidate and establish ownership;
- **owned and unchanged, candidate unchanged:** keep the target without rewriting
  it, unless `--force` requests rematerialization;
- **owned and unchanged, candidate changed:** replace it from the staged candidate;
- **owned but locally modified:** preserve it and record a local-change issue
  without `--force`; replace it with `--force`;
- **unmanaged existing target:** preserve it and record an unmanaged-target issue
  without `--force`; replace it with `--force`;
- **unsafe or unverifiable:** fail closed without replacing the target.

Targets not resolved from the current requirements file are outside the sync
operation. Ritebook does not plan, inspect, modify, delete, or retain ownership
metadata for them. Removing a declaration therefore leaves its directory
untouched and removes its entry from newly generated sync state.

Force replacement is exact: Ritebook stages the verified index candidate,
revalidates the observed current tree digest immediately before mutation,
replaces the selected directory, and records its baseline in the lockfile.
`--force` does not relax source, target, symlink, special-file, path-containment,
or inspection-snapshot checks. Sync does not promise a transaction spanning all
targets and the lockfile. Direct install retains R7's transaction guarantees.

### R7 — Staged writes, sync interruption, and direct-install transactions

#### Shared target protection

- Each replacement is staged beside the target. Immediately before mutation,
  Ritebook revalidates symlink-free ancestry, target type, canonical identity,
  and the tree digest captured during inspection.
- Tree hashing opens every ancestor and descendant directory without following
  symlinks. Replacement uses descriptor-relative mutation against verified parent
  directories. Removing sync transactions does not weaken these path protections.

#### Project sync

- Sync stages and validates complete candidate content before replacing its
  target; it must not copy candidate files into a live target incrementally.
- Sync writes the lockfile by atomic same-directory replacement. A failed write
  before replacement preserves the previous complete file, or leaves it absent
  if no file existed. The lockfile schema and deterministic ordering do not change.
- Sync does not acquire an installation operation lock, implement an alternative
  concurrency coordinator, or promise compare-and-swap protection of lockfile
  writes. Users must run one mutating installation command at a time for the
  affected targets and project. Overlapping invocations are unsupported.
- Index refresh still uses the index registry's independent transaction and
  locking protocol. This does not serialize sync target mutations.
- Sync does not persist a recovery journal, retain batch-wide rollback state, or
  automatically recover earlier invocations. Completed replacements may remain
  after a later target failure, lockfile-write failure, or process interruption.
- A later sync compares current targets with the available lockfile baseline.
  Mismatches are preserved and reported as local changes; existing directories
  without a baseline are preserved and reported as unmanaged. Neither matching
  current index content nor a suspected interrupted run authorizes adoption.
- On handled failure, diagnostics must explain possible partial progress and
  manual repair. After interruption, users inspect affected content and rerun;
  force replacement is an explicit choice after review, not an automatic retry.
- Temporary staging and per-target replacement artifacts may exist beside a
  target. Clean up artifacts belonging to the current invocation when possible;
  report retained paths on handled cleanup failures. Interrupted runs may require
  manual inspection and cleanup. There is no cross-target atomicity guarantee
  or guarantee that a target is continuously present during replacement.

#### Direct install

- Direct install acquires an exclusive operation lock before reading
  ownership state. The lock remains held through refresh, target inspection,
  mutation, generated-state commit, and finalization.
- Lock acquisition is bounded and a conflicting live operation produces a
  user-facing error. Direct install acquires its operation lock before registry
  access and target or generated-state work.
- Backup, rollback, and interrupted-run recovery use descriptor-relative mutation
  against verified parent directories; journal entries retain stable path strings
  only for durable recovery guidance.
- The prior target is moved to an installer-owned same-filesystem backup. The
  backup is retained until all generated-state files for the operation commit.
- Ownership reads compute a SHA-256 digest from the exact bytes they parse.
  Direct install attaches the ownership snapshot digest to its generated
  ownership candidate.
- Immediately before state backup or replacement, the transaction compares each
  supplied snapshot digest with the current file bytes and fails without writing
  generated state when a file changed concurrently.
- A persistent schema-v1 transaction journal records the operation identifier,
  phase, target mutations, backup paths, generated-state paths, prior-state
  backups, and candidate-state digests. Journal and phase changes use atomic
  replacement and file/directory synchronization where supported.
- On an ordinary failure before state commit, Ritebook restores prior targets and
  prior generated state before releasing the lock. If restoration fails, it
  retains the journal and backups and reports exact safe recovery paths.
- At the start of the next operation under the same lock, Ritebook recovers an
  existing journal. If every generated-state file matches its candidate digest,
  it finalizes committed target changes; otherwise it restores prior targets and
  generated state.
- A successful operation removes only its own journal, staging paths, backups,
  and prior-state snapshots.

### R8 — Truthful schema-v3 lock state

`ritebook.lock` is portable, deterministic repository-shared state. In this
example, source and content digests are illustrative; `target_id` is computed
from the shown target path:

```json
{
  "schema_version": 3,
  "requirements_file": "ritebook.toml",
  "state": "complete",
  "skills": [
    {
      "requirement": "platform-skills/code-review",
      "index_name": "platform-skills",
      "skill_name": "code-review",
      "target": ".claude/skills/code-review",
      "target_id": "sha256:f7cbdcdef65a2824eae9956bc4be1fc8d86859db63584e2e203b9efae9381b87",
      "target_ref": "claude",
      "desired": true,
      "status": "materialized",
      "source": "git@github.com:company/internal-skills.git",
      "source_type": "git_url",
      "source_revision": "0123456789abcdef0123456789abcdef01234567",
      "source_branch": "refs/heads/main",
      "index_digest": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      "index_schema_version": 1,
      "skill_path": "skills/code-review",
      "skill_file": "skills/code-review/SKILL.md",
      "installed_tree_digest": "sha256:cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
    }
  ],
  "issues": []
}
```

- `skills` describes only targets selected by the current requirements file that
  Ritebook owns or preserved as locally modified owned targets.
- New sync writes set `desired` to `true`. Valid older schema-v3 entries with
  `desired: false` remain readable for compatibility but do not establish sync
  ownership and are omitted by the next sync unless selected again.
- `status` is `materialized` for an unchanged or successfully installed target,
  or `local_changes` for a declared edited owned target preserved without force.
- `issues` describes current declared targets that could not be materialized.
  Issues use stable codes and terminal-safe detail.
- `state` is `complete` only when every current declared target is materialized
  and no issue remains. Undeclared directories do not make state partial.
- Entries are sorted by `target_id`; issues are sorted by target and code.
- The file contains no timestamps, canonical machine paths, credentials, or local
  repository sources. Re-running a complete no-change sync produces identical
  bytes.
- Schema-v1 and schema-v2 lockfiles are rejected without automatic migration.
  They cannot bootstrap current ownership or provenance. `--force` authorizes
  target replacement but does not migrate invalid generated state.

### R9 — Partial reconciliation and CLI results

- A declared target-specific skip does not erase independent successful target
  mutations.
- After processing current declarations normally, Ritebook writes lock state
  describing current declared owned targets and issues. Sync writes no companion
  ownership file. Handled per-target failures must not be recorded as materialized
  successes.
- Sync exits zero only when every current declaration is materialized. It exits
  nonzero when any declared target was skipped or failed, lockfile persistence or
  cleanup failed, or index refresh failed. A fatal error may leave the previous
  lockfile and already changed targets; output must not claim batch rollback.
- Success output reports installed, updated, and unchanged counts.
- Partial output reports those counts plus one terminal-safe diagnostic per issue.
- A local-change skip explains that `--force` overwrites the selected skill and
  that `skills contribute <qualified-reference>` can prepare an upstream change
  when a valid lockfile baseline exists. The contribution workflow prepares a
  local commit and manual push/review instructions; diagnostics must not promise
  automatic merge-request creation.
- An unmanaged-target skip explains that the directory was preserved and force
  can establish a new baseline. Missing-lockfile guidance must not suggest
  contributing an entry that has no recorded baseline.
- CLI handlers translate command-construction, application, adapter-validation,
  and persistence errors without traceback leakage or terminal-control injection.
- Direct install reports success only after ownership state commits and
  transaction artifacts are finalized.

### R10 — Contribution compatibility

- Contribution lockfile reading supports schema version 3 only.
- Only an exact `skills` entry with a safe Git URL source, verified provenance,
  `installed_tree_digest`, and a materialized or local-changes status is a valid
  contribution baseline.
- Issue-only entries and entries with `desired: false` are not selected by
  fallback. New sync writes do not retain undeclared entries.
- Contribution continues to resolve the exact qualified `requirement`; it never
  falls back to skill name or repository-relative path.

### R11 — Retire project-local sync state

- Sync must not create `.ritebook/` for bookkeeping. The absence of that directory
  must have no effect on sync, contribution, or lockfile validation.
- Existing `.ritebook/` contents are obsolete to new sync, regardless of their
  format. Sync must not consult, migrate, replay, modify, or automatically delete
  them. The selected lockfile remains authoritative even if an old ledger
  disagrees with it or contains malformed data.
- Upgrade guidance must distinguish disposable old ledgers and lock files from
  possible recovery journals and backups. Users with an unfinished old operation
  resolve it with the previous version or inspect and repair it manually before
  removing old artifacts. New sync does not infer recovery instructions from
  those files.
- After confirming that no old operation or recovery remains pending, users may
  remove obsolete generated `.ritebook/` data. Preserve unrelated files; no new
  automatic cleanup command is required.
- Direct-install registries, locks, and journals, and index-registry locking and
  provenance, retain their existing contracts.

## Implementation and Verification Evidence

- `application/use_cases/install_from_requirements.py` in the installation slice
  reads lockfile ownership and uses the dedicated `SyncWriterPort` for staged
  target replacement and atomic lockfile writes.
- `application/use_cases/install_skill.py` uses the direct-install ownership
  registry and recoverable transaction. The composition root wires these
  workflows separately.
- The following source-based checks and installed-wheel scenarios cover current
  behavior. Use `make verify` for a complete execution check; evidence from the
  source tree alone does not establish that the Docker gate has passed.

| Acceptance checks | Current evidence |
| --- | --- |
| AC1 | Direct-install reconciliation/transaction unit tests, `test_installation_process_recovery.py`, and installed-wheel direct-install workflows retain locking, rollback, and recovery coverage. |
| AC2 | Reconciliation refresh ordering/failure tests, index-refresher tests, advancing-source interruption fixtures, and installed-wheel exact/collection selection. |
| AC3 | Canonical tree digest and filesystem-installer tests retain content, path, executable-bit, symlink, and special-file checks. |
| AC4, AC7 | Mixed successful/edited/unmanaged reconciliation, deterministic partial-state rendering, terminal-safe CLI tests, and installed-wheel force and contribution workflows. |
| AC5 | Filesystem sync-writer/staging fault tests and `test_sync_interruption.py` prove individual restoration, retained artifacts, whole lockfile bytes, and conservative stale/absent-lock repair after process termination. |
| AC6 | No-transaction application test, held legacy-lock integration fixture, composition-root assertions, and retained direct-install process-lock test. |
| AC8, AC11, AC12 | `test_sync_workflows.py` and installed-wheel `test_sync_lockfile_is_portable_idempotent_and_authoritative` cover relocation, custom lockfiles, missing-lock partial progress/force, and unchanged legacy artifacts. |
| AC9 | Strict state/contribution reader tests, undesired-entry reconciliation, and invalid-selected-lock integration cases with and without force. |
| AC10 | `make verify` executes quality checks, package builds, and the clean installed-wheel Docker suite. |
| AC13 | Source-CLI preserved-edit contribution and installed-wheel `test_publish_skill_change_creates_isolated_branch_and_commit` prepare a local contribution from preserved lockfile provenance without `.ritebook/`. |

## Constraints and Execution Boundaries

- Domain and application code remain independent of JSON, TOML, Git commands,
  filesystem APIs, process-lock APIs, and CLI rendering.
- Adapters validate all untrusted generated state before returning application
  DTOs.
- Cross-slice refresh uses the index registry's published application port; the
  installation application does not import index-registry adapters.
- Production diagnostics do not reveal Git credentials, raw state payloads, raw
  index bytes, raw skill contents, or terminal controls.
- Target mutation uses same-filesystem atomic rename semantics. Cross-device
  target replacement is unsupported. A directory replacement may use multiple
  renames; it is not a whole-sync atomic operation.
- Direct install may use a platform-specific advisory lock where supported, but
  unsupported locking must fail closed. Sync has no installation lock requirement
  and must not substitute a user-global sync lock or stale-lock protocol.

## Acceptance Checks

| ID | Requirements | Scenario | Expected observable result | Verification method |
| --- | --- | --- | --- | --- |
| AC1 | R1, R4, R5, R7 | Direct install missing and existing targets with and without force; inject state-write failures and terminate a process. | Existing targets remain without force; force records verified replacement; existing direct-install rollback and next-run recovery guarantees hold. | Direct-install application, adapter, process integration, and installed-wheel tests. |
| AC2 | R2, R3 | Sync exact and collection requirements after sources advance, then fail one refresh. | Aliases refresh before resolution; selected content is verified; refresh failure changes no targets or installation state and has no stale fallback. | Application fakes and local-Git integration/E2E tests. |
| AC3 | R4 | Vary tree creation order, timestamps, paths, executable bits, bytes, and entry types. | Equivalent trees hash identically; content-identity changes alter the digest; symlinks and special files fail. | Existing canonical-tree and filesystem adapter tests. |
| AC4 | R5, R6 | Sync missing, unchanged, outdated, modified, and unmanaged declared targets, with and without force; omit prior declarations. | Rules govern each selected target; omitted directories are untouched and omitted from new state; preserved edits retain the old baseline. | Reconciliation unit tests and installed-wheel sync tests. |
| AC5 | R7, R9 | Fail staging, a later target replacement, or lockfile persistence; kill sync after an installed target changes but before lockfile replacement. | No incomplete candidate is copied into a live target; earlier replacements may remain; lockfile bytes remain whole; rerun preserves mismatches or unmanaged targets and permits reviewed force repair without journal recovery. | Filesystem fault injection and a deterministic process-kill sync integration test. |
| AC6 | R7, R11 | Exercise sync with no local state directory and with an old operation-lock file held; inspect its ports and wiring. | Sync acquires no installation operation lock or alternative coordinator and does not use the transaction journal. Concurrent sync correctness is not promised; direct-install locks still work. | Sync orchestration spy/fake tests, held legacy-lock integration fixture, and direct-install process-lock regression test. |
| AC7 | R8, R9 | Combine a successful target, local edits, and an unmanaged directory. | Lock schema v3 records only current owned targets and sorted issues with partial state; success remains; exit is nonzero; edits suggest force or contribution, and unmanaged content suggests force without inventing a contribution baseline. | Application, CLI diagnostic, and installed-wheel tests. |
| AC8 | R8, R11 | Run a complete sync twice, including a relocated checkout and a custom lockfile path. | No-change sync mutates no targets, produces byte-identical portable lock state, and creates no `.ritebook/` bookkeeping directory. | Local filesystem integration and installed-wheel tests. |
| AC9 | R5, R8, R10 | Supply legacy or malformed selected lockfiles, unsafe sources, unknown fields, undesired entries, and issue-only contribution state. | Strict readers retain rejection behavior even with force; undesired entries establish no ownership or contribution baseline. | State-reader, contribution-reader, and application tests. |
| AC10 | R1-R11 | Run the complete implementation handoff gate. | Required formatting, lint, typing, import contracts, tests, package builds, and Docker E2E pass; unavailable checks are explicitly reported as unverified. | `make verify` from the repository root. |
| AC11 | R5, R8, R9 | Delete the selected lockfile while both missing and existing declared skills are present; rerun with and without force. | Missing targets install; existing directories remain and are reported without force; force establishes a new verified baseline; existing old ledgers cannot override this rule. | Reconciliation tests and installed-wheel missing-lockfile workflow. |
| AC12 | R5, R11 | Present conflicting or malformed old `.ritebook/` ledgers, journals, and unrelated sentinel files; read upgrade guidance. | Sync ignores and leaves all old contents unchanged; a valid selected lockfile governs installation; docs distinguish pending old recovery from disposable state and describe manual retirement. | Filesystem integration/E2E tests plus documentation review. |
| AC13 | R9, R10, R11 | Edit a lockfile-backed skill, sync, and prepare a contribution without `.ritebook/`. | Sync preserves edits and prior provenance; contribution uses the unchanged schema-v3 baseline and produces its existing local workflow without automatic push or MR creation. | Installed-wheel sync/contribution workflow. |

## Assumptions

- Installation consumes only registered Git-backed indexes satisfying the shared
  catalog and source-provenance contract.
- The repository remains pre-release, so schema-v1 generated installation state
  may be rejected instead of automatically migrated.
- Users serialize mutating installation commands and accept partial progress and
  manual inspection and repair after interrupted sync. Sync supplies no hidden
  concurrency coordinator or automatic recovery.
- Material unresolved assumptions: None.

## Open Questions

None.
