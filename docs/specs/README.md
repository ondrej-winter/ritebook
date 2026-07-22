# Specification Governance

This directory contains Ritebook's product and workflow specifications. Each
specification uses the same lifecycle metadata so readers can distinguish the
authority of the document from the completeness of its implementation.

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
- Current-state notes belong under `Implementation status`. They describe evidence
  in the current tree and are not additional requirements.
- Deferred behavior must name its owner or link to a tracked follow-up.
- Future ideas that are not commitments must be labeled as such and require a new
  approved specification or plan item before implementation.
- A superseded specification must link to its replacement in the metadata or at
  the start of the document.

## Review process

When behavior, dependencies, or architecture decisions change:

1. Update the specification and its implementation evidence together.
2. Recheck dependency and ADR links.
3. Update `Spec version` when the document contract changes materially.
4. Set `Last reviewed` only after comparing the document with the current tree.
5. Update `Implementation state` and identify any remaining work with an owner or
   linked follow-up.
