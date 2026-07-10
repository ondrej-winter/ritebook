# Spec: Docker E2E Integration Testing

## Objective

Introduce Docker-based end-to-end integration testing for Ritebook so maintainers
can catch real workflow regressions across the CLI, Git operations, registry and
cache files, and generated publisher indexes.

The first implementation milestone should provide a reliable clean-room test
runner rather than broad infrastructure. Docker is the execution boundary that
proves the workflow outside local developer state and outside unit-test fakes.

## Current context

- Ritebook is a Python 3.13 CLI package managed with `uv`.
- The package exposes the console script `ritebook = "ritebook.cli:main"`.
- Current automated tests are unit tests under `tests/unit/`.
- The existing test suite covers domain, application, adapter, and CLI behavior
  through direct Python tests and fakes.
- There is currently no Dockerfile, Docker Compose configuration, or `tests/e2e/`
  suite.
- GitHub Actions currently runs formatting, linting, type checking, pytest, and
  package build steps directly on `ubuntu-latest`.
- The highest-value workflow to verify end-to-end is the publisher-to-consumer
  path across these commands:
  - `lint-skills`
  - `publish-index`
  - `add-index`
  - `list-skills`
  - `update-index`

## Desired behavior

The future implementation should add a containerized e2e test runner that builds
from the repository and runs black-box CLI tests inside Docker.

The first e2e scenario must focus on the publisher-to-consumer workflow:

1. Create temporary valid skill fixtures.
2. Run `ritebook lint-skills --skills-root <skills-root>`.
3. Run `ritebook publish-index --skills-root <skills-root> --index-name <name>`.
4. Initialize and commit a local Git repository containing the generated
   `ritebook-index.json`.
5. Run `ritebook add-index --source <local-git-repo> --registry-path <path>
   --cache-root <path>`.
6. Run `ritebook list-skills --registry-path <path> --show-description`.
7. Modify the source skills, regenerate the publisher index, and commit the
   repository update.
8. Run `ritebook update-index --name <name> --registry-path <path>
   --cache-root <path>`.
9. Run `ritebook list-skills --registry-path <path> --show-description` again
   and verify the output reflects the updated cached index.

The tests should prefer stable, high-signal assertions over exhaustive coverage.
The first milestone should prove the workflow works as a system, not duplicate
all unit-level edge cases.

## Commands and validation

Target local Docker workflow for the future implementation:

```bash
docker build -f Dockerfile.e2e -t ritebook-e2e .
docker run --rm ritebook-e2e
```

The container default command should run the e2e suite, for example:

```bash
uv run pytest tests/e2e
```

Existing project validation remains:

```bash
uv run ruff format .
uv run ruff check .
uv run mypy .
uv run pytest
uv build
```

For this spec-only step, validation is limited to reviewing this document.

## Project structure

This spec is the only file required for the current step:

- Spec: `docs/specs/docker-e2e-integration-testing-spec.md`

Expected future implementation files:

- `Dockerfile.e2e`: dedicated Docker e2e test-runner image.
- `.dockerignore`: keep Docker build context small and avoid copying local caches
  and generated artifacts.
- `tests/e2e/`: black-box e2e pytest suite.
- `tests/e2e/conftest.py`: shared fixtures for subprocess execution, temporary
  skills, local Git repositories, registry paths, and cache roots when useful.
- `tests/e2e/test_cli_workflows.py`: publisher-to-consumer workflow tests.
- `README.md`: local Docker e2e usage documentation.
- `.github/workflows/ci-cd.yaml`: optional CI visibility for Docker e2e tests.

## Conventions

- Keep e2e tests black-box from the perspective of Ritebook behavior: execute the
  real CLI rather than importing application services directly.
- Use `pytest` for e2e tests to stay aligned with existing tooling.
- Use `uv` for dependency installation and command execution inside the test
  runner.
- Use temporary paths for all registry and cache files.
- Configure local Git repositories deterministically in test setup, including
  author name and email needed for commits.
- Keep helper code small, explicit, and focused on test orchestration.
- Do not introduce Docker Compose for the first milestone.
- Do not add production Docker image requirements to this testing spec.

## Testing strategy

The Docker e2e suite should optimize for reliability first.

Required first scenario:

- A publisher-to-consumer happy path that exercises real CLI commands, real local
  Git commits, generated `ritebook-index.json`, explicit registry path, explicit
  cache root, and cached skill listing before and after an update.

Recommended secondary scenario:

- One invalid skill metadata path that proves validation failure is visible
  through the real CLI with a non-zero exit code and stable diagnostic output.

The e2e tests should not depend on live external services, real remote Git
repositories, wall-clock-sensitive assertions, developer home directories, or
test order.

## CI stance

The Docker e2e workflow should be possible to run locally and visible in CI.
However, in the first implementation it should not be a hard release stopper if
it fails or proves flaky or slow.

Acceptable first CI approaches include:

- a non-blocking or explicitly allowed-to-fail Docker e2e job,
- a manually triggered workflow,
- a documented local-only command with a follow-up task to wire CI once stable.

The implementation should choose the simplest reliable approach and document the
trade-off.

## Boundaries

Always:

- Use local temporary Git repositories for the first milestone.
- Pass explicit `--registry-path` and `--cache-root` values in e2e tests.
- Keep Docker e2e tests isolated from real `~/.config/ritebook` and
  `~/.cache/ritebook` state.
- Treat Docker as a clean-room test runner, not as product runtime packaging.
- Prefer deterministic fixtures and fewer assertions over broad fragile checks.

Ask first:

- Adding Docker Compose or service containers.
- Requiring live remote Git repositories or network-dependent test scenarios.
- Making Docker e2e a blocking CI or release gate.
- Adding new runtime dependencies only to support e2e tests.

Never:

- Touch real user registry or cache paths in e2e tests.
- Depend on private repositories, credentials, or external services.
- Put business workflow assertions only in shell scripts without pytest-level
  assertions.
- Replace unit tests with Docker e2e tests.
- Use Docker e2e to justify broad production code rewrites.

## Success criteria

For the future implementation:

- `docker build -f Dockerfile.e2e -t ritebook-e2e .` succeeds.
- `docker run --rm ritebook-e2e` exits with status `0` when the e2e workflow is
  healthy.
- The e2e suite executes the real Ritebook CLI rather than direct application
  imports.
- The publisher-to-consumer workflow verifies generated index creation,
  local-Git-backed registration, cached skill listing, source update, cache
  refresh, and updated listing.
- The tests use explicit temporary registry and cache paths.
- README documents the local Docker e2e workflow.
- CI either exposes the Docker e2e workflow or clearly documents why it remains
  local-only until stabilized.

For this spec-only task:

- This document captures the confirmed intent, scope, boundaries, testing
  strategy, and success criteria.
- No Docker, test, README, or CI files are changed yet.

## Open questions

- Which CI shape should the first implementation choose: non-blocking job,
  manual workflow, or local-only documentation with a follow-up task?
- Should the first Docker test image install Ritebook as an editable project for
  fast iteration, or build and install the wheel to maximize packaging fidelity?
- Should the e2e command use `uv run ritebook` or the installed `ritebook` console
  script directly?