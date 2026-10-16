# 0007. Scope Skill Sync to Declarations and Make Force Replacement Explicit

Date: 2026-10-11
Status: Accepted

Project-sync state, locking, rollback, and recovery are amended by
[ADR 0009](./0009-use-the-lockfile-as-the-only-project-sync-state.md).
The declaration-scoped selection and force rules below remain accepted;
direct-install transaction guarantees are unchanged.

## Context

ADR 0004 made installation ownership-aware and transactional. It also treated
`skills sync` as exact reconciliation: targets removed from `ritebook.toml` could
be pruned, while `--force` could replace only an unchanged Ritebook-owned target.

That model does not match the intended command contract. A requirements file
should identify only the skills that one sync invocation handles. Skill
directories outside the current declarations may be managed manually or by
another workflow and must be left alone. Conversely, `--force` is an explicit
destructive opt-in for the exact selected target, so requiring prior ownership or
an unchanged digest prevents the flag from doing the job users request.

The destructive opt-in must not weaken path, provenance, concurrency, rollback,
or recovery protections.

## Decision

Ritebook will process only targets selected by the current install command or
`ritebook.toml`. `--force` authorizes transactional replacement of an existing
safe target directory even when it is unmanaged or locally modified. Sync will
never prune targets omitted from the current requirements file.

### Explicit replacement

- Without `--force`, direct install rejects an existing target. Sync preserves an
  unmanaged or locally modified declared target, records an issue, and exits
  nonzero.
- With `--force`, direct install and sync replace the exact selected target from
  the verified index snapshot regardless of prior Ritebook ownership or local
  modifications. The successful transaction establishes fresh ownership and an
  installed-tree digest for the replacement.
- Force applies only to a normal directory at the exact validated target. It does
  not authorize filesystem roots, escaping paths, symlinks, special files, unsafe
  ancestry, invalid source content, or unverified provenance.
- Ritebook hashes the inspected target and revalidates that digest immediately
  before mutation. If the target changes after inspection, replacement fails
  rather than deleting unexamined content.

### Declaration-scoped sync

- Sync refreshes and installs or updates only targets resolved from the current
  `ritebook.toml`.
- A target previously recorded by sync but absent from the current declarations
  is not planned, inspected, modified, or deleted.
- Newly generated sync ownership and lock state contain only current declarations.
  Dropping an entry relinquishes Ritebook ownership metadata without deleting the
  directory. If that path is declared later, it is an existing unmanaged target
  and requires `--force` to replace.
- Removing an undeclared directory is an explicit user or future dedicated-command
  action, not a side effect of sync.

### Transaction and state safety

- ADR 0004 deterministic tree digest, exclusive installation lock, retained
  same-filesystem backup, compare-and-swap state commit, persistent recovery
  journal, descriptor-relative mutation, rollback, and interruption-recovery
  guarantees remain required.
- The target digest supplied to replacement is an inspection snapshot, not proof
  of ownership. It prevents time-of-check/time-of-use replacement races for both
  managed and unmanaged directories.
- Generated installation state remains schema version 3. New sync writes use
  `desired: true`; existing valid schema-v3 entries with `desired: false` remain
  readable and are normalized away by the next sync unless declared again.

## Consequences

### Positive

- `--force` has a direct, predictable meaning: replace the exact selected safe
  directory with the verified indexed skill.
- Users can intentionally recover from stale ownership ledgers, unmanaged target
  collisions, or local edits without a separate manual move step.
- Sync cannot delete a skill merely because a declaration was removed or a
  requirements file changed.
- Transactional rollback and race detection still protect the previous directory
  until generated state commits.

### Negative

- `--force` can intentionally destroy unmanaged content or uncommitted local
  edits at the selected target. CLI help and documentation must state this
  clearly.
- Removing a declaration no longer cleans up its directory. Users must delete or
  archive unwanted directories explicitly.
- A previously omitted directory loses Ritebook ownership metadata, so declaring
  it again requires `--force` even if its bytes still match an older lock entry.

### Neutral

- Without `--force`, unmanaged content and local edits remain protected.
- Publisher index schema v1 and installation state schema v3 do not change.
- Immutable source provenance remains governed by
  [ADR 0001](./0001-source-provenance-and-trust.md).

## Alternatives considered

| Option | Reason rejected |
| ------ | --------------- |
| Keep ADR 0004 semantics | Makes `--force` unable to replace the conflicts users explicitly ask it to replace and lets sync delete omitted skills. |
| Always overwrite declared targets | Removes the explicit destructive opt-in and risks accidental data loss during ordinary sync. |
| Keep pruning but add a separate no-prune mode | Makes the destructive behavior the default and conflicts with declaration-scoped sync. |
| Blindly delete before staging | Loses rollback and race protection and can destroy content that changed after inspection. |
| Preserve omitted entries indefinitely in generated state | Claims ownership over paths the current requirements file no longer manages. |

## Related specifications

- [Skill Installation](../specs/skill-installation-spec.md)
- [Skill Contribution](../specs/skill-contribution-spec.md)
