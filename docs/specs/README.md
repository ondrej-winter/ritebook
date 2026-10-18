# Specifications

This directory owns Ritebook's current product, shared-contract, and verification
requirements and the rationale needed to maintain them. Read the owning
specification before changing a supported workflow.

## Catalog

| Specification | Owner | State | Implementation | Purpose |
| --- | --- | --- | --- | --- |
| [Shared Catalog Contract](shared-catalog-contract-spec.md) | Shared kernel and consuming slices | Active | Implemented | Catalog identity, schema-v1 parsing, source provenance, and shared trust rules. |
| [Skill Linter](skill-linter-spec.md) | `skill_linter` | Active | Implemented | Portable headers, catalog discovery, diagnostics, and validated snapshots. |
| [Publisher](publisher-spec.md) | `publisher` | Active | Implemented | Generate an index from one successful validation snapshot. |
| [Index Registry](index-registry-spec.md) | `index_registry` | Active | Implemented | Registration, refresh, cache isolation, offline listing, and explicit recovery. |
| [Skill Installation](skill-installation-spec.md) | `skill_installation` | Active | Implemented | Direct installation, declaration-scoped sync, ownership, and failure handling. |
| [Skill Contribution](skill-contribution-spec.md) | `skill_contribution` | Active | Implemented | Prepare a local contribution from a lockfile-backed installed skill. |
| [Docker E2E Testing](docker-e2e-testing-spec.md) | Cross-feature verification | Active | Implemented | Clean installed-wheel validation of release-critical CLI workflows. |

The catalog provides navigation; each specification owns its metadata and
dependencies. Update both when adding or removing a specification.

## Authority and ownership

- An `Active` specification defines the contract for the behavior it owns. Code,
  tests, CLI help, and derived documentation must conform to it; implementation
  evidence does not silently redefine requirements.
- Feature specifications own workflow rules, interfaces, side effects, failure
  handling, and the rationale for their design. Put shared contracts in one named
  specification when at least two slices consume them.
- Explain current decisions and trade-offs under `Objective and Context`. Keep
  normative outcomes in `Requirements` and `Constraints and Execution Boundaries`,
  without a second contract in separate decision records.
- [`README.md`](../../README.md) owns setup and concise usage;
  [`AGENTS.md`](../../AGENTS.md) owns repository policy. Specifications link to
  those owners rather than copying their rules.
- Maintain the current baseline in place. Remove obsolete narratives, amendment
  chains, and completed execution logs after checking that current obligations
  have an owner. Editorial cleanup must not change supported behavior.

## Metadata

Place a `Status` section immediately after the title with these exact fields:

| Field | Meaning |
| --- | --- |
| `State` | `Draft` for proposed requirements; `Active` for the current contract. |
| `Revision` | Document contract version, independent of runtime file-format schemas. |
| `Acceptance basis` | Existing active contract, explicit instruction, or delegated decision authority that settles the requirements. |
| `Owner` | Role accountable for review and maintenance. |
| `Last reviewed` | Date checked against relevant code, tests, CLI, and dependent contracts, in `YYYY-MM-DD` format. |
| `Implementation state` | `Not started`, `Partially implemented`, or `Implemented`. |
| `Dependencies` | Repository-relative links to consumed specifications, or `None`. |

Requirements acceptance and implementation coverage are separate. `Implemented`
means the current tree represents the contract with identifiable evidence; it
does not establish that every verification gate ran. Partial coverage must name
the remaining work and its owner or resolution condition.

## Structure

Use these headings in order:

1. `Status`
2. `Objective and Context`
3. `Scope`
4. `Requirements`
5. `Implementation and Verification Evidence`
6. `Constraints and Execution Boundaries`
7. `Acceptance Checks`
8. `Assumptions`
9. `Open Questions`

Use a `Design rationale` subsection to explain choices or trade-offs. Describe the
current design directly, without making readers reconstruct a timeline. Detailed
contracts may use subsections for schemas, provenance, path safety, or isolation.

Requirements and acceptance checks use stable IDs. Each acceptance check names
the requirement, starting conditions and action, observable pass condition, and
verification method. Cover relevant failure, compatibility, and boundary cases;
requiring tests to exist or pass is insufficient.

Implementation evidence identifies source ownership, test scenarios, and runnable
commands. Distinguish it from executed results: files and test definitions provide
structural evidence; a passing gate requires an actual run.
Report current run results and skipped checks in the task handoff rather than
accumulating execution diaries in specifications.

Use `None` when no material assumption or open question remains. A current open
question must identify its impact, blocking status, owner or needed evidence, and
resolution condition. Uncommitted future ideas do not expand the supported scope.

## Maintenance

1. Compare the affected contract with its implementation, tests, CLI help, and
   dependent specifications. Surface material conflicts before choosing an
   unsupported product outcome.
2. Keep each obligation with its owning specification. Move necessary rationale
   with it, and update references before removing redundant documents.
3. For a behavior, compatibility, data-format, or supported-workflow change,
   settle the requirements and update the contract, implementation
   evidence, and acceptance checks together.
4. Update `Revision` for material contract changes; editorial consolidation alone
   does not require a version change. Set `Last reviewed` only after review.
5. Check dependencies, metadata, catalog state, links, examples, and referenced
   commands. Update the README when setup, usage, or operator guidance changes.
