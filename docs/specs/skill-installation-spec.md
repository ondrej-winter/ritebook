# Specification: Skill Installation

## Status

- State: Active
- Revision: 3.2
- Acceptance basis: User-approved October 6, 2026 exact-reconciliation plan, the October 7, 2026 committed-header coherence decision in ADR 0005, and the October 9, 2026 canonical-branch provenance decision in ADR 0001.
- Accepted by / on: User / 2026-10-09
- Owner: Ritebook maintainers
- Last reviewed: 2026-10-09
- Implementation state: Implemented
- Dependencies: [Shared Catalog Contract](shared-catalog-contract-spec.md) and [Index Registry](index-registry-spec.md)
- Associated ADRs: [ADR 0001](../adr/0001-source-provenance-and-trust.md), [ADR 0004](../adr/0004-reconcile-installed-skills-with-owned-transactional-state.md), and [ADR 0005](../adr/0005-enforce-a-strict-portable-schema-v1-catalog-boundary.md)
- Supersedes: Revision 2.1 of this specification

## Objective and Context

Ritebook installs one exact skill into an explicit target and reconciles a
repository's installed skills with declarations in `ritebook.toml`. Installation
consumes registered Git-backed indexes and preserves the commit-and-index-digest
binding defined by ADR 0001.

Revision 2.1 implemented sync as sequential copy followed by a full lockfile
rewrite. It did not record ownership or installed bytes, could not prune safely,
could overwrite unmanaged directories with `--force`, deleted backups before
generated state committed, and allowed concurrent lost updates. Revision 3.0
defines exact, ownership-aware reconciliation with deterministic tree digests,
referenced-index refresh, exclusive locking, rollback, interruption recovery,
truthful partial state, and schema-v2 generated state. Revision 3.2 advances
generated installation state to schema v3 so the canonical source branch is
retained with the immutable commit-and-index binding.

## Scope

- In scope: exact direct install, exact repository reconciliation, referenced
  index refresh, generated lock and ownership state, content identity, local-edit
  preservation, safe pruning, locking, target/state transactions, interruption
  recovery, path and symlink safety, deterministic output, CLI behavior, and
  schema-v1 and schema-v2 migration rejection.
- Out of scope: unregistered live sources, default direct-install destinations,
  dependency resolution between skills, publisher signatures, cross-host shared
  ownership state, automatic adoption of legacy targets, and overriding local
  edits or unmanaged content.

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
- A missing target may be installed. An existing target may be replaced only when
  the user passed `--force`, the target is already owned by the same direct-install
  registry, and its current tree digest matches its last committed digest.
- `--force` does not authorize replacement of unmanaged targets, locally modified
  targets, symlinks, special files, dangerous paths, or targets whose ownership
  cannot be verified.

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

- Ritebook may replace or prune only a target recorded in schema-v3 ownership
  state for the same canonical target and `target_id`.
- Repository sync stores local ownership at
  `<requirements-file-directory>/.ritebook/installations.json`.
- The repository-local ownership ledger contains canonical target paths and is
  local generated state. Projects must not commit `.ritebook/`.
- When the local ledger is absent, sync may reconstruct it from the repository's
  strict schema-v3 `ritebook.lock`. It resolves each portable target under the
  requirements-file directory and treats the lock entry as ownership evidence
  only when its path is safe and its current tree matches the recorded
  `installed_tree_digest` before replacement or pruning.
- A lock mismatch does not adopt the target. The target is preserved as local
  changes, and unlisted existing targets remain unmanaged.
- Direct install stores ownership in
  `~/.config/ritebook/installations.json`, or the explicit
  `--installation-registry-path` override.
- Ownership entries are sorted by `target_id` and record the owning workflow,
  requirement, target identity, canonical target, installed tree digest, and
  verified source provenance.
- Local ownership files use schema version 3, strict root and entry validation,
  no unknown fields, atomic same-directory replacement, and POSIX mode `0600`
  where supported.
- Schema-v1 and schema-v2 installation registries or ownership files are not
  current ownership evidence. Ritebook rejects them with instructions to inspect
  and remove or relocate legacy targets before reinstalling.

### R6 — Exact reconciliation and safe pruning

For each desired resolved target, sync classifies current state under the
operation lock:

- **missing:** install the candidate and establish ownership;
- **owned and unchanged, candidate unchanged:** keep the target without rewriting
  it;
- **owned and unchanged, candidate changed:** replace it transactionally;
- **owned but locally modified:** preserve it and record a local-change issue;
- **unmanaged existing target:** preserve it and record an unmanaged-target issue;
- **unsafe or unverifiable:** preserve it and record a safety issue.

For each previously owned target no longer desired:

- unchanged targets are pruned transactionally;
- locally modified, unsafe, missing-with-inconsistent-state, or unverifiable
  targets are retained and recorded as issues;
- Ritebook never prunes a path based only on its location or name.

`--force` may request rematerialization of an unchanged owned desired target. It
does not change ownership, local-edit, pruning, or safety rules.

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
  ownership, and expected tree digest.
- Tree hashing opens every ancestor and descendant directory without following
  symlinks. Target replacement, backup, pruning, rollback, and interrupted-run
  recovery use descriptor-relative mutation against verified parent directories;
  journal entries retain stable path strings only for durable recovery guidance.
- The prior target is moved to an installer-owned same-filesystem backup. The
  backup is retained until all generated-state files for the operation commit.
- Ownership and lockfile reads compute a SHA-256 digest from the exact bytes they
  parse. Direct install attaches the ownership snapshot digest to its generated
  ownership candidate. Sync captures both the authoritative ownership snapshot
  and the companion `ritebook.lock` snapshot before reconciliation, then attaches
  the corresponding digests to both generated-state candidates.
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

- `skills` describes actual retained Ritebook-owned materialized targets, not only
  the latest desired candidates.
- `desired` distinguishes current requirements from retained no-longer-desired
  targets that could not be pruned safely.
- `status` is `materialized` for an unchanged or successfully installed target,
  `local_changes` for an edited retained target, or `retained` for another
  retained owned target.
- `issues` describes desired targets that could not be materialized and retained
  targets requiring user action. Issues use stable codes and terminal-safe detail.
- `state` is `complete` only when every desired target is materialized and every
  no-longer-desired owned target is pruned. Otherwise it is `partial`.
- Entries are sorted by `target_id`; issues are sorted by target and code.
- The file contains no timestamps, canonical machine paths, credentials, or local
  repository sources. Re-running a complete no-change sync produces identical
  bytes.
- Schema-v1 and schema-v2 lockfiles are rejected without automatic migration.
  They do not authorize target replacement or pruning because they lack all
  current ownership and canonical-branch provenance.

### R9 — Partial reconciliation and CLI results

- A target-specific install, update, or prune failure does not erase independent
  successful target mutations.
- After target processing, Ritebook commits ownership and lock state that exactly
  describe the resulting owned targets and issues.
- Sync exits zero only for complete reconciliation. It exits nonzero when any
  desired target was skipped or failed, any obsolete owned target was retained,
  state commit or recovery failed, or index refresh failed.
- Success output reports installed, updated, unchanged, and pruned counts.
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
- Issue-only entries and retained no-longer-desired entries are not selected by
  fallback.
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
- ADR 0004 defines ownership, reconciliation, locking, transaction, recovery, and
  schema-transition decisions.
- Revision-3 implementation evidence must include focused unit and integration
  tests for tree hashing, strict schema parsing, refresh failure, ownership,
  unmanaged targets, local edits, pruning, partial state, idempotence, concurrent
  processes, interruption recovery, symlink races, and CLI exit behavior.
- Handoff requires the configured formatting, lint, type, import-boundary, full
  non-E2E test, package build, installed-wheel Docker E2E, real concurrent-process,
  and process-kill recovery checks when the environment supports them.

## Acceptance Checks

| ID | Requirements | Scenario | Expected observable result |
| --- | --- | --- | --- |
| AC1 | R1, R4, R5, R7 | Direct install a missing target, reinstall unchanged owned content, modify it locally, and attempt unmanaged replacement. | Missing target installs with schema-v3 ownership; owned unchanged replacement is safe; local edits and unmanaged targets are preserved; success follows state commit. |
| AC2 | R2, R3 | Sync exact and collection requirements whose registered sources have advanced, then make one refresh fail. | Referenced aliases refresh before resolution; new committed content is selected; any refresh failure causes no target or install-state mutation and no stale fallback. |
| AC3 | R4 | Hash equivalent trees with different creation order and timestamps, then change path, executable bit, bytes, or entry type. | Equivalent trees have one stable digest; every content-identity change changes the digest; symlinks and special files are rejected. |
| AC4 | R5, R6 | Reconcile missing, unchanged, outdated, locally edited, unmanaged, and obsolete targets. | Ritebook installs, keeps, updates, preserves, skips, or prunes exactly according to ownership and digest rules. |
| AC5 | R7 | Inject failures before mutation, after backup, after target swap, during each state write, during rollback, and after process termination. | Prior state is restored or exact recovery artifacts remain; next-run recovery deterministically finalizes committed state or rolls back uncommitted state. |
| AC6 | R7 | Run two real processes against the same ownership state and change generated state after its snapshot is read. | Only one holds the operation lock; no interleaved target/state transaction occurs; stale snapshot commits fail before generated-state replacement. |
| AC7 | R8, R9 | Cause one target success, one local-edit skip, one unmanaged-target skip, and one prune success. | Lock schema v3 truthfully represents retained owned targets and sorted issues, state is `partial`, successful changes persist, and CLI exits nonzero. |
| AC8 | R8 | Run a complete sync twice without source or target changes. | The second run mutates no targets and writes byte-identical lock and ownership state. |
| AC9 | R5, R8, R10 | Present schema-v1 and schema-v2 lock and installation state, malformed schema-v3 documents, unknown fields, unsafe sources, and non-materialized contribution entries. | Readers reject them with safe migration or regeneration guidance and never infer ownership or provenance. |
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
