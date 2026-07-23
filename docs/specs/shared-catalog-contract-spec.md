# Spec: Shared Catalog Contract

> **Status:** Active
> **Owner:** Ritebook maintainers
> **Spec version:** 1.0
> **Last reviewed:** 2026-07-23
> **Implementation state:** Implemented
> **Dependencies:** None
> **Associated ADRs:** [ADR 0001: Bind Cached Indexes and Installed Skills to Git Commits](../adr/0001-source-provenance-and-trust.md)

## Objective

This specification defines the catalog identity, schema-v1 path model, source
provenance, and trust-boundary rules shared by Ritebook's publisher, index
registry, skill installation, and skill contribution feature slices.

Feature specifications depend on this contract instead of redefining its terms.
They remain responsible for workflow-specific orchestration, persistence,
diagnostics, and recovery behavior.

## Implementation status

- Shared identifier and catalog-path rules are implemented under
  `src/ritebook/shared_kernel/`.
- Publisher output and consumer index readers enforce the same schema-v1 catalog
  structure.
- Registry, installation, and contribution state bind an exact publisher index to
  a full Git commit and digest in accordance with ADR 0001.
- Feature-specific adapters add stricter filesystem and mutation checks where
  their workflows require them.

## Shared terminology and identity

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
  exact-skill commands such as `install-skill` or `publish-skill-change`.
- A **repository-relative skill path** includes the published `skills_root` before
  the catalog skill path. It may therefore contain more segments than a catalog
  selector while remaining a safe relative path.

## Canonical identifiers

Published names, local aliases, skill directory names, and collection directory
names must use the canonical Ritebook identifier form:

- 1 to 64 characters;
- lowercase ASCII letters, digits, and hyphens only;
- no leading or trailing hyphen; and
- no consecutive hyphens.

Feature adapters must reject invalid external identifiers before invoking an
application use case.

## Catalog structure

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

## Publisher index schema v1

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

## Compatibility-sensitive names

The following schema and CLI names remain unchanged in version 1 even where their
names are less specific than their semantics:

- Publisher `index.name` and `publish-index --index-name` carry the published name.
- Consumer `indexes.json` field `name`, `update-index --name`, and
  `list-skills --index-name` carry or select the local alias.
- Generated `ritebook.lock` and `installations.json` field `index_name` carries the
  local alias from the corresponding qualified skill reference.
- Generated `ritebook.lock` fields `skill_path` and `skill_file` are safe paths
  relative to the source repository, not catalog-relative selectors.

A rename requires an explicitly versioned migration. Documentation and
diagnostics must state the semantic role of these fields in the meantime.

## Source provenance contract

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

## Shared trust and path rules

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

## Boundaries

- Shared kernel code may own pure identifiers, path policies, and immutable
  boundary concepts used by multiple slices.
- Feature orchestration, feature state formats, and adapter failure recovery must
  remain in the owning slice.
- The shared contract must not become a catch-all for generic architecture,
  tooling, CLI rendering, or test conventions.
- A schema change requires an explicitly versioned specification update and a
  compatibility or migration decision.

## Success criteria

- Publisher and consumer features use one catalog vocabulary and path model.
- Every schema-v1 reader rejects structurally invalid catalog metadata before use.
- Published names and local aliases retain distinct ownership and semantics.
- Catalog-relative and repository-relative paths are not conflated.
- Cached and generated consumer state preserves the commit-and-digest provenance
  binding required by ADR 0001.
- Feature specifications depend on this contract and document only their stricter
  or workflow-specific behavior.
