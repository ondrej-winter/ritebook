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

Maintainers can generate a reviewable skill catalog index from an explicit skills
root:

```bash
uv run ritebook publish-index --skills-root <path>
```

The `--skills-root` option is required so the command only scans the intended
skills directory. Ritebook always writes the canonical index file
`ritebook-index.json` in the current working directory.

Review the generated `ritebook-index.json` before committing it with the related
skill changes.

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