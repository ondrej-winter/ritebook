# 0009. Use the Lockfile as the Only Project Sync State

Date: 2026-10-16
Status: Accepted

Accepted as the development contract after the user's explicit interview
confirmation. Implementation is pending the linked plan.

## Context

ADR 0007 retained ADR 0004's installation ledger, operation lock, transaction
journal, and whole-operation rollback guarantees. Project sync consequently
writes both portable `ritebook.lock` entries and machine-specific ownership
entries under `.ritebook/`. It can already derive ownership from a valid
lockfile when the local ledger is absent.

The user wants to remove redundant project state. They explicitly accepted
partial completion and manual repair after an interrupted sync, declined a
sync operation lock even outside the project, and took responsibility for
running one mutating installation command at a time. Local edits must remain
protected: skip the skill and explain force replacement or the existing
contribution workflow. Without a lockfile, existing directories must be skipped
unless force explicitly authorizes replacement.

An index describes verified candidate content. It cannot establish which
content was previously installed or distinguish unpublished edits from an
interrupted update. The lockfile's recorded installed-tree digest supplies that
baseline without another ownership ledger.

## Decision

Project sync will use the selected schema-v3 `ritebook.lock` as its only
persistent installation record. It will create no `.ritebook/` bookkeeping
directory, sync operation lock, alternate concurrency coordinator, installation
ledger, or durable recovery journal. Whole-sync rollback and automatic next-run
recovery are removed from the sync contract.

- Derive canonical target paths in memory from portable lock entries and the
  requirements-file location. Keep the schema-v3 provenance, digest, target
  identity, status, and partial-result contracts.
- Preserve locally modified and unmanaged directories without force. Keep the
  previous baseline when preserving edits. Do not infer ownership from an index
  match or adopt uncertain bytes after interruption.
- Install missing targets when the lockfile is absent. Skip existing directories
  without force; force replacement can establish a new baseline.
- Keep complete candidate staging, source verification, target-digest
  revalidation, symlink and path protection, same-filesystem replacement, and
  atomic lockfile writes. Temporary per-target artifacts remain possible; they
  do not constitute durable recovery state.
- Completed replacements may remain after failure or interruption, with a stale
  or absent lockfile. A subsequent run preserves discrepancies and reports
  manual repair options. Overlapping mutating installation commands are
  unsupported and are the user's responsibility.
- Local-edit guidance names `--force` as destructive replacement and
  `skills contribute` as the existing local contribution workflow when a valid
  lock baseline exists. It does not promise automatic push or MR creation.
- Old `.ritebook/` data is ignored and left untouched. Upgrade guidance requires
  resolving an unfinished old operation with the previous version or manual
  inspection before removing obsolete artifacts. No automatic legacy cleanup
  or recovery migration is introduced.

This decision amends ADR 0007 and the sync-specific guarantees inherited from
ADR 0004. Their direct-install state, locks, journals, rollback, and recovery
guarantees remain required. Index-registry locking in ADR 0006 and source
provenance in ADR 0001 are unchanged. No file-format schema bump is required.

## Consequences

- Projects have one portable installation record; machine paths and duplicate
  ownership metadata need not persist separately.
- Sync orchestration and failure handling can be separated from the recoverable
  transaction adapter still needed by direct install.
- An interrupted or failed sync can leave updated targets and an older lockfile,
  or temporary replacement artifacts. Users inspect and repair these manually;
  rerunning without force conservatively preserves uncertain existing content.
- An interruption during a directory swap may leave the selected target absent.
  Complete staging and atomic individual renames do not make the whole swap or
  sync atomic.
- Concurrent invocations can conflict or lose updates. No coordination guarantee
  is provided for project sync; index-registry locks cover only registry work.
- Removing a lockfile also removes sync's ownership evidence. Even a directory
  matching published content is preserved without force.
- Existing strict provenance checks, declaration-scoped selection, no-prune
  behavior, and local-edit preservation remain required.

## Alternatives considered

| Option | Reason rejected |
| ------ | --------------- |
| Keep both the ledger and lockfile | Duplicates installation facts already available in the portable lockfile. |
| Keep a journal and whole-sync rollback | Preserves complexity the user explicitly traded for manual repair. |
| Keep a project-local or user-global sync lock | The user explicitly chose to serialize commands themselves. |
| Infer prior ownership from the current index | Cannot distinguish the previous installed baseline from local edits or interrupted updates. |
| Always overwrite declared targets | Conflicts with the explicit requirement to preserve edits unless forced. |
| Simplify direct install and registry locking too | Exceeds the confirmed project-sync scope. |

## Related specifications and plan

- [Skill Installation, revision 3.4](../specs/skill-installation-spec.md)
- [Skill Contribution](../specs/skill-contribution-spec.md)
- [Project sync state simplification plan](../plans/project-sync-state-simplification-plan.md)
