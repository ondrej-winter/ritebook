# Implementation Plan: Publisher Index Generation

## Overview

Ritebook will complete the publisher-side skill catalog workflow described in
`docs/specs/publisher-index-generation.md`. The MVP lets maintainers run a
validation-only `lint-skills` workflow and a `publish-index` workflow that refuses
to write `ritebook-index.json` unless every discovered `SKILL.md` has a valid
Agent Skill header. The existing `skill_catalog` vertical slice already contains
catalog domain models, recursive filesystem discovery, JSON index writing,
`publish-index` orchestration, CLI wiring, and focused tests. The remaining work
is to add shared header validation, expose it through `lint-skills`, make
`publish-index` reuse the same validation precondition, update documentation, and
run the full local quality gate.

## Confirmed Decisions

- The implementation plan is stored at
  `docs/plans/publisher-index-generation-plan.md`.
- Discovery starts from the explicit `--skills-root`; every non-hidden directory
  under that root containing `SKILL.md` is a skill, including deeply nested
  directories.
- Validation issue output is deterministic and path scoped, using plain lines
  such as `relative/path/SKILL.md: message`.
- Root inspection, filesystem, and other adapter-level errors may keep the
  existing `ritebook: error: ...` CLI style.
- `PyYAML` is approved as a runtime dependency because the spec requires
  `yaml.safe_load()` for frontmatter parsing.

## Architecture Decisions

- Keep the feature inside the existing vertical slice:
  `src/ritebook/features/skill_catalog/`.
- Keep domain catalog concepts in `domain/`, application orchestration and
  contracts in `application/`, and CLI/filesystem/JSON details in `adapters/`.
- Keep YAML/frontmatter parsing in an outbound adapter. Pass plain parsed data or
  path-scoped parse issues into application validation.
- Share validation between `lint-skills` and `publish-index` through one
  application use case or service so the rules cannot drift.
- Keep `publish-index` deterministic for unchanged input except for the
  documented generation timestamp.
- Do not add consumer install, sync, list commands, content hashes, signatures,
  multiple roots, hidden-directory scanning, or configurable output paths in this
  milestone.

## Progress Tracking

Update task and checkpoint checkboxes as implementation progresses. Keep this
plan current automatically during implementation without requiring separate user
prompts for status updates.

## Task List

### Phase 1: Validation Foundation

#### Task 1: Add `PyYAML` Runtime Dependency

**Description:** Add `PyYAML` as a runtime dependency for bounded Agent Skill
frontmatter parsing.

**Acceptance criteria:**

- [ ] `pyproject.toml` includes `PyYAML` under `[project].dependencies`.
- [ ] `uv.lock` is updated consistently.
- [ ] YAML parsing is not treated as a development-only dependency.

**Verification:**

- [ ] `uv sync`
- [ ] `uv run python -c "import yaml; print(yaml.__name__)"`

**Dependencies:** None

**Files likely touched:**

- `pyproject.toml`
- `uv.lock`

**Estimated scope:** Small

#### Task 2: Model Skill Validation Issues and Reports

**Description:** Add application DTOs that represent validation inputs, issues,
and results so CLI, lint, and publish workflows can share deterministic,
path-scoped validation semantics.

**Acceptance criteria:**

- [ ] Validation issues include a relative `skill_file` path and a rule/message.
- [ ] Validation reports can answer whether validation succeeded.
- [ ] Validation reports expose deterministic issue ordering.
- [ ] DTOs reject invalid empty paths or messages where appropriate.

**Verification:**

- [ ] Focused DTO tests pass, or equivalent use-case tests cover DTO behavior.
- [ ] `uv run pytest tests/unit/features/skill_catalog/application`

**Dependencies:** None

**Files likely touched:**

- `src/ritebook/features/skill_catalog/application/dtos/skill_validation.py`
- `src/ritebook/features/skill_catalog/application/dtos/__init__.py`
- `tests/unit/features/skill_catalog/application/test_skill_validation.py`

**Estimated scope:** Small

#### Task 3: Implement Pure Header Contract Validation

**Description:** Add validation logic for the Agent Skill header contract over
plain parsed data. Filesystem access, Markdown file reading, and YAML parsing
must stay outside this validation core.

**Acceptance criteria:**

- [ ] Frontmatter/header data must be a mapping.
- [ ] `name` is required.
- [ ] `name` must be a string using valid kebab-case: 1-64 characters,
      lowercase ASCII letters, digits, and hyphens only; no leading/trailing
      hyphen; no consecutive hyphens.
- [ ] `name` must match the parent skill directory name derived from the skill
      path. For a root-level `SKILL.md`, compare against the explicit root
      directory basename already used by discovery.
- [ ] `description` is required, must be a non-empty string, and must be at most
      1024 characters.
- [ ] `metadata` is required and must be a mapping.
- [ ] `metadata.version` is required and must be a string.
- [ ] `metadata.dependencies` is required and must be a mapping.
- [ ] `metadata.dependencies.tools` is required and must be a list.
- [ ] `metadata.dependencies.skills` is required and must be a list.
- [ ] Dependency list items may be strings for this milestone.
- [ ] Validation issues identify the relative skill file path and violated rule
      without including full file contents.
- [ ] Application/domain validation logic does not import `yaml`, `pathlib.Path`,
      or filesystem APIs.

**Verification:**

- [ ] Tests cover a valid header.
- [ ] Tests cover missing or non-mapping frontmatter data.
- [ ] Tests cover invalid names and name/path mismatches.
- [ ] Tests cover missing or invalid description.
- [ ] Tests cover missing metadata, missing version, missing dependencies, and
      invalid dependency list types.
- [ ] `uv run pytest tests/unit/features/skill_catalog/application`

**Dependencies:** Task 2

**Files likely touched:**

- `src/ritebook/features/skill_catalog/application/use_cases/validate_skill_headers.py`
- `src/ritebook/features/skill_catalog/application/dtos/skill_validation.py`
- `tests/unit/features/skill_catalog/application/test_skill_header_validation.py`

**Estimated scope:** Medium

### Checkpoint: Validation Core

- [ ] Application validation tests pass.
- [ ] Validation logic has no filesystem or YAML dependency leaks.
- [ ] Issue ordering and formatting are deterministic.

### Phase 2: Filesystem Validation Adapter

#### Task 4: Add Filesystem Frontmatter Reader/Parser Adapter

**Description:** Extend the outbound filesystem capability to discover skill
files using the existing traversal rules and parse bounded YAML frontmatter into
plain application DTOs, reporting parse and delimiter issues path-by-path.

**Acceptance criteria:**

- [ ] Traversal requires an explicit root and uses the same recursive rules as
      `publish-index`.
- [ ] Hidden directories under the skills root are skipped by default.
- [ ] Output order is deterministic.
- [ ] Only discovered `SKILL.md` files are read.
- [ ] Frontmatter must open with `---` on the first line.
- [ ] Frontmatter must include a closing `---` delimiter before the Markdown body.
- [ ] The adapter uses `yaml.safe_load()` only on the bounded frontmatter block.
- [ ] Adapter output contains parsed plain data or validation issues without full
      file contents.
- [ ] Missing, non-directory, or unreadable roots produce clear adapter errors.

**Verification:**

- [ ] Filesystem adapter tests cover recursive discovery and relative paths.
- [ ] Filesystem adapter tests cover hidden directory skipping.
- [ ] Filesystem adapter tests cover missing frontmatter, missing closing
      delimiter, malformed YAML, and non-mapping YAML.
- [ ] Filesystem adapter tests cover root inspection errors.
- [ ] `uv run pytest tests/unit/features/skill_catalog/adapters/outbound`

**Dependencies:** Tasks 1-3

**Files likely touched:**

- `src/ritebook/features/skill_catalog/adapters/outbound/filesystem/adapter.py`
- `src/ritebook/features/skill_catalog/adapters/outbound/filesystem/frontmatter.py`
- `src/ritebook/features/skill_catalog/adapters/outbound/filesystem/__init__.py`
- `tests/unit/features/skill_catalog/adapters/outbound/test_filesystem_skill_discovery.py`
- `tests/unit/features/skill_catalog/adapters/outbound/test_filesystem_skill_headers.py`

**Estimated scope:** Medium

### Phase 3: Lint Use Case and CLI

#### Task 5: Add `lint-skills` Application Port and Use Case

**Description:** Add a validation-only use case that discovers/parses skill
headers, applies the shared validation rules, and returns a deterministic report
without writing any index file.

**Acceptance criteria:**

- [ ] `lint-skills` validates the same discovered skills as `publish-index`.
- [ ] The use case succeeds only when all discovered skills are valid.
- [ ] The use case returns validated skill count on success.
- [ ] The use case returns deterministic issue lists on failure.
- [ ] The use case has no dependency on the index writer.

**Verification:**

- [ ] Application tests use fakes for validation input discovery/parsing.
- [ ] Tests cover success with validated skill count.
- [ ] Tests cover invalid skills producing a failure report.
- [ ] Tests prove no index writer interaction is part of lint behavior.
- [ ] `uv run pytest tests/unit/features/skill_catalog/application`

**Dependencies:** Tasks 2-4

**Files likely touched:**

- `src/ritebook/features/skill_catalog/application/ports/lint_skills.py`
- `src/ritebook/features/skill_catalog/application/use_cases/lint_skills.py`
- `src/ritebook/features/skill_catalog/application/dtos/lint_skills.py`
- `src/ritebook/features/skill_catalog/application/ports/__init__.py`
- `src/ritebook/features/skill_catalog/application/use_cases/__init__.py`
- `src/ritebook/features/skill_catalog/application/dtos/__init__.py`
- `tests/unit/features/skill_catalog/application/test_lint_skills.py`

**Estimated scope:** Medium

#### Task 6: Add `lint-skills` CLI Command

**Description:** Extend the CLI adapter and composition root so users can run
`uv run ritebook lint-skills --skills-root <path>`.

**Acceptance criteria:**

- [ ] `lint-skills` requires explicit `--skills-root`.
- [ ] On success, it prints concise validated skill count and exits `0`.
- [ ] On validation issues, it prints deterministic `relative/path/SKILL.md:
      message` lines to stderr and exits non-zero.
- [ ] On root inspection/read errors, it prints a clear `ritebook: error: ...`
      message and exits non-zero.
- [ ] It does not write or update `ritebook-index.json`.

**Verification:**

- [ ] CLI tests cover argument mapping.
- [ ] CLI tests cover missing `--skills-root`.
- [ ] CLI tests cover success output.
- [ ] CLI tests cover validation failure output.
- [ ] CLI tests cover root error translation.
- [ ] `uv run pytest tests/unit/features/skill_catalog/adapters/inbound/test_cli.py`

**Dependencies:** Task 5

**Files likely touched:**

- `src/ritebook/features/skill_catalog/adapters/inbound/cli.py`
- `src/ritebook/cli.py`
- `tests/unit/features/skill_catalog/adapters/inbound/test_cli.py`

**Estimated scope:** Medium

### Checkpoint: Lint Workflow

- [ ] Focused lint workflow tests pass.
- [ ] CLI behavior is deterministic for valid and invalid skill fixtures.
- [ ] `lint-skills` does not depend on or invoke JSON index writing.

### Phase 4: Publish Validation Precondition

#### Task 7: Integrate Shared Validation into `publish-index`

**Description:** Update `PublishIndex` so it validates discovered skill headers
using the same validation flow as `lint-skills` before writing
`ritebook-index.json`.

**Acceptance criteria:**

- [ ] `publish-index` calls the shared validation flow before index writing.
- [ ] `publish-index` refuses to call `SkillIndexWriterPort.write_index(...)`
      when validation fails.
- [ ] CLI emits path-scoped validation issues and exits non-zero on validation
      failure.
- [ ] Valid skills continue to produce schema v1 JSON with existing deterministic
      behavior.
- [ ] Existing publish tests are updated rather than replaced unnecessarily.

**Verification:**

- [ ] Application test proves writer is not called on validation failure.
- [ ] CLI test proves publish validation failure output and non-zero exit.
- [ ] Existing JSON writer tests still pass.
- [ ] `uv run pytest tests/unit/features/skill_catalog/application/test_publish_index.py tests/unit/features/skill_catalog/adapters/inbound/test_cli.py`

**Dependencies:** Tasks 5-6

**Files likely touched:**

- `src/ritebook/features/skill_catalog/application/use_cases/publish_index.py`
- `src/ritebook/features/skill_catalog/adapters/inbound/cli.py`
- `src/ritebook/cli.py`
- `tests/unit/features/skill_catalog/application/test_publish_index.py`
- `tests/unit/features/skill_catalog/adapters/inbound/test_cli.py`

**Estimated scope:** Medium

### Phase 5: Documentation and Final Validation

#### Task 8: Update README for Lint Workflow and Validation Guarantees

**Description:** Document `lint-skills`, shared validation behavior, and publish
refusal-on-invalid behavior.

**Acceptance criteria:**

- [ ] README shows `uv run ritebook publish-index --skills-root <path>`.
- [ ] README shows `uv run ritebook lint-skills --skills-root <path>`.
- [ ] README states invalid skills prevent index writes.
- [ ] README remains concise and aligned with
      `docs/specs/publisher-index-generation.md`.

**Verification:**

- [ ] Documentation review against the publisher index generation spec.

**Dependencies:** Tasks 5-7

**Files likely touched:**

- `README.md`

**Estimated scope:** Small

#### Task 9: Run Full Local Quality Gate and Build

**Description:** Run final validation using the project’s configured tooling.

**Acceptance criteria:**

- [ ] Formatting is applied.
- [ ] Ruff lint passes.
- [ ] Mypy strict type checking passes.
- [ ] Pytest passes.
- [ ] Package build succeeds.

**Verification:**

- [ ] `uv run ruff format .`
- [ ] `uv run ruff check .`
- [ ] `uv run mypy .`
- [ ] `uv run pytest`
- [ ] `uv build`

**Dependencies:** Tasks 1-8

**Files likely touched:** None unless checks reveal fixes.

**Estimated scope:** Small

### Checkpoint: Complete

- [ ] `lint-skills` validates every discovered `SKILL.md` and exits non-zero on
      invalid skills.
- [ ] `publish-index` reuses the same validation flow and refuses to write on
      invalid skills.
- [ ] Generated index schema remains version `1` and includes documented fields.
- [ ] Missing or invalid input paths produce clear user-facing errors.
- [ ] Relevant unit tests cover discovery, validation, index generation, JSON
      output, and CLI argument mapping.
- [ ] Full local quality gate and build pass.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Validation responsibility leaks into the filesystem adapter | Medium | Keep YAML parsing in the adapter, but keep contract validation in application logic over plain DTOs. |
| `publish-index` and `lint-skills` validation rules drift | High | Make both workflows call the same validation use case or service. |
| `SkillDiscoveryPort` becomes overloaded | Medium | Add a separate validation/header reader port if needed instead of forcing discovery to own validation. |
| CLI error handling becomes inconsistent | Medium | Use explicit validation report/error types and centralize issue rendering in the CLI adapter. |
| Root-level `SKILL.md` name matching is ambiguous | Medium | Preserve existing root skill behavior and compare the header `name` to the explicit root directory basename already used by discovery. |
| PyYAML typing creates mypy friction | Low | Keep `yaml.safe_load()` behind adapter-local type guards or narrow casts. |

## Assumptions

- The existing `SkillCatalog` and `SkillEntry` model should remain the canonical
  index domain model.
- The current canonical output filename, `ritebook-index.json`, remains fixed and
  no `--output` argument is added.
- A root directory may itself be a skill when it contains `SKILL.md`, and nested
  skill folders remain valid discoveries.
- Validation issues should not include full skill file contents.
- Default tests must not rely on live services, network access, global developer
  state, or current wall-clock time.

## Parallelization Opportunities

- After Tasks 2-3 define validation DTOs and rules, adapter tests for filesystem
  parsing and CLI tests for lint output can be drafted in parallel with the use
  case implementation.
- Documentation updates can be done independently after CLI behavior is settled.
- Final quality gate and build must be sequential after implementation and docs
  are complete.

## Handoff Notes for Implementers

- Start with focused tests for validation behavior before modifying publish or
  CLI flows.
- Preserve the existing adapter and test naming style.
- Keep changes small and reviewable; avoid unrelated cleanup.
- Run focused checks while iterating, then the full local quality gate before
  handoff.