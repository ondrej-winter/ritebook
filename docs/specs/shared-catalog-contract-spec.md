# Specification: Shared Catalog Contract

## Status

- State: Active
- Revision: 1.1
- Acceptance basis: Existing Active repository contract; format normalized under the user's October 2, 2026 instruction without changing normative behavior.
- Accepted by / on: Original accepting person and date were not recorded.
- Owner: Ritebook maintainers
- Last reviewed: 2026-08-27
- Implementation state: Implemented
- Dependencies: None
- Associated ADRs: [ADR 0001: Bind Cached Indexes and Installed Skills to Git Commits](../adr/0001-source-provenance-and-trust.md)
- Supersedes: None

## Objective and Context

This specification defines the catalog identity, schema-v1 path model, source
provenance, and trust-boundary rules shared by Ritebook's publisher, index
registry, skill installation, and skill contribution feature slices.

Feature specifications depend on this contract instead of redefining its terms.
They remain responsible for workflow-specific orchestration, persistence,
diagnostics, and recovery behavior.

### Current-state evidence

- Shared identifier and catalog-path rules are implemented under
  `src/ritebook/shared_kernel/`.
- Publisher output and consumer index readers enforce the same schema-v1 catalog
  structure.
- Registry, installation, and contribution state bind an exact publisher index to
  a full Git commit and digest in accordance with ADR 0001.
- Feature-specific adapters add stricter filesystem and mutation checks where
  their workflows require them.

## Scope

- In scope: Shared catalog terminology, canonical identifiers, schema-v1
  catalog structure and publisher index fields, compatibility-sensitive names,
  source provenance, and common trust and path rules consumed by multiple slices.
- Out of scope: Feature-specific orchestration, persistence formats, mutation
  recovery, transport integration, and generic architecture or tooling policy.

## Requirements

The following requirement groups preserve the normative shared contract of revision 1.1.

All consuming slices use the terminology, catalog structure, compatibility rules,
and provenance requirements defined below rather than redefining them locally.

### R1 — Shared terminology and identity

**Basis:** Existing active Ritebook contract and the dependencies recorded in the Status section.

- A **published name** is the publisher-owned stable identifier stored as
  `index.name` in `ritebook-index.json`. Application code may call this value
  `published_name`. Consumers must not rewrite it when choosing a local namespace.
- A **local alias** is the consumer-owned namespace for a registered index. It
  defaults to the published name, but `add-index --alias` may choose another value.
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
- A **repository-relative skill path** includes the published `skills_root` before
  the catalog skill path. It may therefore contain more segments than a catalog
  selector while remaining a safe relative path.

### R2 — Canonical identifiers

**Basis:** Existing active Ritebook contract and the dependencies recorded in the Status section.

Published names, local aliases, skill directory names, and collection directory
names must use the canonical Ritebook identifier form:

- 1 to 64 characters;
- lowercase ASCII letters, digits, and hyphens only;
- no leading or trailing hyphen; and
- no consecutive hyphens.

Feature adapters must reject invalid external identifiers before invoking an
application use case.

### R3 — Catalog structure

**Basis:** Existing active Ritebook contract and the dependencies recorded in the Status section.

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

The one-or-two-segment rule applies to catalog paths and selectors. It does not
limit safe repository-relative paths formed by prefixing a catalog path with
`skills_root`.

### R4 — Publisher index schema v1

**Basis:** Existing active Ritebook contract and the dependencies recorded in the Status section.

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
- `generated_at` is a timezone-aware UTC timestamp in ISO 8601 format.
- `skills_root` is a safe normalized POSIX path relative to the repository root;
  `.` identifies the repository root itself.
- `skills` is a deterministically sorted array.
- `skills[].name` is the skill directory name.
- `skills[].path` is the catalog skill path and satisfies the shared catalog
  structure rules.
- `skills[].skill_file` is the path from `skills_root` to the skill's `SKILL.md`.
- `skills[].description` is a required non-empty description copied from the
  validated skill header.

Publisher and consumer readers must reject missing, unsupported, malformed,
unsafe, duplicate, over-deep, or mixed-node schema-v1 data before using it.

### R5 — Compatibility-sensitive names

**Basis:** Existing active Ritebook contract and the dependencies recorded in the Status section.

The following schema and CLI names remain unchanged in version 1 even where their
names are less specific than their semantics:

- Publisher `index.name` and `indexes publish --name` carry the published name.
- Consumer `indexes.json` field `name`, `indexes update <local-alias>`, and
  `skills list --index` carry or select the local alias.
- Generated `ritebook.lock` and `installations.json` field `index_name` carries the
  local alias from the corresponding qualified skill reference.
- Generated `ritebook.lock` fields `skill_path` and `skill_file` are safe paths
  relative to the source repository, not catalog-relative selectors.

A rename requires an explicitly versioned migration. Documentation and
diagnostics must state the semantic role of these fields in the meantime.

### R6 — Source provenance contract

**Basis:** Existing active Ritebook contract and ADR 0001.

- A consumer registry entry must bind cached index bytes to both a full Git commit
  in `source_revision` and a digest of the exact index bytes in `index_digest`.
- A consumer must verify both values before trusting cached metadata or reading
  skill content.
- Installation must preserve that binding in generated state used by downstream
  contribution workflows.
- Contribution must select the exact qualified lockfile requirement and use its
  recorded commit and digest. It must not fall back to a mutable source `HEAD`, a
  skill name, or a repository-relative path.
- Missing provenance is an invalid pre-release schema-v1 state. Ritebook must give
  regeneration guidance instead of inferring provenance from mutable sources.
- The consumer-owned digest does not alter the publisher schema and does not by
  itself authenticate the publisher.

### R7 — Shared trust and path rules

**Basis:** Existing active Ritebook contract and the dependencies recorded in the Status section.

- Treat publisher indexes, registry files, lockfiles, and installation manifests
  as untrusted external input at their reader boundaries.
- Reject absolute paths, parent traversal, empty or root-like mutation targets,
  and other paths that escape the intended root.
- Validate catalog paths separately from repository-relative and target paths;
  passing one policy must not imply passing another.
- Reject C0 controls (`U+0000`–`U+001F`), DEL (`U+007F`), and C1 controls
  (`U+0080`–`U+009F`) in persisted path and display metadata.
- Preserve ordinary Unicode descriptions outside those control ranges.
- Render any control character that reaches a CLI boundary as a visible,
  deterministic ASCII escape rather than emitting terminal control bytes.
- Never print secrets, Git credentials, raw index contents, or raw skill contents
  in diagnostics.
- A mutating feature must define its own symlink, atomic-write, rollback, and
  recovery semantics in its owning specification.

## Implementation and Verification Evidence

### Commands and validation

- Test: `uv run pytest tests/unit/shared_kernel tests/unit/features/index_registry`
- Lint and static checks: `uv run ruff check . && uv run ty check src/ritebook`
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
| AC4 | R4 | A publisher index is generated or read by a schema-v1 consumer. | Required fields and deterministic ordering are preserved, while missing, malformed, unsafe, duplicate, over-deep, or mixed-node data is rejected before use. | Publisher JSON tests and consumer index-reader tests. |
| AC5 | R5 | Schema-v1 compatibility-sensitive fields and CLI options are rendered or consumed. | Each field retains its documented semantic role, and no rename occurs without a versioned migration. | Schema and CLI contract review plus focused tests. |
| AC6 | R6 | Registry, installation, or contribution code trusts cached or committed index data. | The exact bytes are bound to and verified against both a full Git commit and SHA-256 digest; mutable source state is never substituted. | Provenance unit tests and publisher-to-consumer E2E coverage. |
| AC7 | R7 | Untrusted paths, metadata, diagnostics, or mutating workflows cross a boundary. | Unsafe paths and controls are rejected or visibly escaped, ordinary Unicode is preserved, secrets and raw contents are not exposed, and each mutating feature supplies its own recovery contract. | Shared safety tests, adapter tests, and manual diagnostic review. |

## Assumptions

- Schema version `1` remains the supported publisher-index compatibility target.
- Git-backed sources remain the supported provenance model for consumer workflows.
- Material unresolved assumptions: None.

## Open Questions

None.

## Revision and Handoff Notes

- October 2, 2026: Reformatted revision 1.1 to the current
  spec-driven-development template under the user's instruction. Requirement
  meaning, lifecycle state, and revision number were preserved.
- Next authorized step: Treat this Active revision as the canonical shared
  contract. Any schema, compatibility, or provenance change requires a revised
  specification and, where durable architecture changes, an ADR.
