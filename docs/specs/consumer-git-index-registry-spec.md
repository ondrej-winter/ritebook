# Spec: Consumer Git Index Registry

## Objective

Ritebook provides a consumer-facing index registry workflow for end
users who consume curated internal Agent Skills from company-maintained Git
repositories.

The workflow lets a user add a Git-backed Ritebook skill index, cache the current
root `ritebook-index.json` locally, list registered indexes, and update one or
all cached copies later from their remembered Git sources. The registry is the
consumer-side catalog foundation used by the implemented `list-skills`,
`install-skill`, and requirements-file `install` workflows.

## Current context

- Ritebook already supports publisher-side skill index generation through
  `publish-index`.
- Publisher indexes are written as root-level `ritebook-index.json` files.
- Publisher schema v1 includes index metadata and skill entries with required
  `name`, `path`, `skill_file`, and non-empty `description`.
- The registry supports `add-index`, `list-indexes`, `list-skills`, and
  `update-index`. The `skill_installation` slice consumes registered cached
  indexes for `install-skill` and `install`.
- The current registry schema persists a full source revision and exact-index
  digest and points to an immutable content-addressed cache generation.
- [ADR 0001](../adr/0001-source-provenance-and-trust.md) defines the required
  end-to-end provenance binding; implementation is tracked in the remediation
  plan's dependent tasks.
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

Optional local alias:

```bash
uv run ritebook add-index \
  --source git@github.com:company/internal-skills.git \
  --alias platform-skills
```

Ritebook distinguishes two index identifiers:

- The **published name** is the canonical publisher-owned `index.name` metadata in
  `ritebook-index.json`. Ritebook validates and preserves this value.
- The **local alias** is the consumer-owned namespace for one registry entry. It
  defaults to the published name and can be set with `--alias` when published
  names collide or a different local namespace is useful.

The local alias is used for registry lookups, cache paths, update selection,
skill listing, and `<alias>/<skill-path>` installation references. Setting
an alias does not rewrite the published name or cached index contents. Projects
that share alias-based references in `ritebook.toml` or `ritebook.lock` must ensure
that collaborators and CI register the source under the same alias.

Requirements:

- `ritebook-index.json` must be located at the repository root.
- Ritebook must read and validate root `ritebook-index.json` before registering
  the index.
- Ritebook must select the source's full Git commit object ID and read the index
  from that commit, not from mutable working-tree contents.
- Ritebook must compute `index_digest` as `sha256:<lowercase-hex>` over the exact
  validated index bytes.
- The published index must include index metadata with a canonical published
  name.
- If `--alias` is not provided, the local alias defaults to the published name
  from `ritebook-index.json`.
- If `--alias` is provided, Ritebook uses it as the local registry namespace
  without changing the published name.
- Ritebook caches the exact validated index contents locally under the local
  alias.
- Ritebook persists the source locator and type, full `source_revision`, and
  `index_digest` with the cached-index path.
- If a local alias is already registered, Ritebook refuses to
  overwrite it unless an explicit replacement flag is provided.

Recommended duplicate replacement flag:

```bash
uv run ritebook add-index --source <git-source> --alias <alias> --force
```

### List indexes

A user can list locally registered indexes.

Example CLI shape:

```bash
uv run ritebook list-indexes
```

Requirements:

- Ritebook reads the same local registry used by `add-index` and `update-index`.
- Output is deterministic and sorted by local alias.
- Empty registries produce concise output: `No indexes registered`.
- Non-empty output includes the local alias, skill count, source type,
  updated timestamp, and remembered source.

### Update index

A user can refresh an existing registered index from its remembered Git source.

Example CLI shape:

```bash
uv run ritebook update-index --name platform-skills
uv run ritebook update-index --all
```

Requirements:

- Ritebook looks up the registered index by local alias. The existing
  `update-index --name` option selects that alias; it does not refer to the
  publisher-owned name.
- For a Git URL source, Ritebook fetches, pulls, or reclones as needed in its
  managed cache.
- For a local Git repository source, Ritebook reads the repository at the
  remembered local path.
- Ritebook selects the candidate full commit object ID after refreshing or reading
  the source and reads root `ritebook-index.json` from that commit.
- Ritebook validates and hashes those exact bytes before replacing the locally
  cached copy.
- The cached bytes, `source_revision`, `index_digest`, and registry metadata form
  one coherent logical state.
- If refresh, revision lookup, index read, validation, hashing, or persistence
  fails, Ritebook keeps the previous coherent binding intact.
- If the published name inside the refreshed `ritebook-index.json` changes,
  Ritebook keeps the local alias and records the refreshed published name.
- `update-index` requires exactly one target mode: `--name <local-alias>` or
  `--all`.
- `update-index --all` refreshes all registered indexes in deterministic
  local-alias order.
- If one index fails during `--all`, Ritebook continues updating the remaining
  indexes, reports failed local aliases to stderr, and returns a non-zero exit
  code after the batch completes.

## Publisher index metadata

The publisher-generated `ritebook-index.json` includes metadata that canonically
names the published index. This name becomes the default local alias but remains
distinct from any consumer-selected alias.

Publisher index schema v1:

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

- Required for generated indexes.
- Single-segment kebab-case identifier using the same general naming constraints
  as skill names.
- Slashes are not allowed because downstream skill installation references use
  `<index-name>/<skill-path>`.
- Intended to be stable across updates.
- Used as the default local alias during `add-index`.
- Preserved separately when `--alias` selects a different local namespace.

## Local registry and cache

Ritebook maintains a local consumer registry and cached index contents.

Recommended default location:

```text
~/.config/ritebook/indexes.json
~/.cache/ritebook/indexes/<local-alias>/<sha256-hex>/ritebook-index.json
~/.cache/ritebook/git/<source-cache-id>/
```

Tests and automation should be able to override these paths with explicit CLI
options or injected settings so unit tests do not mutate real user state.

Example registry schema:

The existing registry `name` field stores the local alias; `published_name`
stores publisher-owned metadata.

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
      "cached_index_path": "/Users/me/.cache/ritebook/indexes/platform-skills/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/ritebook-index.json",
      "source_revision": "0123456789abcdef0123456789abcdef01234567",
      "index_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
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
  "cached_index_path": "/Users/me/.cache/ritebook/indexes/platform-skills-local/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/ritebook-index.json",
  "source_revision": "0123456789abcdef0123456789abcdef01234567",
  "index_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "source_schema_version": 1,
  "skill_count": 12,
  "added_at": "2026-07-08T18:20:00Z",
  "updated_at": "2026-07-08T18:20:00Z"
}
```

Registry schema-v1 provenance requirements follow
[ADR 0001](../adr/0001-source-provenance-and-trust.md):

- `source_revision` is required and stores the full commit object ID whose root
  index was validated.
- `index_digest` is required and binds `cached_index_path` to the exact validated
  index bytes.
- Pre-release schema-v1 registry files missing either field are rejected with
  guidance to regenerate the registration. Ritebook does not infer provenance
  from the source's current `HEAD` or silently migrate on first use.

### Registry/cache commit protocol

- Cached indexes are immutable, content-addressed generations. The directory name
  is the lowercase SHA-256 hex from `index_digest`; the adapter verifies the exact
  bytes again before writing that generation.
- `add-index --force` and `update-index` preserve the generation referenced by the
  current registry entry while writing and synchronizing the candidate generation.
- The deterministic registry file is the commit record. Ritebook writes and
  synchronizes a uniquely named same-directory temporary registry file, then
  atomically replaces `indexes.json` so readers see either the old entry or the new
  entry, never a partially written entry.
- If candidate cache writing or registry replacement fails, the previous registry
  entry continues to reference its unchanged generation. Ritebook attempts to
  discard the unreferenced candidate without changing the reported commit failure.
- A process interruption may leave an unreferenced generation or adapter-owned
  temporary file. The next add or update for that local alias preserves the
  registry-referenced generation and the current candidate while deterministically
  removing other content-addressed generations and temporary files. Registry
  writes similarly remove abandoned adapter-owned registry temporary files.
- Cleanup never deletes legacy cache paths or files outside the expected
  content-addressed alias directory. Such paths remain readable until a successful
  registration or update switches the registry to a generated path.

## Duplicate behavior

- Duplicate skill names are allowed across different indexes.
- Duplicate skill names are also allowed within one index when their relative
  skill paths differ, such as `backend/code-review` and `frontend/code-review`.
- A skill's relative `path` is its identity and resolution key within an index;
  `skills[].name` is metadata and is not a fallback selector.
- The local alias plus relative skill path is the namespace boundary.
- Installation references skills as `<alias>/<skill-path>` in the
  separate `skill_installation` slice.
- Duplicate local aliases are not allowed unless the user explicitly
  replaces the existing registration.
- Local `--alias` exists primarily to resolve published-name collisions.

## Git source behavior

### Git URL sources

- Ritebook manages its own cached clone.
- `add-index` clones the repository into Ritebook's cache area.
- `update-index` refreshes that managed clone from the remote.
- Advancing mutable refs in the managed clone does not replace the previous
  registry/cache binding until the candidate commit and index are validated and
  persisted coherently.
- A detached candidate commit is valid. Rewritten refs do not invalidate an
  existing binding while its commit object remains available.
- If a bound commit is not available in the managed clone, Ritebook may fetch the
  remembered source to recover that exact object. If recovery fails, downstream
  use fails safely rather than substituting a current ref.
- Authentication is delegated to the user's existing Git setup, such as SSH keys,
  credential helpers, or configured Git access.
- Ritebook should surface Git failures clearly without exposing secrets.

### Local Git repository sources

- Ritebook validates that the path appears to be a Git repository.
- Ritebook does not own or mutate the local repository.
- `add-index` and `update-index` reject staged, unstaged, or untracked changes and
  provide guidance to commit or discard them.
- Ritebook reads root `ritebook-index.json` from the selected commit object without
  checking out, resetting, or cleaning the user-owned repository.
- Whether the local repository is up to date is the user's responsibility.
- Ritebook does not snapshot local repositories. A missing repository or bound
  commit fails safely and requires the user to restore it or explicitly refresh
  the registration from a new clean committed state.

## CLI and workflow requirements

Registry commands:

```bash
uv run ritebook add-index --source <git-url-or-local-git-repo> [--alias <local-alias>] [--force]
uv run ritebook update-index --name <local-alias>
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

The implementation uses the `index_registry` vertical feature slice:

```text
src/ritebook/features/index_registry/
├── application/
│   ├── dtos/
│   │   └── index_registry.py
│   ├── ports/
│   │   ├── add_index.py
│   │   ├── cached_index_reader.py
│   │   ├── list_indexes.py
│   │   ├── list_skills.py
│   │   ├── update_index.py
│   │   ├── git_source.py
│   │   ├── index_cache.py
│   │   ├── index_registry.py
│   │   └── index_source_reader.py
│   └── use_cases/
│       ├── add_index.py
│       ├── list_indexes.py
│       ├── list_skills.py
│       └── update_index.py
└── adapters/
    ├── inbound/cli/
    │   └── commands.py
    └── outbound/
        ├── filesystem_registry/
        │   └── adapter.py
        ├── git/
        │   └── adapter.py
        ├── index_cache/
        │   └── adapter.py
        └── json_index/
            └── reader.py
```

CLI integration and composition root:

- `src/ritebook/adapters/inbound/cli/parser.py`
- `src/ritebook/features/index_registry/adapters/inbound/cli/commands.py`
- `src/ritebook/adapters/inbound/cli/adapter.py`
- `src/ritebook/cli.py`

Publisher index metadata is implemented in:

- `src/ritebook/features/publisher/domain/catalog.py`
- `src/ritebook/features/publisher/adapters/outbound/json_index/writer.py`

Tests should mirror source ownership:

```text
tests/unit/features/index_registry/
├── application/
│   ├── test_add_index.py
│   ├── test_list_skills.py
│   └── test_update_index.py
└── adapters/outbound/
    ├── test_filesystem_registry.py
    ├── test_git_source.py
    ├── test_index_cache.py
    └── test_json_index_reader.py
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
- Persists the candidate commit and exact-index digest as one binding.
- Rejects dirty local repositories before caching or registry mutation.
- Uses the published name as the default local alias.
- Allows a local alias without changing the published name.
- Refuses duplicate local aliases without `force`.
- Replaces duplicate local aliases with `force`.

### Update index application tests

- Refreshes a registered Git URL source.
- Refreshes a registered local Git repository source.
- Updates cached index contents and metadata when validation succeeds.
- Preserves the existing coherent cache/revision/digest binding when refresh,
  validation, or persistence fails.
- Fails clearly for unknown local aliases.
- Requires either `--name` or `--all`, but not both.
- Refreshes all registered indexes when requested.
- Continues after per-index failures during all-index updates and reports failed
  local aliases.

### List indexes application tests

- Lists registered index summaries in deterministic local-alias order.
- Returns an empty result for an empty registry.

### Adapter tests

- JSON index reader rejects invalid JSON, missing root metadata, unsupported schema
  versions, missing `skills`, malformed entries, absolute paths, and `..`
  traversal paths.
- Filesystem registry writes deterministic `indexes.json` and preserves unrelated
  entries.
- Index cache writes complete synchronized `ritebook-index.json` generations
  before registry metadata can reference them.
- Content-addressed cache generations preserve the registry-referenced bytes until
  the registry commit succeeds and recover abandoned adapter-owned artifacts on the
  next mutation.
- Registry/cache readers reject schema-v1 entries missing required provenance and
  detect cached-index digest mismatches.
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
- Success output includes local alias and skill count.
- Error output is concise and user-facing.

## Commands and validation

When changing this workflow, use focused tests first, then the full quality gate:

```bash
uv run ruff format .
uv run ruff check .
uv run ty check src/ritebook
uv run pytest
uv build
```

## Boundaries

Registry responsibilities:

- Support `add-index` and `update-index` for index registration and refresh.
- Support `list-indexes` for registered index metadata only.
- Support both Git URLs and local Git repository paths.
- Require root-level `ritebook-index.json`.
- Cache the current index contents locally.
- Bind cached index contents to the selected full Git commit and exact-index
  SHA-256 digest according to
  [ADR 0001](../adr/0001-source-provenance-and-trust.md).
- Use publisher index metadata as the default local alias.
- Allow `--alias` to resolve published-name collisions without rewriting
  publisher metadata.
- Namespace skills by local alias and relative skill path.
- Preserve the previous cached index when `update-index` fails validation.
- Reject dirty local Git repositories before binding an index.
- Continue after per-index failures during `update-index --all`.

Extensions outside this registry specification:

- Skill browsing is specified in `list-skills-spec.md`.
- Skill installation is specified in `install-skill-spec.md`.
- Adding remote non-Git HTTP indexes.
- Adding trust signatures, approvals, lockfiles, or policy enforcement.
- Changing install path conventions.

Never:

- Assume an index file outside the repository root for this milestone.
- Mutate user-owned local repositories during add/update.
- Infer missing provenance from a mutable branch, tag, or working-tree `HEAD`.
- Print secrets, Git credentials, raw index contents, or raw skill file contents
  in errors.
- Treat duplicate skill names across different indexes or at distinct paths in one
  index as an error.

## Success criteria

- Publisher-generated `ritebook-index.json` includes an index name metadata field.
- A user can add an index from a Git repository URL.
- A user can add an index from an existing local Git repository.
- Ritebook caches the current root `ritebook-index.json` locally when adding an
  index.
- Every cached index is bound to a required full `source_revision` and verified
  `index_digest`.
- A user can update a registered index and refresh the cached index contents.
- Failed updates do not destroy the previous cached index.
- Dirty local repositories and pre-release schema-v1 entries without provenance
  fail with actionable regeneration guidance.
- The local alias defaults from published index metadata and can be set with
  `--alias` without changing the published name.
- Duplicate skill names across different local aliases and at distinct paths within
  one index are allowed.
- Duplicate local aliases are refused unless explicitly replaced.
- Relevant unit tests cover application behavior, JSON validation, registry/cache
  persistence, Git source handling, and CLI argument mapping.
- `uv run ruff format .`, `uv run ruff check .`, `uv run ty check src/ritebook`,
  `uv run pytest`, and `uv build` pass before handoff.

## Out of scope for the registry slice

- Skill browsing behavior owned by the `list-skills` use case.
- Skill installation behavior owned by the `skill_installation` slice.
- Non-Git HTTP index sources.
- Signed indexes, trust policy, approvals, and enterprise governance.
- Multiple index files per repository.
- Index files outside repository root.
