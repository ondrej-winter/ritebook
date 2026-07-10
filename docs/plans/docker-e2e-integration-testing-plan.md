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
- Final checks pass: `uv run ruff format .`, `uv run ruff check .`,
  `uv run mypy .`, `uv run pytest`, `uv build`, Docker build, and Docker run.

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
- Keep assertions stable and high-signal. The E2E suite should prove system
  behavior, not duplicate unit-level validation matrices or tree-rendering edge
  cases.

## Progress Tracking

Update task and checkpoint checkboxes as implementation progresses. Keep this
plan current automatically during implementation without requiring separate user
prompts for status updates.

## Task List

### Phase 1: Docker Test Runner Foundation

#### Task 1: Add Docker E2E Runner Image

**Description:** Add `Dockerfile.e2e` that builds from the repository, prepares a
Python 3.13 development test environment with `uv` and Git, and defaults to
running the E2E pytest suite.

**Acceptance criteria:**

- [ ] `Dockerfile.e2e` uses Python 3.13 to match `pyproject.toml`.
- [ ] The image installs Git for local repository initialization and commits.
- [ ] The image installs or copies `uv` in a reproducible, non-interactive way.
- [ ] The image uses `uv sync --frozen --group dev` or an equivalent frozen
      dependency install.
- [ ] The default command runs `uv run pytest tests/e2e`.
- [ ] The Dockerfile is clearly scoped to E2E testing and does not introduce
      production image requirements.

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

- [ ] `.dockerignore` excludes `.venv/`, `.pytest_cache/`, `.ruff_cache/`,
      `.mypy_cache/`, `dist/`, `build/`, and Python cache files.
- [ ] `.dockerignore` excludes local Ritebook cache/config artifacts if they are
      ever created in the repository tree.
- [ ] `.dockerignore` does not exclude files needed to build/install the project
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

### Phase 2: Black-Box E2E Test Fixtures

#### Task 3: Create E2E Pytest Subprocess Fixtures

**Description:** Add shared pytest fixtures and helpers for running the real CLI,
creating temporary valid and invalid skill fixtures, initializing local Git
repositories, and providing explicit registry/cache paths.

**Acceptance criteria:**

- [ ] CLI helper runs `uv run ritebook ...` and captures stdout, stderr, and exit
      code.
- [ ] Helper assertion output includes captured stdout/stderr when a command
      unexpectedly fails.
- [ ] E2E fixtures do not import Ritebook application services directly.
- [ ] Skill fixture helpers create minimal valid `SKILL.md` files with valid
      Agent Skill headers and descriptions.
- [ ] Invalid skill fixture helper creates one stable metadata failure for the
      secondary scenario.
- [ ] Git helper initializes a local repository and configures deterministic
      `user.name` and `user.email` before commits.
- [ ] Registry path and cache root fixtures come from `tmp_path`, not user home
      directories.
- [ ] Helper code remains small, explicit, and focused on test orchestration.

**Verification:**

- [ ] `uv run pytest tests/e2e -q` once tests exist.
- [ ] Code review confirms no direct application imports in E2E tests.

**Dependencies:** Tasks 1-2 are useful for Docker verification, but local pytest
authoring can start before Docker is complete.

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

- [ ] Test creates temporary valid skill fixtures.
- [ ] Test runs `uv run ritebook lint-skills --skills-root <skills-root>` and
      asserts success.
- [ ] Test runs `uv run ritebook publish-index --skills-root <skills-root>
      --index-name <name>` and asserts `ritebook-index.json` exists.
- [ ] Test initializes and commits a local Git repository containing the generated
      `ritebook-index.json`.
- [ ] Test runs `add-index` with explicit `--registry-path` and `--cache-root`.
- [ ] Test runs `list-skills --registry-path <path> --show-description` and
      asserts stable high-signal output for the initial cached index.
- [ ] Test modifies the source skills, regenerates the publisher index, and
      commits the repository update.
- [ ] Test runs `update-index --name <name> --registry-path <path> --cache-root
      <path>`.
- [ ] Test runs `list-skills --registry-path <path> --show-description` again and
      verifies output reflects the updated cached index.
- [ ] Assertions avoid absolute temporary paths and fragile incidental output.

**Verification:**

- [ ] `uv run pytest tests/e2e/test_cli_workflows.py -q`
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

- [ ] Test creates an invalid `SKILL.md` fixture with one stable validation
      problem.
- [ ] Test runs `uv run ritebook lint-skills --skills-root <skills-root>` through
      the subprocess helper.
- [ ] Test asserts a non-zero exit code.
- [ ] Test asserts a stable diagnostic message without depending on absolute temp
      paths.
- [ ] Test does not duplicate the unit-level validation matrix.

**Verification:**

- [ ] `uv run pytest tests/e2e/test_cli_workflows.py -q`
- [ ] `docker run --rm ritebook-e2e`

**Dependencies:** Task 3

**Files likely touched:**

- `tests/e2e/test_cli_workflows.py`

**Estimated scope:** Small

### Checkpoint: E2E Behavior

- [ ] Focused E2E tests pass locally outside Docker.
- [ ] Docker E2E image runs the same tests successfully.
- [ ] No E2E test touches real `~/.config/ritebook` or `~/.cache/ritebook`.
- [ ] No live network, credentials, private repositories, service containers, or
      Docker Compose are required.

### Phase 4: Documentation and CI Visibility

#### Task 6: Document Local Docker E2E Workflow

**Description:** Update README with concise instructions for building and running
the Docker E2E runner and explain what workflow it verifies.

**Acceptance criteria:**

- [ ] README documents `docker build -f Dockerfile.e2e -t ritebook-e2e .`.
- [ ] README documents `docker run --rm ritebook-e2e`.
- [ ] README states the runner is a clean-room E2E test boundary, not production
      packaging.
- [ ] README briefly describes that the Docker E2E suite verifies the
      publisher-to-consumer CLI workflow with local Git, registry, and cache
      files.
- [ ] Existing local quality gate and package build instructions remain intact.

**Verification:**

- [ ] Documentation review against
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
      unchanged unless a separate manual workflow file is not chosen.
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
- [ ] Package build succeeds.
- [ ] Docker image builds.
- [ ] Docker container run succeeds.

**Verification:**

- [ ] `uv run ruff format .`
- [ ] `uv run ruff check .`
- [ ] `uv run mypy .`
- [ ] `uv run pytest`
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

## Open Questions and Assumptions

- Decision: the first CI integration is a manual `workflow_dispatch` workflow only,
  not an allowed-to-fail job in the main CI/CD workflow and not a release gate.
- Decision: the Docker test image uses the project source plus `uv sync` rather
  than building and installing the wheel for this first milestone.
- Decision: E2E subprocess helpers invoke `uv run ritebook` to align with README
  and current development workflows.
- Assumption: `uv run pytest tests/e2e` should be included in `uv run pytest`
  because project pytest discovery already uses `testpaths = ["tests"]`. If the
  Docker E2E suite later becomes too slow for default local runs, revisit pytest
  markers or command separation explicitly.
- Assumption: E2E tests may create local Git repositories under pytest temporary
  directories, but must not depend on live remote repositories, credentials, or
  network access.
- Assumption: no new runtime dependencies are needed for this milestone. If a
  test-only dependency becomes necessary, add it to the dev dependency group and
  update `uv.lock` intentionally.

## Parallelization Opportunities

- Tasks 1 and 2 can be implemented together as Docker foundation work.
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

- Start with the Dockerfile and `.dockerignore`, then build the E2E fixtures and
  one complete happy path before adding the invalid metadata scenario.
- Keep E2E tests black-box: use subprocesses and the real CLI, not application
  use-case imports.
- Keep all registry and cache paths explicit and temporary.
- Configure Git identity inside tests before committing.
- Avoid broad production code rewrites. If E2E tests reveal a product bug, fix the
  smallest root cause and add focused lower-level regression coverage when useful.
- Run focused checks while iterating, then the full local quality gate, package
  build, Docker build, and Docker run before handoff.