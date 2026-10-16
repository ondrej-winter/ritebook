# 0008. Rebuild Legacy Index Registrations on Explicit Force

Date: 2026-10-16
Status: Accepted

## Context

Schema-v1 registries retain source locations but cannot satisfy the current
branch and provenance contract. Rejecting them before `indexes update --force`
runs makes users re-enter recoverable registrations by hand.

## Decision

An explicit forced index update may rebuild schema-v1 registrations from their
validated local aliases, source locations, and source types. It discovers the
current canonical branch, reads and validates a fresh committed index, and
creates current provenance. It never infers the provenance of old cached bytes
or trusts legacy cache paths for reading or deletion.

This supersedes ADR 0001's manual-regeneration requirement for consumer index
registries only. Ordinary readers remain strict; installation state and
lockfile compatibility are unchanged.

Recovery uses the existing exclusive registry lock and atomic commit point.
Successful entries persist alongside untouched failed legacy entries in schema
v1 until every entry has been rebuilt in that run; the final successful
replacement writes schema v2. Retry with `--all --force` to complete a partially
recovered batch. Malformed JSON, unknown schema versions, ambiguous aliases, and
unsafe source locators remain errors without registry mutation.

## Consequences

- `indexes update --all --force` can recover old registrations without manually
  copying URLs or trusting stale provenance.
- A failed or interrupted recovery retains source registrations for retry.
- Ordinary registry consumers remain unavailable until recovery completes.
- Legacy caches remain on disk because their paths are not deletion authority.
- Recovery selects the source's current branch; it does not reproduce an old
  installation or repair an invalid upstream publisher index.
