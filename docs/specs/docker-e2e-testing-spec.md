# Specification: Docker E2E Testing

## Status

- State: Active
- Revision: 3.3
- Acceptance basis: Existing active installed-wheel Docker verification contract.
- Owner: Ritebook maintainers
- Last reviewed: 2026-10-16
- Implementation state: Implemented
- Dependencies: [Skill Linter](skill-linter-spec.md), [Publisher](publisher-spec.md), [Index Registry](index-registry-spec.md), [Skill Installation](skill-installation-spec.md), and [Skill Contribution](skill-contribution-spec.md)

## Objective and Context

Provide a mandatory Docker end-to-end quality gate that proves Ritebook's
release-critical CLI workflows through a clean, consumer-style installation of a
wheel built from the commit under test.

The gate is designed to catch failures that source-based tests can miss, including
wheel-content omissions, invalid console-script packaging, incomplete runtime
dependency declarations, and regressions across real CLI, filesystem, Git,
registry, cache, installation, lockfile, and publisher boundaries. Docker is the
only supported E2E execution path; unit and integration tests provide faster
source-based feedback outside this boundary.

The Docker image is test infrastructure, not a production runtime image. Its
evidence covers only the Python version, operating system, and CPU architecture
used by the mandatory CI job.

### Current-state evidence

- Ritebook is a Python package with a `ritebook = "ritebook.cli:main"` console
  script and a declared minimum Python version of 3.13.
- `Dockerfile.e2e` builds the wheel, prepares separate test and consumer Python
  environments, and runs `tests/e2e/` without copying the project source or
  project metadata into the final stage.
- The E2E harness invokes the installed `ritebook` executable directly.
- The existing E2E scenarios use temporary local Git repositories to validate
  publisher, registry, listing, update, installation, synchronization, and
  contribution workflows.
- `.github/workflows/ci-cd.yaml` runs Docker E2E as an independent job and makes
  the repository-controlled release job depend on its success.
- Existing repository configuration treats the Docker E2E check as required for
  pull-request merges.

## Scope

- In scope: Building a same-commit wheel, installing it as a consumer would,
  running black-box release-critical workflows inside Docker, separate locked
  test tooling, unprivileged execution, controlled user state, local Git fixtures,
  normal anonymous network access, parallel pytest execution, and merge- and
  release-blocking CI behavior.
- Out of scope: Testing the exact bytes later published to PyPI, installing or
  executing the source distribution, production container packaging, native
  macOS or Windows E2E, Python-version or CPU-architecture matrices, required
  live-service scenarios, scheduled dependency-drift checks, immutable base-image
  digests, retained failure artifacts, and duration budgets.

## Requirements

### R1 — Clean wheel build and consumer installation

The Docker build must create a Ritebook wheel from the repository commit under
test with `uv build --wheel`. Only the built wheel may cross from the package
build stage into the consumer installation stage. Docker E2E does not need to
build or validate an sdist; the standard quality job remains responsible for
building the configured distribution formats.
The source distribution must exclude the externally sourced `.agents/` tree.

The consumer environment must install the wheel non-editably and resolve runtime
dependencies from the wheel's declared package metadata. `uv.lock` must not pin
the consumer environment's runtime dependency versions. This intentionally makes
the gate sensitive to incomplete or incompatible runtime dependency declarations
and to current compatible dependency resolution.

Docker E2E may test an independently built same-commit wheel; it need not be
byte-identical to the versioned distributions rebuilt by the later release job.

### R2 — Separate test-tool and consumer environments

The image must use separate Python environments for test tooling and the Ritebook
consumer installation.

- The test-tool environment must install the repository's complete locked `dev`
  dependency group without installing the Ritebook project. The equivalent
  command is `uv sync --frozen --only-group dev --no-install-project`.
- The consumer environment must contain the built Ritebook wheel and dependencies
  resolved from the wheel metadata.
- Pytest must execute from the test-tool environment while the `ritebook`
  executable resolves from the consumer environment.

The final test stage must not contain `src/`, `pyproject.toml`, `uv.lock`, or
another repository path that could import or execute Ritebook from the source
checkout. The E2E environment test must positively verify that the test-tool
Python cannot import Ritebook, the console script belongs to the consumer
environment, and the installed Ritebook module resolves below that consumer
environment.

### R3 — Release-critical black-box workflow coverage

E2E tests must invoke the installed `ritebook` console script as an external
process rather than importing Ritebook application or domain services. The
required baseline covers:

1. validating skills with `skills lint`;
2. generating an index with `indexes publish`;
3. registering a Git-backed index with `indexes add`;
4. browsing cached skills with `skills list`;
5. updating a registered index with `indexes update`;
6. direct skill installation with `skills install`;
7. requirements-file installation and synchronization with `skills sync`; and
8. preparing an upstream skill change with `skills contribute`.

The workflows must exercise real local filesystem and Git process boundaries.
They must verify the commit and digest provenance required by
[Shared Catalog Contract](shared-catalog-contract-spec.md), including that installed
content comes from the validated commit and mismatched bindings fail before
content is copied.

Currently required scenarios must use temporary local Git repositories. Future
scenarios may use anonymous public services; the supported suite requires no
live-service test.

### R4 — Risk-based coverage growth

A change must add or update Docker E2E coverage when it introduces or materially
alters a release-critical CLI workflow spanning multiple real boundaries, such as
CLI parsing, filesystem state, Git, generated metadata, package installation, or
subprocess behavior.

Docker E2E must remain a curated high-signal suite. Narrow validation rules,
exhaustive error matrices, and ordinary command variants and edge cases belong
primarily in unit or integration tests.

### R5 — Container user and state boundary

The final test stage must run as a non-root user. `HOME`, `XDG_CONFIG_HOME`, and
`XDG_CACHE_HOME` must identify controlled, writable, image-owned directories.
The username, numeric UID, and exact absolute paths are implementation details.

E2E workflow fixtures must use explicit temporary registry and cache paths and
must not read or write developer-local Ritebook state. The image must not receive
host filesystem mounts, environment files, credential-helper state, tokens, SSH
keys, private repository access, or other service credentials.

### R6 — Network policy

Docker E2E runs with normal container networking. Image construction and runtime
may access public dependency indexes, public Git repositories, or other anonymous
public services. Tests requiring credentials or private services are prohibited.

There is no suite-wide retry, skip, timeout, or outage-classification policy for
future live-service scenarios. Each scenario may define its own behavior. The
gate also has no E2E-specific subprocess timeout, job timeout, or duration budget;
platform and tool defaults apply unless an individual test chooses a narrower
limit.

### R7 — Explicit opt-in, parallel, and isolated test execution

Repository-level pytest configuration must classify tests collected from
`tests/e2e/` as `e2e` and deselect them unless `--run-e2e` is present. Plain
`pytest` is thus the standard non-E2E command without repeated negative marker
expressions.

The final image must identify itself with the Docker-only
`RITEBOOK_DOCKER_E2E=1` environment signal and invoke pytest with explicit
`--run-e2e -m e2e -n auto` options. Explicit `--run-e2e` use without that signal
must fail with usage guidance for the supported Docker build and run commands.

Tests must not depend on execution order or shared mutable workflow state. Each
scenario must use isolated temporary paths and repositories.

Failure diagnostics must be readable from pytest and captured CLI or Git output
in the CI console. JUnit uploads, retained temporary repositories, container
workspace archives, and other failure artifacts are not required.

### R8 — Mandatory CI gate

The main CI/CD workflow must run a stably named `Docker E2E` job for pull requests
and pushes to the release branch. It may run independently and in parallel with
the standard quality job.

The job's separately named build and run steps must invoke the repository-owned
`make docker-e2e-build` and `make docker-e2e-run` targets. The standard quality
job must likewise invoke repository-owned leaf targets so local and CI commands
remain aligned without collapsing CI diagnostics into one aggregate step.
The standard quality gate must verify that the architecture graph covers every
Ritebook source module and that a forbidden feature-core import fails validation.
Import contracts must include type-checking imports, enforce inward feature and
application layers, isolate the shared kernel and composition root, protect
private slice implementations, and reject configured I/O-library imports from
core code. Cross-slice application ports, DTOs, and errors remain public; their
implementation submodules remain private. The shared CLI dispatcher may import
each slice's inbound CLI facade, while the composition root may wire concrete
implementations. These module-level contracts do not prove API-call purity or
detect dynamic imports.

A failed Docker E2E check must block pull-request merge through existing
repository configuration. The repository-controlled release job must declare a
workflow dependency on both the standard quality job and Docker E2E so it cannot
continue after either fails. Automated proof or auditing of the external GitHub
ruleset is not required by this specification.

### R9 — Evidence and portability boundaries

The mandatory gate runs on Python 3.13 in a Linux container on the CI runner's
CPU architecture, currently expected to be `amd64`. Passing the gate warrants
only that evidenced environment.

Ritebook is expected to work on later supported Python versions, other operating
systems, and other CPU architectures. Platform-specific failures are product
bugs, but this Docker gate alone does not warrant those environments.

The Dockerfile may use practical version-oriented pins, including named Python
3.13 slim images and a versioned `uv` image. Mutable base-image contents, current
OS package versions, and consumer-resolved runtime dependency versions are
accepted. The image is not bit-reproducible and need not pin base images by
digest.

## Implementation and Verification Evidence

### Commands and validation

The only supported E2E execution path is:

```bash
make docker-e2e
```

The Makefile target delegates to the canonical Docker build and run commands:

```bash
docker build -f Dockerfile.e2e -t ritebook-e2e .
docker run --rm ritebook-e2e
```

Plain host pytest commands deselect tests under `tests/e2e/`. Direct host opt-in
with `--run-e2e` must be rejected because it does not establish the clean
installed-wheel boundary.

The final image's default command must run the equivalent of:

```bash
/opt/test-venv/bin/pytest -n auto --run-e2e -m e2e tests/e2e
```

The standard quality and packaging checks remain separate; plain pytest
automatically excludes Docker E2E:

```bash
make quality
make build
```

`make verify` is the complete local aggregate for quality, package building, and
Docker E2E. It must not silently skip Docker when Docker is unavailable.

### Project structure

- `Dockerfile.e2e`: wheel build, locked test-tool environment, consumer install,
  and final non-root E2E image.
- `Makefile`: shared local and CI targets for the standard quality checks,
  distribution build, and separate Docker E2E build and run steps.
- `tests/conftest.py`: suite-wide E2E classification, default deselection, and
  Docker-only `--run-e2e` enforcement.
- `.dockerignore`: excludes developer state, credentials, caches, and generated
  artifacts from the Docker build context.
- `tests/e2e/conftest.py`: installed-CLI runner, temporary paths, and local Git
  fixtures.
- `tests/e2e/test_container_environment.py`: executable evidence for the
  non-root, controlled-state, separate-environment, no-source boundary.
- `tests/e2e/test_cli_workflows.py`: publisher, registry, installation, and
  synchronization workflows.
- `tests/e2e/test_installation_provenance_workflow.py`: bound-commit installation
  and pre-copy provenance mismatch rejection.
- `tests/e2e/test_skill_contribution_workflow.py`: contribution workflow.
- `.github/workflows/ci-cd.yaml`: mandatory Docker E2E and release dependency.
- `README.md` and `AGENTS.md`: canonical local validation commands and concise
  operator guidance.

## Constraints and Execution Boundaries

### Binding constraints

- Build a wheel with `uv build --wheel`; do not install Ritebook from source.
- Keep test tooling and the consumer installation in separate environments.
- Keep source code and project metadata out of the final stage.
- Invoke the installed `ritebook` executable directly.
- Run only inside Docker as a non-root user with controlled writable state.
- Use explicit temporary registry and cache locations in workflow tests.
- Keep the current required scenarios on local temporary Git repositories.
- Allow only anonymous access to public external services.
- Deselect E2E tests from plain pytest execution.
- Require Docker-only `--run-e2e -m e2e -n auto` execution for the E2E suite.
- Keep Docker E2E independent from the standard quality job and blocking for
  merge and release.
- Keep the repository Makefile as the shared local and CI command interface while
  preserving separately named CI steps and jobs.

### Changes requiring specification approval

- Testing the exact final release artifact instead of an independently built
  same-commit wheel.
- Making sdist installation part of Docker E2E.
- Installing or invoking Ritebook from the source checkout.
- Supporting direct-host E2E as an equivalent acceptance path.
- Adding credentials, private repositories, or secret-backed services.
- Adding Docker Compose or service containers as required infrastructure.
- Adding a Python, operating-system, or CPU-architecture matrix.

### Exclusions and prohibited behavior

- Do not copy `src/`, `pyproject.toml`, or `uv.lock` into the final test stage.
- Do not let the test-tool environment install or shadow Ritebook.
- Do not mount host credentials, developer home directories, or Ritebook state.
- Do not claim validation of exact PyPI artifact bytes, sdists, production
  packaging, non-Linux platforms, later Python versions, or non-runner CPU
  architectures.
- Do not replace focused unit and integration coverage with Docker E2E.
- Do not require uploaded reports, retained workspaces, scheduled runs, or a
  performance budget under this revision.

## Acceptance Checks

| ID | Requirement | Conditions and action | Expected observable result | Verification method |
| --- | --- | --- | --- | --- |
| AC1 | R1-R2 | Build `Dockerfile.e2e` from a clean repository context. | The build creates only a wheel for Ritebook, creates a locked test-tool environment without Ritebook, installs the wheel and metadata-resolved runtime dependencies into a separate consumer environment, and constructs the final stage without source or project metadata. | `make docker-e2e-build` plus Dockerfile review. |
| AC2 | R2, R5 | Run the container environment test in the final image. | The process is non-root; home and XDG paths are controlled and writable; test Python cannot import Ritebook; the `ritebook` script and imported package resolve from the consumer environment; `src/`, `pyproject.toml`, and `uv.lock` are absent. | `tests/e2e/test_container_environment.py` through `make docker-e2e-run`. |
| AC3 | R3-R4 | Run the full E2E suite against local temporary Git fixtures. | The installed CLI completes the required publisher, registry, listing, update, install, sync, and contribution workflows and verifies the shared commit-and-digest binding. | `make docker-e2e-run`. |
| AC4 | R6 | Build and run with ordinary Docker networking and no credential injection. | The suite does not require `--network none`, credentials, private repositories, host mounts, or environment files; the currently required tests remain local-fixture based. | Docker/CI command review and E2E execution. |
| AC5 | R7 | Run plain host pytest commands, attempt explicit host opt-in, and run the final image's default command. | Plain host pytest deselects E2E; host `--run-e2e` fails with Docker usage guidance; the image supplies its Docker-only signal and executes E2E with `--run-e2e -m e2e -n auto`; isolated tests pass without order or shared-state dependence; failures include readable command diagnostics in console output. | `make test`, direct focused host pytest commands, image command review, and `make docker-e2e-run`. |
| AC6 | R8 | Review and execute the main CI/CD workflow. | The stable `Docker E2E` job runs on PRs and release-branch pushes; release depends on both quality and Docker E2E; existing repository configuration blocks merge when the check fails. | Workflow review and CI execution; external ruleset proof is not required. |
| AC7 | R9 | Review the image and documentation claims. | Commands and documentation describe Python 3.13/Linux/runner-architecture evidence, practical pins, and the explicit package/platform warranty boundaries without claiming reproducible or cross-platform proof. | Dockerfile, README, AGENTS, and specification review. |

## Assumptions

- Docker is available to maintainers and CI.
- Existing repository configuration requires the stably named Docker E2E check
  before pull-request merge.
- GitHub-hosted `ubuntu-latest` Docker execution currently provides the expected
  Linux `amd64` evidence.
- Consumer dependency drift is evaluated only when configured pull-request, push,
  or release-related workflows run; no scheduled run is required.
- Public-service outages may block a future live-service scenario according to
  that test's chosen behavior.
- Platform/default timeouts and console diagnostics are sufficient for this gate.
- Material unresolved assumptions: None.

## Open Questions

None.
