# Specification: Skill Installation

## Status

- State: Active
- Revision: 3.3
- Acceptance basis: User-approved October 11, 2026 declaration-scoped sync and explicit force-replacement decision in ADR 0007, plus the provenance and catalog decisions in ADRs 0001 and 0005.
- Accepted by / on: User / 2026-10-11
- Owner: Ritebook maintainers
- Last reviewed: 2026-10-11
- Implementation state: Implemented
- Dependencies: [Shared Catalog Contract](shared-catalog-contract-spec.md) and [Index Registry](index-registry-spec.md)
- Associated ADRs: [ADR 0001](../adr/0001-source-provenance-and-trust.md), [ADR 0005](../adr/0005-enforce-a-strict-portable-schema-v1-catalog-boundary.md), and [ADR 0007](../adr/0007-scope-skill-sync-to-declarations-and-make-force-replacement-explicit.md)
- Supersedes: Revision 3.2 of this specification

## Objective and Context

Ritebook installs one exact skill into an explicit target and installs the skills
currently declared by a repository in `ritebook.toml`. Installation consumes
registered Git-backed indexes and preserves the commit-and-index-digest binding
defined by ADR 0001.

Revision 3.0 introduced ownership-aware transactional installation with
deterministic tree digests, referenced-index refresh, exclusive locking,
rollback, interruption recovery, truthful partial state, and schema-v2 generated
state. Revision 3.2 advanced generated installation state to schema v3 so the
canonical source branch is retained with the immutable commit-and-index binding.
Revision 3.3 makes `--force` an explicit authorization to replace an existing
safe target even when it is unmanaged or locally modified, and scopes sync to
current declarations so omitted directories are never pruned.

## Scope

- In scope: exact direct install, declaration-scoped repository sync, referenced
  index refresh, generated lock and ownership state, content identity, default
  local-edit and unmanaged-target preservation, explicit force replacement,
  locking, target/state transactions, interruption recovery, path and symlink
  safety, deterministic output, CLI behavior, and schema-v1 and schema-v2
  migration rejection.
- Out of scope: unregistered live sources, default direct-install destinations,
  dependency resolution between skills, publisher signatures, cross-host shared
  ownership state, automatic deletion of undeclared targets, and force overrides
  for symlinks, special files, dangerous paths, unsafe ancestry, or invalid
  provenance.

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

### R5 — Ownership and local state

- Repository sync stores local ownership at
  `<requirements-file-directory>/.ritebook/installations.json`.
- The repository-local ownership ledger contains canonical target paths and is
  local generated state. Projects must not commit `.ritebook/`.
- When the local ledger is absent, sync may reconstruct ownership for currently
  desired entries from the repository's strict schema-v3 `ritebook.lock`. It
  resolves each portable target under the requirements-file directory and treats
  a matching desired entry as prior ownership evidence.
- Existing valid schema-v3 lock or local-ledger entries with `desired: false`
  remain readable but never establish local ownership. A path represented only
  by such an entry is unmanaged when declared again.
- Without `--force`, automatic replacement of an existing target requires
  matching ownership and a current tree digest equal to the recorded
  `installed_tree_digest`. A mismatch remains a local edit and an unlisted
  existing target remains unmanaged.
- With `--force`, prior ownership is not required. Ritebook uses the current
  inspected tree digest as a race-detection snapshot and records ownership only
  after target mutation and generated-state commit succeed.
- Direct install stores ownership in
  `~/.config/ritebook/installations.json`, or the explicit
  `--installation-registry-path` override.
- Ownership entries are sorted by `target_id` and record the owning workflow,
  requirement, target identity, canonical target, installed tree digest, and
  verified source provenance.
- New sync ownership state contains only targets selected by the current
  requirements file. Omitted prior entries are dropped from generated state
  without inspecting, modifying, or deleting their directories.
- Local ownership files use schema version 3, strict root and entry validation,
  no unknown fields, atomic same-directory replacement, and POSIX mode `0600`
  where supported.
- Schema-v1 and schema-v2 installation registries or ownership files are not
  current ownership evidence. Ritebook rejects them with instructions to inspect
  and remove or relocate legacy targets before reinstalling.

### R6 — Declaration-scoped sync and explicit force replacement

For each target resolved from the current requirements file, sync classifies the
current state under the operation lock:

- **missing:** install the candidate and establish ownership;
- **owned and unchanged, candidate unchanged:** keep the target without rewriting
  it, unless `--force` requests rematerialization;
- **owned and unchanged, candidate changed:** replace it transactionally;
- **owned but locally modified:** preserve it and record a local-change issue
  without `--force`; replace it transactionally with `--force`;
- **unmanaged existing target:** preserve it and record an unmanaged-target issue
  without `--force`; replace it transactionally with `--force`;
- **unsafe or unverifiable:** fail closed without replacing the target.

Targets not resolved from the current requirements file are outside the sync
operation. Ritebook does not plan, inspect, modify, delete, or retain ownership
metadata for them. Removing a declaration therefore leaves its directory
untouched and removes its entry from newly generated sync state.

Force replacement is exact and transactional: Ritebook stages the verified index
candidate, revalidates the observed current tree digest immediately before
mutation, retains the prior directory for rollback, places the candidate, and
commits new ownership and lock state. `--force` does not relax source, target,
symlink, special-file, path-containment, locking, or recovery checks.

### R7 — Transactions, locking, and recovery

- Direct install and sync acquire an exclusive operation lock before reading
  ownership state. The lock remains held through refresh, target inspection,
  mutation, generated-state commit, and finalization.
- Lock acquisition is bounded and a conflicting live operation produces a
  user-facing error. All installation workflows use the same deterministic lock
  order: operation lock, then index-registry refresh operations, then target and
  generated-state work.
- Each replacement is staged beside the target. Immediately before mutation,
  Ritebook revalidates symlink-free ancestry, target type, canonical identity,
  and the tree digest captured during inspection.
- Tree hashing opens every ancestor and descendant directory without following
  symlinks. Target replacement, backup, rollback, and interrupted-run recovery use
  descriptor-relative mutation against verified parent directories; journal
  entries retain stable path strings only for durable recovery guidance.
- The prior target is moved to an installer-owned same-filesystem backup. The
  backup is retained until all generated-state files for the operation commit.
- Ownership and lockfile reads compute a SHA-256 digest from the exact bytes they
  parse. Direct install attaches the ownership snapshot digest to its generated
  ownership candidate. Sync captures both the authoritative ownership snapshot
  and the companion `ritebook.lock` snapshot before processing declarations, then
  attaches the corresponding digests to both generated-state candidates.
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

`ritebook.lock` is portable, deterministic repository-shared state with this
shape:

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
      "target_id": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
  `desired: false` remain readable for compatibility but do not bootstrap local
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
- After processing current declarations, Ritebook commits ownership and lock state
  that exactly describe current declared owned targets and issues.
- Sync exits zero only when every current declaration is materialized. It exits
  nonzero when any declared target was skipped or failed, state commit or recovery
  failed, or index refresh failed.
- Success output reports installed, updated, and unchanged counts.
- Partial output reports those counts plus one terminal-safe diagnostic per issue.
- CLI handlers translate command-construction, application, adapter-validation,
  and persistence errors without traceback leakage or terminal-control injection.
- Direct install reports success only after ownership state commits and transaction
  artifacts are finalized.

### R10 — Contribution compatibility

- Contribution lockfile reading supports schema version 3 only.
- Only an exact `skills` entry with a safe Git URL source, verified provenance,
  `installed_tree_digest`, and a materialized or local-changes status is a valid
  contribution baseline.
- Issue-only entries and entries with `desired: false` are not selected by
  fallback. New sync writes do not retain undeclared entries.
- Contribution continues to resolve the exact qualified `requirement`; it never
  falls back to skill name or repository-relative path.

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
  target replacement is unsupported.
- The implementation may use a platform-specific advisory lock where supported,
  but unsupported locking must fail closed rather than run unlocked.

## Implementation and Verification Evidence

- ADR 0001 defines immutable source provenance.
- ADR 0007 defines declaration-scoped sync, explicit force replacement, and the
  transaction guarantees carried forward from ADR 0004.
- Revision-3.3 implementation evidence includes focused unit and E2E tests for
  force replacement of unmanaged and locally modified targets, default
  preservation without force, undeclared-target non-mutation, generated-state
  relinquishment, legacy undesired-entry migration, tree hashing, strict schema
  parsing, refresh failure, idempotence, concurrent processes, interruption
  recovery, symlink races, and CLI exit behavior.
- Handoff requires the configured formatting, lint, type, import-boundary, full
  non-E2E test, package build, installed-wheel Docker E2E, real concurrent-process,
  and process-kill recovery checks when the environment supports them.

## Acceptance Checks

| ID | Requirements | Scenario | Expected observable result |
| --- | --- | --- | --- |
| AC1 | R1, R4, R5, R7 | Direct install a missing target; retry existing unmanaged, unchanged owned, and locally modified owned targets with and without force. | Missing installs; every existing target is preserved without force; force replaces each safe directory from verified indexed content, records fresh ownership, and commits before success. |
| AC2 | R2, R3 | Sync exact and collection requirements whose registered sources have advanced, then make one refresh fail. | Referenced aliases refresh before resolution; new committed content is selected; any refresh failure causes no target or install-state mutation and no stale fallback. |
| AC3 | R4 | Hash equivalent trees with different creation order and timestamps, then change path, executable bit, bytes, or entry type. | Equivalent trees have one stable digest; every content-identity change changes the digest; symlinks and special files are rejected. |
| AC4 | R5, R6 | Sync missing, unchanged, outdated, locally edited, and unmanaged declared targets with and without force, while prior owned directories are omitted from the file. | Declared targets install, keep, update, preserve, or force-replace according to the rules; omitted directories are not inspected or mutated and disappear from newly generated sync state. |
| AC5 | R7 | Inject failures before mutation, after backup, after target swap, during each state write, during rollback, and after process termination. | Prior state is restored or exact recovery artifacts remain; next-run recovery deterministically finalizes committed state or rolls back uncommitted state. |
| AC6 | R7 | Run two real processes against the same ownership state and change generated state after its snapshot is read. | Only one holds the operation lock; no interleaved target/state transaction occurs; stale snapshot commits fail before generated-state replacement. |
| AC7 | R8, R9 | Cause one target success, one local-edit skip, and one unmanaged-target skip. | Lock schema v3 contains only current declared owned targets and sorted issues, state is `partial`, successful changes persist, and CLI exits nonzero. |
| AC8 | R8 | Run a complete sync twice without source or target changes. | The second run mutates no targets and writes byte-identical lock and ownership state. |
| AC9 | R5, R8, R10 | Present schema-v1 and schema-v2 lock and installation state, malformed schema-v3 documents, unknown fields, unsafe sources, legacy `desired: false` entries, and non-materialized contribution entries. | Invalid readers reject with safe migration or regeneration guidance; valid legacy undesired entries remain readable but cannot bootstrap ownership or contribution selection. |
| AC10 | R1-R10 | Run all repository handoff gates and installed-wheel workflows. | Formatting, linting, typing, import contracts, tests, build, Docker E2E, concurrency, and interruption checks pass or an environmental limitation is reported exactly. |

## Assumptions

- Installation consumes only registered Git-backed indexes satisfying the shared
  catalog contract and ADR 0001.
- The repository remains pre-release, so schema-v1 generated installation state
  may be rejected instead of automatically migrated.
- Material unresolved assumptions: None.

## Open Questions

None.

## Revision and Handoff Notes

- October 6, 2026: Revision 3.0 replaced install-and-rewrite sync with the
  accepted exact-reconciliation contract in ADR 0004.
- October 7, 2026: Marked revision 3.0 implemented after schema-v2 state,
  ownership-aware reconciliation, referenced-index refresh, transactional target
  and state commit, interruption recovery, partial CLI results, contribution
  compatibility, and descriptor-bound symlink-race hardening were verified in the
  tree.
- October 7, 2026: Revision 3.1 added digest-before-parse and selected committed
  header coherence before mutation under ADR 0005.
- October 7, 2026: Marked revision 3.1 implemented after direct and sync
  workflows validated all selected committed headers before target planning,
  staging, mutation, or generated-state commit.
- October 9, 2026: Revision 3.2 propagated exact-byte ownership and lockfile
  snapshot digests into direct-install and sync generated-state candidates so the
  transaction compare-and-swap check rejects stale state before replacement.
- October 11, 2026: Revision 3.3 adopted ADR 0007. Force now replaces an exact
  safe declared or direct target even when unmanaged or locally modified; sync
  processes only current declarations, never prunes omitted directories, and
  writes only current declaration ownership state.
