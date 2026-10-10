# 0004. Reconcile Installed Skills with Owned Transactional State

Date: 2026-10-06
Status: Accepted

## Context

Ritebook's original `skills sync` workflow planned a set of copies, installed
them sequentially, and rewrote `ritebook.lock` after all copies succeeded. That
model could install declared skills but could not safely reconcile an existing
installation tree:

- it did not distinguish Ritebook-owned targets from unmanaged directories;
- it did not record the installed tree bytes, so it could not distinguish an
  unchanged target from local edits;
- it could not safely prune requirements removed from `ritebook.toml`;
- it deleted replacement backups before generated state committed;
- concurrent processes could validate the same old state and overwrite one
  another's updates;
- an interruption could leave target directories and generated state describing
  different realities; and
- sync consumed stale registered indexes unless the user separately remembered
  to refresh them.

`ritebook.lock` is repository-shared provenance state. Machine-specific canonical
paths, lock ownership, recovery journals, and transaction artifacts must not be
stored in that portable file. Direct `skills install` has the same target and
state consistency risks even though its generated registry is user-local.

Ritebook is still pre-release, so a direct schema transition is preferable to a
long-lived compatibility shim. Safety takes priority over automatically claiming
legacy targets whose installed bytes were never recorded.

## Decision

Ritebook will reconcile installed skills under explicit ownership using a
deterministic tree digest, an exclusive operation lock, retained replacement
backups, and a persistent recovery journal. Repository sync will refresh every
referenced registered index before reading installable metadata and will not fall
back to stale cached state when refresh fails.

### Ownership and content identity

- Every managed target has exactly one Ritebook owner and one last committed
  installed-tree digest.
- The digest is SHA-256 over a canonical, sorted representation of every regular
  file and directory below the target. It includes relative POSIX paths, entry
  type, file executable bits, file size, and exact file bytes; it excludes
  timestamps, uid/gid, and other machine-specific metadata.
- Symlinks and special files are never valid managed skill-tree entries.
- Repo-local sync stores portable provenance and reconciliation status in
  `ritebook.lock` schema v3 and stores canonical machine paths and ownership in a
  local schema-v3 ownership ledger. Schema v3 adds the canonical source branch
  required by ADR 0001.
- On a fresh checkout where the local ledger is absent, a strict schema-v3
  `ritebook.lock` may bootstrap local ownership only for safe repository-relative
  targets. Replacement or pruning still requires the current target tree digest
  to match the lock entry's committed `installed_tree_digest`; a mismatch remains
  a local edit and arbitrary unlisted directories remain unmanaged.
- Direct installs store the same ownership and tree-digest facts in the user-level
  installation registry.
- Ritebook never claims an existing unmanaged directory merely because its path
  is declared or `--force` is present.

### Reconciliation

- Sync refreshes the distinct local aliases referenced by `ritebook.toml` before
  trusting cached index metadata or mutating targets. Any refresh failure aborts
  the operation before target mutation; stale fallback is prohibited.
- An absent desired target may be installed and becomes owned only when target
  mutation and generated-state commit both succeed.
- An owned target may be replaced or removed only when its current canonical tree
  digest matches the last committed digest. A mismatch is a local edit and is
  preserved.
- A no-longer-desired owned target is pruned only when it is unchanged. Modified,
  unmanaged, unsafe, or otherwise unverifiable targets are retained.
- Independent target failures or safety skips do not erase successful outcomes.
  Sync writes truthful mixed lock state, reports every skipped or failed target,
  and exits nonzero whenever any item was skipped or failed.
- Re-running sync after a complete successful reconciliation is idempotent: no
  target bytes or deterministic generated state change.

### Locking, transactions, and recovery

- Direct install and sync acquire an exclusive process lock before reading
  generated ownership state and retain it through target finalization and state
  commit.
- Target replacement is staged beside the target. The prior target is retained as
  an installer-owned backup until all corresponding generated state commits.
- A persistent journal records the transaction identifier, affected paths,
  expected candidate state, retained backups, and phase transitions using atomic
  replacement and synchronization.
- Ordinary failures roll target mutations back before releasing the operation
  lock. If rollback cannot complete, backups and the journal are retained and
  their exact safe paths are reported.
- On the next operation under the same lock, Ritebook recovers an interrupted
  transaction before reading current ownership state: it finalizes only when all
  committed generated-state files match the journal's candidate digests;
  otherwise it restores prior state and targets.
- Filesystem operations revalidate target ownership, type, and symlink-free
  ancestry immediately before mutation and use same-directory atomic renames.

### Schema transition

- New writes use schema version 3.
- Schema-v1 and schema-v2 state are rejected without migration. Schema v1 lacks an
  installed-tree digest; schema v2 lacks canonical source-branch provenance.
- Ritebook does not silently adopt, replace, or prune a legacy target. Users must
  inspect and remove or relocate legacy target directories, then rerun install or
  sync so schema-v3 ownership can be established from a known transaction.
- Contribution consumes only materialized schema-v3 lock entries with verified
  provenance and an installed-tree digest. Non-materialized mixed-state entries
  are not publishable baselines.

## Consequences

### Positive

- Local edits and unmanaged directories are preserved by default.
- Removed requirements can be pruned without deleting unknown content.
- A successful lockfile or installation-registry entry describes the exact target
  tree committed by Ritebook.
- Concurrent processes cannot perform lost-update writes against the same owned
  installation state.
- Interruptions have deterministic next-run recovery instead of relying on manual
  inference from temporary directories.
- Sync both refreshes and reconciles, so users do not accidentally install from a
  stale cached catalog.

### Negative

- Installation requires more local state, filesystem hashing, locking, journal
  writes, and recovery code.
- Sync may complete only partially and return nonzero even though some targets
  were successfully reconciled.
- Legacy schema targets require explicit user cleanup before Ritebook can manage
  them safely.
- Very large skill trees incur content-hashing cost during inspection.

### Neutral

- The Git commit and index-digest provenance binding remains governed by
  [ADR 0001](./0001-source-provenance-and-trust.md).
- Publisher index schema v1 does not change. Installed-tree digests are computed
  by the consumer from materialized committed content.
- `--force` may request re-materialization of an unchanged owned target but does
  not override ownership, local-edit, symlink, or path-safety checks.

## Alternatives considered

| Option | Reason rejected |
| ------ | --------------- |
| Treat every declared path as managed | Would allow destructive replacement or pruning of unmanaged user content. |
| Use `--force` as an ownership override | A command flag cannot prove ownership or distinguish local edits from unrelated data. |
| Store only Git and index provenance | Proves source metadata but not the bytes currently present in the installed target. |
| Keep backups only in memory | Cannot recover after process termination or host interruption. |
| Update targets and best-effort rewrite state | Recreates the split-brain condition between filesystem reality and generated state. |
| Keep sync offline-first | Makes exact reconciliation depend on users separately remembering to refresh every referenced index. |
| Silently adopt schema-v1 targets | Legacy state contains no target-tree digest, so adoption could bless edited or unrelated content. |

## Related specifications

- [Skill Installation](../specs/skill-installation-spec.md)
- [Index Registry](../specs/index-registry-spec.md)
- [Skill Contribution](../specs/skill-contribution-spec.md)
- [Docker E2E Testing](../specs/docker-e2e-testing-spec.md)
