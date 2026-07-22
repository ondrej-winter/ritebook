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

Run the mandatory isolated Docker E2E gate before handoff:

```bash
docker build -f Dockerfile.e2e -t ritebook-e2e .
docker run --rm --network none ritebook-e2e
```

`Dockerfile.e2e` is an isolated end-to-end test boundary, not production
packaging. Image construction uses the network to obtain the pinned base image
and locked dependencies. Runtime tests execute as an unprivileged user with a
controlled writable home and no non-loopback IPv4 route. Tests use local Git
repositories, explicit registry files, and explicit cache directories. The image
does not receive host credentials or developer-local Ritebook state. CI/CD uses
the same build and run commands as this local workflow and runs Docker E2E as a
mandatory quality gate in parallel with the non-E2E quality checks.

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
uv run ritebook publish-index --skills-root <path> --index-name <published-name>
```

Run `publish-index` from the repository directory that will contain the generated
index. Ritebook always writes `ritebook-index.json` in that current directory.
The required `--skills-root` may be relative or absolute, but it must resolve to
that directory or one of its descendants. Ritebook serializes it as a portable
repository-relative `skills_root`; equivalent relative and absolute inputs
produce the same index paths. The `--index-name` option is required and must be a
stable single-segment kebab-case identifier such as `company-skills`; slashes are
not allowed because skill references use `<local-alias>/<skill-path>`. This
published name is written to `ritebook-index.json` as `index.name` and becomes the
default consumer local alias.
The `publish-index` command reuses the same validation flow as `lint-skills` and
refuses to write or overwrite `ritebook-index.json` when any discovered skill is
invalid. When validation succeeds, the success message reports the canonical
output path `ritebook-index.json` relative to the invocation directory.

Review the generated `ritebook-index.json` before committing it with the related
skill changes.

## Consumer index registry

Users can register, refresh, browse, and install skills from Git-backed Ritebook
skill indexes.

Register a Git URL source:

```bash
uv run ritebook add-index --source git@github.com:company/internal-skills.git
```

Use SSH configuration, a Git credential helper, or another Git-managed
authentication mechanism. Do not embed usernames, passwords, or tokens in a
standard URL: Ritebook rejects URL authority user-info before running Git or
writing local state. scp-like SSH sources such as the example above remain
supported.

Register an already-cloned local Git repository without Ritebook mutating it:

```bash
uv run ritebook add-index --source ./internal-skills
```

Assign a local alias to resolve a published-name collision, or replace an
existing registration with the same alias:

```bash
uv run ritebook add-index \
  --source git@github.com:company/internal-skills.git \
  --alias platform-skills \
  --force
```

Each index has a publisher-owned name in `ritebook-index.json` and a local alias
in the consumer registry. The alias defaults to the published name. `--alias`
changes only the local namespace used for cache paths, updates, listing, and
skill references; it does not rewrite publisher metadata. If a project shares
alias-based references in `ritebook.toml` or `ritebook.lock`, collaborators and
CI must register the source with the same alias.

Refresh a registered index from its remembered Git source:

```bash
uv run ritebook update-index --name platform-skills
```

List skills from all locally cached registered indexes:

```bash
uv run ritebook list-skills
```

List skills from one local index alias:

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

Non-empty output is grouped by local alias in a deterministic tree:

```text
Indexes
├── platform-skills
│   ├── skill-a
│   └── browser/skill-b
└── data-skills
    └── query-helper
```

By default, the tree shows each skill's cached relative path, which can be copied
after the local alias into `install-skill`. With `--show-description`, Ritebook
appends descriptions cached from publisher indexes when that metadata is present:

```text
Indexes
└── platform-skills
    └── skill-a — Helps with platform workflows.
```

Relative paths identify skills within an index. Duplicate skill names are valid at
different paths, such as `backend/code-review` and `frontend/code-review`; Ritebook
does not fall back from a path to the final skill name.

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

For skills published below subfolders, use the relative skill path shown by
`list-skills` after the local alias:

```bash
uv run ritebook install-skill platform-skills/browser/runtime-verification \
  --target .claude/skills/runtime-verification
```

`install-skill` resolves that path exactly. A shorthand such as
`platform-skills/runtime-verification` does not select
`platform-skills/browser/runtime-verification`.

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

On POSIX platforms, Ritebook writes both `indexes.json` and `installations.json`
with mode `0600`. Persisted source values never include standard-URL user-info, and
`list-indexes` defensively removes such user-info from displayed sources. Existing
unsafe generated state is rejected and must be removed and regenerated.

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

`target = "nickname"` resolves to `<targets.nickname>/<final-skill-name>`.
`target_path` is used exactly as the target path for that skill entry. Each skill
entry must use exactly one of `target` or `target_path`.

In `ritebook.toml`, a `name` may also select a folder prefix. For example,
`platform-skills/browser` installs all indexed skills below `browser/` in
deterministic path order. Folder expansion still follows paths and never searches
by `skills[].name`.

After a successful requirements install, Ritebook writes deterministic generated
state to `ritebook.lock` by default. Commit `ritebook.lock` when a repository uses
`ritebook.toml` so repo-local skill installation state is reviewable and
repeatable. Because the lockfile is meant to be shared, Ritebook does not force a
private file mode; it rejects credential-bearing standard source URLs before
writing instead.

Shared `ritebook.lock` entries require indexes registered from portable Git URLs.
An index registered from a local repository path remains available for browsing
and direct `install-skill`, but `ritebook install` rejects it before copying because
relative, absolute, missing, or moved machine-local paths are not commit-safe. To
migrate, register the same published index from its Git URL (using the same local
alias when applicable), then rerun `ritebook install` to regenerate the lockfile.

## Contributing installed skill changes upstream

After editing a repo-local skill installed from `ritebook.toml`, prepare one
reviewable upstream contribution from its `ritebook.lock` provenance:

```bash
uv run ritebook publish-skill-change platform-skills/code-review
```

The reference must be `<local-alias>/<skill-path>` and resolves by exact indexed
path without falling back to `skill_name`. By default, Ritebook reads
`ritebook.lock` from the current working directory and creates or reuses an isolated,
Ritebook-owned checkout under `~/.cache/ritebook/contributions`. Tests and
automation can override both paths:

```bash
uv run ritebook publish-skill-change platform-skills/code-review \
  --lockfile <path-to-ritebook.lock> \
  --contribution-root <checkout-root>
```

Ritebook compares the installed skill with the current upstream skill. If the
skill is unchanged, the command succeeds without creating a branch or commit:

```text
No local changes to publish for platform-skills/code-review
```

When local changes exist, Ritebook copies only that skill into the isolated
checkout, validates it, regenerates `ritebook-index.json`, and creates a local
branch and commit. Branches use
`ritebook/<skill-path-with-dashes>-<YYYYMMDDHHMMSS>` in UTC. For a portable Git
URL source with a usable `origin`, output resembles:

```text
Prepared contribution for platform-skills/code-review
Branch: ritebook/code-review-20260718201534
Commit: 0123456789abcdef0123456789abcdef01234567
Checkout: /path/to/contributions/0123456789abcdef/platform-skills-code-review-01234567
Next: cd /path/to/contributions/0123456789abcdef/platform-skills-code-review-01234567 && git push origin ritebook/code-review-20260718201534
```

Ritebook does not run the suggested command, push any branch, or open a merge
request or pull request. Inspect the checkout and commit before following the
suggested next step.

Contribution publishing accepts only portable `git_url` entries from shared
`ritebook.lock`. Legacy or hand-written `local_git_repo` entries fail before any
contribution clone or Git operation, with guidance to re-register by Git URL and
regenerate the lockfile.

If the selected upstream skill path changed after the lockfile's
`source_revision`, Ritebook stops instead of attempting to merge or overwrite the
upstream change. Refresh/reinstall the skill and reconcile the changes manually
before retrying.

By default, Ritebook stores registry metadata and cached index contents under:

```text
~/.config/ritebook/indexes.json
~/.cache/ritebook/indexes/<local-alias>/<sha256-hex>/ritebook-index.json
~/.cache/ritebook/git/<source-cache-id>/
```

Local aliases are single path-safe kebab-case segments. Each validated index is
stored as an immutable generation under its alias, keyed by the lowercase SHA-256
hex recorded in registry metadata. The registry file atomically switches to the
new generation only after the complete cache file has been synchronized.

Tests and automation can override these locations:

```bash
uv run ritebook add-index \
  --source <git-url-or-local-git-repo> \
  --registry-path <path-to-indexes.json> \
  --cache-root <cache-directory>

uv run ritebook update-index \
  --name <local-alias> \
  --registry-path <path-to-indexes.json> \
  --cache-root <cache-directory>

uv run ritebook list-skills \
  --registry-path <path-to-indexes.json>

uv run ritebook list-skills \
  --index-name <local-alias> \
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
