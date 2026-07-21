# Spec: Consumer List Skills

## Objective

Ritebook provides a consumer-facing `list-skills` workflow for users who have
already registered one or more Git-backed skill indexes with `add-index`.

The command helps a Ritebook consumer browse locally cached skill indexes from
the terminal and pick a skill by relative path. It should be deterministic,
offline-first, and grouped by local index alias so duplicate skill names across
indexes and at distinct paths within one index remain valid.

## Current context

- Ritebook already supports publisher-side index generation through
  `publish-index`.
- Publisher indexes are root-level `ritebook-index.json` files with schema
  version `1`.
- Publisher schema v1 includes index metadata and skill entries with required
  `name`, `path`, `skill_file`, and non-empty `description`.
- Consumer registry functionality already exists in
  `src/ritebook/features/index_registry/`:
  - `add-index` registers a Git URL or local Git repository source.
  - `update-index` refreshes cached index contents.
  - `list-indexes` lists registered index metadata.
- Registry entries already store each index's local alias and
  `cached_index_path`.
- [ADR 0001](../adr/0001-source-provenance-and-trust.md) requires each cached
  index to be bound to a full Git commit and exact-index digest. The current
  listing implementation does not yet verify that digest; implementation is
  tracked separately.
- `consumer-git-index-registry-spec.md` defines the registry foundation consumed
  by this browsing workflow.
- `list-skills` is implemented in the existing `index_registry` feature slice.
- The project follows hexagonal architecture with vertical feature slices under
  `src/ritebook/features/`.

## Desired behavior

### CLI shape

A user can list skills from all registered cached indexes:

```bash
uv run ritebook list-skills
```

A user can list skills from one local index alias:

```bash
uv run ritebook list-skills --index-name platform-skills
```

Tests and automation can override the registry path:

```bash
uv run ritebook list-skills --registry-path /tmp/indexes.json
uv run ritebook list-skills --index-name platform-skills --registry-path /tmp/indexes.json
```

A user can opt in to displaying descriptions:

```bash
uv run ritebook list-skills --show-description
uv run ritebook list-skills --index-name platform-skills --show-description
```

If `--index-name` is omitted, Ritebook lists skills from all registered indexes.

### Data source

- `list-skills` reads the existing local consumer registry.
- `list-skills` reads each selected registry entry's `cached_index_path`.
- Before trusting cached metadata, `list-skills` verifies the exact cached bytes
  against the registry entry's required `index_digest`.
- `list-skills` does not clone, fetch, pull, or otherwise contact Git remotes.
- `list-skills` does not scan publisher skill directories.
- `list-skills` does not read raw `SKILL.md` files.
- If a cached index file is missing, unreadable, or invalid, the command fails
  with a clear user-facing error.
- A digest mismatch fails as a cache-integrity error. Listing never falls back to
  a mutable source working tree or repairs provenance implicitly.

### Listing all skills

When no `--index-name` is provided:

- Ritebook reads all registered indexes in deterministic local-alias order.
- Ritebook reads each cached `ritebook-index.json`.
- Ritebook lists skills from each cached index under its local alias.
- Output is deterministic by local alias, then skill path.
- Duplicate skill names across different indexes and at distinct paths within one
  index are allowed.

### Listing one index

When `--index-name <local-alias>` is provided:

- Ritebook looks up the registered index by local alias.
- If the index is unknown, Ritebook fails with a clear user-facing error.
- Ritebook reads only that index's cached index file.
- Output keeps the same tree shape as all-index output, including the `Indexes`
  root and the matching index node.

### Empty output

If no skills are found, print:

```text
No skills found
```

This applies when no indexes are registered and when selected cached indexes
contain no skills.

### Default output format

Use a concise tree intended for human browsing:

```text
Indexes
├── data-skills
│   └── query-helper
└── platform-skills
    ├── browser/skill-b
    └── skill-a
```

Filtered output preserves the same shape:

```text
Indexes
└── platform-skills
    ├── browser/skill-b
    └── skill-a
```

Tree rules:

- The root label is `Indexes`.
- First-level children are local aliases.
- Second-level children are cached relative skill paths that can be copied after
  the local alias into `install-skill`.
- Relative skill paths, not `skills[].name`, identify entries within an index.
- Skill descriptions are shown only when `--show-description` is provided.
- `skill_file` values may be parsed and carried in application DTOs for install
  workflows, but they are not shown by this command.

When `--show-description` is provided, descriptions are appended to skill paths:

```text
Indexes
└── platform-skills
    ├── skill-a — Helps with platform workflows.
    └── skill-b — Helps with another platform workflow.
```

Schema v1 cached indexes without non-empty `description` metadata are invalid.

## Commands and validation

Focused checks during implementation:

```bash
uv run pytest tests/unit/features/index_registry/application/test_list_skills.py
uv run pytest tests/unit/features/index_registry/adapters/outbound/test_json_index_reader.py
uv run pytest tests/unit/adapters/inbound/cli/test_adapter.py
```

Full validation before handoff:

```bash
uv run ruff format .
uv run ruff check .
uv run ty check src/ritebook
uv run pytest -m "not e2e"
uv build
docker build -f Dockerfile.e2e -t ritebook-e2e .
docker run --rm ritebook-e2e
```

## Project structure

- Spec: `docs/specs/list-skills-spec.md`
- `src/ritebook/features/index_registry/application/dtos/index_registry.py`:
  command, result, and skill summary DTOs for `list-skills`, including the
  opt-in description display flag and cached skill descriptions.
- `src/ritebook/features/index_registry/application/ports/list_skills.py`:
  inbound application port for listing skills.
- `src/ritebook/features/index_registry/application/ports/cached_index_reader.py`:
  outbound port for reading skill entries from cached index files.
- `src/ritebook/features/index_registry/application/use_cases/list_skills.py`:
  application service that coordinates registry lookup and cached index reading.
- `src/ritebook/features/index_registry/adapters/outbound/json_index/reader.py`:
  JSON/filesystem cached index parsing.
- `src/ritebook/adapters/inbound/cli/parser.py`: `list-skills` arguments.
- `src/ritebook/features/index_registry/adapters/inbound/cli/commands.py`: CLI
  command handler and tree rendering.
- `src/ritebook/adapters/inbound/cli/adapter.py`: CLI dispatch and injected port.
- `src/ritebook/cli.py`: composition-root wiring.
- `tests/unit/features/index_registry/application/test_list_skills.py`:
  application behavior tests.
- `tests/unit/features/index_registry/adapters/outbound/test_json_index_reader.py`:
  cached index reader behavior tests.
- `tests/unit/adapters/inbound/cli/test_adapter.py`: CLI argument mapping and tree
  output tests.
- `README.md`: user-facing command documentation.

## Conventions

- Keep application logic independent of filesystem, JSON, and Git details.
- Keep cached index parsing in an outbound adapter.
- Use application-owned DTOs at application boundaries.
- Use explicit inbound and outbound ports.
- Keep tree rendering in the CLI adapter.
- Preserve deterministic output and deterministic tests.
- Keep description display opt-in so default output remains compact.
- Keep errors user-facing at the CLI boundary.
- Do not print secrets, Git credentials, raw index contents, or raw skill file
  contents in errors.
- Follow the existing hexagonal vertical-slice structure under
  `src/ritebook/features/index_registry/`.

## Testing strategy

### Application tests

Cover:

- Lists skill paths from all registered indexes.
- Rejects registry entries without required provenance and cached indexes whose
  bytes do not match `index_digest`.
- Sorts output deterministically by local alias and skill path.
- Preserves duplicate names at distinct relative paths within one index.
- Filters by `--index-name` / local alias.
- Returns an empty result when there are no registered indexes.
- Returns an empty result when cached indexes contain no skills.
- Fails clearly for an unknown local alias.
- Does not require or call any Git source port.

### JSON cached-index reader tests

Cover:

- Reads valid schema v1 cached indexes and returns skill entries.
- Reads required descriptions for opt-in display.
- Rejects invalid JSON.
- Rejects missing or unsupported `schema_version`.
- Rejects missing or malformed `skills`.
- Rejects malformed skill entries.
- Rejects unsafe absolute or parent-traversal paths using the same path-safety
  expectations as existing index validation.

### CLI tests

Cover:

- `list-skills` maps arguments to `ListSkillsCommand`.
- `list-skills --index-name <name>` maps the filter correctly.
- `list-skills --registry-path <path>` maps the registry path correctly.
- `list-skills --show-description` maps the description display flag correctly.
- Non-empty output is deterministic and tree-shaped.
- Filtered output still includes the `Indexes` root and index node.
- Description output appends descriptions only when requested.
- Empty output prints `No skills found`.
- Application and adapter errors are rendered as concise
  `ritebook: error: ...` messages.

## Boundaries

### Always

- List from locally cached registered indexes.
- Verify each cached index against the exact-byte digest selected by
  [ADR 0001](../adr/0001-source-provenance-and-trust.md).
- Group skills under local aliases.
- Include the `Indexes` root and index nodes in non-empty output.
- Show skill paths only in the default output.
- Show skill descriptions only when explicitly requested with
  `--show-description`.
- Reject cached schema v1 indexes without non-empty descriptions.
- Allow duplicate skill names across different local aliases and at distinct paths
  within one index.
- Keep output deterministic.
- Keep Git and network behavior out of `list-skills`.
- Keep implementation inside the existing `index_registry` feature slice unless a
  later spec changes the product boundary.

### Ask first

- Coupling installation side effects to `list-skills`.
- Adding live Git refresh behavior to `list-skills`.
- Adding path, description, or other metadata to default output.
- Adding JSON, CSV, table, or other script-oriented output modes.
- Adding search or filtering by tags, description, or path.
- Changing publisher index schema.
- Adding new persistent registry/cache locations or configuration mechanisms.

### Never

- Read live Git sources during `list-skills`.
- Mutate registered indexes during `list-skills`.
- Mutate cached index files during `list-skills`.
- Infer or repair missing provenance from a live Git source.
- Read raw `SKILL.md` contents for listing.
- Treat duplicate skill names across different indexes or at distinct paths in one
  index as an error.
- Print secrets, credentials, raw index contents, or raw skill file contents.

## Success criteria

- `uv run ritebook list-skills` lists a tree of all locally cached registered
  indexes and their skill paths.
- `uv run ritebook list-skills --index-name <local-alias>` lists only that
  index's skills while preserving the `Indexes` root and index node.
- `uv run ritebook list-skills --show-description` appends cached descriptions
  without changing default output.
- Unknown index names fail with a clear user-facing error.
- Empty registries or empty cached indexes print `No skills found`.
- Output is deterministic and grouped by local alias.
- No Git or network operations happen during skill listing.
- Cached metadata is displayed only after its required index digest is verified.
- Application, adapter, and CLI unit tests cover the behavior.
- README documents the new command.
- The configured non-E2E quality gate, package build, and Docker E2E suite pass
  before handoff.

## Open questions

- None. The current v1 intent and output shape were confirmed interactively.
