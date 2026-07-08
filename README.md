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
uv run pytest
```

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
kebab-case identifier, such as `company-skills`; it is written to the generated
index metadata as the default consumer registry name. The `publish-index` command
reuses the same validation flow as `lint-skills` and refuses to write or
overwrite `ritebook-index.json` when any discovered skill is invalid. When
validation succeeds, Ritebook writes the canonical index file
`ritebook-index.json` in the current working directory.

Review the generated `ritebook-index.json` before committing it with the related
skill changes.

## Consumer index registry

Users can register and refresh Git-backed Ritebook skill indexes. Listing and
skill installation are not part of this milestone.

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

By default, Ritebook stores registry metadata and cached index contents under:

```text
~/.config/ritebook/indexes.json
~/.cache/ritebook/indexes/<effective-index-name>/ritebook-index.json
~/.cache/ritebook/git/<source-cache-id>/
```

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
```

Consumer registration requires published schema version `1` indexes to include
`index.name` metadata. Legacy `ritebook-index.json` files without that metadata
are rejected instead of guessing a name.

## Publishing

The GitHub Actions workflow in `.github/workflows/ci-cd.yaml` runs formatting,
linting, type checking, tests, and package builds. It publishes to PyPI when a
GitHub release is published.

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