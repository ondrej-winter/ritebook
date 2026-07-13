# ritebook

Ritebook is a Python CLI for validating, publishing, registering, browsing, and
installing Agent Skill indexes. It supports publisher workflows that generate
reviewable `ritebook-index.json` files and consumer workflows that install skills
from registered Git-backed indexes.

## Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/) for dependency management and command
  execution

## Development setup

Install development dependencies:

```bash
uv sync --group dev
```

Install the Git pre-commit hook:

```bash
uv run pre-commit install
```

Run the pre-commit hooks across the full repository when changing the hook
configuration or before opening a PR:

```bash
uv run pre-commit run --all-files
```

Pre-commit provides fast local feedback for file hygiene, Ruff formatting and
linting, and ty type checking. It complements, but does not replace, the full
local quality gate.

Run local quality checks:

```bash
uv run ruff format .
uv run ruff check .
uv run ty check src/ritebook
uv run pytest -m "not e2e"
```

Run E2E tests directly when iterating on the black-box CLI workflow:

```bash
uv run pytest tests/e2e -q
```

Run the mandatory clean-room Docker E2E gate before handoff:

```bash
docker build -f Dockerfile.e2e -t ritebook-e2e .
docker run --rm ritebook-e2e
```

`Dockerfile.e2e` is a clean-room end-to-end test boundary, not production
packaging. The Docker runner verifies the publisher-to-consumer CLI workflow
using local Git repositories, explicit registry files, and explicit cache
directories without relying on developer-local Ritebook state. CI/CD runs Docker
E2E as a mandatory quality gate in parallel with the non-E2E quality checks.

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
single-segment kebab-case identifier such as `company-skills`; slashes are not
allowed because skill references use `<index-name>/<skill-name>`. The index name
is written to the generated index metadata as the default consumer registry name.
The `publish-index` command reuses the same validation flow as `lint-skills` and
refuses to write or overwrite `ritebook-index.json` when any discovered skill is
invalid. When validation succeeds, Ritebook writes the canonical index file
`ritebook-index.json` in the current working directory.

Review the generated `ritebook-index.json` before committing it with the related
skill changes.

## Consumer index registry

Users can register, refresh, browse, and install skills from Git-backed Ritebook
skill indexes.

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

## Consumer skill installation

Ritebook installs skills from already registered and cached indexes. Installation
commands are offline-first: they read the local registry and cached
`ritebook-index.json` files, then copy skill directories from the remembered
source repository path or managed local clone. They do not clone, fetch, pull, or
mutate source repositories. Run `update-index` first when you want to refresh the
cached index and managed Git clone before installing.

Install one fully qualified skill into an explicit target path:

```bash
uv run ritebook install-skill platform-skills/code-review \
  --target .claude/skills/code-review
```

Ritebook copies the whole skill directory, creates missing target parent
directories, and refuses to overwrite an existing target unless `--force` is
provided:

```bash
uv run ritebook install-skill platform-skills/code-review \
  --target .claude/skills/code-review \
  --force
```

Direct `install-skill` runs write generated user-level installation state to:

```text
~/.config/ritebook/installations.json
```

Tests and automation can override both the index registry and direct-install
state paths:

```bash
uv run ritebook install-skill platform-skills/code-review \
  --target .claude/skills/code-review \
  --registry-path <path-to-indexes.json> \
  --installation-registry-path <path-to-installations.json>
```

Repositories can declare repeatable skill installations in `ritebook.toml`:

```toml
[targets]
claude = ".claude/skills"
agents = ".agents/skills"

[[skills]]
name = "platform-skills/code-review"
target = "claude"

[[skills]]
name = "platform-skills/test-driven-development"
target = "agents"

[[skills]]
name = "company-agents/security-review"
target_path = "../shared-agent-skills/security-review"
```

Install all declared skills from the default `ritebook.toml` in the current
working directory:

```bash
uv run ritebook install
```

Use `--file` to read a different requirements file, `--force` to replace existing
target directories, and `--lockfile` to choose where generated lock state is
written:

```bash
uv run ritebook install \
  --file path/to/ritebook.toml \
  --force \
  --registry-path <path-to-indexes.json> \
  --lockfile <path-to-ritebook.lock>
```

`target = "nickname"` resolves to `<targets.nickname>/<skill-name>`.
`target_path` is used exactly as the target path for that skill entry. Each skill
entry must use exactly one of `target` or `target_path`.

After a successful requirements install, Ritebook writes deterministic generated
state to `ritebook.lock` by default. Commit `ritebook.lock` when a repository uses
`ritebook.toml` so repo-local skill installation state is reviewable and
repeatable.

By default, Ritebook stores registry metadata and cached index contents under:

```text
~/.config/ritebook/indexes.json
~/.cache/ritebook/indexes/<effective-index-name>/ritebook-index.json
~/.cache/ritebook/git/<source-cache-id>/
```

Effective index names are single path-safe kebab-case segments, so cached index
contents are stored directly under that name.

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
linting, type checking, non-E2E tests, package builds, Docker E2E, patch
releases, and PyPI publishing. Docker E2E runs as a separate mandatory job in
parallel with the main quality-check job, and releases require both jobs to pass.

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
