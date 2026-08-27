# Specification Governance

This directory is the canonical source for Ritebook's product, shared-contract,
and supported-workflow requirements. Each specification uses the same lifecycle
metadata so readers can distinguish the authority of the document from the
completeness of its implementation.

## Authority and precedence

- An `Active` specification is the normative contract for the behavior it owns.
- Feature code, tests, CLI help, generated artifacts, and user-facing
  documentation must conform to their owning active specification. They provide
  implementation or conformance evidence; they do not redefine the contract.
- The root [`README.md`](../../README.md) owns setup and concise usage guidance.
  It must link to the owning specification instead of duplicating detailed
  product requirements.
- [Architecture Decision Records](../adr/README.md) own durable decision
  rationale, trade-offs, and consequences. A specification linked to an ADR must
  implement that decision's outcome without copying its rationale wholesale.
- If an active specification conflicts with code, tests, CLI help, or derived
  documentation, correct the conflicting artifact in the same change. Do not
  silently treat current implementation as a contract change.
- If an active specification appears to conflict with an accepted ADR, stop and
  reconcile both documents before implementation. Use a new ADR to change a
  durable decision; then update or supersede the affected specification.

Specifications stay in one flat directory while their filenames communicate
ownership. Feature specifications map to vertical slices under
`src/ritebook/features/`; shared specifications define contracts consumed by more
than one slice; quality specifications govern cross-cutting validation
infrastructure.

## Specification catalog

### Shared contract

| Specification | Owner | Status | Implementation | Purpose |
| --- | --- | --- | --- | --- |
| [Shared Catalog Contract](shared-catalog-contract-spec.md) | Shared kernel and consuming slices | Active | Implemented | Catalog identity, schema-v1 paths, index fields, provenance, and shared trust rules. |

### Feature slices

| Specification | Slice | Status | Implementation | Direct dependencies |
| --- | --- | --- | --- | --- |
| [Skill Linter](linter-spec.md) | `linter` | Active | Implemented | Shared catalog contract |
| [Publisher](publisher-spec.md) | `publisher` | Active | Implemented | Shared catalog contract; linter |
| [Index Registry](index-registry-spec.md) | `index_registry` | Active | Implemented | Shared catalog contract |
| [Skill Installation](skill-installation-spec.md) | `skill_installation` | Active | Implemented | Shared catalog contract; index registry |
| [Skill Contribution](skill-contribution-spec.md) | `skill_contribution` | Active | Implemented | Shared catalog contract; installation; index registry; publisher |

### Quality and infrastructure

| Specification | Area | Status | Implementation | Purpose |
| --- | --- | --- | --- | --- |
| [Docker E2E Testing](docker-e2e-testing-spec.md) | Cross-feature quality gate | Active | Implemented | Hermetic container validation of supported CLI workflows. |

The catalog is the navigation index, not a replacement for metadata in each
specification. Update both when adding, retiring, or superseding a specification.

## Required metadata

Every specification must declare these fields immediately after its title:

| Field | Meaning |
| --- | --- |
| `Status` | Lifecycle state of the specification. |
| `Owner` | Role accountable for review and follow-up. |
| `Spec version` | Version of the document contract, independent of file-format schema versions. |
| `Last reviewed` | Date the specification was checked against the repository, in `YYYY-MM-DD` format. |
| `Implementation state` | Current implementation coverage of the normative behavior. |
| `Dependencies` | Specifications whose contracts this workflow consumes, or `None`. |
| `Associated ADRs` | Architecture decisions governing the specification, or `None`. |

All specifications must use the exact field names above and link dependencies
and ADRs with repository-relative Markdown links.

## Required specification structure

Every feature, shared-contract, and quality specification must use the
spec-driven-development template headings: `Objective`, `Current context`,
`Assumptions`, `Desired behavior`, `Commands and validation`, `Project
structure`, `Conventions`, `Testing strategy`, `Boundaries`, `Success criteria`,
and `Open questions`.

Feature-specific normative sections may appear between `Desired behavior` and
`Commands and validation` when they make a contract easier to review, such as a
schema, provenance, path-safety, or isolation contract. An implemented
specification may record confirmed compatibility and operating foundations under
`Assumptions`; it must state `None` when no unresolved assumptions remain.
Likewise, use `None` under `Open questions` when the current specification
version has no decision awaiting maintainer input.

## Allowed lifecycle values

`Status` must be one of:

- `Draft`: under review and not yet authoritative.
- `Active`: authoritative for current development and maintenance.
- `Superseded`: replaced by another linked specification or decision.
- `Retired`: no longer applicable and retained only for historical context.

`Implementation state` must be one of:

- `Not started`: no normative behavior has been implemented.
- `Partially implemented`: some normative behavior is implemented, with remaining
  work identified in the specification or a linked follow-up.
- `Implemented`: the normative behavior is represented in the current tree and
  has implementation evidence in tests, project structure, or validation notes.

Lifecycle status and implementation state are independent. For example, an
active specification may be only partially implemented, while a superseded
specification may describe behavior that remains in the tree during migration.

## Content classification

- Normative requirements belong in sections such as `Desired behavior`,
  `Boundaries`, and `Success criteria` and use requirement language such as
  **must**, **must not**, or an unambiguous imperative.
- Current-state notes belong under `Current context`. They describe evidence
  in the current tree and are not additional requirements.
- Deferred behavior must name its owner or link to a tracked follow-up.
- Future ideas that are not commitments must be labeled as such and require a new
  approved specification or plan item before implementation.
- A superseded specification must link to its replacement in the metadata or at
  the start of the document.

## Shared contracts

Cross-feature terminology and normative behavior belong in a named shared
specification rather than in this governance file or repeated across feature
specifications. The current shared catalog vocabulary, schema-v1 path model,
compatibility-sensitive names, provenance binding, and trust rules are defined by
the [Shared Catalog Contract](shared-catalog-contract-spec.md).

Create another shared specification only when at least two slices consume one
stable product contract. Generic architecture, tooling, and documentation policy
belong in their existing project rules or ADRs instead.

## Review process

When behavior, dependencies, or architecture decisions change:

1. Update the specification and its implementation evidence together.
2. Recheck dependency and ADR links.
3. Update `Spec version` when normative behavior, compatibility, data format, or
   an externally visible workflow changes materially. Editorial-only corrections
   do not require a version increase.
4. Set `Last reviewed` only after comparing the document with the current tree,
   relevant tests, CLI surface, and linked contracts.
5. Update `Implementation state` and identify any remaining work with an owner or
   linked follow-up.
6. Update the root README only when setup, supported usage, or operator guidance
   changes; keep detailed requirements in the owning specification.
