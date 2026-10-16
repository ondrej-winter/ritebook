# Specification: Index Registry

## Status

- State: Active
- Revision: 2.5
- Acceptance basis: Existing active registry, cache, and explicit source-recovery contract.
- Owner: Ritebook maintainers
- Last reviewed: 2026-10-16
- Implementation state: Implemented
- Dependencies: [Shared Catalog Contract](shared-catalog-contract-spec.md)

## Objective and Context

Ritebook provides a consumer-facing index registry workflow for end
users who consume curated internal Agent Skills from company-maintained Git
repositories.

The workflow lets a user add a Git-backed Ritebook skill index, cache the current
root `ritebook-index.json` locally, list registered indexes, and update one or
all cached copies later from their remembered Git sources. The registry is the
consumer-side catalog foundation used by the implemented `skills list`,
`skills install`, and requirements-file `skills sync` workflows.

### Design rationale

The registry file is the commit record for a validated source and cached index.
Writing durable candidates before replacing that file prevents mixed bindings.
Registry locks serialize read and write snapshots; namespacing caches by the
canonical registry path prevents independent registries from claiming or cleaning
each other's files.

Legacy recovery rebuilds a binding from saved safe source locations. It preserves
registrations for retry without treating old cached bytes or paths as authority.

### Current-state evidence

- Ritebook supports publisher-side skill index generation through
  `indexes publish`.
- Publisher indexes are written as root-level `ritebook-index.json` files.
- Publisher schema v1 includes index metadata and skill entries with required
  `name`, `path`, `skill_file`, and non-empty `description`.
- Schema-v1 parsing validates literal catalog paths, one-or-two-segment depth,
  canonical segments, duplicate paths, and mixed nodes before candidate cache or
  registry mutation.
- The registry supports `indexes add`, `indexes list`, `skills list`, and
  `indexes update`. The `skill_installation` slice consumes registered cached
  indexes for `skills install` and `skills sync`.
- Registry schema v2 persists source revision, branch, and exact-index digest
  and points to an immutable content-addressed cache generation.
- [Shared Catalog Contract](shared-catalog-contract-spec.md) defines the implemented
  end-to-end provenance binding.
- Internal skill distribution should primarily support Git repositories because
  company skills are expected to live in private Git repositories.
- The project follows hexagonal architecture with vertical feature slices under
  `src/ritebook/features/`.

## Scope

- In scope: Adding and updating Git-backed publisher indexes, maintaining
  coherent registry and content-addressed cache state, listing indexes and cached
  skills offline, alias semantics, and Git source safety.
- Out of scope: Skill installation side effects, non-Git remote indexes, live
  source refresh while listing, search or script-oriented listing formats, trust
  signatures, and publisher schema changes.

## Requirements

The following groups define the normative index-registry contract.

### R1 — Add index

A user can register a curated skill index from either:

1. A Git repository URL that Ritebook clones into its own local cache.
2. An already-cloned local Git repository path that Ritebook reads from.

Example CLI shape:

```bash
uv run ritebook indexes add --source git@github.com:company/internal-skills.git
uv run ritebook indexes add --source ./internal-skills
```

Optional local alias:

```bash
uv run ritebook indexes add \
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
skill listing, and `<local-alias>/<skill-path>` installation references. Setting
an alias does not rewrite the published name or cached index contents. Projects
that share alias-based references in `ritebook.toml` or `ritebook.lock` must ensure
that collaborators and CI register the source under the same alias.

Requirements:

- `ritebook-index.json` must be located at the repository root.
- Ritebook must read and validate root `ritebook-index.json` before registering
  the index.
- Source admission applies the shared bounded strict-JSON preflight and complete
  closed schema-v1 semantic validation before cache or registry mutation.
- Every `skills[].path` must contain exactly one or two non-empty safe POSIX path
  segments: `<skill>` or `<collection>/<skill>`. Paths with three or more segments
  are invalid legacy catalog metadata.
- Every collection and skill segment in `skills[].path` must use the canonical
  1–64 character Ritebook kebab-case identifier form.
- An index must not contain both a root skill path `<name>` and any collected skill
  path beginning `<name>/`. That path set would make the first segment both a skill
  and a collection and is invalid schema-v1 metadata.
- `indexes add`, including forced replacement, must reject a structurally invalid
  schema-v1 index before committing cache or registry state and direct the user to
  reorganize and republish the source catalog.
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
- Registry schema v2 persists `alias_origin = "published_name"` for the default
  and `alias_origin = "explicit"` for a supplied alias. Update preserves the
  origin while preserving the local alias.
- Ritebook caches the exact validated index contents locally under the local
  alias as bytes without decode/re-encode normalization.
- Ritebook persists the source locator and type, full `source_revision`, and
  `index_digest` with the cached-index path.
- Git URL sources must not contain standard-URL authority user-info. Ritebook
  rejects username-only, password/token, and percent-encoded user-info before Git
  execution, managed-cache creation, or persistence. Authentication uses the
  user's SSH configuration, credential helper, or other Git-managed mechanism.
- scp-like SSH syntax such as `git@github.com:company/internal-skills.git` remains
  supported; its username is treated as an SSH identity, not embedded URL
  credentials.
- If a local alias is already registered, Ritebook refuses to
  overwrite it unless an explicit replacement flag is provided.

Recommended duplicate replacement flag:

```bash
uv run ritebook indexes add --source <git-source> --alias <alias> --force
```

### R2 — List indexes

A user can list locally registered indexes.

Example CLI shape:

```bash
uv run ritebook indexes list
```

Requirements:

- Ritebook reads the same local registry used by `indexes add` and `indexes update`.
- Output is deterministic and sorted by local alias.
- Empty registries produce concise output: `No indexes registered`.
- Non-empty output includes the local alias, skill count, source type,
  updated timestamp, and remembered source.
- Remembered sources are rendered through a defensive display form that removes
  standard-URL user-info and never prints embedded credentials.

### R3 — List cached skills

A user can browse all cached skills or filter by one local alias without network
access:

```bash
uv run ritebook skills list
uv run ritebook skills list --index platform-skills
uv run ritebook skills list --show-description
uv run ritebook skills list --registry-path /tmp/indexes.json
uv run ritebook skills list --index platform-skills --registry-path /tmp/indexes.json
```

Requirements:

- Read selected entries from the existing local registry and their immutable
  `cached_index_path` values.
- Verify the exact cached bytes against each registry entry's `index_digest`
  before UTF-8 decoding, JSON parsing, or displaying metadata.
- Do not clone, fetch, pull, inspect publisher directories, or read `SKILL.md`.
- Apply the shared schema-v1 catalog validation before displaying any entry.
- List all indexes in deterministic local-alias order and skills in catalog-path
  order. Duplicate names at distinct paths remain valid.
- Treat `--index` as a local-alias filter. Unknown aliases fail clearly.
- Render non-empty output as a tree rooted at `Indexes`, with local aliases as
  first-level nodes and catalog paths as second-level nodes.
- Show descriptions only with `--show-description`; default output remains paths
  only. `skill_file` is never displayed.
- Preserve ordinary Unicode descriptions and visibly escape control characters at
  the CLI boundary.
- Print `No skills found` when no selected cached index contains a skill.
- Accept `--registry-path` as an explicit test and automation override without
  changing the default user registry location.

Example:

```text
Indexes
├── data-skills
│   └── query-helper
└── platform-skills
    ├── browser/skill-b
    └── skill-a
```

### R4 — Update index

A user can refresh an existing registered index from its remembered Git source.

Example CLI shape:

```bash
uv run ritebook indexes update platform-skills
uv run ritebook indexes update platform-skills --force
uv run ritebook indexes update --all
uv run ritebook indexes update --all --force
```

Requirements:

- Ritebook looks up the registered index by the positional local alias. It does not
  refer to the publisher-owned name.
- For a Git URL source, Ritebook fetches, pulls, or reclones as needed in its
  managed cache.
- For a local Git repository source, Ritebook reads the repository at the
  remembered local path.
- `--force` is valid with either one local alias or `--all`. For a Git URL source,
  Ritebook clones into a fresh registry-owned path rather than trusting or
  mutating the currently registered managed clone.
- For a local Git repository source, `--force` re-reads the remembered clean
  committed state but never deletes, resets, cleans, or otherwise mutates the
  user-owned repository.
- Ritebook selects the candidate full commit object ID after refreshing or reading
  the source and reads root `ritebook-index.json` from that commit.
- Ritebook validates and hashes those exact bytes before replacing the locally
  cached copy.
- `indexes update` applies the same one-or-two-segment schema-v1 skill-path
  validation as `indexes add`.
- The cached bytes, `source_revision`, `index_digest`, and registry metadata form
  one coherent logical state.
- If refresh, revision lookup, index read, validation, hashing, or persistence
  fails, Ritebook keeps the previous coherent binding intact.
- A forced Git URL update switches `source_cache_path` only after candidate index
  validation, cache synchronization, and registry replacement succeed. A failed
  forced update best-effort removes its fresh unreferenced clone.
- A successful forced update best-effort removes the superseded managed clone only
  when no remaining registry alias references that exact `source_cache_path`.
- Forced cache writing repairs the content-addressed generation even when the
  validated digest is unchanged and the existing local bytes are damaged.
- An over-deep candidate index is a validation failure; update preserves the
  previously registered cache, revision, digest, and metadata.
- If the published name inside the refreshed `ritebook-index.json` changes,
  Ritebook keeps the local alias and records the refreshed published name.
- `indexes update` requires exactly one target mode: `<local-alias>` or `--all`.
- `update-index --all` refreshes all registered indexes in deterministic
  local-alias order.
- If one index fails during `--all`, Ritebook continues updating the remaining
  indexes, reports failed local aliases to stderr, and returns a non-zero exit
  code after the batch completes.
- `--force` repairs consumer-managed source and cache state only. It does not run
  publisher-side index discovery or regenerate `ritebook-index.json`.
- Explicit force also permits schema-v1 registry recovery. Validate saved aliases,
  source locations, and source types; rebuild selected entries from fresh
  committed content with newly discovered canonical branches. Do not reuse or
  delete paths from legacy entries, or infer provenance for their cached bytes.
- Preserve failed legacy entries verbatim alongside successful rebuilt entries.
  Keep schema v1 until every entry has been rebuilt in that run, then atomically
  write schema v2. Ordinary consumers reject incomplete recovery. Rerun
  `indexes update --all --force` after resolving failures to complete recovery.
- Malformed JSON, unsupported versions, duplicate aliases, invalid aliases, and
  unsafe source locators fail before Git or registry mutation. Force is not a
  general registry salvage mode.

### R5 — Publisher index metadata

The publisher index schema, published-name contract, and catalog path model are
defined by the shared catalog contract. The registry validates that complete
contract when adding, updating, or reading a cached index. It uses `index.name`
as the default local alias while preserving the publisher-owned value separately
when the consumer chooses `--alias`.

### R6 — Local registry and cache

Ritebook maintains a local consumer registry and cached index contents.

Recommended default location:

```text
~/.config/ritebook/indexes.json
~/.cache/ritebook/registries/<registry-id>/indexes/<local-alias>/<sha256-hex>/ritebook-index.json
~/.cache/ritebook/registries/<registry-id>/git/<source-cache-id>/
```

Tests and automation should be able to override these paths with explicit CLI
options or injected settings so unit tests do not mutate real user state.

Example current registry (schema v2):

The existing registry `name` field stores the local alias; `published_name`
stores publisher-owned metadata; `alias_origin` records how the alias was chosen.

```json
{
  "schema_version": 2,
  "indexes": [
    {
      "name": "platform-skills",
      "published_name": "company-skills",
      "alias_origin": "explicit",
      "source": "git@github.com:company/internal-skills.git",
      "source_type": "git_url",
      "source_cache_path": "/Users/me/.cache/ritebook/registries/<registry-id>/git/<cache-id>",
      "cached_index_path": "/Users/me/.cache/ritebook/registries/<registry-id>/indexes/platform-skills/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/ritebook-index.json",
      "source_revision": "0123456789abcdef0123456789abcdef01234567",
      "source_branch": "refs/heads/main",
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
  "alias_origin": "explicit",
  "source": "/absolute/path/to/internal-skills",
  "source_type": "local_git_repo",
  "source_cache_path": null,
  "cached_index_path": "/Users/me/.cache/ritebook/registries/<registry-id>/indexes/platform-skills-local/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/ritebook-index.json",
  "source_revision": "0123456789abcdef0123456789abcdef01234567",
  "source_branch": "refs/heads/main",
  "index_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "source_schema_version": 1,
  "skill_count": 12,
  "added_at": "2026-07-08T18:20:00Z",
  "updated_at": "2026-07-08T18:20:00Z"
}
```

Registry provenance follows the
[Shared Catalog Contract](shared-catalog-contract-spec.md):

- `source_revision` is required and stores the full commit object ID whose root
  index was validated.
- `source_branch` is required and stores the canonical `refs/heads/...` branch
  selected during registration or explicit legacy recovery.
- `index_digest` is required and binds `cached_index_path` to the exact validated
  index bytes.
- Ordinary reads reject schema-v1 registries with guidance to run explicit force
  recovery. Recovery creates new bindings from validated committed content; it
  does not infer provenance for old bytes or silently migrate on first use.
- Schema-v2 entries require `alias_origin`. Recovered legacy aliases are retained
  as explicit aliases, independently of the freshly discovered published name.

#### Registry ownership and locking

- Registry snapshots use a shared POSIX lock; add, update, recovery, and cleanup
  use an exclusive lock. Acquisition is bounded and reports a busy error when
  another operation holds the lock beyond the timeout.
- The write transaction spans reading the registry, preparing Git and cache
  candidates, committing metadata, and cleanup. Registry code does not wait for
  installation or contribution-checkout locks.
- Managed clones and index generations live beneath
  `<cache-root>/registries/<registry-id>/`, where `<registry-id>` is the SHA-256
  hex of the canonical registry path. Sharing a cache root does not grant a
  registry ownership of another registry's namespace.
- The registry replacement remains the commit point. Source or cache cleanup
  failures do not reverse a committed binding.

#### Registry/cache commit protocol

- Cached indexes use content-addressed generations. Ordinary writes treat an
  existing digest path as immutable and verify its exact bytes. Explicit
  `indexes update --force` may atomically replace that path with the validated
  bytes to repair local corruption. The directory name is the lowercase SHA-256
  hex from `index_digest`.
- Every cached read receives the registered digest, reads bytes, verifies the
  digest, and only then runs strict JSON and semantic validation.
- `indexes add --force` and `indexes update` preserve the current registry's
  referenced generation while writing and synchronizing its candidate.
- `indexes update --force` rewrites the validated content-addressed generation even
  when its digest is unchanged, allowing damaged local bytes to be repaired before
  the registry commit remains or becomes authoritative.
- The deterministic registry file is the commit record. Ritebook writes and
  synchronizes a uniquely named same-directory temporary registry file, then
  atomically replaces `indexes.json` so readers see either the old entry or the new
  entry, never a partially written entry.
- Before replacement, the temporary registry file receives POSIX mode `0600` where
  supported so newly written user-owned registry state is private.
- Registry readers reject legacy entries containing standard-URL user-info and
  direct users to remove and regenerate the unsafe registration.
- If candidate cache writing or registry replacement fails, the previous registry
  entry continues to reference its unchanged generation. Ritebook attempts to
  discard the unreferenced candidate without changing the reported commit failure.
- Candidate and abandoned-generation cleanup is best-effort. The registry atomic
  replacement result remains authoritative and cleanup failure never rewrites or
  masks a successful registry commit.
- Forced Git URL updates apply the same rule to managed clones: failed candidates
  are best-effort discarded, and a superseded clone is discarded only after a
  successful registry commit and only when no other alias still references it.
- A process interruption may leave an unreferenced generation or adapter-owned
  temporary file. The next add or update for that local alias preserves the
  registry-referenced generation and the current candidate while deterministically
  removing other content-addressed generations and temporary files. Registry
  writes similarly remove abandoned adapter-owned registry temporary files.
- Cleanup never deletes legacy cache paths or files outside the expected
  content-addressed alias directory. Such paths remain readable until a successful
  registration or update switches the registry to a generated path.

### R7 — Duplicate behavior

- Duplicate skill names are allowed across different indexes.
- Duplicate skill names are also allowed within one index when their relative
  skill paths differ, such as `backend/code-review` and `frontend/code-review`.
- Valid relative skill paths contain one segment (`<skill>`) or two segments
  (`<collection>/<skill>`). Consumer validation rejects an index that uses the
  same first segment as both a root skill and a collection.
- A skill's relative `path` is its identity and resolution key within an index;
  `skills[].name` is metadata and is not a fallback selector.
- Consumer validation rejects C0 controls (`U+0000`–`U+001F`), DEL (`U+007F`),
  and C1 controls (`U+0080`–`U+009F`) in `skills_root`, `skills[].path`,
  `skills[].skill_file`, and `skills[].description`. Existing ASCII identifier
  validation provides the same protection for index and skill names.
- Valid Unicode descriptions outside those control ranges are preserved unchanged.
- The local alias plus relative skill path is the namespace boundary.
- Installation references skills as `<local-alias>/<skill-path>` in the
  separate `skill_installation` slice.
- Duplicate local aliases are not allowed unless the user explicitly
  replaces the existing registration.
- Local `--alias` exists primarily to resolve published-name collisions.

### R8 — Git source behavior

#### Git URL sources

- Ritebook manages its own cached clone.
- `indexes add` clones the repository into Ritebook's cache area.
- `indexes update` refreshes that managed clone from the remote.
- `indexes update --force` clones the remembered source into a fresh uniquely named
  registry-owned path, validates and caches from that clone, then atomically
  switches the registry binding. It does not delete the prior clone while another
  registry alias references the same path.
- Advancing mutable refs in the managed clone does not replace the previous
  registry/cache binding until the candidate commit and index are validated and
  persisted coherently.
- Registration records the canonical remote branch; normal refresh follows
  that saved branch. Reading a bound commit does not require it to be checked
  out. Rewritten refs do not invalidate an existing binding while its commit
  object remains available.
- If a bound commit is not available in the managed clone, Ritebook may fetch the
  remembered source to recover that exact object. If recovery fails, downstream
  use fails safely rather than substituting a current ref.
- Authentication is delegated to the user's existing Git setup, such as SSH keys,
  credential helpers, or configured Git access.
- Standard URLs containing authority user-info are rejected before Git or
  filesystem mutation. This includes username-only, password/token, and
  percent-encoded forms; scp-like SSH sources remain supported.
- Source identifiers displayed by the CLI are credential-redacted first and then
  have any terminal control characters rendered as visible deterministic escapes.
  A remembered source cannot inject additional output lines or ANSI formatting.
- Ritebook surfaces a stable, generic Git failure without exposing raw subprocess
  stdout or stderr, which may contain credentials.

#### Local Git repository sources

- Ritebook validates that the path appears to be a Git repository.
- Ritebook does not own or mutate the local repository. Registration requires
  a checked-out branch to record canonical retrieval metadata; refresh reads
  the saved branch without checking it out.
- `indexes add` and `indexes update` reject staged, unstaged, or untracked changes and
  provide guidance to commit or discard them.
- `indexes update --force` does not change that ownership boundary; it re-reads the
  clean committed repository without deleting or modifying it.
- Ritebook reads root `ritebook-index.json` from the selected commit object without
  checking out, resetting, or cleaning the user-owned repository.
- Whether the local repository is up to date is the user's responsibility.
- Ritebook does not snapshot local repositories. A missing repository or bound
  commit fails safely and requires the user to restore it or explicitly refresh
  the registration from a new clean committed state.

### R9 — CLI and workflow requirements

Registry commands:

```bash
uv run ritebook indexes add --source <git-url-or-local-git-repo> [--alias <local-alias>] [--force]
uv run ritebook indexes update <local-alias> [--force]
uv run ritebook indexes update --all [--force]
uv run ritebook indexes list
```

Potential test/automation path overrides:

```bash
uv run ritebook indexes add \
  --source <source> \
  --registry-path <path> \
  --cache-root <path>

uv run ritebook indexes update <local-alias> \
  [--force] \
  --registry-path <path> \
  --cache-root <path>

uv run ritebook indexes update \
  --all \
  [--force] \
  --registry-path <path> \
  --cache-root <path>

uv run ritebook indexes list \
  --registry-path <path>

uv run ritebook skills list \
  [--index <local-alias>] \
  [--show-description] \
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
ritebook: error: local alias platform-skills already exists; use --force to replace it
ritebook: error: ritebook-index.json was not found at the repository root
ritebook: error: unsupported index schema_version: 2
Failed to update 1 index(es): platform-skills
```

## Implementation and Verification Evidence

### Project structure

- [`src/ritebook/features/index_registry/application/`](../../src/ritebook/features/index_registry/application/)
  owns use cases, ports, DTOs, and application errors.
- [`src/ritebook/features/index_registry/adapters/`](../../src/ritebook/features/index_registry/adapters/)
  owns the feature CLI and outbound I/O.
- [`tests/unit/features/index_registry/`](../../tests/unit/features/index_registry/)
  mirrors feature ownership; [`tests/integration/`](../../tests/integration/)
  and [`tests/e2e/`](../../tests/e2e/) verify real local workflows.
- `src/ritebook/adapters/inbound/cli/parser.py` defines command arguments;
  `src/ritebook/adapters/inbound/cli/adapter.py` dispatches to feature CLI facades;
  `src/ritebook/cli.py` wires dependencies.

Publisher catalog metadata lives in
`src/ritebook/features/publisher/domain/catalog.py`; its JSON writer lives in
`src/ritebook/features/publisher/adapters/outbound/json_index/writer.py`.

### Conventions

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

### Testing strategy

#### Publisher index metadata tests

- Publisher output includes index metadata with a valid published name.
- Generated JSON remains deterministic except for timestamp.
- Missing or invalid published names are rejected where appropriate.

#### Add index application tests

- Adds a Git URL source and caches validated index contents.
- Adds a local Git repository source and caches validated index contents.
- Persists the candidate commit and exact-index digest as one binding.
- Rejects dirty local repositories before caching or registry mutation.
- Uses the published name as the default local alias.
- Allows a local alias without changing the published name.
- Refuses duplicate local aliases without `force`.
- Replaces duplicate local aliases with `force`.

#### Update index application tests

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
- Propagates `--force` for one-alias and all-alias updates.
- Rebuilds Git URL sources through fresh managed clones and repairs cached index
  bytes even when the validated digest is unchanged.
- Preserves the prior coherent binding and discards the fresh candidate when a
  forced update fails.
- Discards a superseded managed clone only when no other registry alias references
  its exact path, while never discarding a local repository source.
- Legacy recovery integration tests exercise one-alias and all-alias forced
  rebuilding for Git URLs and local repositories, partial failure and retry, and
  empty registries. Filesystem tests cover unsafe sources, duplicate aliases,
  malformed entries, and failed registry replacement. Docker E2E verifies the
  installed CLI's legacy rejection, explicit recovery, and subsequent listing.

#### List indexes application tests

- Lists registered index summaries in deterministic local-alias order.
- Returns an empty result for an empty registry.

#### List skills tests

- Application tests cover all-index and filtered listing, deterministic ordering,
  duplicate names at distinct paths, empty results, unknown aliases, provenance
  verification, and the absence of Git calls.
- Cached-index reader tests cover schema-v1 validation, required descriptions,
  unsafe paths, control characters, digest mismatches, and ordinary Unicode.
- CLI tests cover argument mapping, stable tree output, opt-in descriptions,
  visible control escapes, empty output, and concise errors.

#### Adapter tests

- JSON index reader rejects invalid JSON, missing root metadata, unsupported schema
  versions, missing `skills`, malformed entries, absolute paths, and `..`
  traversal paths.
- JSON index reader accepts root and collected skill paths and rejects schema-v1
  paths with three or more segments or a mixed root-skill/collection path set.
- Filesystem registry writes deterministic `indexes.json` and preserves unrelated
  entries.
- Index cache writes complete synchronized `ritebook-index.json` generations
  before registry metadata can reference them.
- Content-addressed cache generations preserve the registry-referenced bytes until
  the registry commit succeeds and recover abandoned adapter-owned artifacts on the
  next mutation.
- Ordinary registry readers reject schema-v1 registries and missing provenance;
  cache readers detect digest mismatches.
- Git adapter invokes Git non-interactively and reports clone/fetch failures
  clearly.
- Git adapter forced refreshes use fresh registry-owned clone paths and cleanup
  rejects paths outside the expected managed-clone namespace.
- Index cache forced writes replace damaged bytes at an existing validated
  content-addressed path.
- Git adapter rejects standard-URL user-info before Git or managed-cache mutation,
  preserves scp-like SSH support, and does not expose credential-bearing Git
  output.
- Registry persistence rejects unsafe source values and writes replacement state
  with POSIX mode `0600` where supported.

#### CLI tests

- `indexes add` maps CLI args into application command DTOs.
- `indexes update` maps CLI args into application command DTOs.
- `update-index --all` maps CLI args into application command DTOs.
- `indexes update` rejects missing or conflicting target modes.
- `indexes list` maps CLI args into application command DTOs.
- `skills list` maps filtering, registry-path, and description flags into its
  application command DTO.
- `indexes list` prints deterministic non-empty output and a concise empty
  registry message.
- `indexes list` defensively removes URL user-info from displayed sources.
- Success output includes local alias and skill count.
- Error output is concise and user-facing.

### Commands and validation

Run focused tests through the Makefile, then the complete verification gate:

```bash
PYTEST_ADDOPTS='tests/unit/features/index_registry' make test
make verify
```

## Constraints and Execution Boundaries

### Binding constraints

- Support `indexes add` and `indexes update` for index registration and refresh.
- Support `indexes list` for registered index metadata.
- Support offline `skills list` browsing from verified cached indexes.
- Support both Git URLs and local Git repository paths.
- Require root-level `ritebook-index.json`.
- Cache the current index contents locally.
- Bind cached index contents to the selected full Git commit and exact-index
  SHA-256 digest according to
  [Shared Catalog Contract](shared-catalog-contract-spec.md).
- Use publisher index metadata as the default local alias.
- Allow `--alias` to resolve published-name collisions without rewriting
  publisher metadata.
- Namespace skills by local alias and relative skill path.
- Validate that every cached schema-v1 skill path has the form `<skill>` or
  `<collection>/<skill>` at add, update, and cached-index read boundaries.
- Preserve the previous cached index when `indexes update` fails validation.
- Reject dirty local Git repositories before binding an index.
- Continue after per-index failures during `update-index --all`.

### Changes requiring specification approval

- Adding installation behavior to the registry slice; installation remains
  governed by `skill-installation-spec.md`.
- Adding remote non-Git HTTP indexes.
- Adding trust signatures, approvals, lockfiles, or policy enforcement.
- Changing install path conventions.

### Exclusions and prohibited behavior

- Assume an index file outside the repository root for this milestone.
- Mutate user-owned local repositories during add/update.
- Infer missing provenance from a mutable branch, tag, or working-tree `HEAD`.
- Print secrets, Git credentials, raw index contents, or raw skill file contents
  in errors.
- Treat duplicate skill names across different indexes or at distinct paths in one
  index as an error.
- Read live Git sources, mutate registry/cache state, or repair provenance while
  listing skills.
- Read raw `SKILL.md` contents while listing skills.
- Add installation side effects, live refresh, script-oriented output formats, or
  search behavior to `skills list` without an approved specification change.

## Acceptance Checks

| ID | Requirement | Conditions and action | Expected observable result | Verification method |
| --- | --- | --- | --- | --- |
| AC1 | R1 | Add a valid Git URL or clean local Git repository with a root schema-v1 index. | Ritebook validates committed index bytes, records the full commit and digest, writes an immutable cached generation, and commits one coherent registry entry. | Add-index application, Git adapter, cache, registry, and JSON-reader tests. |
| AC2 | R1 | Add an invalid, dirty, unsafe-credential, duplicate-alias, or over-deep source, with and without `--force`. | Invalid sources fail before coherent state changes; duplicate aliases require explicit replacement; published names remain unchanged by local aliases. | Boundary and failure-path tests. |
| AC3 | R2 | List an empty or populated registry. | Output is deterministic by local alias, includes remembered metadata, and prints the documented empty result without source mutation. | List-index application and CLI tests. |
| AC4 | R3 | List all or one cached index, with and without descriptions, while sources are offline. | Verified cached skills render in deterministic tree order; unknown aliases fail; descriptions are opt-in; empty results print `No skills found`; no Git or raw `SKILL.md` reads occur. | List-skills application, cached-reader, and CLI tests. |
| AC5 | R4 | Update one or all indexes, with and without `--force`, across successful and failing refresh, validation, or persistence paths. | Successful updates atomically replace the binding; forced Git URL updates use fresh managed clones and repair same-digest cache bytes; failures preserve the previous coherent state; superseded clones remain while referenced by another alias; `--all` continues deterministically and returns non-zero after reporting failures. | Update-index application, CLI, cache, Git-adapter, integration, and E2E tests. |
| AC6 | R5 | Add, update, or read publisher schema-v1 metadata. | The complete shared catalog contract is validated, publisher `index.name` is preserved, and local alias selection remains consumer-owned. | Publisher metadata and JSON-reader tests. |
| AC7 | R6 | Write a candidate cache generation and registry replacement, including simulated failures, forced repair, and concurrent readers. | Cache generations remain content-addressed and immutable during ordinary writes; explicit force repair may replace damaged bytes with validated bytes at the same digest path; the synchronized registry file is the atomic commit record; failed candidates do not invalidate referenced state. | Filesystem registry and index-cache tests. |
| AC8 | R7 | Register duplicate published names or skill names at distinct aliases or paths. | Distinct local aliases and catalog paths remain valid; only duplicate local aliases require refusal or explicit replacement. | Application and reader duplicate tests. |
| AC9 | R8 | Use Git URL and local repository sources, including dirty, missing, detached, unavailable, or credential-bearing cases. | Ritebook uses committed objects without mutating user repositories, rejects unsafe or unavailable state, and never infers required provenance from mutable refs. | Git-source adapter tests. |
| AC10 | R9 | Invoke each documented registry and skill-list command and path override. | Arguments map to the owning use case and produce concise documented success or actionable error output. | CLI parser and adapter tests. |
| AC11 | R1-R9 | Run the documented implementation handoff gates. | Formatting, linting, type checking, import contracts, non-E2E tests, package build, and Docker E2E all succeed. | Commands recorded under Implementation and Verification Evidence. |
| AC12 | R4, R6 | Force-update a schema-v1 registry, including partial failure and retry. | Saved aliases and safe sources rebuild into validated schema-v2 bindings; failed registrations remain saved; legacy paths stay untouched; ordinary reads remain strict. | Recovery integration, filesystem boundary, and installed-wheel Docker E2E tests. |
| AC13 | R6 | Hold a registry writer lock, then attempt another snapshot; derive cache paths for two registries sharing one alias and cache root. | The competing read fails busy after its bounded timeout; each registry receives a distinct cache namespace derived from its canonical path. | Filesystem registry lock tests and adapter-level cache-path checks. |

## Assumptions

- Git URLs and clean local Git repositories remain the supported index sources.
- Publisher schema version `1` and the shared commit-and-digest binding remain the
  compatibility baseline.
- Material unresolved assumptions: None.

## Open Questions

None.
