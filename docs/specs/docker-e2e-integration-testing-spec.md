# Spec: Docker E2E Integration Testing

> **Status:** Active
> **Owner:** Ritebook maintainers
> **Spec version:** 1.0
> **Last reviewed:** 2026-07-22
> **Implementation state:** Implemented
> **Dependencies:** [Publisher Skill Index Generation](publisher-index-generation-spec.md), [Consumer Git Index Registry](consumer-git-index-registry-spec.md), [Consumer List Skills](list-skills-spec.md), [Consumer Skill Installation](install-skill-spec.md), and [Upstream Skill Contributions](upstream-skill-contributions-spec.md)
> **Associated ADRs:** [ADR 0001: Source Provenance and Trust](../adr/0001-source-provenance-and-trust.md)

## Objective

Provide Docker-based end-to-end integration testing for Ritebook so maintainers
can catch real workflow regressions across the CLI, Git operations, registry and
cache files, and generated publisher indexes.

The implementation provides an isolated test runner rather than broad
infrastructure. Docker proves the workflow outside local developer state and
unit-test fakes under the explicit state, permission, and network contract below.

## Implementation status

- Ritebook is a Python 3.13 CLI package managed with `uv`.
- The package exposes the console script `ritebook = "ritebook.cli:main"`.
- Current automated tests include unit tests under `tests/unit/` and black-box
  CLI E2E tests under `tests/e2e/`.
- The existing test suite covers domain, application, adapter, and CLI behavior
  through direct Python tests and fakes.
- `Dockerfile.e2e` provides an isolated Docker test runner for E2E pytest.
- The image runs tests as the fixed unprivileged `ritebook` user with effective
  UID `10001` and controlled writable `HOME`, `XDG_CONFIG_HOME`, and
  `XDG_CACHE_HOME` paths below `/home/ritebook`.
- Docker runtime networking is disabled. The container has no non-loopback IPv4
  route, and the E2E suite uses local temporary Git repositories without external
  services.
- `.github/workflows/ci-cd.yaml` runs Docker E2E as a mandatory gate in parallel
  with the non-E2E quality-check job.
- GitHub Actions runs formatting, linting, type checking, non-E2E pytest, and
  package build steps directly on `ubuntu-latest` in a separate mandatory job.
- The highest-value workflow verified end to end is the publisher-to-consumer
  path across these commands:
  - `lint-skills`
  - `publish-index`
  - `add-index`
  - `list-skills`
  - `update-index`
  - `install-skill`
  - `install`

## Desired behavior

The implementation includes a containerized E2E test runner that builds from the
repository and runs black-box CLI tests inside Docker.

The primary E2E scenario focuses on the publisher-to-consumer workflow:

1. Create temporary valid skill fixtures.
2. Run `ritebook lint-skills --skills-root <skills-root>`.
3. Run `ritebook publish-index --skills-root <skills-root> --index-name
   <published-name>`.
4. Initialize and commit a local Git repository containing the generated
   `ritebook-index.json`.
5. Run `ritebook add-index --source <local-git-repo> --registry-path <path>
   --cache-root <path>`.
6. Verify the registry binds the cached index to the source's full commit object
   ID and the exact index digest required by
   [ADR 0001](../adr/0001-source-provenance-and-trust.md).
7. Run `ritebook list-skills --registry-path <path> --show-description`.
8. Modify the source skills, regenerate the publisher index, and commit the
   repository update.
9. Run `ritebook update-index --name <local-alias> --registry-path <path>
   --cache-root <path>`.
10. Run `ritebook list-skills --registry-path <path> --show-description` again
    and verify the output reflects the newly bound commit and cached index.

Additional E2E scenarios cover direct and requirements-file installation and the
upstream skill-contribution workflow. The tests prefer stable, high-signal
assertions over exhaustive coverage and do not duplicate all unit-level edge
cases.

Installation scenarios must prove the full binding: the cached index and root
`ritebook-index.json` at the selected commit both match the persisted digest, and
the copied skill bytes come from that commit. A digest mismatch on either side
must fail before content is copied.

## Commands and validation

Target local Docker workflow:

```bash
docker build -f Dockerfile.e2e -t ritebook-e2e .
docker run --rm --network none ritebook-e2e
```

The container's default command runs the E2E suite:

```bash
uv run pytest tests/e2e
```

Existing project validation remains:

```bash
uv run ruff format .
uv run ruff check .
uv run ty check src/ritebook
uv run pytest
uv build
```

## Project structure

Implemented files:

- Spec: `docs/specs/docker-e2e-integration-testing-spec.md`
- `Dockerfile.e2e`: dedicated Docker E2E test-runner image.
- `.dockerignore`: keep Docker build context small and avoid copying local caches
  and generated artifacts.
- `tests/e2e/`: black-box E2E pytest suite.
- `tests/e2e/conftest.py`: shared fixtures for subprocess execution, temporary
  skills, local Git repositories, registry paths, and cache roots when useful.
- `tests/e2e/test_cli_workflows.py`: publisher-to-consumer workflow tests.
- `README.md`: local Docker E2E usage documentation.
- `.github/workflows/ci-cd.yaml`: mandatory Docker E2E gate in the main CI/CD
  workflow.

## Conventions

- Keep E2E tests black-box from the perspective of Ritebook behavior: execute the
  real CLI rather than importing application services directly.
- Use `pytest` for E2E tests to stay aligned with existing tooling.
- Use `uv` for dependency installation and command execution inside the test
  runner.
- Use temporary paths for all registry and cache files.
- Run container tests as the fixed unprivileged image user rather than root.
- Set `HOME`, `XDG_CONFIG_HOME`, and `XDG_CACHE_HOME` to writable image-owned
  paths rather than inheriting host state.
- Disable Docker runtime networking. Image construction may use public network
  access to obtain the pinned base image, system package metadata, and the exact
  dependencies selected by `uv.lock`.
- Configure local Git repositories deterministically in test setup, including
  author name and email needed for commits.
- Keep helper code small, explicit, and focused on test orchestration.
- Do not introduce Docker Compose for the first milestone.
- Do not add production Docker image requirements to this testing spec.

## Testing strategy

The Docker E2E suite optimizes for reliability first.

Primary scenario:

- A publisher-to-consumer happy path that exercises real CLI commands, real local
  Git commits, generated `ritebook-index.json`, explicit registry path, explicit
  cache root, verified commit/index bindings, and cached skill listing before and
  after an update.

Provenance regression scenarios prove that uncommitted local source changes are
rejected and that changing source content after registration cannot silently
change installed bytes.

Secondary validation scenario:

- One invalid skill metadata path that proves validation failure is visible
  through the real CLI with a non-zero exit code and stable diagnostic output.

The E2E tests should not depend on live external services, real remote Git
repositories, wall-clock-sensitive assertions, developer home directories, or
test order.

The focused container-environment scenario runs only when the image sets
`RITEBOOK_DOCKER_E2E=1`. It verifies the non-root effective UID, controlled
writable home and XDG directories, and absence of non-loopback IPv4 routes.
Direct host execution skips this container-specific assertion while running the
same black-box workflow tests.

## CI stance

Docker E2E is a mandatory quality gate in the main CI/CD workflow. The Docker E2E
job runs independently from the standard formatting, linting, type-checking,
non-E2E pytest, and build job so both jobs can execute in parallel on GitHub
Actions runners.

Releases require both the standard quality-check job and the Docker E2E job to
pass. Maintainers can rerun the Docker E2E job from the main workflow when
investigating a failure.

## Boundaries

Always:

- Use local temporary Git repositories for the first milestone.
- Pass explicit `--registry-path` and `--cache-root` values in E2E tests.
- Keep Docker E2E tests isolated from real `~/.config/ritebook` and
  `~/.cache/ritebook` state.
- Build without host credential mounts, environment-file injection, or host
  filesystem mounts.
- Run with `--network none` as the unprivileged image user and controlled home.
- Treat Docker as an isolated test runner, not as product runtime packaging.
- Prefer deterministic fixtures and fewer assertions over broad fragile checks.

Ask first:

- Adding Docker Compose or service containers.
- Requiring live remote Git repositories or network-dependent test scenarios.
- Adding new runtime dependencies only to support E2E tests.

Never:

- Touch real user registry or cache paths in E2E tests.
- Depend on private repositories, credentials, or external services.
- Claim that image construction is network-independent; it resolves public image,
  system-package, and locked Python dependency sources.
- Claim VM-grade isolation, host-kernel isolation, reproducible mutable base-image
  contents, or production-runtime equivalence.
- Put business workflow assertions only in shell scripts without pytest-level
  assertions.
- Replace unit tests with Docker E2E tests.
- Use Docker E2E to justify broad production code rewrites.

## Success criteria

For the implementation:

- `docker build -f Dockerfile.e2e -t ritebook-e2e .` succeeds.
- `docker run --rm --network none ritebook-e2e` exits with status `0` when the E2E
  workflow is healthy.
- The focused environment test proves non-root execution, controlled writable
  home and XDG state, and absence of non-loopback IPv4 routes.
- The E2E suite executes the real Ritebook CLI rather than direct application
  imports.
- The publisher-to-consumer workflow verifies generated index creation,
  local-Git-backed registration, cached skill listing, source update, cache
  refresh, updated listing, and the provenance binding selected by ADR 0001.
- The tests use explicit temporary registry and cache paths.
- README documents the local Docker E2E workflow.
- CI/CD runs Docker E2E as a blocking gate before release and publishing.

## Isolation contract

The Docker E2E boundary isolates dependencies and Ritebook process state from the
developer environment, exercises realistic unprivileged filesystem permissions,
and prevents runtime network access. Build-time public network access remains
required. The boundary does not promise a reproducible operating-system image,
separate kernel, production packaging, or protection against a malicious test
process with container-escape capabilities.
