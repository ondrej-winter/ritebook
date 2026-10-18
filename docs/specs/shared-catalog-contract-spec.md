# Specification: Shared Catalog Contract

## Status

- State: Active
- Revision: 1.2
- Acceptance basis: Existing active catalog, provenance, and trust contract.
- Owner: Ritebook maintainers
- Last reviewed: 2026-10-16
- Implementation state: Implemented
- Dependencies: None

## Objective and Context

This specification defines the catalog identity, schema-v1 path model, source
provenance, and trust-boundary rules shared by Ritebook's publisher, index
registry, skill installation, and skill contribution feature slices.

Feature specifications consume this contract without redefining its terms. They
own workflow-specific orchestration, persistence, diagnostics, and recovery.

### Design rationale

One closed, bounded catalog contract prevents publishers and consumers from
interpreting the same bytes differently. Exact-byte digests detect cache
corruption and mismatched artifacts; Git commits identify the repository base
needed by installation and contribution. Neither establishes publisher
authenticity. Signatures and approval policy are separate concerns.

### Current-state evidence

- Shared identifier and catalog-path rules are implemented under
  `src/ritebook/shared_kernel/`.
- Publisher output and consumer index readers enforce the same schema-v1 catalog
  structure.
- Registry, installation, and contribution state bind an exact publisher index to
  a full Git commit and exact-index digest.
- Feature-specific adapters add stricter filesystem and mutation checks where
  their workflows require them.

## Scope

- In scope: Shared catalog terminology, canonical identifiers, schema-v1
  catalog structure and publisher index fields, compatibility-sensitive names,
  source provenance, and common trust and path rules consumed by multiple slices.
- Out of scope: Feature-specific orchestration, persistence formats, mutation
  recovery, transport integration, and generic architecture or tooling policy.

## Requirements

Consuming slices use the terminology, catalog structure, compatibility rules, and
provenance requirements below without redefining them locally.

### R1 — Shared terminology and identity

- A **published name** is the publisher-owned stable identifier stored as
  `index.name` in `ritebook-index.json`. Application code may call this value
  `published_name`. Consumers must not rewrite it when choosing a local namespace.
- A **local alias** is the consumer-owned namespace for a registered index. It
  defaults to the published name, but `indexes add --alias` may set another value.
- A **catalog skill path** identifies one published skill relative to
  `skills_root`. In schema v1 it is `<skill>` or `<collection>/<skill>`.
- A **catalog selector** is the catalog-relative portion after the local alias in a
  qualified reference.
- A **qualified skill reference** is `<local-alias>/<catalog-selector>`. Its first
  segment is always a local alias, never an independently resolved published name.
- A **collection** is an implicit first-level catalog directory whose immediate
  child directories are skills. It is not itself a skill or index entry.
- A **collection selector** is `<local-alias>/<collection>` in `ritebook.toml`. It
  resolves only the collection's immediate child skills and is not accepted by
  exact-skill commands such as `skills install` or `skills contribute`.
- A **repository-relative skill path** prefixes the catalog skill path with the
  published `skills_root`. It may therefore contain more segments than a catalog
  selector while remaining a safe relative path.

### R2 — Canonical identifiers

Published names, local aliases, skill directory names, and collection directory
names must use the canonical Ritebook identifier form:

- 1 to 64 characters;
- lowercase ASCII letters, digits, and hyphens only;
- no leading or trailing hyphen; and
- no consecutive hyphens.

Feature adapters must reject invalid external identifiers before invoking an
application use case.

### R3 — Catalog structure

- A skill is a directory containing `SKILL.md`.
- A catalog skill path contains exactly one or two non-empty safe POSIX segments:
  `<skill>` or `<collection>/<skill>`.
- A `SKILL.md` directly at `skills_root` is an invalid zero-segment candidate.
- A first-level directory without `SKILL.md` may act as a collection when one or
  more immediate child directories are skills.
- A directory containing `SKILL.md` must not also contain another candidate skill
  below it. This mixed skill/collection node is invalid.
- Candidate paths with three or more catalog-relative segments are invalid rather
  than ignored or flattened.
- Empty and non-skill directories are ignored.
- Duplicate skill names are allowed at distinct catalog paths. The catalog path,
  not `skills[].name`, is the unique identity and downstream resolution key.
- Catalog entries must be ordered deterministically by path.

The one-or-two-segment rule applies to catalog paths and selectors, without
limiting safe repository-relative paths that prefix a catalog path with
`skills_root`.

### R4 — Publisher index schema v1

The canonical publisher artifact is the repository-root
`ritebook-index.json`:

```json
{
  "schema_version": 1,
  "index": {
    "name": "company-skills"
  },
  "generated_at": "2026-07-04T18:49:00Z",
  "skills_root": ".",
  "skills": [
    {
      "name": "example-skill",
      "path": "example-skill",
      "skill_file": "example-skill/SKILL.md",
      "description": "Helps users complete an example workflow."
    }
  ]
}
```

Field requirements:

- `schema_version` is the integer `1`.
- `index.name` is a canonical published name.
- `generated_at` is a real canonical UTC RFC 3339 timestamp ending in `Z`.
- `skills_root` is a safe normalized POSIX path relative to the repository root;
  `.` identifies the repository root itself.
- `skills` is a deterministically sorted array.
- `skills[].name` is the skill directory name.
- `skills[].path` is the catalog skill path and satisfies the shared catalog
  structure rules.
- `skills[].skill_file` is the path from `skills_root` to the skill's `SKILL.md`.
- `skills[].description` is required, non-empty, and copied from the validated
  skill header after trimming leading and trailing whitespace. In this normalized
  trimmed form, it is at most 1024 Unicode scalar values and contains no C0, DEL,
  C1, or surrogate code points.

The root object contains exactly `schema_version`, `index`, `generated_at`,
`skills_root`, and `skills`. The `index` object contains exactly `name`. Every
skill object contains exactly `name`, `path`, `skill_file`, and `description`.
Publisher and consumer readers reject missing, unknown, malformed, unsafe,
duplicate, over-deep, or mixed-node schema-v1 data before using it.

Before constructing a JSON object graph, consumers apply a bounded strict preflight:

- the exact input is non-empty UTF-8 without a byte-order mark;
- non-standard `NaN`, `Infinity`, and `-Infinity` constants are invalid;
- duplicate object member names are invalid; and
- input is at most 16 MiB (16,777,216 bytes);
- JSON object/array nesting depth is at most 32; and
- `skills` contains at most 10,000 entries.

`skills_root` is `.` or a normalized portable relative POSIX path. Portable path
segments reject empty, current, parent, control, surrogate, Windows-reserved,
trailing-dot or trailing-space, and Windows-forbidden forms. Catalog `path`
remains the canonical one-or-two-segment identity; `name` equals its final segment;
and `skill_file` equals `<path>/SKILL.md` exactly.

### R5 — Compatibility-sensitive names

These schema and CLI names remain unchanged in version 1, even where less
specific than their semantics:

- Publisher `index.name` and `indexes publish --name` carry the published name.
- Consumer `indexes.json` field `name`, `indexes update <local-alias>`, and
  `skills list --index` carry or select the local alias.
- Generated `ritebook.lock` and `installations.json` field `index_name` carries the
  local alias from the corresponding qualified skill reference.
- Generated `ritebook.lock` fields `skill_path` and `skill_file` are safe paths
  relative to the source repository, not catalog-relative selectors.

A rename requires an explicitly versioned migration. Until then, documentation
and diagnostics must state each field's semantic role.

### R6 — Source provenance contract

- A consumer binding includes a validated `source` locator and `source_type`,
  full Git commit object ID in `source_revision`, exact-index SHA-256 digest in
  `index_digest`, and canonical `refs/heads/...` retrieval branch in
  `source_branch`. The branch and locator retrieve content; the commit and digest
  identify the validated repository state and artifact.
- The digest covers the exact root `ritebook-index.json` bytes at the bound
  commit. A working-tree `HEAD`, branch, tag, timestamp, or source path cannot
  substitute for that binding.
- A consumer must verify the commit-and-digest binding before trusting metadata
  or reading skill content.
- Installation must preserve that binding in generated state used by downstream
  contribution workflows.
- Contribution must select the exact qualified lockfile requirement and use its
  recorded commit and digest. It must not fall back to a mutable source `HEAD`, a
  skill name, or a repository-relative path.
- Missing provenance is invalid. Ritebook must give regeneration or explicit
  recovery guidance, never infer old bytes' identity from mutable sources.
  Publisher indexes use schema v1, registries use schema v2, and
  installation state uses schema v3; each owning specification defines recovery.
- The consumer-owned digest does not alter the publisher schema and does not by
  itself authenticate the publisher.
- Consumers preserve the committed index as exact `bytes`, verify cached bytes
  against `index_digest` before decoding or parsing, and never replace the
  digest-bound artifact with a decoded-and-reencoded representation.

### R7 — Shared trust and path rules

- Treat publisher indexes, registry files, lockfiles, and installation manifests
  as untrusted external input at their reader boundaries.
- Reject absolute paths, parent traversal, empty or root-like mutation targets,
  and other paths that escape the intended root.
- Validate catalog paths separately from repository-relative and target paths;
  passing one policy must not imply passing another.
- Reject C0 controls (`U+0000`–`U+001F`), DEL (`U+007F`), and C1 controls
  (`U+0080`–`U+009F`) and Unicode surrogate code points in persisted path and
  display metadata.
- Preserve ordinary Unicode descriptions outside those control ranges.
- Render any control character that reaches a CLI boundary as a visible,
  deterministic ASCII escape rather than emitting terminal control bytes.
- Never print secrets, Git credentials, raw index contents, or raw skill contents
  in diagnostics.
- Each mutating feature's specification must define its symlink, atomic-write,
  rollback, and recovery semantics.

## Implementation and Verification Evidence

### Commands and validation

- Focused tests: `PYTEST_ADDOPTS='tests/unit/shared_kernel tests/unit/features/index_registry' make test`
- Quality gate: `make quality`
- Manual verification: inspect a generated schema-v1 `ritebook-index.json` and
  verify consumers reject invalid catalog paths and provenance.

### Project structure

- Spec: `docs/specs/shared-catalog-contract-spec.md`
- `src/ritebook/shared_kernel/`: shared pure identifiers, catalog paths, and
  source-safety concepts.
- `tests/unit/shared_kernel/`: shared-contract unit coverage.
- Consuming feature slices: enforce their workflow-specific boundaries.

### Conventions

- Use exact terms defined by this contract rather than overloaded aliases.
- Keep transport, filesystem, Git, and persistence concerns in owning adapters.

### Testing strategy

- Shared-kernel tests cover identifiers, catalog paths, and unsafe-input handling.
- Publisher and consumer adapter tests verify schema-v1 parsing and provenance at
  their boundaries.
- E2E tests verify the binding survives the publisher-to-consumer workflow.

## Constraints and Execution Boundaries

### Binding constraints

- Shared kernel code may own pure identifiers, path policies, and immutable
  boundary concepts used by multiple slices.
- Feature orchestration, feature state formats, and adapter failure recovery must
  remain in the owning slice.
- The shared contract must not become a catch-all for generic architecture,
  tooling, CLI rendering, or test conventions.
- A schema change requires an explicitly versioned specification update and a
  compatibility or migration decision.

### Changes requiring specification approval

- Adding a shared concept that fewer than two feature slices consume.
- Changing schema-v1 compatibility or the provenance binding.

### Exclusions and prohibited behavior

- Let the shared contract become a generic architecture, tooling, or CLI policy
  catch-all.
- Treat mutable source state as a substitute for required provenance.

## Acceptance Checks

| ID | Requirement | Conditions and action | Expected observable result | Verification method |
| --- | --- | --- | --- | --- |
| AC1 | R1 | Publisher and consumer features exchange catalog identifiers and references. | Published names, local aliases, catalog paths, selectors, and repository-relative paths retain the distinct meanings defined by this specification. | Shared-kernel and consuming-slice contract tests. |
| AC2 | R2 | A boundary receives valid and invalid identifier values. | Canonical identifiers are accepted; invalid length, character, edge-hyphen, or consecutive-hyphen forms are rejected before application orchestration. | Shared-kernel identifier tests and adapter tests. |
| AC3 | R3 | A catalog contains root skills, collection children, duplicates at distinct paths, mixed nodes, or over-deep candidates. | Only valid one- or two-segment catalog paths are accepted; valid duplicate names remain distinct by path; mixed and over-deep structures fail deterministically. | Catalog-path unit tests and publisher/consumer adapter tests. |
| AC4 | R4 | A publisher index is generated or read by a schema-v1 consumer. | Closed object shapes and deterministic ordering are preserved, while missing, unknown, malformed, unsafe, duplicate, over-deep, or mixed-node data is rejected before use. Exact bytes receive strict preflight before semantic use. | Shared strict-reader tests, publisher JSON tests, and consumer index-reader tests. |
| AC5 | R5 | Schema-v1 compatibility-sensitive fields and CLI options are rendered or consumed. | Each field retains its documented semantic role, and no rename occurs without a versioned migration. | Schema and CLI contract review plus focused tests. |
| AC6 | R6 | Registry, installation, or contribution code trusts cached or committed index data. | The exact bytes are bound to and verified against both a full Git commit and SHA-256 digest; mutable source state is never substituted. | Provenance unit tests and publisher-to-consumer E2E coverage. |
| AC7 | R7 | Untrusted paths, metadata, diagnostics, or mutating workflows cross a boundary. | Unsafe paths and controls are rejected or visibly escaped, ordinary Unicode is preserved, secrets and raw contents are not exposed, and each mutating feature supplies its own recovery contract. | Shared safety tests, adapter tests, and manual diagnostic review. |

## Assumptions

- Schema version `1` remains the supported publisher-index compatibility target.
- Git-backed sources remain the supported provenance model for consumer workflows.
- Material unresolved assumptions: None.

## Open Questions

None.
