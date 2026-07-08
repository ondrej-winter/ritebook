# Implementation Plan: Consumer Git Index Registry

## Overview

Ritebook will implement the first consumer-facing index registry workflow from
`docs/specs/consumer-git-index-registry.md`. The milestone lets users register a
Git-backed skill index with `add-index`, cache the current root
`ritebook-index.json` locally, and refresh that cached copy later with
`update-index`. This establishes the consumer-side catalog foundation for future
`list-skills` and `install-skill` workflows without implementing listing or
installation yet.

## Goal

Implement the consumer-side foundation for registering and refreshing Git-backed
Ritebook skill indexes, while keeping Git, filesystem, JSON parsing, and user
config/cache path mechanics outside the application core.

## Deliverables

- Publisher index metadata support: generated `ritebook-index.json` includes
  required `index.name` metadata.
- New `index_registry` vertical feature slice with application DTOs, ports, use
  cases, and outbound adapters.
- CLI commands:
  - `ritebook add-index --source <git-url-or-local-git-repo> [--name <effective-name>] [--force] [--registry-path <path>] [--cache-root <path>]`
  - `ritebook update-index --name <effective-name> [--registry-path <path>] [--cache-root <path>]`
- Unit tests for publisher metadata, add/update application flows, JSON index
  validation, filesystem registry/cache persistence, Git source handling, and CLI
  mapping.
- README/config documentation updates for consumer registry usage and local
  storage paths.
- Full quality gate and build pass before handoff.

## Success Criteria

- Publisher-generated indexes include required `index.name` metadata.
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
- Relevant unit tests cover application behavior, JSON validation,
  registry/cache persistence, Git source handling, and CLI argument mapping.
- `uv run ruff format .`, `uv run ruff check .`, `uv run mypy .`,
  `uv run pytest`, and `uv build` pass before handoff.

## Architecture Decisions

- Add a new vertical slice under `src/ritebook/features/index_registry/`.
- Preserve the existing top-level CLI adapter pattern in
  `src/ritebook/adapters/inbound/cli/` and wire new application ports in
  `src/ritebook/cli.py`.
- Treat publisher index schema as schema version `1` with an added required
  `index.name` metadata object rather than bumping to schema `2`, matching the
  spec's "schema v1 extension" option. This is an intentional compatibility
  break for consumer registration: `add-index` rejects legacy schema v1 indexes
  that do not include `index.name` instead of guessing a default name.
- Keep local effective index names as the registry namespace. Skill names may
  duplicate across indexes.
- Require `publish-index --index-name <name>` for newly generated indexes. Do
  not infer publisher index identity from the current directory or Git remote.
- Use one canonical kebab-case identifier validator for skill names and index
  names: 1-64 lowercase ASCII letters, digits, and hyphens; no leading/trailing
  hyphen; no consecutive hyphens. The implementation must place this helper in a
  reusable core location rather than duplicating regexes across publisher,
  linter, and index registry code.
- Keep application path values as strings at public DTO/port boundaries for this
  milestone. Adapters and composition may use `pathlib.Path` internally, but they
  must normalize path values to strings before crossing into application DTOs or
  ports.
- Use injected path settings and clocks for deterministic tests; default user
  paths are resolved only in composition/bootstrap or adapters.
- Preserve cached index contents on failed `update-index` validation by
  validating into a temporary/loaded representation before replacing cache files
  or registry metadata.
- Use best-effort local-file consistency for successful validation: read and
  validate the refreshed index, write cached index content via temp file and
  replace, then write registry metadata via temp file and replace. If registry
  persistence fails after cache replacement, surface a clear error, leave the
  previous registry intact, and accept orphaned cache content as an MVP cleanup
  concern.
- `--force` replacement overwrites the registry entry and cached index for the
  effective name, but does not eagerly prune old managed Git or cache directories
  unless the implementation naturally reuses the same paths. Add cache pruning as
  deferred maintenance work.
- Derive managed Git cache IDs deterministically from the original source string
  with a secret-safe hash-based identifier, such as a SHA-256 prefix. Do not place
  raw Git URLs, credentials, or tokens in directory names or user-facing errors.
- Git adapter should shell out to `git` non-interactively via `subprocess`, never
  through shell heredocs or interactive prompts, and surface sanitized
  user-facing failures.

## Constraints and Boundaries

Always:

- Support `add-index` and `update-index` only for this milestone.
- Support both Git URLs and local Git repository paths.
- Require root-level `ritebook-index.json`.
- Cache the current index contents locally.
- Use publisher index metadata as the default index name.
- Allow local name override to avoid effective-name collisions.
- Namespace duplicate skill names by effective index name.
- Preserve the previous cached index when `update-index` fails validation.

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

## Implementation Status

Completed on 2026-07-08. The consumer Git index registry slice has been implemented end-to-end, including publisher index.name metadata, add-index and update-index CLI commands, the index_registry application slice, JSON/filesystem/Git outbound adapters, README updates, and final validation. Final checks passed: uv run ruff format ., uv run ruff check ., uv run mypy ., uv run pytest (134 passed), and uv build.

## Progress Tracking

Update task and checkpoint checkboxes as implementation progresses. Keep this
plan current automatically during implementation without requiring separate user
prompts for status updates.

## Task List

### Phase 1: Publisher Metadata Foundation

#### Task 1: Add Publisher Index Name to Domain and JSON Output

**Description:** Extend the publisher catalog model and JSON writer so newly
generated indexes include required `index.name` metadata while preserving
deterministic output and existing skill entry behavior.

**Acceptance criteria:**

- [x] `SkillCatalog` includes a required stable index name.
- [x] Index name uses the same kebab-case constraints as skill names.
- [x] JSON writer emits:
  ```json
  "index": { "name": "..." }
  ```
- [x] Existing schema version remains `1` unless implementation discovers a
      stronger reason to bump.
- [x] Existing publisher behavior remains deterministic except for
      `generated_at`.

**Verification:**

- [x] `uv run pytest tests/unit/features/publisher/domain tests/unit/features/publisher/adapters/outbound/test_json_index_writer.py`

**Dependencies:** None

**Files likely touched:**

- `src/ritebook/features/publisher/domain/catalog.py`
- `src/ritebook/features/publisher/adapters/outbound/json_index/writer.py`
- `tests/unit/features/publisher/domain/test_catalog.py`
- `tests/unit/features/publisher/adapters/outbound/test_json_index_writer.py`

**Estimated scope:** Medium

#### Task 2: Thread Publisher Index Name Through Publish Use Case and CLI

**Description:** Add required `--index-name` support so `publish-index` can set
the published index name and generated indexes satisfy the new required
metadata.

**Acceptance criteria:**

- [x] `PublishIndexCommand` carries `index_name`.
- [x] `publish-index` CLI requires an explicit `--index-name` to avoid guessing
      repository identity.
- [x] Application validates empty/invalid index names before writing.
- [x] Success output remains concise.
- [x] README and CLI tests document that this is an intentional publisher CLI
      compatibility change.

**Verification:**

- [x] `uv run pytest tests/unit/features/publisher/application tests/unit/adapters/inbound/cli/test_adapter.py`

**Dependencies:** Task 1

**Files likely touched:**

- `src/ritebook/features/publisher/application/dtos/publish_index.py`
- `src/ritebook/features/publisher/application/use_cases/publish_index.py`
- `src/ritebook/adapters/inbound/cli/parser.py`
- `src/ritebook/adapters/inbound/cli/commands.py`
- `tests/unit/features/publisher/application/test_publish_index.py`
- `tests/unit/adapters/inbound/cli/test_adapter.py`

**Estimated scope:** Medium

### Checkpoint: Publisher Metadata

- [x] Publisher output includes required index metadata.
- [x] Existing publish/lint behavior remains compatible except for the
      intentional `publish-index` metadata argument change.
- [x] Focused publisher and CLI tests pass.

### Phase 2: Index Registry Application Core

#### Task 3: Add Index Registry DTOs and Domain-Like Application Types

**Description:** Create application-owned DTOs and application error types for
add/update commands, results, published index payload summaries, registered index
records, source metadata, and path settings.

**Acceptance criteria:**

- [x] DTOs represent Git URL and local Git repo source types without exposing
      adapter implementation details.
- [x] Add command supports `source`, optional `name`, `force`, `registry_path`,
      and `cache_root`.
- [x] Update command supports `name`, `registry_path`, and `cache_root`.
- [x] Registry entries include effective name, published name, source, source
      type, source cache path, cached index path, source schema version, skill
      count, `added_at`, and `updated_at`.
- [x] DTO validation rejects empty names, invalid kebab-case names, invalid
      counts, and empty required paths.
- [x] DTOs use normalized strings for path values at application boundaries;
      adapters may convert to and from `Path` internally.
- [x] Application-specific errors are named and exported for duplicate index
      names, unknown index names, invalid index metadata, and failed registry or
      cache operations that the CLI must render clearly.

**Verification:**

- [x] `uv run pytest tests/unit/features/index_registry/application`

**Dependencies:** Task 1 for published index metadata shape

**Files likely touched:**

- `src/ritebook/features/index_registry/application/dtos/index_registry.py`
- `src/ritebook/features/index_registry/application/errors.py`
- `src/ritebook/features/index_registry/application/dtos/__init__.py`
- `tests/unit/features/index_registry/application/test_index_registry_dtos.py`
- `tests/unit/features/index_registry/application/test_errors.py`

**Estimated scope:** Medium

#### Task 4: Define Index Registry Application Ports

**Description:** Add small application-owned ports for add/update inbound use
cases and outbound source preparation, index reading, registry persistence, and
index cache writing.

**Acceptance criteria:**

- [x] Inbound ports define `AddIndexPort.execute(...)` and
      `UpdateIndexPort.execute(...)`.
- [x] Outbound ports hide Git, JSON, and filesystem details from application
      services.
- [x] Port signatures use application DTOs or simple primitives, not `Path`,
      subprocess results, or JSON dicts.
- [x] Source preparation port can distinguish managed Git URL clones from
      read-only local Git repositories.

**Verification:**

- [x] `uv run mypy src/ritebook/features/index_registry/application`

**Dependencies:** Task 3

**Files likely touched:**

- `src/ritebook/features/index_registry/application/ports/add_index.py`
- `src/ritebook/features/index_registry/application/ports/update_index.py`
- `src/ritebook/features/index_registry/application/ports/git_source.py`
- `src/ritebook/features/index_registry/application/ports/index_source_reader.py`
- `src/ritebook/features/index_registry/application/ports/index_registry.py`
- `src/ritebook/features/index_registry/application/ports/index_cache.py`
- `src/ritebook/features/index_registry/application/ports/__init__.py`

**Estimated scope:** Small

#### Task 5: Implement `AddIndex` Use Case with Fakes

**Description:** Implement add-index orchestration independent of Git, JSON, and
filesystem mechanics.

**Acceptance criteria:**

- [x] Resolves source to a readable repository/index location through outbound
      source port.
- [x] Reads and validates root `ritebook-index.json` through index reader port.
- [x] Uses published index name by default.
- [x] Uses `--name` override when supplied.
- [x] Refuses duplicate effective names unless `force=True`.
- [x] Writes cached index contents under the effective name.
- [x] Upserts registry metadata with injected timestamps.

**Verification:**

- [x] Tests cover Git URL source, local Git repository source, default name,
      override name, duplicate refusal, and forced replacement.
- [x] `uv run pytest tests/unit/features/index_registry/application/test_add_index.py`

**Dependencies:** Tasks 3-4

**Files likely touched:**

- `src/ritebook/features/index_registry/application/use_cases/add_index.py`
- `src/ritebook/features/index_registry/application/use_cases/__init__.py`
- `tests/unit/features/index_registry/application/test_add_index.py`

**Estimated scope:** Medium

#### Task 6: Implement `UpdateIndex` Use Case with Fakes

**Description:** Implement update-index orchestration so registered indexes
refresh from remembered sources and preserve previous cache on validation
failure.

**Acceptance criteria:**

- [x] Looks up existing registry entry by effective name.
- [x] Fails clearly for unknown index names.
- [x] Refreshes managed Git URL sources through source port.
- [x] Reads local Git repository sources without mutating them.
- [x] Validates refreshed root `ritebook-index.json` before replacing cached
      contents.
- [x] Keeps local effective name even if published name changes.
- [x] Leaves previous cached index intact when validation/read fails.

**Verification:**

- [x] Tests cover Git URL refresh, local repo refresh, unknown name, successful
      metadata update, changed published name, and validation failure preserving
      cache.
- [x] `uv run pytest tests/unit/features/index_registry/application/test_update_index.py`

**Dependencies:** Tasks 3-5

**Files likely touched:**

- `src/ritebook/features/index_registry/application/use_cases/update_index.py`
- `tests/unit/features/index_registry/application/test_update_index.py`

**Estimated scope:** Medium

### Checkpoint: Application Core

- [x] Add/update application tests pass with fakes.
- [x] Application layer has no imports from Git, JSON, filesystem, subprocess,
      argparse, or user environment APIs.
- [x] Duplicate and failed-update semantics match the spec.

### Phase 3: Outbound Adapters

#### Task 7: Add JSON Published Index Reader Adapter

**Description:** Implement a JSON reader/validator for root
`ritebook-index.json` that returns application DTOs and validated raw/cacheable
content.

**Acceptance criteria:**

- [x] Requires `ritebook-index.json` at repository root.
- [x] Rejects invalid JSON.
- [x] Rejects unsupported `schema_version`.
- [x] Requires `index.name` and validates kebab-case.
- [x] Rejects legacy schema v1 indexes that omit `index.name` with a clear
      compatibility error instead of inferring a name.
- [x] Requires `skills` array and validates skill entries.
- [x] Rejects absolute paths, backslash paths, and `..` traversal in `path` and
      `skill_file`.
- [x] Returns skill count and deterministic/cacheable JSON content.

**Verification:**

- [x] Adapter tests cover invalid JSON, missing metadata, unsupported schema,
      malformed entries, absolute paths, and traversal paths.
- [x] `uv run pytest tests/unit/features/index_registry/adapters/outbound/test_json_index_reader.py`

**Dependencies:** Tasks 1 and 3-4

**Files likely touched:**

- `src/ritebook/features/index_registry/adapters/outbound/json_index/reader.py`
- `src/ritebook/features/index_registry/adapters/outbound/json_index/__init__.py`
- `tests/unit/features/index_registry/adapters/outbound/test_json_index_reader.py`

**Estimated scope:** Medium

#### Task 8: Add Filesystem Registry and Index Cache Adapters

**Description:** Implement local `indexes.json` registry persistence and cached
index file writing under configurable paths.

**Acceptance criteria:**

- [x] Registry adapter reads missing registry as empty schema version `1`
      registry.
- [x] Registry adapter writes deterministic `indexes.json` with stable ordering.
- [x] Registry adapter preserves unrelated entries on add/update.
- [x] Cache adapter writes current index contents under
      `<cache-root>/indexes/<effective-name>/ritebook-index.json`.
- [x] Cache replacement is atomic enough for local use, e.g. write temp then
      replace.
- [x] Tests cover cache-write success followed by registry-write failure:
      previous registry metadata remains intact, the error is surfaced, and
      orphaned cache content is accepted as deferred cleanup.
- [x] Adapter creates required parent directories.

**Verification:**

- [x] Tests use `tmp_path` and do not mutate real user state.
- [x] `uv run pytest tests/unit/features/index_registry/adapters/outbound/test_filesystem_registry.py tests/unit/features/index_registry/adapters/outbound/test_index_cache.py`

**Dependencies:** Tasks 3-6

**Files likely touched:**

- `src/ritebook/features/index_registry/adapters/outbound/filesystem_registry/adapter.py`
- `src/ritebook/features/index_registry/adapters/outbound/filesystem_registry/__init__.py`
- `src/ritebook/features/index_registry/adapters/outbound/index_cache/adapter.py`
- `src/ritebook/features/index_registry/adapters/outbound/index_cache/__init__.py`
- `tests/unit/features/index_registry/adapters/outbound/test_filesystem_registry.py`
- `tests/unit/features/index_registry/adapters/outbound/test_index_cache.py`

**Estimated scope:** Medium

#### Task 9: Add Git Source Adapter

**Description:** Implement source preparation/refresh for Git URLs and local Git
repositories using non-interactive Git subprocess calls.

**Acceptance criteria:**

- [x] Classifies local paths versus Git URLs deterministically.
- [x] Local source must exist and appear to be a Git repository.
- [x] Local source is never mutated.
- [x] Git URL source clones into `<cache-root>/git/<source-cache-id>/` on add.
- [x] Managed clone cache IDs are deterministic, hash-based, and do not expose raw
      URLs, credentials, tokens, or private host/path details.
- [x] Git URL source refreshes existing managed clone on update or reclones if
      needed.
- [x] Git failures become clear sanitized adapter errors.
- [x] Tests do not require live network access; subprocess invocation is
      faked/mocked.

**Verification:**

- [x] Tests cover local repo validation, Git URL clone command construction,
      refresh command construction, reclone fallback if chosen, and failure
      translation.
- [x] `uv run pytest tests/unit/features/index_registry/adapters/outbound/test_git_source.py`

**Dependencies:** Tasks 3-6

**Files likely touched:**

- `src/ritebook/features/index_registry/adapters/outbound/git/adapter.py`
- `src/ritebook/features/index_registry/adapters/outbound/git/__init__.py`
- `tests/unit/features/index_registry/adapters/outbound/test_git_source.py`

**Estimated scope:** Medium

### Checkpoint: Adapter Layer

- [x] JSON reader, registry/cache, and Git adapter tests pass.
- [x] No default test uses network, real user config/cache, or global Git state.
- [x] Adapter errors are user-facing and do not include secrets or raw index
      contents.

### Phase 4: CLI and Composition Root

#### Task 10: Add `add-index` CLI Command

**Description:** Extend the shared CLI parser/commands adapter to map `add-index`
arguments into the `AddIndexCommand` and render success/errors.

**Acceptance criteria:**

- [x] Parser accepts `add-index --source ... [--name ...] [--force]
      [--registry-path ...] [--cache-root ...]`.
- [x] CLI maps arguments into application DTOs exactly.
- [x] Success output is `Added index <name> with <n> skill(s)`.
- [x] Duplicate effective name error is concise and mentions `--force`.
- [x] Source, JSON, registry, and cache adapter errors render as
      `ritebook: error: ...`.

**Verification:**

- [x] `uv run pytest tests/unit/adapters/inbound/cli/test_adapter.py`

**Dependencies:** Tasks 3-9

**Files likely touched:**

- `src/ritebook/adapters/inbound/cli/parser.py`
- `src/ritebook/adapters/inbound/cli/commands.py`
- `src/ritebook/adapters/inbound/cli/adapter.py`
- `tests/unit/adapters/inbound/cli/test_adapter.py`

**Estimated scope:** Medium

#### Task 11: Add `update-index` CLI Command

**Description:** Extend CLI mapping and output for refreshing an existing
registered index.

**Acceptance criteria:**

- [x] Parser accepts `update-index --name ... [--registry-path ...]
      [--cache-root ...]`.
- [x] CLI maps arguments into `UpdateIndexCommand` exactly.
- [x] Success output is `Updated index <name> with <n> skill(s)`.
- [x] Unknown index and validation failures render clear user-facing errors.

**Verification:**

- [x] `uv run pytest tests/unit/adapters/inbound/cli/test_adapter.py`

**Dependencies:** Task 10

**Files likely touched:**

- `src/ritebook/adapters/inbound/cli/parser.py`
- `src/ritebook/adapters/inbound/cli/commands.py`
- `src/ritebook/adapters/inbound/cli/adapter.py`
- `tests/unit/adapters/inbound/cli/test_adapter.py`

**Estimated scope:** Medium

#### Task 12: Wire Index Registry Use Cases in Composition Root

**Description:** Instantiate new adapters and use cases in `src/ritebook/cli.py`,
including default config/cache path resolution.

**Acceptance criteria:**

- [x] `main()` wires `AddIndex` and `UpdateIndex` with filesystem, JSON, Git,
      registry, cache, and clock dependencies.
- [x] Defaults resolve to `~/.config/ritebook/indexes.json` and
      `~/.cache/ritebook` unless CLI overrides are supplied.
- [x] Environment and user path expansion stays outside application use cases.
- [x] Focused tests cover default path expansion and CLI override handling without
      mutating real user state.
- [x] Existing `lint-skills` and `publish-index` wiring still works.

**Verification:**

- [x] `uv run pytest tests/unit/adapters/inbound/cli/test_adapter.py`
- [x] Focused default path resolver tests, if path resolution is split into a
      helper module.
- [x] `uv run mypy src/ritebook/cli.py src/ritebook/adapters/inbound/cli src/ritebook/features/index_registry`

**Dependencies:** Tasks 10-11

**Files likely touched:**

- `src/ritebook/cli.py`
- Possibly `src/ritebook/adapters/inbound/cli/adapter.py`
- Possibly a small composition/helper module for default registry/cache paths

**Estimated scope:** Small

### Checkpoint: CLI Flow

- [x] CLI unit tests cover add/update argument mapping and output.
- [x] Composition root type-checks.
- [x] Existing publisher/linter CLI behavior still passes tests.

### Phase 5: Documentation and Final Validation

#### Task 13: Update README and Configuration Notes

**Description:** Document publisher index naming, consumer add/update commands,
default local registry/cache paths, and test/automation overrides.

**Acceptance criteria:**

- [x] README shows required `publish-index --index-name <name>` usage.
- [x] README shows `add-index` and `update-index` examples.
- [x] README documents default local registry/cache paths.
- [x] README notes that local Git repositories are read-only from Ritebook's
      perspective.
- [x] README states listing and installation are not part of this milestone.
- [x] README or release-facing notes call out that consumer registration rejects
      legacy schema v1 indexes without `index.name`.

**Verification:**

- [x] Documentation reviewed against `docs/specs/consumer-git-index-registry.md`.

**Dependencies:** Tasks 1-12

**Files likely touched:**

- `README.md`
- Optionally `docs/specs/consumer-git-index-registry.md` only if clarifications
  are needed, not to change scope.

**Estimated scope:** Small

#### Task 14: Run Full Local Quality Gate and Build

**Description:** Run final project validation after implementation and docs are
complete.

**Acceptance criteria:**

- [x] Formatting is applied.
- [x] Ruff lint passes.
- [x] Mypy passes.
- [x] Pytest passes.
- [x] Package build succeeds.

**Verification:**

- [x] `uv run ruff format .`
- [x] `uv run ruff check .`
- [x] `uv run mypy .`
- [x] `uv run pytest`
- [x] `uv build`

**Dependencies:** Tasks 1-13

**Files likely touched:** None unless checks reveal fixes.

**Estimated scope:** Small

### Checkpoint: Complete

- [x] Publisher-generated indexes include required `index.name` metadata.
- [x] `add-index` supports Git URLs and local Git repositories.
- [x] `update-index` refreshes registered indexes from remembered sources.
- [x] Cached index contents are stored locally under effective index name.
- [x] Failed update validation preserves previous cached index.
- [x] Duplicate effective names are refused unless `--force` is used.
- [x] Unit tests cover application, adapters, CLI, and publisher metadata
      updates.
- [x] Full local quality gate and build pass.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Publisher metadata requirement breaks existing `publish-index` users | Medium | Document the new `--index-name` requirement clearly and update CLI tests/README together. |
| Git adapter accidentally mutates user-owned local repos | High | Separate source types in DTOs and tests; local repo path is read-only and never passed to pull/fetch commands. |
| Failed update corrupts cached index | High | Validate refreshed index before cache replacement; use temp writes and update registry after cache write succeeds. |
| Application layer leaks filesystem/Git details | Medium | Keep ports DTO-based and review imports in `features/index_registry/application`. |
| Live Git/network tests become flaky | Medium | Unit-test command construction and failure translation with fake subprocess runner; no live network in default suite. |
| Secrets leak in Git errors | Medium | Sanitize subprocess errors; do not print env, credentials, raw remote URLs with embedded tokens, or raw file contents. |
| Path traversal from malicious index payload | High | JSON reader rejects absolute, backslash, and `..` paths before caching or future install workflows can use them. |

## Open Questions and Assumptions

- Assumption: publisher schema remains `schema_version: 1` with an added required
  `index.name` object, as suggested by the spec. Consumer `add-index` rejects
  older schema v1 index files that omit the metadata.
- Decision: `publish-index` requires `--index-name` rather than inferring a
  default from the current directory. This avoids unstable or surprising
  published names.
- Assumption: `--registry-path` should point to the full `indexes.json` file,
  while `--cache-root` should point to the root cache directory containing
  `indexes/` and `git/`.
- Assumption: Git URL source detection can initially be pragmatic: existing local
  path means local repo; otherwise treat common Git URL forms such as `git@...`,
  `ssh://...`, `https://...`, and `file://...` as cloneable Git sources.
- Decision: `--force` replacement does not eagerly delete old managed Git/cache
  directories. Cleanup/pruning is deferred unless replacement naturally reuses
  the same effective-name cache path.

## Parallelization Opportunities

- After Tasks 3-4 define DTOs and ports, Tasks 5-6 application use cases can be
  developed independently from outbound adapter test drafting.
- Tasks 7-9 can be implemented in parallel after application contracts stabilize.
- CLI tasks should wait until application DTOs and errors are stable.
- Documentation can be updated after CLI shapes are finalized.
- Final quality gate and build must be sequential after implementation and docs
  are complete.

## Handoff Notes for Implementers

- Start with publisher metadata because consumer `add-index` depends on
  `index.name`.
- Prefer focused tests before implementation for each task.
- Keep application use cases free of Git, JSON, filesystem, subprocess, argparse,
  and environment imports.
- Do not use live network access in default tests.
- Preserve existing CLI output style: concise success lines and
  `ritebook: error: ...` for user-facing runtime errors.
- Run focused checks while iterating, then the full local quality gate before
  handoff.