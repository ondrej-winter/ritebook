# ritebook

Ritebook is currently a minimal Python package placeholder intended to reserve
the package name on PyPI while the project is being designed.

## Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/) for dependency management and command
  execution

## Development setup

Install development dependencies:

```bash
uv sync --group dev
```

Run local quality checks:

```bash
uv run ruff format .
uv run ruff check .
uv run mypy .
uv run pytest -m "not e2e"
```

The default local quality gate excludes Docker end-to-end tests while that
workflow is being introduced. Run E2E tests explicitly:

```bash
uv run pytest tests/e2e -q
```

Run the same E2E suite in a clean Docker test runner:

```bash
docker build -f Dockerfile.e2e -t ritebook-e2e .
docker run --rm ritebook-e2e
```

`Dockerfile.e2e` is a clean-room end-to-end test boundary, not production
packaging. The Docker runner verifies the publisher-to-consumer CLI workflow
using local Git repositories, explicit registry files, and explicit cache
directories without relying on developer-local Ritebook state. For the first
milestone, Docker E2E remains an explicit workflow rather than part of the
default quality gate.

Build the package distributions:

```bash
uv build
```

## Publisher skill index generation

Maintainers can validate skill headers and generate a reviewable skill catalog
index from an explicit skills root:

```bash
uv run ritebook lint-skills --skills-root <path>
```

The `lint-skills` command recursively discovers `SKILL.md` files under the
skills root and validates their required Agent Skill headers without writing an
index file.

```bash
uv run ritebook publish-index --skills-root <path> --index-name <name>
```

The `--skills-root` option is required so the command only scans the intended
skills directory. The `--index-name` option is required and must be a stable
index name, either a kebab-case identifier such as `company-skills` or an
owner/repository-style name such as `ondrej-winter/ritebook-shelf`; it is written
to the generated index metadata as the default consumer registry name. The
`publish-index` command reuses the same validation flow as `lint-skills` and
refuses to write or overwrite `ritebook-index.json` when any discovered skill is
invalid. When validation succeeds, Ritebook writes the canonical index file
`ritebook-index.json` in the current working directory.

Review the generated `ritebook-index.json` before committing it with the related
skill changes.

## Consumer index registry

Users can register, refresh, and browse Git-backed Ritebook skill indexes. Skill
installation is not part of this milestone.

Register a Git URL source:

```bash
uv run ritebook add-index --source git@github.com:company/internal-skills.git
```

Register an already-cloned local Git repository without Ritebook mutating it:

```bash
uv run ritebook add-index --source ./internal-skills
```

Override the local effective index name or replace an existing registration:

```bash
uv run ritebook add-index \
  --source git@github.com:company/internal-skills.git \
  --name platform-skills \
  --force
```

Refresh a registered index from its remembered Git source:

```bash
uv run ritebook update-index --name platform-skills
```

List skills from all locally cached registered indexes:

```bash
uv run ritebook list-skills
```

List skills from one effective index name:

```bash
uv run ritebook list-skills --index-name platform-skills
```

Show cached skill descriptions when available:

```bash
uv run ritebook list-skills --show-description
```

The `list-skills` command is offline-first: it reads the local registry and each
selected registry entry's cached `ritebook-index.json` file only. It does not
clone, fetch, pull, scan publisher skill directories, or read raw `SKILL.md`
files.

Non-empty output is grouped by effective index name in a deterministic tree:

```text
Indexes
├── platform-skills
│   ├── skill-a
│   └── skill-b
└── data-skills
    └── query-helper
```

By default, the tree shows skill names only. With `--show-description`, Ritebook
appends descriptions cached from publisher indexes when that metadata is present:

```text
Indexes
└── platform-skills
    └── skill-a — Helps with platform workflows.
```

When no registered cached skills are available, Ritebook prints:

```text
No skills found
```

By default, Ritebook stores registry metadata and cached index contents under:

```text
~/.config/ritebook/indexes.json
~/.cache/ritebook/indexes/<effective-index-name>/ritebook-index.json
~/.cache/ritebook/git/<source-cache-id>/
```

When an effective index name includes an owner separator, Ritebook keeps the
registry name unchanged but flattens the cache directory by replacing `/` with
`_`; for example, `ondrej-winter/ritebook-shelf` is cached under
`~/.cache/ritebook/indexes/ondrej-winter_ritebook-shelf/ritebook-index.json`.

Tests and automation can override these locations:

```bash
uv run ritebook add-index \
  --source <git-url-or-local-git-repo> \
  --registry-path <path-to-indexes.json> \
  --cache-root <cache-directory>

uv run ritebook update-index \
  --name <effective-index-name> \
  --registry-path <path-to-indexes.json> \
  --cache-root <cache-directory>

uv run ritebook list-skills \
  --registry-path <path-to-indexes.json>

uv run ritebook list-skills \
  --index-name <effective-index-name> \
  --registry-path <path-to-indexes.json>
```

Consumer registration requires published schema version `1` indexes to include
`index.name` metadata. Legacy `ritebook-index.json` files without that metadata
are rejected instead of guessing a name.

## Publishing

The GitHub Actions workflow in `.github/workflows/ci-cd.yaml` runs formatting,
linting, type checking, tests, package builds, patch releases, and PyPI
publishing.

During the early project lifecycle, releases stay on the `0.1.x` line and every
non-bot push to `master` increments the patch version. The CI/CD workflow uses
Python Semantic Release to:

1. run the quality gate,
2. bump `pyproject.toml` from `0.1.x` to the next patch version,
3. commit the version bump,
4. create the matching `v0.1.x` tag, and
5. publish a GitHub release without maintaining a changelog, and
6. publish the built distributions to PyPI in the same workflow run.

The release job skips commits authored by `github-actions[bot]` so the automated
version-bump commit does not trigger another release. When the project is ready
to move beyond patch-only `0.1.x` releases, the same Semantic Release tooling can
be used for normal commit-derived SemVer releases.

For the current solo-maintainer workflow, `master` can allow direct pushes and
CI/CD verifies changes after each push. Repository rules should allow GitHub
Actions to write release bump commits and tags.

Publishing uses PyPI Trusted Publishing through GitHub Actions OIDC. Before the
first release, configure a trusted publisher for this repository in the PyPI
project settings:

- Repository owner: `ondrej-winter`
- Repository name: `ritebook`
- Workflow filename: `ci-cd.yaml`
- Environment name: `pypi`

## Architecture direction

Future business capabilities should be implemented as vertical feature slices
under `src/ritebook/features/`, keeping domain, application ports/use cases, and
adapters separated according to hexagonal architecture principles.