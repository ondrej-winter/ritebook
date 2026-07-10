# Implementation Plan: Consumer List Skills

## Overview

Implement the consumer-facing `ritebook list-skills` workflow defined in
`docs/specs/list-skills-spec.md`. The command will list skill names from locally
cached registered indexes, grouped under effective index names, without
performing Git/network operations or scanning raw skill directories.

## Goal

Add an offline-first CLI workflow that reads the existing local index registry
and cached `ritebook-index.json` files, returning deterministic tree-shaped
output for all registered indexes or one selected effective index.

## Deliverables

- New `list-skills` application DTOs and result shapes in
  `src/ritebook/features/index_registry/application/dtos/index_registry.py`.
- New inbound application port:
  `src/ritebook/features/index_registry/application/ports/list_skills.py`.
- New outbound cached index reader contract:
  `src/ritebook/features/index_registry/application/ports/cached_index_reader.py`.
  Keep this distinct from the existing source index reader so cached, offline
  listing cannot accidentally reuse source/Git-oriented add/update workflows.
- Application use case:
  `src/ritebook/features/index_registry/application/use_cases/list_skills.py`.
- JSON cached-index reading support in
  `src/ritebook/features/index_registry/adapters/outbound/json_index/reader.py`.
- CLI support in:
  - `src/ritebook/adapters/inbound/cli/parser.py`
  - `src/ritebook/adapters/inbound/cli/commands.py`
  - `src/ritebook/adapters/inbound/cli/adapter.py`
  - `src/ritebook/cli.py`
- Tests for application behavior, JSON cached-index validation, CLI
  mapping/output, and docs update.
- README documentation for `list-skills`.

## Success Criteria

- `uv run ritebook list-skills` prints all locally cached registered indexes and
  skill names in deterministic tree form.
- `uv run ritebook list-skills --index-name <effective-name>` lists only the
  selected index while preserving the `Indexes` root and index node.
- `--registry-path` overrides the local registry file for tests/automation.
- Unknown index names fail with a concise `ritebook: error: ...` message.
- Missing, unreadable, malformed, or unsupported cached index files fail with
  clear user-facing errors.
- Empty registries or selected cached indexes with no skills print
  `No skills found`.
- No Git source port is injected into or called by the list-skills use case.
- Unit tests cover application, adapter, and CLI behavior.
- README documents the command.
- Final checks pass: `uv run ruff format .`, `uv run ruff check .`,
  `uv run mypy .`, `uv run pytest`.

## Architecture Decisions

- Keep implementation inside the existing `index_registry` feature slice because
  `list-skills` consumes registered index metadata and cached index paths.
- Keep filesystem and JSON parsing in the outbound `json_index` adapter; the
  application use case only coordinates registry lookup and cached-index reading
  through ports.
- Use a dedicated `CachedIndexReaderPort` for cached skill listing instead of
  extending `IndexSourceReaderPort`. The source reader remains responsible for
  validating publisher indexes from prepared source repositories for add/update.
- Reuse existing `IndexRegistryPort.list()` / `get()` as the source of registered
  indexes.
- Add application-owned DTOs for skill summaries and grouped index results;
  preserve path and `skill_file` values in DTOs for future workflows, but render
  only skill names in v1 CLI output.
- Preserve empty selected-index groups in the application result when an index is
  selected and has no skills; the CLI decides that a zero total skill count prints
  `No skills found`.
- Render the tree in the CLI adapter, not in the application layer.
- Keep output deterministic in the application result: indexes sorted by
  effective name and skills sorted by skill name.
- Do not change publisher index schema.
- Do not contact Git or network during `list-skills`.

## Progress Tracking

Update task and checkpoint checkboxes as implementation progresses. Keep this
plan current automatically during implementation without requiring separate user
prompts for status updates.

## Task List

### Phase 1: Application Boundary

#### Task 1: Add List Skills DTOs ✅

**Description:** Add command/result DTOs and skill summary types to the existing
index registry DTO module.

**Acceptance criteria:**

- [x] `ListSkillsCommand` accepts optional `index_name` and optional
      `registry_path`.
- [x] `index_name`, when present, uses existing index-name validation.
- [x] `CachedSkillSummary` or equivalent carries `name`, `path`, `skill_file`,
      and optional `title`.
- [x] `ListedIndexSkills` or equivalent groups skills under an effective index
      name.
- [x] `ListSkillsResult` contains grouped index results.
- [x] DTOs reject empty names/paths and malformed required fields.
- [x] New DTOs are exported from the application DTO package consistently with
      existing public-import patterns.

**Verification:**

- [x] `uv run pytest tests/unit/features/index_registry/application/test_index_registry_dtos.py`

**Dependencies:** None

**Files likely touched:**

- `src/ritebook/features/index_registry/application/dtos/index_registry.py`
- `src/ritebook/features/index_registry/application/dtos/__init__.py`
- `tests/unit/features/index_registry/application/test_index_registry_dtos.py`

**Estimated scope:** Small

#### Task 2: Define List Skills Ports ✅

**Description:** Add the inbound `ListSkillsPort` and a dedicated outbound
`CachedIndexReaderPort` for reading cached skill entries from a cached index file
path.

**Acceptance criteria:**

- [x] `ListSkillsPort.execute(command: ListSkillsCommand) -> ListSkillsResult`
      exists.
- [x] `CachedIndexReaderPort.read_skills(cached_index_path: str) ->
      tuple[CachedSkillSummary, ...]` or an equivalent explicitly named method
      exists.
- [x] Cached index reader port accepts a cached index path string and returns
      validated skill summaries.
- [x] Port signatures use application DTOs/simple primitives only, not `Path`,
      raw JSON dictionaries, or framework types.
- [x] Ports are exported from the index registry application ports package.
- [x] The cached reader port remains separate from `IndexSourceReaderPort`.

**Verification:**

- [x] `uv run mypy src/ritebook/features/index_registry/application`

**Dependencies:** Task 1

**Files likely touched:**

- `src/ritebook/features/index_registry/application/ports/list_skills.py`
- `src/ritebook/features/index_registry/application/ports/cached_index_reader.py`
- `src/ritebook/features/index_registry/application/ports/__init__.py`

**Estimated scope:** Small

### Checkpoint: Application Contracts

- [x] DTOs and ports type-check.
- [x] Application boundary exposes no JSON/filesystem/Git details.

### Phase 2: Application Use Case

#### Task 3: Implement List Skills Use Case with Fakes ✅

**Description:** Implement `ListSkills` orchestration by reading registered
indexes, optionally filtering by effective index name, and reading each selected
cached index through the cached-index reader port.

**Acceptance criteria:**

- [x] With no `index_name`, lists all registry entries in deterministic
      effective-name order.
- [x] With `index_name`, reads only the selected registry entry.
- [x] Unknown effective index name raises the existing or new user-facing
      unknown-index application error.
- [x] Skills within each index are sorted deterministically by skill name.
- [x] Empty registry returns an empty result, not an error.
- [x] Empty cached indexes are represented with empty `skills` tuples in the
      application result; the CLI prints `No skills found` when total skills are
      zero.
- [x] Use case does not depend on Git source, cache writer, filesystem, JSON,
      argparse, or environment APIs.
- [x] Tests construct the use case with only registry and cached-reader fakes,
      proving no Git source or cache writer dependency is required.

**Verification:**

- [x] `uv run pytest tests/unit/features/index_registry/application/test_list_skills.py`

**Dependencies:** Tasks 1-2

**Files likely touched:**

- `src/ritebook/features/index_registry/application/use_cases/list_skills.py`
- `src/ritebook/features/index_registry/application/use_cases/__init__.py`
- `tests/unit/features/index_registry/application/test_list_skills.py`
- `tests/unit/features/index_registry/application/fakes.py`

**Estimated scope:** Medium

### Checkpoint: Application Behavior

- [x] Focused application tests pass.
- [x] No Git/network-capable dependency is present in the list-skills use case.
- [x] Unknown index, empty registry, and deterministic ordering are covered.

### Phase 3: Cached Index Reader Adapter

#### Task 4: Extend JSON Index Reader for Cached Skill Listing ✅

**Description:** Add cached-index reading behavior to the existing JSON index
reader adapter while preserving existing published-index validation behavior used
by add/update.

**Acceptance criteria:**

- [x] Reads a cached `ritebook-index.json` by exact cached index file path.
- [x] Rejects missing/unreadable files with clear `InvalidPublishedIndexError` or
      an equivalent index-registry adapter error.
- [x] Rejects invalid JSON and non-object payloads.
- [x] Rejects missing/unsupported `schema_version`.
- [x] Rejects missing/malformed `skills`.
- [x] Rejects malformed skill entries.
- [x] Rejects unsafe absolute, backslash, or parent-traversal `path` and
      `skill_file` values using existing path-safety rules.
- [x] Returns skill summaries including `name`, `path`, `skill_file`, and
      optional `title`.
- [x] Does not read raw `SKILL.md` files.
- [x] Error messages are concise and safe; they do not include raw JSON payloads,
      skill file contents, secrets, or credentials.

**Verification:**

- [x] `uv run pytest tests/unit/features/index_registry/adapters/outbound/test_json_index_reader.py`

**Dependencies:** Tasks 1-2

**Files likely touched:**

- `src/ritebook/features/index_registry/adapters/outbound/json_index/reader.py`
- `src/ritebook/features/index_registry/adapters/outbound/json_index/__init__.py`
- `tests/unit/features/index_registry/adapters/outbound/test_json_index_reader.py`

**Estimated scope:** Medium

### Checkpoint: Adapter Behavior

- [x] JSON reader tests cover both existing add/update index reading and cached
      skill listing.
- [x] Adapter errors remain concise and safe; no raw index contents or skill file
      contents are printed.

### Phase 4: CLI and Composition

#### Task 5: Add `list-skills` Parser, CLI Mapping, and Tree Rendering ✅

**Description:** Extend the CLI adapter to parse `list-skills`, map arguments to
`ListSkillsCommand`, and render the default human-readable tree.

**Acceptance criteria:**

- [x] Parser accepts `list-skills [--index-name <effective-name>]
      [--registry-path <path>]`.
- [x] CLI maps arguments exactly into `ListSkillsCommand`.
- [x] Empty result prints `No skills found`.
- [x] Non-empty output begins with `Indexes`.
- [x] First-level children are effective index names.
- [x] Second-level children are skill names only; titles/paths are not shown.
- [x] Filtered output preserves the same tree shape.
- [x] Tree connector characters match the spec examples.
- [x] Application/adapter errors render as `ritebook: error: ...`.

**Verification:**

- [x] `uv run pytest tests/unit/adapters/inbound/cli/test_adapter.py`

**Dependencies:** Tasks 1-4

**Files likely touched:**

- `src/ritebook/adapters/inbound/cli/parser.py`
- `src/ritebook/adapters/inbound/cli/commands.py`
- `src/ritebook/adapters/inbound/cli/adapter.py`
- `tests/unit/adapters/inbound/cli/test_adapter.py`

**Estimated scope:** Medium

#### Task 6: Wire List Skills in Composition Root ✅

**Description:** Instantiate `ListSkills` in `src/ritebook/cli.py` using the
existing registry adapter and JSON index reader adapter, then inject it into the
CLI adapter.

**Acceptance criteria:**

- [x] `main()` wires `ListSkills(registry=..., cached_index_reader=...)` or
      equivalent.
- [x] Existing `add-index`, `update-index`, `list-indexes`, `publish-index`, and
      `lint-skills` wiring remains intact.
- [x] Composition root keeps default path resolution inside adapters/bootstrap,
      not application use cases.
- [x] `ListSkills` is exported from the index registry application use cases
      package consistently with existing use-case exports.

**Verification:**

- [x] `uv run mypy src/ritebook/cli.py src/ritebook/adapters/inbound/cli src/ritebook/features/index_registry`
- [x] `uv run pytest tests/unit/adapters/inbound/cli/test_adapter.py`

**Dependencies:** Task 5

**Files likely touched:**

- `src/ritebook/cli.py`
- `src/ritebook/adapters/inbound/cli/adapter.py`

**Estimated scope:** Small

### Checkpoint: CLI Flow

- [x] CLI tests cover argument mapping, tree output, filtered output, empty
      output, and error translation.
- [x] Composition root type-checks.
- [x] Existing commands still pass CLI tests.

### Phase 5: Documentation and Final Validation

#### Task 7: Update README for `list-skills`

**Description:** Document the new consumer command, its offline cached-index
behavior, filtering option, registry-path override, and empty output behavior.

**Acceptance criteria:**

- [ ] README includes `uv run ritebook list-skills`.
- [ ] README includes `uv run ritebook list-skills --index-name <effective-name>`.
- [ ] README includes `--registry-path` test/automation override for
      `list-skills`.
- [ ] README states `list-skills` reads local cached indexes only and does not
      fetch Git remotes.
- [ ] README shows or describes the tree output shape.
- [ ] README no longer says listing is not part of the milestone.

**Verification:**

- [ ] Documentation reviewed against `docs/specs/list-skills-spec.md`.

**Dependencies:** Tasks 1-6

**Files likely touched:**

- `README.md`

**Estimated scope:** Small

#### Task 8: Run Final Quality Gate

**Description:** Run project formatting, linting, typing, and tests after
implementation and documentation are complete.

**Acceptance criteria:**

- [ ] Formatting applied.
- [ ] Ruff lint passes.
- [ ] Mypy passes.
- [ ] Pytest passes.

**Verification:**

- [ ] `uv run ruff format .`
- [ ] `uv run ruff check .`
- [ ] `uv run mypy .`
- [ ] `uv run pytest`

**Dependencies:** Tasks 1-7

**Files likely touched:** None unless checks reveal fixes.

**Estimated scope:** Small

### Checkpoint: Complete

- [ ] `list-skills` works for all registered cached indexes.
- [ ] `list-skills --index-name` works for one effective index.
- [ ] Empty cases print `No skills found`.
- [ ] Output is deterministic and tree-shaped.
- [ ] No Git or network operations happen during listing.
- [ ] Tests and README are updated.
- [ ] Full local quality gate passes.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Accidentally reusing add/update source-reading path and contacting Git | High | Define list-skills use case dependencies narrowly: registry + cached-index reader only; test with fakes that no Git source exists. |
| JSON reader changes regress add/update validation | Medium | Extend existing adapter tests rather than replacing behavior; run focused JSON reader tests. |
| Tree rendering has subtle ordering/connector bugs | Medium | Cover multi-index, single-index, last-child, and empty cases in CLI tests. |
| Missing cached file errors expose unsafe raw paths or contents | Medium | Use concise adapter/application errors; never print raw JSON or skill file contents. |
| Empty selected index semantics become ambiguous | Low | Treat no skills in selected cached index as `No skills found`, per spec. |
| Repository-style index names containing `/` may affect tree display | Low | Treat effective index name as a label only; no path interpretation during rendering. |

## Open Questions and Assumptions

- No open questions from the spec; it states v1 intent and output shape are
  confirmed.
- Decision: add a dedicated `CachedIndexReaderPort` rather than extending
  `IndexSourceReaderPort`, because cached offline listing and source repository
  validation have different semantics and failure modes.
- Decision: the application result may preserve selected indexes with empty skill
  tuples; CLI rendering is responsible for converting any zero-total-skill result
  into `No skills found`.
- Assumption: the existing `UnknownIndexNameError` from the index registry
  application errors, if present, should be reused for unknown `--index-name`.
- Assumption: the existing `InvalidPublishedIndexError` can remain the
  adapter-facing error for malformed cached index files, unless naming clarity
  suggests adding a subclass/alias during implementation.
- Assumption: cached skill entries should carry optional `title` internally but
  CLI v1 must not display it.

## Parallelization Opportunities

- After Tasks 1-2 define DTOs and ports, Task 3 application tests/use case and
  Task 4 adapter tests can be developed independently.
- CLI work should wait until DTO/result shape stabilizes.
- README can be updated once the CLI shape and output examples are final.
- Final quality gate must be sequential after implementation and docs.

## Handoff Notes for Implementers

- Start with application DTOs/ports so the cached-index reader and use case have
  stable contracts.
- Prefer focused tests before implementation for each task.
- Keep `list-skills` application code free of Git, JSON, filesystem, subprocess,
  argparse, and environment imports.
- Do not use live network access in default tests.
- Preserve existing CLI output style: concise success/empty lines and
  `ritebook: error: ...` for user-facing runtime errors.
- Run focused checks while iterating, then the full local quality gate before
  handoff.