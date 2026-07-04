# Implementation Plan: Publisher Skill Index Generation

## Overview

Ritebook will add its first publisher-side workflow for internal agent skill
maintainers. A maintainer will run an explicit CLI command against one skills
root, Ritebook will recursively discover directories containing `SKILL.md`, and
it will write a deterministic, reviewable `ritebook-index.json` file using
schema version `1`.

This plan implements the specification in
`docs/specs/publisher-index-generation.md` while preserving the repository's
hexagonal vertical-slice direction.

## Goal

Deliver the MVP publisher workflow:

```bash
uv run ritebook publish-index --skills-root <path> --output ritebook-index.json
```

The command must produce a valid JSON index listing every discovered skill under
the explicit skills root.

## Deliverables

- `skill_catalog` vertical feature slice under `src/ritebook/features/`.
- Pure domain catalog types and invariants independent of CLI, filesystem, and
  JSON concerns.
- Application DTOs, inbound use case/port, and outbound ports for discovery and
  writing.
- Filesystem discovery adapter that skips hidden directories by default.
- JSON index writer adapter with two-space pretty output and schema v1 fields.
- CLI adapter and package entry point for `ritebook publish-index`.
- Unit tests mirroring the source structure under
  `tests/unit/features/skill_catalog/`.
- README usage documentation for the publisher command.
- Passing local validation: formatting, linting, type checking, tests, and build.

## Constraints

- Require exactly one explicit `--skills-root`; do not implicitly scan a whole
  repository.
- Default `--output` to `ritebook-index.json`.
- Skip hidden directories in the MVP.
- Do not require mandatory metadata inside `SKILL.md`.
- Do not add hashes, signatures, policy enforcement, consumer list/sync/install
  commands, or multi-root support.
- Keep filesystem traversal, CLI parsing, JSON serialization, and user-facing
  path validation in adapters or bootstrap code.
- Keep business/catalog logic in domain and application layers.
- Use Python 3.13, `uv`, `ruff`, `mypy --strict`, and `pytest`.

## Architecture Decisions

- **Feature slice:** implement under
  `src/ritebook/features/skill_catalog/`.
- **CLI framework:** use standard-library `argparse` for the MVP to avoid adding
  a dependency before the CLI grows.
- **Timestamp source:** inject a clock/callable at the application boundary so
  tests can assert deterministic `generated_at` values. `generated_at` should be
  serialized as a timezone-aware UTC ISO 8601 timestamp with a `Z` suffix.
- **Path representation:** index entries use POSIX-style paths relative to the
  explicit skills root. The top-level `skills_root` field should be a stable,
  human-reviewable lexical string derived from the explicit user input. Avoid
  resolving to machine-specific absolute paths unless the user supplied an
  absolute path.
- **Output path semantics:** relative `--output` values follow normal CLI
  behavior and are interpreted relative to the current working directory.
- **Title extraction:** keep Markdown H1 extraction in the filesystem adapter
  because it reads file contents; domain receives only the optional title value.
- **Missing title:** omit the `title` field when no Markdown H1 is available.
- **CLI error format:** use standard-library `argparse` default formatting for
  parse errors. Use concise custom runtime errors for invalid filesystem inputs.

## Task List

### Phase 1: Foundation

#### Task 1: Add skill catalog domain model

**Description:** Create pure domain concepts for discovered skill entries and
catalogs, including deterministic ordering and basic invariants.

**Acceptance criteria:**

- [ ] `SkillEntry` represents `name`, `path`, `skill_file`, and optional `title`
      without importing adapter or framework modules.
- [ ] `SkillCatalog` or equivalent domain object stores schema version `1`,
      generated timestamp, scanned root string, and sorted skill entries.
- [ ] Skill entries are sorted deterministically by relative path or another
      documented stable key.

**Verification:**

- [ ] Domain unit tests cover entry creation, relative paths, optional title, and
      deterministic ordering.
- [ ] Run `uv run pytest tests/unit/features/skill_catalog/domain`.

**Dependencies:** None

**Files likely touched:**

- `src/ritebook/features/skill_catalog/domain/*.py`
- `tests/unit/features/skill_catalog/domain/test_*.py`

**Estimated scope:** Small/Medium

#### Task 2: Add application DTOs, ports, and publish-index use case

**Description:** Define the application boundary for publishing an index and
orchestrate discovery plus writing through outbound ports.

**Acceptance criteria:**

- [ ] Application DTOs exist under `application/dtos/`, such as
      `PublishIndexCommand` and `PublishIndexResult`.
- [ ] Application ports exist under `application/ports/`.
- [ ] An inbound application port or service exposes the publish-index use case.
- [ ] Outbound ports describe skill discovery and index writing without
      filesystem or JSON-specific types leaking into the core.
- [ ] The use case accepts an injectable timestamp source for deterministic
      tests.
- [ ] `generated_at` is represented as a timezone-aware UTC value and serialized
      with a `Z` suffix by the JSON boundary.
- [ ] The result includes discovered skill count and output path for CLI success
      output.

**Verification:**

- [ ] Application tests use fakes for discovery and writing ports.
- [ ] Run `uv run pytest tests/unit/features/skill_catalog/application`.
- [ ] Run `uv run mypy .` during iteration.

**Dependencies:** Task 1

**Files likely touched:**

- `src/ritebook/features/skill_catalog/application/dtos/*.py`
- `src/ritebook/features/skill_catalog/application/ports/*.py`
- `src/ritebook/features/skill_catalog/application/use_cases/*.py`
- `tests/unit/features/skill_catalog/application/test_*.py`

**Estimated scope:** Medium

### Checkpoint: Foundation

- [ ] `uv run pytest tests/unit/features/skill_catalog/domain tests/unit/features/skill_catalog/application`
- [ ] `uv run mypy .`
- [ ] Confirm no adapter/framework imports leaked into domain/application.

### Phase 2: Outbound Adapters

#### Task 3: Add filesystem skill discovery adapter

**Description:** Implement recursive discovery under an explicit skills root
using `pathlib`, finding directories containing `SKILL.md`, deriving relative
paths, extracting optional first Markdown H1 titles, and skipping hidden
directories.

**Acceptance criteria:**

- [ ] Missing or non-directory roots are rejected with adapter-level errors
      suitable for CLI translation.
- [ ] Unreadable roots or unreadable `SKILL.md` files are translated into clear
      adapter-level errors without exposing file contents.
- [ ] Discovery recursively finds every non-hidden directory containing
      `SKILL.md`.
- [ ] Hidden directories are not traversed by default.
- [ ] Returned entries use relative POSIX-style paths from the skills root.
- [ ] `title` is the first Markdown H1 when available and absent otherwise.
- [ ] Skill file contents are not logged or printed.

**Verification:**

- [ ] Filesystem adapter tests use `tmp_path` and cover nested skills, hidden
      directories, relative path handling, missing root, and title extraction.
- [ ] Run `uv run pytest tests/unit/features/skill_catalog/adapters/outbound`.

**Dependencies:** Task 2

**Files likely touched:**

- `src/ritebook/features/skill_catalog/adapters/outbound/filesystem/adapter.py`
- `src/ritebook/features/skill_catalog/adapters/outbound/filesystem/exceptions.py`
- `tests/unit/features/skill_catalog/adapters/outbound/test_filesystem*.py`

**Estimated scope:** Medium

#### Task 4: Add JSON index writer adapter

**Description:** Serialize the catalog representation to schema v1 JSON with
two-space indentation and stable ordering.

**Acceptance criteria:**

- [ ] Writer outputs valid JSON with `schema_version`, `generated_at`,
      `skills_root`, and `skills` fields.
- [ ] Output is pretty-printed with two-space indentation.
- [ ] Entry fields match the spec: `name`, `path`, `skill_file`, and optional
      `title`; entries without a Markdown H1 omit `title` rather than writing
      `null`.
- [ ] Existing output file is overwritten only when the explicit command/use case
      is run.
- [ ] Serialization is deterministic for unchanged catalog input.

**Verification:**

- [ ] JSON writer tests parse generated JSON and assert schema version, field
      names, order, optional title behavior, and indentation.
- [ ] Run `uv run pytest tests/unit/features/skill_catalog/adapters/outbound`.

**Dependencies:** Task 2

**Files likely touched:**

- `src/ritebook/features/skill_catalog/adapters/outbound/json_index/writer.py`
- `tests/unit/features/skill_catalog/adapters/outbound/test_json*.py`

**Estimated scope:** Small/Medium

### Checkpoint: Core Adapters

- [ ] `uv run pytest tests/unit/features/skill_catalog`
- [ ] `uv run ruff check .`
- [ ] `uv run mypy .`
- [ ] Manually inspect generated JSON shape against the spec.

### Phase 3: CLI and Package Wiring

#### Task 5: Add CLI inbound adapter and console script entry point

**Description:** Provide `ritebook publish-index` as the first user-facing
command, mapping CLI arguments to the application command and translating
adapter/application errors into clear user-facing output.

**Acceptance criteria:**

- [ ] `pyproject.toml` exposes a `ritebook` console script.
- [ ] CLI requires `--skills-root` for `publish-index`.
- [ ] CLI supports `--output` with default `ritebook-index.json`.
- [ ] Relative `--output` paths are interpreted relative to the current working
      directory.
- [ ] Missing or invalid skills root produces a clear error and non-zero exit
      code.
- [ ] CLI parse errors use `argparse` default formatting.
- [ ] Success output includes discovered skill count and output path.
- [ ] CLI wiring constructs filesystem discovery adapter, JSON writer adapter,
      and publish-index use case in an adapter/bootstrap boundary.

**Verification:**

- [ ] CLI adapter tests cover argument mapping, missing required argument,
      invalid root error handling, and success output.
- [ ] Run `uv run pytest tests/unit/features/skill_catalog/adapters/inbound`.
- [ ] Run a manual smoke check with a temporary local skills directory.

**Dependencies:** Tasks 3 and 4

**Files likely touched:**

- `src/ritebook/features/skill_catalog/adapters/inbound/cli.py`
- `src/ritebook/cli.py` or `src/ritebook/__main__.py`
- `pyproject.toml`
- `tests/unit/features/skill_catalog/adapters/inbound/test_cli*.py`

**Estimated scope:** Medium

#### Task 6: Update README usage documentation

**Description:** Document the new publisher command and basic expected workflow
for maintainers.

**Acceptance criteria:**

- [ ] README includes the `uv run ritebook publish-index --skills-root <path>
      --output ritebook-index.json` example.
- [ ] README explains that `--skills-root` is explicit and that output defaults
      to `ritebook-index.json`.
- [ ] README notes the index is intended to be reviewed and committed by
      maintainers.
- [ ] README does not document out-of-scope consumer install/sync/list behavior.

**Verification:**

- [ ] Documentation review against the spec's publisher workflow.

**Dependencies:** Task 5, or can be drafted in parallel after the CLI shape is
finalized.

**Files likely touched:**

- `README.md`

**Estimated scope:** XS

### Checkpoint: User-Facing Workflow

- [ ] Focused CLI tests pass.
- [ ] Manual CLI smoke test produces expected JSON.
- [ ] README command matches actual CLI behavior.

### Phase 4: Final Quality Gate

#### Task 7: Run full validation and fix any issues

**Description:** Run the complete local validation suite required by project
rules and the spec, then fix root causes for any failures.

**Acceptance criteria:**

- [ ] Formatting, linting, type checking, tests, and build all pass.
- [ ] No architecture boundary violations are introduced.
- [ ] No out-of-scope functionality is included.

**Verification:**

```bash
uv run ruff format .
uv run ruff check .
uv run mypy .
uv run pytest
uv build
```

**Dependencies:** Tasks 1-6

**Files likely touched:** Any files needed to resolve validation failures.

**Estimated scope:** Small, unless validation reveals design issues.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| CLI tests become coupled to parser internals | Medium | Test observable exit codes, stdout/stderr, and command-to-DTO behavior rather than private parser structure. |
| Timestamp makes output nondeterministic | Medium | Inject timestamp source in application tests; production wiring supplies current UTC time. |
| Path formatting differs across platforms | Medium | Use `pathlib` internally and convert index entry paths to POSIX-style relative paths. |
| Domain/application layers import adapter details | High | Keep ports in application, adapters under `adapters/`, and review boundaries at checkpoints. |
| Hidden directory traversal edge cases | Medium | Test hidden root children and nested hidden directories explicitly with `tmp_path`. |
| Optional `title` encoding regresses | Medium | Omit `title` when unavailable; cover the behavior in JSON writer tests and documentation review. |
| `skills_root` becomes machine-specific | Medium | Preserve a stable lexical form based on user input and avoid resolving relative paths to absolute paths. |
| Output path semantics surprise users | Low | Treat relative `--output` values as current-working-directory relative and document the behavior. |

## Assumptions

- `docs/specs/publisher-index-generation.md` is the authoritative implementation
  target.
- Standard-library `argparse` is acceptable for the first CLI.
- A console script can be added to `pyproject.toml`.
- Tests should be created under `tests/unit/features/skill_catalog/` even though
  current tests are minimal.
- Missing Markdown H1 titles are omitted from JSON entries.
- The displayed `skills_root` value is a stable lexical form based on the
  user-provided `--skills-root` value.
- CLI parse errors use `argparse` default formatting.

## Resolved Plan Review Decisions

1. For skills without a Markdown H1, omit the `title` field from the JSON entry.
2. Preserve a stable lexical `skills_root` representation based on the explicit
   user input; do not resolve relative paths to machine-specific absolute paths.
3. Use `argparse` default formatting for CLI parse errors and concise custom
   runtime errors for invalid filesystem inputs.

## Implementation Order

1. Domain model and tests.
2. Application DTOs, ports, use case, and tests.
3. Filesystem scanner and tests.
4. JSON writer and tests.
5. CLI adapter, console script, and tests.
6. README update.
7. Full quality gate.