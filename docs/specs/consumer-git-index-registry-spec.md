# Spec: Consumer Git Index Registry

## Objective

Ritebook will provide the first consumer-facing index registry workflow for end
users who consume curated internal Agent Skills from company-maintained Git
repositories.

The workflow lets a user add a Git-backed Ritebook skill index, cache the current
root `ritebook-index.json` locally, list registered indexes, and update one or
all cached copies later from their remembered Git sources. This establishes the
consumer-side catalog foundation for future `list-skills` and `install-skill`
workflows without implementing skill listing or installation yet.

## Current context

- Ritebook already supports publisher-side skill index generation through
  `publish-index`.
- Publisher indexes are written as root-level `ritebook-index.json` files.
- Publisher schema v1 includes skill entries with `name`, `description`, `path`,
  and `skill_file`.
- The next product primitive is not skill installation yet. It is registering and
  refreshing curated indexes that future consumer commands can use.
- Internal skill distribution should primarily support Git repositories because
  company skills are expected to live in private Git repositories.
- The project follows hexagonal architecture with vertical feature slices under
  `src/ritebook/features/`.

## Desired behavior

### Add index

A user can register a curated skill index from either:

1. A Git repository URL that Ritebook clones into its own local cache.
2. An already-cloned local Git repository path that Ritebook reads from.

Example CLI shape:

```bash
uv run ritebook add-index --source git@github.com:company/internal-skills.git
uv run ritebook add-index --source ./internal-skills
```

Optional local name override:

```bash
uv run ritebook add-index \
  --source git@github.com:company/internal-skills.git \
  --name platform-skills
```

Requirements:

- `ritebook-index.json` must be located at the repository root.
- Ritebook must read and validate root `ritebook-index.json` before registering
  the index.
- The published index must include index metadata with a default index name.
- If `--name` is not provided, Ritebook uses the index name from
  `ritebook-index.json`.
- If `--name` is provided, Ritebook uses it as the local effective index name.
- Ritebook caches the current index contents locally under the effective index
  name.
- Ritebook remembers enough source information to update the cached index later.
- If an effective index name is already registered, Ritebook refuses to
  overwrite it unless an explicit replacement flag is provided.

Recommended duplicate replacement flag:

```bash
uv run ritebook add-index --source <git-source> --name <name> --force
```

### List indexes

A user can list locally registered indexes.

Example CLI shape:

```bash
uv run ritebook list-indexes
```

Requirements:

- Ritebook reads the same local registry used by `add-index` and `update-index`.
- Output is deterministic and sorted by effective index name.
- Empty registries produce concise output: `No indexes registered`.
- Non-empty output includes the effective index name, skill count, source type,
  updated timestamp, and remembered source.

### Update index

A user can refresh an existing registered index from its remembered Git source.

Example CLI shape:

```bash
uv run ritebook update-index --name platform-skills
uv run ritebook update-index --all
```

Requirements:

- Ritebook looks up the registered index by effective index name.
- For a Git URL source, Ritebook fetches, pulls, or reclones as needed in its
  managed cache.
- For a local Git repository source, Ritebook reads the repository at the
  remembered local path.
- Ritebook reads root `ritebook-index.json` after refreshing or reading the
  source.
- Ritebook validates the index before replacing the locally cached copy.
- If validation fails, Ritebook keeps the previous cached copy intact.
- If the index name inside the refreshed `ritebook-index.json` changes, Ritebook
  keeps the local effective name unless the user explicitly re-adds or renames
  the index in a later workflow.
- `update-index` requires exactly one target mode: `--name <effective-name>` or
  `--all`.
- `update-index --all` refreshes all registered indexes in deterministic
  effective-name order.
- If one index fails during `--all`, Ritebook continues updating the remaining
  indexes, reports failed effective names to stderr, and returns a non-zero exit
  code after the batch completes.

## Publisher index metadata update

The publisher-generated `ritebook-index.json` should include metadata that names
the index. This name becomes the default consumer registry name.

Proposed publisher index schema v2 or schema v1 extension:

```json
{
  "schema_version": 1,
  "index": {
    "name": "company-skills"
  },
  "generated_at": "2026-07-08T18:20:00Z",
  "skills_root": ".",
  "skills": [
    {
      "name": "skill-a",
      "path": "skill-a",
      "skill_file": "skill-a/SKILL.md",
      "description": "Helps with skill A workflows."
    }
  ]
}
```

Index name requirements:

- Required for newly generated indexes once this feature is implemented.
- Kebab-case identifier using the same general naming constraints as skill names.
- Intended to be stable across updates.
- Used as the default effective index name during `add-index`.
- Can be locally overridden during `add-index` to avoid collisions.

## Local registry and cache

Ritebook should maintain a local consumer registry and cached index contents.

Recommended default location:

```text
~/.config/ritebook/indexes.json
~/.cache/ritebook/indexes/<effective-index-name>/ritebook-index.json
~/.cache/ritebook/git/<source-cache-id>/
```

Tests and automation should be able to override these paths with explicit CLI
options or injected settings so unit tests do not mutate real user state.

Example registry schema:

```json
{
  "schema_version": 1,
  "indexes": [
    {
      "name": "platform-skills",
      "published_name": "company-skills",
      "source": "git@github.com:company/internal-skills.git",
      "source_type": "git_url",
      "source_cache_path": "/Users/me/.cache/ritebook/git/<cache-id>",
      "cached_index_path": "/Users/me/.cache/ritebook/indexes/platform-skills/ritebook-index.json",
      "source_schema_version": 1,
      "skill_count": 12,
      "added_at": "2026-07-08T18:20:00Z",
      "updated_at": "2026-07-08T18:20:00Z"
    }
  ]
}
```

For local repository sources:

```json
{
  "name": "platform-skills-local",
  "published_name": "company-skills",
  "source": "/absolute/path/to/internal-skills",
  "source_type": "local_git_repo",
  "source_cache_path": null,
  "cached_index_path": "/Users/me/.cache/ritebook/indexes/platform-skills-local/ritebook-index.json",
  "source_schema_version": 1,
  "skill_count": 12,
  "added_at": "2026-07-08T18:20:00Z",
  "updated_at": "2026-07-08T18:20:00Z"
}
```

## Duplicate behavior

- Duplicate skill names are allowed across different indexes.
- The effective index name is the namespace boundary.
- Future installation behavior may install or reference skills as
  `<index-name>/<skill-name>`, but installation is out of scope for this
  milestone.
- Duplicate effective index names are not allowed unless the user explicitly
  replaces the existing registration.
- Local `--name` override exists primarily to resolve same-name index collisions.

## Git source behavior

### Git URL sources

- Ritebook manages its own cached clone.
- `add-index` clones the repository into Ritebook's cache area.
- `update-index` refreshes that managed clone from the remote.
- Authentication is delegated to the user's existing Git setup, such as SSH keys,
  credential helpers, or configured Git access.
- Ritebook should surface Git failures clearly without exposing secrets.

### Local Git repository sources

- Ritebook validates that the path appears to be a Git repository.
- Ritebook does not own or mutate the local repository.
- `add-index` and `update-index` read root `ritebook-index.json` from that path.
- Whether the local repository is up to date is the user's responsibility.

## CLI and workflow requirements

Initial commands:

```bash
uv run ritebook add-index --source <git-url-or-local-git-repo> [--name <effective-name>] [--force]
uv run ritebook update-index --name <effective-name>
uv run ritebook update-index --all
uv run ritebook list-indexes
```

Potential test/automation path overrides:

```bash
uv run ritebook add-index \
  --source <source> \
  --registry-path <path> \
  --cache-root <path>

uv run ritebook update-index \
  --name <name> \
  --registry-path <path> \
  --cache-root <path>

uv run ritebook update-index \
  --all \
  --registry-path <path> \
  --cache-root <path>

uv run ritebook list-indexes \
  --registry-path <path>
```

Success output should be concise, for example:

```text
Added index platform-skills with 12 skill(s)
Updated index platform-skills with 14 skill(s)
Updated 2 index(es) with 26 total skill(s)
No indexes registered
platform-skills	14 skill(s)	git_url	2026-07-08T18:20:00Z	git@github.com:company/internal-skills.git
```

Error output should be clear and user-facing, for example:

```text
ritebook: error: index platform-skills already exists; use --force to replace it
ritebook: error: ritebook-index.json was not found at the repository root
ritebook: error: unsupported index schema_version: 2
Failed to update 1 index(es): platform-skills
```

## Project structure

Implementation should add a new vertical feature slice:

```text
src/ritebook/features/index_registry/
├── application/
│   ├── dtos/
│   │   └── index_registry.py
│   ├── ports/
│   │   ├── add_index.py
│   │   ├── list_indexes.py
│   │   ├── update_index.py
│   │   ├── git_source.py
│   │   ├── index_cache.py
│   │   ├── index_registry.py
│   │   └── index_source_reader.py
│   └── use_cases/
│       ├── add_index.py
│       ├── list_indexes.py
│       └── update_index.py
└── adapters/
    └── outbound/
        ├── git/
        │   └── adapter.py
        ├── json_index/
        │   └── reader.py
        └── filesystem_registry/
            └── adapter.py
```

Update shared CLI adapter and composition root:

- `src/ritebook/adapters/inbound/cli/parser.py`
- `src/ritebook/adapters/inbound/cli/commands.py`
- `src/ritebook/adapters/inbound/cli/adapter.py`
- `src/ritebook/cli.py`

Update publisher index output:

- `src/ritebook/features/publisher/domain/catalog.py`
- `src/ritebook/features/publisher/adapters/outbound/json_index/writer.py`
- related publisher DTOs/tests as needed

Tests should mirror source ownership:

```text
tests/unit/features/index_registry/
├── application/
│   ├── test_add_index.py
│   ├── test_list_indexes.py
│   └── test_update_index.py
└── adapters/outbound/
    ├── test_git_source.py
    ├── test_json_index_reader.py
    └── test_filesystem_registry.py
```

## Conventions

- Keep Git operations, filesystem access, JSON parsing, and user config/cache
  paths in adapters or composition root.
- Keep application use cases independent of Git, JSON, and filesystem details.
- Use application-owned DTOs for commands, results, cached index metadata, and
  index source metadata.
- Validate external inputs at adapter boundaries.
- Do not log or print secrets, credentials, repository contents, or raw skill
  file contents.
- Use deterministic JSON output for registry/cache files.
- Use injected clocks for timestamps in tests.

## Testing strategy

### Publisher index metadata tests

- Publisher output includes index metadata with a valid name.
- Generated JSON remains deterministic except for timestamp.
- Missing or invalid index names are rejected where appropriate.

### Add index application tests

- Adds a Git URL source and caches validated index contents.
- Adds a local Git repository source and caches validated index contents.
- Uses published index name by default.
- Allows local name override.
- Refuses duplicate effective names without `force`.
- Replaces duplicate effective names with `force`.

### Update index application tests

- Refreshes a registered Git URL source.
- Refreshes a registered local Git repository source.
- Updates cached index contents and metadata when validation succeeds.
- Preserves existing cached index when refreshed source validation fails.
- Fails clearly for unknown index names.
- Requires either `--name` or `--all`, but not both.
- Refreshes all registered indexes when requested.
- Continues after per-index failures during all-index updates and reports failed
  effective names.

### List indexes application tests

- Lists registered index summaries in deterministic effective-name order.
- Returns an empty result for an empty registry.

### Adapter tests

- JSON index reader rejects invalid JSON, missing root metadata, unsupported schema
  versions, missing `skills`, malformed entries, absolute paths, and `..`
  traversal paths.
- Filesystem registry writes deterministic `indexes.json` and preserves unrelated
  entries.
- Index cache writes cached `ritebook-index.json` atomically enough for local use.
- Git adapter invokes Git non-interactively and reports clone/fetch failures
  clearly.

### CLI tests

- `add-index` maps CLI args into application command DTOs.
- `update-index` maps CLI args into application command DTOs.
- `update-index --all` maps CLI args into application command DTOs.
- `update-index` rejects missing or conflicting target modes.
- `list-indexes` maps CLI args into application command DTOs.
- `list-indexes` prints deterministic non-empty output and a concise empty
  registry message.
- Success output includes effective index name and skill count.
- Error output is concise and user-facing.

## Commands and validation

During implementation, use focused tests first, then the full quality gate:

```bash
uv run ruff format .
uv run ruff check .
uv run mypy .
uv run pytest
uv build
```

## Boundaries

Always:

- Support `add-index` and `update-index` only for this milestone.
- Support `list-indexes` for registered index metadata only.
- Support both Git URLs and local Git repository paths.
- Require root-level `ritebook-index.json`.
- Cache the current index contents locally.
- Use publisher index metadata as the default index name.
- Allow local name override to avoid effective-name collisions.
- Namespace duplicate skill names by effective index name.
- Preserve the previous cached index when `update-index` fails validation.
- Continue after per-index failures during `update-index --all`.

Ask first:

- Adding `list-skills`.
- Adding `install-skill`.
- Adding remote non-Git HTTP indexes.
- Adding trust signatures, approvals, lockfiles, or policy enforcement.
- Changing install path conventions.

Never:

- Assume an index file outside the repository root for this milestone.
- Mutate user-owned local repositories during add/update.
- Print secrets, Git credentials, raw index contents, or raw skill file contents
  in errors.
- Treat duplicate skill names across different indexes as an error.

## Success criteria

- Publisher-generated `ritebook-index.json` includes an index name metadata field.
- A user can add an index from a Git repository URL.
- A user can add an index from an existing local Git repository.
- Ritebook caches the current root `ritebook-index.json` locally when adding an
  index.
- A user can update a registered index and refresh the cached index contents.
- Failed updates do not destroy the previous cached index.
- The effective index name defaults from published index metadata and can be
  locally overridden.
- Duplicate skill names across different effective index names are allowed.
- Duplicate effective index names are refused unless explicitly replaced.
- Relevant unit tests cover application behavior, JSON validation, registry/cache
  persistence, Git source handling, and CLI argument mapping.
- `uv run ruff format .`, `uv run ruff check .`, `uv run mypy .`,
  `uv run pytest`, and `uv build` pass before handoff.

## Out of scope

- Listing skills.
- Installing skills.
- Deciding final installation namespace/path behavior.
- Non-Git HTTP index sources.
- Signed indexes, trust policy, approvals, and enterprise governance.
- Multiple index files per repository.
- Index files outside repository root.
