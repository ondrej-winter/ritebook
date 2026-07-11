# Implementation Plan: Consumer Skill Installation

## Overview

Implement the workflows from `docs/specs/install-skill-spec.md`: direct
single-skill installation with `ritebook install-skill` and repository-declared
installation with `ritebook install`. Both workflows resolve skills from already
registered cached Git indexes, copy whole skill directories safely, and persist
deterministic generated installation state.

## Goal

- Support `ritebook install-skill <index-name>/<skill-name> --target <path> [--force]`.
- Support `ritebook install [--file ritebook.toml] [--force]`.
- Resolve install sources from existing local registry entries and cached
  `ritebook-index.json` files.
- Copy whole skill directories while refusing unsafe sources, dangerous targets,
  and accidental overwrites.
- Write deterministic generated state for both direct installs and
  requirements-file installs.

## Deliverables

- New vertical slice: `src/ritebook/features/skill_installation/`.
- Application DTOs, ports, errors, and use cases for direct single-skill install
  and requirements-file install.
- Outbound adapters for source repository resolution, safe filesystem copying,
  TOML requirements reading, direct user installation registry JSON, and repo
  `ritebook.lock` JSON.
- CLI parser, handler, and composition-root wiring for `install-skill` and
  `install`.
- Unit tests mirroring source ownership.
- README updates for commands, `ritebook.toml`, `ritebook.lock`, generated state
  paths, and offline-first behavior.
- Final quality gate evidence.

## Success Criteria

- Direct install copies the selected cached skill directory into an explicit
  target path.
- Requirements install reads `ritebook.toml`, resolves target nicknames/direct
  paths, installs all declared skills, and writes deterministic `ritebook.lock`
  only after successful planned installs.
- Existing targets are refused unless `--force` is passed.
- Direct installs write deterministic user state under
  `~/.config/ritebook/installations.json` by default, with CLI override for
  tests and automation.
- Unknown indexes, unknown skills, malformed TOML, duplicate requirements,
  duplicate targets, unsafe source paths, and dangerous targets fail with clear
  `ritebook: error: ...` messages.
- No installation command fetches, pulls, mutates source repositories, or
  installs from unregistered remotes.
- `uv run ruff format .`, `uv run ruff check .`, `uv run mypy .`,
  `uv run pytest`, and `uv build` pass before handoff.

## Architecture Decisions

- Keep installation behavior in `features/skill_installation/` rather than
  expanding `index_registry`, because installation owns separate persistence,
  source resolution, copy policy, and requirements semantics.
- Reuse the existing index registry as an outbound dependency from the
  installation slice through port-shaped dependencies. Do not import registry
  adapters into application logic.
- Reuse existing `RegisteredIndex`, `IndexSourceType`, and cached skill metadata
  shape where practical, but define installation-owned DTOs for installation
  commands, results, and manifests.
- Keep TOML, JSON, filesystem, Git revision probing, and path traversal handling
  in outbound adapters.
- Keep CLI rendering and argument mapping in `src/ritebook/adapters/inbound/cli/`.
- Use injected clocks for `installed_at`, `locked_at`, and deterministic tests.
- Treat cached index paths and skill paths as untrusted data at filesystem/source
  adapter boundaries.

## Implementation Notes and Boundary Clarifications

- The installation slice should own the application-facing ports used by its use
  cases. When installation needs existing registry behavior, wire adapters in the
  composition root that delegate to the index-registry slice or its published
  contracts. Avoid importing another slice's private use cases, DTO internals, or
  adapters into installation application code.
- Keep application DTOs focused on install intent and manifest state. Existing
  registry/index DTOs may be mapped at adapter boundaries, but installation use
  cases should not depend on transport, JSON, TOML, Git, or filesystem shapes.
- Treat requirements-file installs as a two-stage workflow where practical:
  first build and validate the complete install plan, then perform copies, then
  write `ritebook.lock`. If a late copy fails after some copies have already
  succeeded, do not update the lockfile and surface the partial-copy warning
  required by the spec.
- Split path-safety responsibility deliberately: the TOML reader validates TOML
  shape and target references; application planning rejects duplicate
  requirements and duplicate resolved targets; filesystem/source adapters reject
  dangerous resolved paths, traversal, symlink targets, and source containment
  violations.
- Separate manifest concerns in implementation and tests: application-owned
  manifest entries/results, user installation registry conflict policy,
  lockfile full-rewrite semantics, and adapter-owned atomic JSON writes.
- Add lightweight `__init__.py` files only where packages need to be regular
  packages or expose an intentional public API. Avoid broad re-export chains for
  the new slice.

## Progress Tracking

Update task and checkpoint checkboxes as work is completed. Keep this plan
current during implementation without requiring a separate status request.

## Task List

### Phase 1: Application contracts and direct install happy path

#### Task 1: Add installation DTOs, errors, and ports

**Description:** Create the skill installation application boundary: command and
result DTOs, manifest DTOs, user-facing errors, and ports for installing a skill,
resolving requirements, reading requirements, locating source repositories,
copying skill directories, and writing manifests.

**Acceptance criteria:**

- [x] `InstallSkillCommand` validates fully qualified
      `<index-name>/<skill-name>`, explicit non-empty target, optional registry
      paths, optional installation registry override, and `force`.
- [x] Shared result/manifest DTOs capture requirement, index name, skill name,
      target, source metadata, schema version, skill path/file, and timestamp.
- [x] Application-specific errors provide clear user-facing messages for unknown
      index, unknown skill, invalid reference, existing target, conflicting
      recorded target, unsafe paths, and persistence failures.
- [x] Ports are small `Protocol`s under
      `features/skill_installation/application/ports/`.
- [x] Installation-owned ports describe the registry/index/source operations
      needed by installation use cases instead of exposing concrete
      index-registry adapters or storage details.
- [x] Package `__init__.py` files remain lightweight and expose only intentional
      public application APIs.

**Verification:**

- [x] Add focused DTO validation tests in
      `tests/unit/features/skill_installation/application/test_install_skill.py`.
- [x] Run: `uv run pytest tests/unit/features/skill_installation/application/test_install_skill.py`.

**Dependencies:** None

**Files likely touched:**

- `src/ritebook/features/skill_installation/application/dtos/install_skill.py`
- `src/ritebook/features/skill_installation/application/errors.py`
- `src/ritebook/features/skill_installation/application/ports/*.py`
- `tests/unit/features/skill_installation/application/test_install_skill.py`

**Estimated scope:** Medium

#### Task 2: Implement direct `InstallSkill` application use case with fakes

**Description:** Implement direct installation orchestration without real
filesystem copying. The use case should parse the qualified skill reference, load
the registered index, read cached skills, resolve the selected skill, resolve
source repository metadata, invoke the installer, then update the user
installation registry.

**Acceptance criteria:**

- [x] Unknown index and unknown skill fail before copy attempts.
- [x] Bare or malformed skill references are rejected.
- [x] Existing target refusal/force semantics are delegated through ports but
      surfaced clearly.
- [x] Successful install writes user installation state after copy succeeds.
- [x] Registry/index data needed for installation is mapped into
      installation-owned DTOs or value objects before use-case orchestration.
- [x] The use case is deterministic with an injected clock and does not access
      filesystem, TOML, or JSON directly.

**Verification:**

- [x] Application tests cover happy path, malformed reference, unknown index,
      unknown skill, refusal without force, replacement with force, and
      manifest-write-after-copy ordering.
- [x] Run: `uv run pytest tests/unit/features/skill_installation/application/test_install_skill.py`.

**Dependencies:** Task 1

**Files likely touched:**

- `src/ritebook/features/skill_installation/application/use_cases/install_skill.py`
- `src/ritebook/features/skill_installation/application/use_cases/__init__.py`
- `tests/unit/features/skill_installation/application/fakes.py`
- `tests/unit/features/skill_installation/application/test_install_skill.py`

**Estimated scope:** Medium

### Checkpoint: Direct application foundation

- [x] Direct installation application tests pass.
- [x] No outbound adapter details appear in application use case code.
- [x] DTOs/ports are small and installation-slice-owned.

### Phase 2: Requirements-file install and manifest model

#### Task 3: Add requirements DTOs and `InstallFromRequirements` use case

**Description:** Add application models for parsed `ritebook.toml` requirements
and implement requirements install orchestration: read requirements, resolve
targets, validate duplicates, plan all installs, copy each skill, and write
`ritebook.lock` only after all planned copies succeed.

**Acceptance criteria:**

- [ ] `target = "nickname"` resolves to `<targets.nickname>/<skill-name>`.
- [ ] `target_path` is used exactly as the target for that skill entry.
- [ ] Duplicate skill requirements and duplicate resolved targets are rejected
      before copy attempts.
- [ ] Unknown indexes, unknown skills, source resolution failures, and target
      planning conflicts are detected before the first copy when possible.
- [ ] Lockfile writer is invoked only after all planned installs succeed.
- [ ] Partial copy rollback remains out of scope, but late-copy failure errors
      clearly say lockfile was not updated and already-copied directories may
      remain.

**Verification:**

- [ ] Application tests cover target nickname resolution, direct target path,
      both/neither target fields, duplicate requirements, duplicate targets,
      successful lockfile writing, and no lockfile on failure.
- [ ] Run:
      `uv run pytest tests/unit/features/skill_installation/application/test_install_from_requirements.py`.

**Dependencies:** Tasks 1-2

**Files likely touched:**

- `src/ritebook/features/skill_installation/application/dtos/install_skill.py`
- `src/ritebook/features/skill_installation/application/ports/install_from_requirements.py`
- `src/ritebook/features/skill_installation/application/use_cases/install_from_requirements.py`
- `tests/unit/features/skill_installation/application/test_install_from_requirements.py`

**Estimated scope:** Medium

#### Task 4: Add manifest DTO semantics for lockfile and user registry

**Description:** Finalize DTOs/results needed by both manifest writers so direct
installs and requirements installs share source metadata consistently while
preserving schema differences: `installed_at` vs `locked_at`, `target_ref` only
for requirements nicknames, and `requirements_file` only for lockfiles.

**Acceptance criteria:**

- [ ] Direct install manifest entries sort by target.
- [ ] Lockfile entries sort by index name then skill name.
- [ ] Source revision is optional and included when resolvable.
- [ ] Repo-relative lockfile paths can remain relative when supplied that way;
      direct user installation registry may store expanded/resolved targets.
- [ ] Application tests distinguish manifest entry construction from adapter
      concerns such as JSON field ordering and atomic file replacement.

**Verification:**

- [ ] Extend application tests to assert manifest DTO values and ordering
      expectations passed to writer fakes.
- [ ] Run: `uv run pytest tests/unit/features/skill_installation/application`.

**Dependencies:** Tasks 2-3

**Files likely touched:**

- `src/ritebook/features/skill_installation/application/dtos/install_skill.py`
- `tests/unit/features/skill_installation/application/test_install_skill.py`
- `tests/unit/features/skill_installation/application/test_install_from_requirements.py`

**Estimated scope:** Small

### Checkpoint: Application behavior complete

- [ ] Direct and requirements application tests pass.
- [ ] Manifest writing order is guarded by tests.
- [ ] No JSON, TOML, or filesystem implementation details leaked into
      application use cases.

### Phase 3: Outbound adapters

#### Task 5: Implement source repository adapter

**Description:** Resolve the actual source repository path and optional source
revision from a `RegisteredIndex` without mutating Git state. For Git URL
sources, use `source_cache_path`; for local Git repositories, use the remembered
`source` path. Read current revision locally when possible.

**Acceptance criteria:**

- [ ] Git URL source uses the managed clone path already stored in the registry
      entry.
- [ ] Local Git source uses the remembered local repository path.
- [ ] Adapter does not fetch, pull, clone, or mutate repositories.
- [ ] Missing source paths or unreadable revision checks fail clearly; inability
      to determine revision can be represented as `None` if the source path is
      otherwise usable.

**Verification:**

- [ ] Unit tests cover Git URL, local Git repo, missing required path, and
      optional revision behavior.
- [ ] Run:
      `uv run pytest tests/unit/features/skill_installation/adapters/outbound/test_source_repository.py`.

**Dependencies:** Task 1

**Files likely touched:**

- `src/ritebook/features/skill_installation/adapters/outbound/source_repository/adapter.py`
- `tests/unit/features/skill_installation/adapters/outbound/test_source_repository.py`

**Estimated scope:** Small-Medium

#### Task 6: Implement safe filesystem installer adapter

**Description:** Copy the whole skill directory from the resolved source
repository to the explicit target path, validating source path containment and
target safety.

**Acceptance criteria:**

- [ ] Copies directories recursively and creates missing target parents.
- [ ] Refuses existing target without `force`.
- [ ] With `force`, removes/replaces only the resolved target path.
- [ ] Rejects source `path`/`skill_file` traversal, absolute paths, backslashes,
      or paths escaping the source repository.
- [ ] Rejects dangerous targets: empty, filesystem root, home directory itself,
      current working directory itself, and existing symlink targets.
- [ ] Does not follow symlink targets outside the intended path in v1.
- [ ] Assumes TOML shape validation has already happened, but independently
      protects the filesystem boundary from unsafe resolved paths.

**Verification:**

- [ ] Unit tests cover recursive copy, parent creation, refusal, forced
      replacement, unsafe source paths, dangerous targets, and symlink rejection.
- [ ] Run:
      `uv run pytest tests/unit/features/skill_installation/adapters/outbound/test_filesystem_installer.py`.

**Dependencies:** Tasks 1-2

**Files likely touched:**

- `src/ritebook/features/skill_installation/adapters/outbound/filesystem_installer/adapter.py`
- `tests/unit/features/skill_installation/adapters/outbound/test_filesystem_installer.py`

**Estimated scope:** Medium

#### Task 7: Implement TOML requirements reader adapter

**Description:** Parse and validate `ritebook.toml` with standard-library
`tomllib`, rejecting invalid root shapes, malformed targets, malformed skills,
unknown fields, and undefined target nicknames at the adapter boundary. Leave
duplicate skill requirements, duplicate resolved targets, and dangerous resolved
target decisions to application planning and filesystem boundary checks.

**Acceptance criteria:**

- [ ] Supports optional `[targets]` when all skills use `target_path`.
- [ ] Validates `[targets]` as non-empty string paths with simple nickname
      identifiers.
- [ ] Validates `[[skills]]` as array of tables with required `name` and exactly
      one target selector.
- [ ] Rejects unknown fields in v1.
- [ ] Uses clear errors without leaking file contents.
- [ ] Does not attempt to resolve registered indexes, inspect cached index JSON,
      or perform filesystem target-safety checks beyond TOML path field shape.

**Verification:**

- [ ] Unit tests cover all TOML reader cases listed in the spec.
- [ ] Run:
      `uv run pytest tests/unit/features/skill_installation/adapters/outbound/test_toml_requirements_reader.py`.

**Dependencies:** Tasks 1 and 3

**Files likely touched:**

- `src/ritebook/features/skill_installation/adapters/outbound/toml_requirements/reader.py`
- `tests/unit/features/skill_installation/adapters/outbound/test_toml_requirements_reader.py`

**Estimated scope:** Medium

#### Task 8: Implement JSON manifest writers

**Description:** Implement deterministic JSON writers for user-level direct
installation state and repo-local `ritebook.lock` with schema version `1`.

**Acceptance criteria:**

- [ ] `installations.json` default path is
      `~/.config/ritebook/installations.json`, overrideable through the CLI and
      application command.
- [ ] Direct reinstall of the same skill/target with `--force` replaces that
      entry.
- [ ] Different skill already recorded for target is refused unless `--force`.
- [ ] `ritebook.lock` writes deterministic schema v1 with `requirements_file`,
      sorted skills, optional `target_ref`, optional `source_revision`, and no
      stale entries for removed requirements.
- [ ] Writes are atomic enough for local CLI use via temp-file replacement.
- [ ] User registry conflict policy is tested separately from lockfile
      full-rewrite behavior.
- [ ] JSON writers receive application-owned manifest DTOs and do not read TOML,
      cached indexes, or source repositories directly.

**Verification:**

- [ ] Unit tests cover deterministic JSON, entry replacement/conflict behavior,
      stale lockfile removal by rewrite, and schema fields.
- [ ] Run:
      `uv run pytest tests/unit/features/skill_installation/adapters/outbound/test_json_installation_registry.py tests/unit/features/skill_installation/adapters/outbound/test_json_lockfile.py`.

**Dependencies:** Tasks 1, 3, and 4

**Files likely touched:**

- `src/ritebook/features/skill_installation/adapters/outbound/json_installation_registry/adapter.py`
- `src/ritebook/features/skill_installation/adapters/outbound/json_lockfile/adapter.py`
- `tests/unit/features/skill_installation/adapters/outbound/test_json_installation_registry.py`
- `tests/unit/features/skill_installation/adapters/outbound/test_json_lockfile.py`

**Estimated scope:** Medium

### Checkpoint: Adapter behavior complete

- [ ] All skill installation adapter tests pass.
- [ ] Path-safety tests cover source and target hazards.
- [ ] Manifest JSON output is deterministic and reviewable.

### Phase 4: CLI and composition root wiring

#### Task 9: Add CLI parser and command handlers

**Description:** Extend the shared CLI adapter with `install-skill` and
`install` commands, mapping args into application DTOs and rendering concise
success/error output.

**Acceptance criteria:**

- [ ] `install-skill` requires positional qualified skill reference and
      `--target`.
- [ ] `install-skill` supports `--force`, `--registry-path`, and
      `--installation-registry-path`.
- [ ] `install` supports `--file` defaulting to `ritebook.toml`, `--force`,
      `--registry-path`, and `--lockfile`.
- [ ] Success output matches spec shape.
- [ ] Application/adapter errors render as `ritebook: error: ...`.
- [ ] Parser and handler tests verify new options without requiring real
      filesystem, Git, TOML, or JSON adapters.

**Verification:**

- [ ] CLI unit tests cover arg mapping, required target, force flags, defaults,
      overrides, success output, and error rendering.
- [ ] Run: `uv run pytest tests/unit/adapters/inbound/cli/test_adapter.py`.

**Dependencies:** Tasks 1-4

**Files likely touched:**

- `src/ritebook/adapters/inbound/cli/parser.py`
- `src/ritebook/adapters/inbound/cli/commands.py`
- `src/ritebook/adapters/inbound/cli/adapter.py`
- `tests/unit/adapters/inbound/cli/test_adapter.py`

**Estimated scope:** Medium

#### Task 10: Wire composition root

**Description:** Instantiate installation use cases and outbound adapters in
`src/ritebook/cli.py`, reusing existing index registry and cached index reader
instances where appropriate.

**Acceptance criteria:**

- [ ] `main()` wires `InstallSkill` and `InstallFromRequirements` with the
      filesystem registry, JSON index reader, source repository adapter,
      filesystem installer, JSON installation registry, TOML reader, JSON
      lockfile writer, and injected UTC clock.
- [ ] Existing commands remain wired unchanged.
- [ ] No application layer imports outbound adapters.

**Verification:**

- [ ] Run CLI tests and a targeted import/smoke command if practical.
- [ ] Run: `uv run pytest tests/unit/adapters/inbound/cli/test_adapter.py`.
- [ ] After wiring, run a local help smoke such as
      `uv run ritebook --help` and, if supported by the parser,
      `uv run ritebook install-skill --help`.

**Dependencies:** Tasks 5-9

**Files likely touched:**

- `src/ritebook/cli.py`
- relevant `__init__.py` exports under `features/skill_installation/`

**Estimated scope:** Small

### Checkpoint: CLI flow wired

- [ ] CLI adapter tests pass.
- [ ] `ritebook --help` includes the new commands.
- [ ] Composition root remains the only place wiring concrete adapters.

### Phase 5: Documentation and final validation

#### Task 11: Update README usage docs

**Description:** Document the new consumer installation workflows,
`ritebook.toml` format, `ritebook.lock` behavior, user-level installation
registry, force behavior, and path overrides.

**Acceptance criteria:**

- [ ] README no longer says skill installation is not part of the consumer
      registry milestone.
- [ ] README includes examples for `install-skill`, `install`, `--force`,
      `--file`, `--registry-path`, `--installation-registry-path`, and
      `--lockfile`.
- [ ] README documents default generated state paths and recommends committing
      `ritebook.lock` when using `ritebook.toml`.
- [ ] README states that installs are offline-first and do not fetch/pull; users
      should run `update-index` first.

**Verification:**

- [ ] Review README examples for consistency with parser options.
- [ ] Check README examples against `uv run ritebook --help` and command help
      output after parser wiring exists.

**Dependencies:** Tasks 9-10

**Files likely touched:**

- `README.md`

**Estimated scope:** Small

#### Task 12: Add focused integration-style workflow coverage

**Description:** Add a focused workflow test using temporary local Git/index
fixtures and explicit registry/cache/lock paths, preferably in the existing E2E
suite if it can remain deterministic and local-only.

**Acceptance criteria:**

- [ ] End-to-end CLI flow can register a local index, install one direct skill,
      install from `ritebook.toml`, and verify copied directory contents plus
      generated state files.
- [ ] Test uses explicit temporary paths and does not touch real `~/.config` or
      `~/.cache`.
- [ ] Test does not require network access.

**Verification:**

- [ ] Run: `uv run pytest tests/e2e -q` if E2E coverage is added.
- [ ] Otherwise, add focused unit-level workflow tests and document why E2E was
      deferred.

**Dependencies:** Tasks 5-10

**Files likely touched:**

- `tests/e2e/test_cli_workflows.py` or focused unit workflow tests

**Estimated scope:** Medium

#### Task 13: Run final quality gate

**Description:** Run formatting, linting, type checking, tests, and build as
required by the spec and repository rules.

**Acceptance criteria:**

- [ ] Formatting applied.
- [ ] Ruff lint passes.
- [ ] Mypy passes.
- [ ] Pytest passes.
- [ ] Package build succeeds.

**Verification:**

```bash
uv run ruff format .
uv run ruff check .
uv run mypy .
uv run pytest
uv build
```

Also run targeted CLI help smoke checks after command wiring exists:

```bash
uv run ritebook --help
uv run ritebook install-skill --help
uv run ritebook install --help
```

**Dependencies:** All implementation and docs tasks

**Files likely touched:** None beyond formatting updates

**Estimated scope:** Small

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Path safety around source index paths and target replacement | High | Put strict validation in `filesystem_installer`; test traversal, root/home/cwd targets, and symlink targets. |
| Partial copies during `install` before a later failure | Medium | Validate full plan before copying; if copy still fails mid-batch, do not write lockfile and surface explicit partial-copy warning. |
| Cross-slice dependency from installation to index registry DTOs | Medium | Prefer installation-owned ports and adapter-side mapping around existing registry behavior; only depend directly on explicitly published registry contracts when that boundary is intentional. |
| Direct install state conflict semantics | Medium | Centralize conflict logic in JSON installation registry adapter, keep it separate from lockfile writing, and cover same-skill/same-target versus different-skill/same-target. |
| Manifest responsibility drift between application and adapters | Medium | Keep manifest DTO construction in application tests, JSON serialization/atomic writes in adapter tests, and avoid adapters resolving source/index/TOML data directly. |
| Machine-specific absolute paths in `ritebook.lock` | Medium | Preserve user-supplied repo-relative target strings for lockfile entries; avoid resolving to absolute paths for repo-local installs. |
| CLI adapter test file growth | Low | Keep additions focused; if it becomes unwieldy later, use `split-python-module`, but do not refactor unrelated CLI tests during this feature. |

## Open Questions

None blocking for the implementation plan. Preserve the spec's current defaults
and defer these intentionally out-of-scope items unless a later spec changes the
scope:

- Installing from unregistered Git URLs.
- Fetching or pulling during install.
- Default target aliases for direct `install-skill`.
- `uninstall-skill`, `update-skill`, `sync`, or `restore` commands.
- Signatures, content hashes, approvals, or trust policy.

## Parallelization Opportunities

- Tasks 5 and 7 can proceed in parallel after the core DTOs in Task 1 are stable.
- Task 8 can proceed in parallel with Task 6 once manifest DTOs are finalized.
- README updates can start after CLI shape is stable, but final examples should
  be checked after Tasks 9-10.

## Final Handoff Checklist

- [ ] Every task has acceptance criteria.
- [ ] Every task has verification steps.
- [ ] Task dependencies are ordered.
- [ ] Checkpoints exist between major phases.
- [ ] Open questions and assumptions are captured.
- [ ] Validation commands are explicit.