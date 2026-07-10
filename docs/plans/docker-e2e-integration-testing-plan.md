# Implementation Plan: Docker E2E Integration Testing

## Overview

Implement the Docker-based end-to-end integration testing workflow described in
`docs/specs/docker-e2e-integration-testing-spec.md`. The first milestone adds a
clean-room Docker test runner and a focused black-box pytest suite that exercises
the real Ritebook CLI across the publisher-to-consumer workflow: skill linting,
index publishing, local Git registration, cached skill listing, source updates,
and cache refresh.

## Goal

Add a reliable containerized E2E testing path that catches regressions across the
CLI, local Git operations, registry/cache files, and generated publisher indexes
without depending on developer-local Ritebook state, private services, remote Git
repositories, or unit-test fakes.

## Deliverables

- `Dockerfile.e2e` for a dedicated test-runner image.
- `.dockerignore` to keep the Docker build context small and reproducible.
- `tests/e2e/` pytest suite that executes the real CLI through subprocesses.
- `tests/e2e/conftest.py` fixtures for CLI execution, temporary skill fixtures,
  local Git repositories, explicit registry paths, and explicit cache roots.
- `tests/e2e/test_cli_workflows.py` with the required publisher-to-consumer happy
  path and one invalid metadata failure scenario.
- README documentation for local Docker E2E usage.
- A manually triggered GitHub Actions workflow for Docker E2E visibility.
- Pytest marker/configuration updates that keep Docker E2E tests out of the
  default blocking quality/release gate for the first milestone.

## Success Criteria

- `docker build -f Dockerfile.e2e -t ritebook-e2e .` succeeds.
- `docker run --rm ritebook-e2e` exits with status `0` when the E2E workflow is
  healthy.
- The E2E tests execute `uv run ritebook ...` through subprocesses instead of
  importing Ritebook application services directly.
- The publisher-to-consumer workflow verifies generated index creation,
  local-Git-backed registration, cached skill listing, source update, cache
  refresh, and updated listing.
- All E2E tests pass explicit temporary `--registry-path` and `--cache-root`
  values where the CLI supports them.
- Tests do not read or write real `~/.config/ritebook` or `~/.cache/ritebook`
  state.
- README documents the local Docker E2E workflow.
- CI exposes a manual Docker E2E workflow without making it a blocking release
  gate in the first milestone.
- Default local and CI `uv run pytest` behavior remains intentional: E2E tests
  are marker-isolated from the blocking quality/release gate, while Docker runs
  them explicitly.
- Final checks pass: `uv run ruff format .`, `uv run ruff check .`,
  `uv run mypy .`, the default pytest gate, the focused E2E pytest suite,
  `uv build`, Docker build, and Docker run.

## Architecture Decisions

- Keep E2E tests under `tests/e2e/` because they verify cross-slice black-box CLI
  behavior rather than one feature slice in isolation.
- Treat Docker as a clean-room test-runner boundary only, not as product runtime
  packaging.
- Use a source/editable-style test environment through `uv sync --frozen --group
  dev` and run the CLI as `uv run ritebook` for the first milestone. This aligns
  with existing README workflows and keeps iteration fast.
- Use local temporary Git repositories only. Do not add remote Git, network,
  credentials, service containers, or Docker Compose in this milestone.
- Add CI as a manual workflow only for now. Do not add Docker E2E as a blocking
  dependency of the existing quality or release jobs until the workflow proves
  stable enough to promote.
- Mark E2E tests explicitly and configure default pytest/CI behavior so the
  first milestone does not accidentally promote Docker E2E into the blocking
  quality/release gate. The Docker runner and focused local E2E commands should
  execute `tests/e2e` explicitly.
- Keep assertions stable and high-signal. The E2E suite should prove system
  behavior, not duplicate unit-level validation matrices or tree-rendering edge
  cases.

## Progress Tracking

Update task and checkpoint checkboxes as implementation progresses. Keep this
plan current automatically during implementation without requiring separate user
prompts for status updates.

### Implementation progress notes

- Added `Dockerfile.e2e` and `.dockerignore` for the Docker E2E runner
  foundation.
- Verified the local CLI entry point with `uv run ritebook --help`.
- Verified focused package metadata tests with
  `uv run pytest tests/unit/test_package_metadata.py -q`.
- Docker image build verification is still pending because the local Docker
  daemon was not running: `Cannot connect to the Docker daemon at
  unix:///Users/owinter/.docker/run/docker.sock`.
- Added pytest `e2e` marker isolation and updated the blocking CI pytest command
  to run `uv run pytest -m "not e2e"`.
- Verified pytest marker registration with `uv run pytest --markers`.
- Verified the default non-E2E pytest gate with `uv run pytest -m "not e2e"`.
- Added `tests/e2e/conftest.py` with black-box CLI subprocess helpers,
  temporary registry/cache path fixtures, skill fixture writers, and local Git
  repository helpers for future E2E workflow tests.
- Verified the E2E fixture module with `uv run ruff check
  tests/e2e/conftest.py`.
- Verified E2E collection with `uv run pytest --collect-only tests/e2e -q`; no
  tests were collected because Task 4 has not added workflow tests yet.
- Re-verified the default non-E2E pytest gate with `uv run pytest -m "not e2e"`.
- Added `tests/e2e/test_cli_workflows.py` with the publisher-to-consumer happy
  path through the real CLI, local Git, explicit registry/cache paths, cached
  listing, source update, and refreshed listing.
- Verified the happy-path E2E test with
  `uv run pytest tests/e2e/test_cli_workflows.py -q`.
- Verified the default non-E2E pytest gate still excludes E2E tests with
  `uv run pytest -m "not e2e"`.
- Added `test_lint_skills_reports_invalid_metadata_failure` to
  `tests/e2e/test_cli_workflows.py`, covering the real CLI `lint-skills` failure
  path for a skill missing required metadata.
- Verified the focused E2E workflow file with
  `uv run pytest tests/e2e/test_cli_workflows.py -q`; both E2E scenarios passed.
- Re-verified the default non-E2E pytest gate with `uv run pytest -m "not e2e"`;
  193 tests passed and 2 E2E tests were deselected.
- Updated `README.md` with focused local E2E and Docker E2E commands, plus the
  first-milestone scope note that Docker E2E is a clean-room test boundary rather
  than production packaging.

## Task List

### Phase 1: Docker Test Runner Foundation

#### Task 1: Add Docker E2E Runner Image

**Description:** Add `Dockerfile.e2e` that builds from the repository, prepares a
Python 3.13 development test environment with `uv` and Git, and defaults to
running the E2E pytest suite.

**Acceptance criteria:**

- [x] `Dockerfile.e2e` uses Python 3.13 to match `pyproject.toml`.
- [x] The image installs Git for local repository initialization and commits.
- [x] The image installs or copies `uv` in a reproducible, non-interactive way,
      such as copying a pinned `uv` binary from an official Astral image or using
      another version-pinned package source.
- [x] The image does not pipe a remote installer script into a shell or
      interpreter.
- [x] The image uses `uv sync --frozen --group dev` or an equivalent frozen
      dependency install.
- [x] The default command runs `uv run pytest tests/e2e`.
- [x] The Dockerfile is clearly scoped to E2E testing and does not introduce
      production image requirements.
- [ ] Network access may be used during Docker build dependency installation,
      but `docker run --rm ritebook-e2e` does not depend on live external
      services, remote Git repositories, or credentials.

**Verification:**

- [ ] `docker build -f Dockerfile.e2e -t ritebook-e2e .`
- [ ] `docker run --rm ritebook-e2e` after E2E tests exist.

**Dependencies:** None

**Files likely touched:**

- `Dockerfile.e2e`

**Estimated scope:** Small

#### Task 2: Add Docker Build Context Hygiene

**Description:** Add `.dockerignore` so Docker builds do not send local virtual
environments, caches, build artifacts, or generated local state into the test
image context.

**Acceptance criteria:**

- [x] `.dockerignore` excludes `.venv/`, `.pytest_cache/`, `.ruff_cache/`,
      `.mypy_cache/`, `dist/`, `build/`, and Python cache files.
- [x] `.dockerignore` excludes local Ritebook cache/config artifacts if they are
      ever created in the repository tree.
- [x] `.dockerignore` does not exclude files needed to build/install the project
      and run E2E tests, including `src/`, `tests/`, `pyproject.toml`, `uv.lock`,
      `README.md`, and relevant docs.
- [ ] Docker builds remain reproducible from repository content.

**Verification:**

- [ ] `docker build -f Dockerfile.e2e -t ritebook-e2e .`

**Dependencies:** None

**Files likely touched:**

- `.dockerignore`

**Estimated scope:** Small

### Checkpoint: Docker Foundation

- [ ] Docker image builds successfully.
- [ ] The image can invoke `uv`, `git`, and `uv run ritebook --help`.
- [ ] The runner command is ready for `tests/e2e`.

#### Task 2.5: Isolate E2E Tests from the Default Blocking Pytest Gate

**Description:** Add pytest marker/configuration so `tests/e2e` is explicit and
does not accidentally become part of the existing blocking quality/release gate
when default pytest discovery scans `tests/`.

**Acceptance criteria:**

- [x] `pyproject.toml` declares an `e2e` pytest marker with a concise
      description.
- [x] E2E tests are marked with `pytest.mark.e2e` at module or test level.
- [x] The existing CI/CD `quality` job continues to run the blocking test suite
      without Docker E2E tests, for example with `uv run pytest -m "not e2e"`.
- [x] Local README guidance distinguishes the default quality gate from the
      explicit E2E commands.
- [ ] The manual Docker E2E workflow remains the first milestone's CI visibility
      path for E2E tests.

**Verification:**

- [x] `uv run pytest -m "not e2e"`
- [x] `uv run pytest tests/e2e -q` after E2E tests exist.

**Dependencies:** Tasks 1-2 can be implemented before this, but this task should
be completed before adding E2E tests to avoid accidental CI behavior.

**Files likely touched:**

- `pyproject.toml`
- `.github/workflows/ci-cd.yaml`
- `README.md`
- `tests/e2e/test_cli_workflows.py` after tests exist

**Estimated scope:** Small

### Phase 2: Black-Box E2E Test Fixtures

#### Task 3: Create E2E Pytest Subprocess Fixtures

**Description:** Add shared pytest fixtures and helpers for running the real CLI,
creating temporary valid and invalid skill fixtures, initializing local Git
repositories, and providing explicit registry/cache paths.

**Acceptance criteria:**

- [x] CLI helper runs `uv run ritebook ...` and captures stdout, stderr, and exit
      code.
- [x] Helper assertion output includes captured stdout/stderr when a command
      unexpectedly fails.
- [x] E2E fixtures do not import Ritebook application services directly.
- [x] Skill fixture helpers create minimal valid `SKILL.md` files with valid
      Agent Skill headers and descriptions.
- [x] Invalid skill fixture helper creates one stable metadata failure for the
      secondary scenario.
- [x] Git helper initializes a local repository and configures deterministic
      `user.name` and `user.email` before commits.
- [x] Registry path and cache root fixtures come from `tmp_path`, not user home
      directories.
- [x] Helper code remains small, explicit, and focused on test orchestration.

**Verification:**

- [ ] `uv run pytest tests/e2e -q` once tests exist.
- [x] Code review confirms no direct application imports in E2E tests.

**Dependencies:** Tasks 1-2 are useful for Docker verification, but local pytest
authoring can start before Docker is complete. Task 2.5 should be completed
before E2E tests are added to the default-discovered `tests/` tree.

**Files likely touched:**

- `tests/e2e/conftest.py`
- `tests/e2e/__init__.py` if preserving package-style test directories

**Estimated scope:** Medium

### Phase 3: Publisher-to-Consumer Workflow

#### Task 4: Add Publisher-to-Consumer Happy Path E2E Test

**Description:** Implement the required black-box E2E scenario from the spec,
covering `lint-skills`, `publish-index`, local Git registration, initial cached
listing, source update, `update-index`, and updated cached listing.

**Acceptance criteria:**

- [x] Test creates temporary valid skill fixtures.
- [x] Test runs `uv run ritebook lint-skills --skills-root <skills-root>` and
      asserts success.
- [x] Test runs `uv run ritebook publish-index --skills-root <skills-root>
      --index-name <name>` and asserts `ritebook-index.json` exists.
- [x] Test initializes and commits a local Git repository containing the generated
      `ritebook-index.json`.
- [x] Test runs `add-index` with explicit `--registry-path` and `--cache-root`.
- [x] Test runs `list-skills --registry-path <path> --show-description` and
      asserts stable high-signal output for the initial cached index.
- [x] Test does not pass `--cache-root` to `list-skills`, because the current CLI
      only supports cache-root isolation through registry entries created or
      refreshed by `add-index` and `update-index`.
- [x] Test modifies the source skills, regenerates the publisher index, and
      commits the repository update.
- [x] Test runs `update-index --name <name> --registry-path <path> --cache-root
      <path>`.
- [x] Test runs `list-skills --registry-path <path> --show-description` again and
      verifies output reflects the updated cached index.
- [x] Assertions avoid absolute temporary paths and fragile incidental output.

**Verification:**

- [x] `uv run pytest tests/e2e/test_cli_workflows.py -q`
- [ ] `docker run --rm ritebook-e2e`

**Dependencies:** Task 3

**Files likely touched:**

- `tests/e2e/test_cli_workflows.py`
- `tests/e2e/conftest.py`

**Estimated scope:** Medium

#### Task 5: Add Invalid Skill Metadata E2E Scenario

**Description:** Add one secondary scenario proving validation failures are
visible through the real CLI with a non-zero exit code and stable diagnostic
output.

**Acceptance criteria:**

- [x] Test creates an invalid `SKILL.md` fixture with one stable validation
      problem.
- [x] Test runs `uv run ritebook lint-skills --skills-root <skills-root>` through
      the subprocess helper.
- [x] Test asserts a non-zero exit code.
- [x] Test asserts a stable diagnostic message without depending on absolute temp
      paths.
- [x] Test does not duplicate the unit-level validation matrix.

**Verification:**

- [x] `uv run pytest tests/e2e/test_cli_workflows.py -q`
- [ ] `docker run --rm ritebook-e2e`

**Dependencies:** Task 3

**Files likely touched:**

- `tests/e2e/test_cli_workflows.py`

**Estimated scope:** Small

### Checkpoint: E2E Behavior

- [x] Focused E2E tests pass locally outside Docker.
- [ ] Docker E2E image runs the same tests successfully.
- [ ] No E2E test touches real `~/.config/ritebook` or `~/.cache/ritebook`.
- [ ] No live network, credentials, private repositories, service containers, or
      Docker Compose are required during test execution.

### Phase 4: Documentation and CI Visibility

#### Task 6: Document Local Docker E2E Workflow

**Description:** Update README with concise instructions for building and running
the Docker E2E runner and explain what workflow it verifies.

**Acceptance criteria:**

- [x] README documents `docker build -f Dockerfile.e2e -t ritebook-e2e .`.
- [x] README documents `docker run --rm ritebook-e2e`.
- [x] README documents the focused local command `uv run pytest tests/e2e -q`.
- [x] README explains that the default quality gate excludes E2E tests in the
      first milestone, while Docker E2E is run explicitly.
- [x] README states the runner is a clean-room E2E test boundary, not production
      packaging.
- [x] README briefly describes that the Docker E2E suite verifies the
      publisher-to-consumer CLI workflow with local Git, registry, and cache
      files.
- [x] Existing local quality gate and package build instructions remain intact.

**Verification:**

- [x] Documentation review against
      `docs/specs/docker-e2e-integration-testing-spec.md`.

**Dependencies:** Tasks 1-5

**Files likely touched:**

- `README.md`

**Estimated scope:** Small

#### Task 7: Add Manual Docker E2E GitHub Actions Workflow

**Description:** Add a manually triggered GitHub Actions workflow that builds and
runs the Docker E2E image without making Docker E2E a blocking release or PR gate
in the first milestone.

**Acceptance criteria:**

- [ ] A manual `workflow_dispatch` workflow exists for Docker E2E.
- [ ] The workflow checks out the repository and runs Docker build/run commands.
- [ ] The workflow is separate from the existing blocking `quality` and
      `patch-release` dependency chain.
- [ ] The existing `.github/workflows/ci-cd.yaml` release behavior remains
      unchanged except for any deliberate default pytest marker exclusion needed
      to keep E2E non-blocking in the first milestone.
- [ ] README or workflow naming makes clear that Docker E2E is manually triggered
      for the first milestone.

**Verification:**

- [ ] YAML review for valid GitHub Actions syntax and a non-blocking dependency
      graph.
- [ ] `docker build -f Dockerfile.e2e -t ritebook-e2e .`
- [ ] `docker run --rm ritebook-e2e`

**Dependencies:** Tasks 1-6

**Files likely touched:**

- `.github/workflows/docker-e2e.yaml`
- `.github/workflows/ci-cd.yaml` if the blocking pytest command is updated to
  exclude the `e2e` marker
- `README.md`

**Estimated scope:** Small

### Phase 5: Final Validation

#### Task 8: Run Full Local Quality Gate and Docker E2E

**Description:** Run final formatting, linting, typing, unit/E2E tests, package
build, and Docker E2E validation after implementation and documentation are
complete.

**Acceptance criteria:**

- [ ] Formatting is applied.
- [ ] Ruff lint passes.
- [ ] Mypy strict type checking passes.
- [ ] Full pytest suite passes.
- [ ] Focused E2E pytest suite passes outside Docker.
- [ ] Package build succeeds.
- [ ] Docker image builds.
- [ ] Docker container run succeeds.

**Verification:**

- [ ] `uv run ruff format .`
- [ ] `uv run ruff check .`
- [ ] `uv run mypy .`
- [ ] `uv run pytest`
- [ ] `uv run pytest tests/e2e -q`
- [ ] `uv build`
- [ ] `docker build -f Dockerfile.e2e -t ritebook-e2e .`
- [ ] `docker run --rm ritebook-e2e`

**Dependencies:** Tasks 1-7

**Files likely touched:** None unless checks reveal fixes.

**Estimated scope:** Small

### Checkpoint: Complete

- [ ] Docker E2E runner builds and runs successfully.
- [ ] E2E tests exercise the real CLI through `uv run ritebook`.
- [ ] Publisher-to-consumer workflow passes through local Git registration,
      cached listing, update, and refreshed listing.
- [ ] Invalid metadata scenario reports a stable non-zero CLI failure.
- [ ] README documents local Docker E2E usage and manual CI visibility.
- [ ] Manual Docker E2E GitHub Actions workflow is available.
- [ ] Full local quality gate, package build, and Docker validation pass.

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Docker image scope expands into production packaging | Medium | Keep the file named `Dockerfile.e2e`, document it as test-only, and avoid runtime service or deployment concerns. |
| E2E tests become flaky due to home directory, Git config, or path assumptions | High | Use `tmp_path`, explicit registry/cache paths, deterministic Git config, and relative/stable output assertions. |
| Docker E2E slows or destabilizes release automation | Medium | Add only a manual workflow in the first milestone; do not make release jobs depend on it. |
| E2E tests duplicate unit coverage and become brittle | Medium | Keep one high-value happy path and one invalid metadata scenario with high-signal assertions. |
| Subprocess failures are hard to diagnose | Low | Capture stdout, stderr, command arguments, and return code in the CLI helper and include them in assertion messages. |
| Git behavior differs between local macOS and Linux Docker | Medium | Treat Docker as the authoritative clean-room runner, configure Git identity explicitly, and avoid assertions tied to platform-specific paths. |
| E2E tests accidentally become a blocking release gate | High | Mark E2E tests explicitly, exclude them from the existing blocking pytest command, and run them through the manual Docker workflow until promoted deliberately. |

## Open Questions and Assumptions

- Decision: the first CI integration is a manual `workflow_dispatch` workflow only,
  not an allowed-to-fail job in the main CI/CD workflow and not a release gate.
- Decision: the Docker test image uses the project source plus `uv sync` rather
  than building and installing the wheel for this first milestone.
- Decision: E2E subprocess helpers invoke `uv run ritebook` to align with README
  and current development workflows.
- Decision: E2E tests should be marked and excluded from the existing blocking
  default pytest gate for the first milestone. Run them explicitly with
  `uv run pytest tests/e2e -q` locally and through `docker run --rm ritebook-e2e`.
- Assumption: Docker build may need network access to install dependencies, but
  Docker test execution must not require live external services, remote Git
  repositories, credentials, or network-dependent scenarios.
- Assumption: E2E tests may create local Git repositories under pytest temporary
  directories, but must not depend on live remote repositories, credentials, or
  network access.
- Assumption: no new runtime dependencies are needed for this milestone. If a
  test-only dependency becomes necessary, add it to the dev dependency group and
  update `uv.lock` intentionally.

## Parallelization Opportunities

- Tasks 1 and 2 can be implemented together as Docker foundation work.
- Task 2.5 should be completed before adding E2E tests under `tests/` so default
  pytest and CI behavior stays intentional.
- After Task 3 defines shared fixtures, Tasks 4 and 5 can be implemented in
  sequence by one agent or split between agents with coordination on fixture
  names.
- README documentation can begin after the Docker commands and E2E scope are
  settled.
- The manual GitHub Actions workflow should wait until local Docker commands are
  verified.
- Final validation must be sequential after implementation, docs, and CI workflow
  updates are complete.

## Handoff Notes for Implementers

- Start with the Dockerfile and `.dockerignore`, then add pytest marker
  isolation before building the E2E fixtures and one complete happy path. Add the
  invalid metadata scenario after the happy path is stable.
- Keep E2E tests black-box: use subprocesses and the real CLI, not application
  use-case imports.
- Keep all registry and cache paths explicit and temporary.
- Remember that `list-skills` currently accepts `--registry-path` but not
  `--cache-root`; cache isolation comes from registry entries created or updated
  with explicit cache roots.
- Configure Git identity inside tests before committing.
- Avoid broad production code rewrites. If E2E tests reveal a product bug, fix the
  smallest root cause and add focused lower-level regression coverage when useful.
- Run focused checks while iterating, then the full local quality gate, package
  build, Docker build, and Docker run before handoff.