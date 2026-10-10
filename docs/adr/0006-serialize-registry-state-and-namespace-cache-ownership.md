# 0006. Serialize Registry State and Namespace Cache Ownership

Date: 2026-10-09
Status: Accepted

## Context

Index refresh currently reads `indexes.json`, performs Git and cache work, then
writes a replacement registry in separate unlocked operations. Two processes can
therefore validate the same prior registry and overwrite one another's updates.
The cache is grouped only by local alias, so two explicit registry files using the
same cache root can also claim or clean the same alias generations. Contribution
adds another race: after refreshing an alias it must import the exact committed
binding into a reusable checkout without allowing a concurrent refresh to change
the handoff underneath it.

Installation state has its own exclusive transaction lock. If registry code waits
for installation or checkout locks while those workflows wait for the registry,
the system can deadlock. A safe design therefore needs explicit ownership,
bounded locks, one registry commit point, and a lock order that keeps registry
transactions independent from downstream state.

## Decision

Ritebook will serialize each canonical registry path with a bounded POSIX
shared/exclusive lock, namespace all registry-owned cache state by a digest of that
canonical path, and treat atomic replacement of `indexes.json` as the sole
registry commit point.

### Registry ownership and locking

- The registry lock path is derived from the canonical registry path and protects
  that registry's metadata and cache ownership decisions.
- Read-only snapshots use a shared lock. Add, refresh, and cleanup use an
  exclusive lock with a bounded timeout and a stable busy diagnostic.
- Registry transactions may perform Git and cache I/O while holding the registry
  lock, but registry code never waits for installation-state or contribution-
  checkout locks.
- A refresh returns the exact immutable binding committed by its registry
  replacement. Callers do not reconstruct that result through a later unlocked
  read.

### Cache namespace and commit point

- Managed Git clones and immutable index generations live below a namespace
  derived from `sha256(canonical-registry-path)`. An alias in one registry cannot
  own, reuse, or clean another registry's files merely because both use the same
  cache root.
- Candidate cache content is durable before registry replacement. The atomic
  registry replacement is the only operation that makes the candidate current.
- Cleanup of unreferenced candidate or prior generations is best-effort after the
  commit point and cannot reverse or obscure a committed registry result.

### Exact-binding handoff

- Contribution first captures installation state without holding the registry
  lock, refreshes the selected alias, then acquires its checkout lock before a
  shared registry handoff lock.
- Under that shared lock it verifies that the alias still equals the exact refresh
  result and imports that commit plus required ancestry into the locked checkout.
- If the alias advanced before handoff, contribution releases the registry lock
  and performs a bounded retry. It never waits for the checkout lock while holding
  the registry lock.
- Installation metadata replacement uses compare-and-swap against the captured
  snapshot. Failure after a committed registry refresh is reported as partial
  success; the registry update remains committed and the user retries.

## Consequences

### Positive

- Concurrent add and refresh operations cannot lose unrelated registry updates.
- Explicit registry files can safely share a cache root without cross-cleanup.
- Contribution consumes the exact binding produced by refresh or retries instead
  of racing a later registry read.
- Lock ordering is explicit and avoids a registry/install/checkout lock cycle.

### Negative

- Registry operations can block for a bounded interval and fail busy.
- Registry and contribution adapters need lock, namespace, retry, and snapshot
  plumbing that was previously unnecessary.
- Holding the exclusive registry lock across Git I/O reduces same-registry
  concurrency in exchange for a simple auditable transaction boundary.

### Neutral

- The publisher `ritebook-index.json` schema remains version 1.
- Installation target transactions remain governed by
  [ADR 0004](./0004-reconcile-installed-skills-with-owned-transactional-state.md).
- Git commit and exact-index provenance remain governed by
  [ADR 0001](./0001-source-provenance-and-trust.md).

## Alternatives considered

| Option | Reason rejected |
| ------ | --------------- |
| Optimistic read and later whole-file rewrite | Concurrent writers can overwrite unrelated entries. |
| Lock only the final file replacement | Git and cache candidates would be based on stale state and cleanup ownership would remain ambiguous. |
| One global cache namespace | Independent registries sharing aliases could reuse or delete one another's managed state. |
| Hold the registry lock while waiting for checkout or installation locks | Creates a lock-order cycle and makes slow downstream work block all registry readers and writers. |
| Re-read the alias after refresh without a shared handoff lock | The alias can advance between verification and Git import. |

## Related specifications

- [Index Registry](../specs/index-registry-spec.md)
- [Skill Installation](../specs/skill-installation-spec.md)
- [Skill Contribution](../specs/skill-contribution-spec.md)
- [Docker E2E Testing](../specs/docker-e2e-testing-spec.md)
