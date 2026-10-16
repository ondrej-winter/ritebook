# ritebook

Ritebook is a Python CLI for validating, installing, synchronizing, and
contributing Agent Skills, and for publishing, registering, and browsing
Git-backed skill indexes. Publishers generate reviewable `ritebook-index.json`
files; consumers install skills from registered indexes.

## Specifications

This README covers setup and common workflows. [Specifications](docs/specs/README.md)
define current contracts and their design rationale.
[Repository instructions](AGENTS.md) govern agent contributions.

## Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/) 0.13.0 or newer for host development and CI
  dependency management and command execution
- GNU Make for the shared local and CI task interface
- Git for index, installation, and contribution workflows
- Docker for the complete verification gate

## Development setup

Install development dependencies:

```bash
make setup
```

Setup checks that `uv.lock` matches `pyproject.toml`; it does not update the
lockfile implicitly.

Install the Git pre-commit hook:

```bash
make install-hooks
```

Run pre-commit across the repository when changing the hook
configuration or before opening a PR:

```bash
make pre-commit
```

Pre-commit checks file hygiene, Ruff formatting and linting, ty types, Import
Linter architecture contracts, and tests. It complements the full quality gate.

The Ruff hooks check without rewriting Python files. Ruff, ty, and pytest run
when Python files, `pyproject.toml`, `uv.lock`, `Makefile`, or
`.pre-commit-config.yaml` change.

Run the standard local quality gate:

```bash
make quality
```

This checks formatting, Ruff linting, ty types, Import Linter architecture
contracts, and the default non-E2E pytest suite. `make help` lists the
corresponding leaf targets and formatting or lint-fix commands.

`make architecture` enforces inward dependencies, private slice boundaries,
shared-kernel and composition-root isolation, and an explicit I/O-library denylist,
including imports under `TYPE_CHECKING`. See [repository instructions](AGENTS.md)
for boundary rules. Dynamic imports and side effects through permitted APIs still
need code review.

Plain pytest deselects Docker E2E tests by default. The Docker image
explicitly opts into them with `--run-e2e -m e2e`; direct host opt-in is rejected
because it cannot establish the clean installed-wheel boundary.

For implementation changes, run the complete verification gate before handoff:

```bash
make verify
```

`make verify` runs the standard quality gate, checks lockfile freshness, builds
distributions, and builds and runs Docker E2E. It fails if Docker is unavailable.
`make docker-e2e` runs only the Docker build and test steps.

`Dockerfile.e2e` tests an installed wheel in a clean consumer environment, with
separate locked test tooling and no project source or developer-local state.
Tests run unprivileged against local Git fixtures. CI runs the same Docker gate
in parallel with non-E2E quality checks. The
[Docker E2E specification](docs/specs/docker-e2e-testing-spec.md) defines isolation,
networking, and the limits of this verification.

Build the package distributions without running the other gates:

```bash
make build
```

The source distribution excludes the externally sourced `.agents/` tree.

Audit locked runtime and development dependencies for known vulnerabilities and
adverse package status:

```bash
make deps-audit
```

This target uses uv's preview audit command and requires network access. It does
not update `uv.lock`.

Print the installed Ritebook version:

```bash
uv run ritebook --version
```

## CLI command structure

Ritebook groups operations by resource:

```text
ritebook skills <lint|list|install|sync|contribute> ...
ritebook indexes <publish|add|list|update> ...
```

## Publisher skill index generation

Validate skill headers under an explicit skills root:

```bash
uv run ritebook skills lint --root <path>
```

`skills lint` finds visible `SKILL.md` candidates and reports invalid nested
declarations and symlinked candidates without following symlinks.

A skill must be either `<skill>/SKILL.md` at the catalog root or
`<collection>/<skill>/SKILL.md` one level below an implicit collection. Every
catalog segment must be a canonical kebab-case identifier. A node cannot be both
a root skill and a collection, and a `SKILL.md` directly at the skills root is
invalid. The [Agent Skills specification](https://agentskills.io/specification) is
the canonical baseline for portable skill headers. The minimal accepted header
contains only `name` and `description`; Ritebook also supports the standard
optional `license`, `compatibility`, `metadata`, and `allowed-tools` fields.
Every `metadata` value must be a string; nested metadata is invalid. An empty
catalog is valid. Successful lint runs report `Checked N skill(s)` without writing
an index. The [Skill Linter specification](docs/specs/skill-linter-spec.md) defines
the full header and diagnostic contract.

The Git-tracked `.agents/` tree contains externally sourced skills. Their owning
collections validate them; Ritebook's local, pre-commit, and CI quality gates
exclude the tree, including file-hygiene hooks.

Generate an index from the validated catalog:

```bash
uv run ritebook indexes publish --skills-root <path> --name <published-name>
```

Run `indexes publish` from the repository directory that will contain
`ritebook-index.json`. The required `--skills-root` may be relative or absolute,
but must resolve to that directory or a descendant. Ritebook stores it as a
portable repository-relative `skills_root`. The required `--name` must be a stable
single-segment kebab-case identifier such as `company-skills`. It becomes
`index.name` in the generated index and the default consumer local alias.

`indexes publish` uses the same validation flow as `skills lint`. It writes only
when every discovered skill is valid, using that pass's immutable snapshot.

Review the generated `ritebook-index.json` before committing it with the related
skill changes. The [publisher specification](docs/specs/publisher-spec.md) defines
generation and output safety; the
[shared catalog contract](docs/specs/shared-catalog-contract-spec.md) defines
schema-v1 fields, paths, and input limits.

## Consumer index registry

Register and refresh Git-backed Ritebook skill indexes, then browse and install
their skills.

Register a Git URL source:

```bash
uv run ritebook indexes add --source git@github.com:company/internal-skills.git
```

Use SSH configuration, a Git credential helper, or another Git-managed
authentication mechanism. Do not embed usernames, passwords, or tokens in a
standard URL: Ritebook rejects URL authority user-info before running Git or
writing local state. scp-like SSH sources such as the example above remain
supported.

Register an already-cloned local Git repository without Ritebook mutating it:

```bash
uv run ritebook indexes add --source ./internal-skills
```

Assign a local alias to resolve a published-name collision, or replace an
existing registration with the same alias:

```bash
uv run ritebook indexes add \
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

Registry schema v2 records whether an alias came from the published name or an
explicit `--alias`. Legacy schema-v1 registries require the force recovery
described below.

Refresh a registered index from its remembered Git source:

```bash
uv run ritebook indexes update platform-skills
```

Force a clean rebuild of Ritebook-owned consumer state when the managed clone or
cached index may be damaged:

```bash
uv run ritebook indexes update platform-skills --force
uv run ritebook indexes update --all --force
```

For Git URL registrations, `--force` fetches through a fresh managed clone and
switches the registry only after the committed root `ritebook-index.json` validates.
For local repository registrations, it re-reads the clean committed repository
without deleting or mutating it. The previous coherent registry/cache binding
remains usable if rebuilding fails. A superseded managed clone is removed only after no
other registry alias references it. This flag repairs consumer state; it does not
generate or publish an upstream index.

The same forced update recovers schema-v1 `indexes.json` registrations from their
saved aliases and source locations. It discovers each source's current branch and
rebuilds validated provenance. Failed registrations remain saved for retry; rerun
`indexes update --all --force` after fixing their sources. The registry becomes
schema v2 once all registrations are rebuilt. Ordinary reads remain unavailable
until recovery completes. Use `--all` to finish a registry with multiple legacy
entries. Legacy cache paths are left untouched.

List registered indexes:

```bash
uv run ritebook indexes list
```

List skills from all cached registered indexes:

```bash
uv run ritebook skills list
```

List skills from one local index alias:

```bash
uv run ritebook skills list --index platform-skills
```

Show cached skill descriptions when available:

```bash
uv run ritebook skills list --show-description
```

`skills list` works offline from the local registry and digest-verified cached
indexes. It does not refresh sources or read skill files.

Non-empty output is grouped by local alias in a deterministic tree:

```text
Indexes
├── data-skills
│   └── query-helper
└── platform-skills
    ├── browser/skill-b
    └── skill-a
```

The tree shows each skill's catalog-relative path. Append it to the local alias
for `skills install`. With `--show-description`, Ritebook appends the cached
description:

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

### Registry storage and overrides

Default registry and cache locations:

```text
~/.config/ritebook/indexes.json
~/.cache/ritebook/registries/<registry-id>/indexes/<local-alias>/<sha256-hex>/ritebook-index.json
~/.cache/ritebook/registries/<registry-id>/git/<source-cache-id>/
```

`<registry-id>` is the SHA-256 hex of the canonical registry path, separating
caches even when registries share aliases and a cache root. Local aliases are
single path-safe kebab-case segments. Each validated index is
stored as an immutable generation under its alias, keyed by the lowercase SHA-256
hex recorded in registry metadata. The registry file atomically switches to the
new generation only after the complete cache file has been synchronized.

Tests and automation can override these locations:

```bash
uv run ritebook indexes add \
  --source <git-url-or-local-git-repo> \
  --registry-path <path-to-indexes.json> \
  --cache-root <cache-directory>

uv run ritebook indexes update <local-alias> \
  --registry-path <path-to-indexes.json> \
  --cache-root <cache-directory>

uv run ritebook skills list \
  --registry-path <path-to-indexes.json>

uv run ritebook skills list \
  --index <local-alias> \
  --registry-path <path-to-indexes.json>
```

Consumer registration requires published schema version `1` indexes to include
`index.name` metadata. Legacy `ritebook-index.json` files without that metadata
are rejected. The [Index Registry specification](docs/specs/index-registry-spec.md)
defines registration, refresh, cache safety, and recovery.

## Consumer skill installation

Ritebook installs skills from registered Git-backed indexes. Direct `skills
install` is offline against the currently registered commit-and-index binding.
Repository `skills sync` refreshes every referenced local alias before resolving
requirements and aborts without target or installation-state mutation if any
refresh fails.

### Install one skill

Install one fully qualified skill into an explicit target path:

```bash
uv run ritebook skills install platform-skills/code-review \
  --target .claude/skills/code-review
```

For skills published in a first-level collection, use the relative skill path
shown by `skills list` after the local alias:

```bash
uv run ritebook skills install platform-skills/browser/runtime-verification \
  --target .claude/skills/runtime-verification
```

`skills install` resolves that path exactly and never expands a collection.
`platform-skills/runtime-verification` does not select
`platform-skills/browser/runtime-verification`.

Ritebook copies the whole skill directory and creates missing target parent
directories. Without `--force`, an existing target is preserved and direct
install exits nonzero. With `--force`, Ritebook transactionally replaces the
exact existing directory even when it is unmanaged or locally edited. The
previous tree is retained for rollback until ownership state commits. Symlinks,
regular files, special files, dangerous paths, unsafe ancestry, and targets that
change after inspection are still rejected.

Before planning or mutating targets, Ritebook validates the selected committed
`SKILL.md` and requires its name and normalized description to match the
digest-bound index entry.

```bash
uv run ritebook skills install platform-skills/code-review \
  --target .claude/skills/code-review \
  --force
```

Direct `skills install` writes user-level installation state to:

```text
~/.config/ritebook/installations.json
```

Direct installation state uses strict schema version 3 and records ownership,
verified source provenance, and the installed-tree digest. On POSIX, Ritebook
writes `indexes.json` and `installations.json` with mode `0600`. Persisted sources
exclude standard-URL user-info; `indexes list` also strips it from displayed
sources. Legacy or unsafe installation state requires inspection and regeneration.

Tests and automation can override both the index registry and direct-install
state paths:

```bash
uv run ritebook skills install platform-skills/code-review \
  --target .claude/skills/code-review \
  --registry-path <path-to-indexes.json> \
  --installation-registry-path <path-to-installations.json>
```

### Sync declared skills

Declare repeatable repository installations in `ritebook.toml`:

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
target_path = "shared-agent-skills/security-review"
```

Refresh referenced indexes and process the skills declared by the default
`ritebook.toml` in the current working directory:

```bash
uv run ritebook skills sync
```

Use `--file` to read a different requirements file, `--force` to replace any
existing safe declared target directory with verified index content, and
`--lockfile` to choose where generated lock state is written:

```bash
uv run ritebook skills sync \
  --file path/to/ritebook.toml \
  --force \
  --registry-path <path-to-indexes.json> \
  --lockfile <path-to-ritebook.lock>
```

`target = "nickname"` resolves to `<targets.nickname>/<final-skill-name>`.
`target_path` specifies the exact target path for that skill entry. Each entry
must use exactly one of `target` or `target_path`. Sync targets are portable
paths relative to the requirements-file directory; absolute paths and parent
traversal are rejected.

In `ritebook.toml` only, a one-segment selector may select an implicit
first-level collection. For example, `platform-skills/browser` expands to the
indexed immediate children `browser/<skill>` in deterministic catalog-path order.
A collection requirement must use `target`, so each child is installed below the
target base by its final skill name; it cannot use `target_path`. Expansion never
matches deeper descendants or searches by `skills[].name`. Direct `skills install`
and `skills contribute` commands remain exact-only and never expand collections.

Sync uses the selected schema-v3 `ritebook.lock` as its only persistent
installation record and creates no `.ritebook/` bookkeeping. Commit the lockfile
when a repository uses `ritebook.toml`. It records current owned declarations,
installed-tree digests, provenance, status, and processing issues. Complete
no-change syncs produce byte-identical lock state. Skipped targets produce
`state = "partial"`, diagnostics, and a nonzero exit while independent successful
changes remain installed.

Locally modified skills are preserved with their recorded baseline. Diagnostics
show how to prepare a local contribution or explicitly replace the skill with
`--force`. If the selected lockfile is missing, sync installs missing targets but
preserves existing directories, even when they match the current index. Review
every current declaration before a force rerun: sync `--force` replaces **all**
selected targets, discarding local edits and unmanaged contents.

### Sync failures and legacy state

Run one mutating installation command at a time for the affected project and
targets. Sync acquires no installation operation lock and provides no concurrent
writer guarantee. Index-registry locking and direct-install recovery remain in
place.

Sync stages complete trees, revalidates each target, and atomically replaces the
lockfile document. It has no whole-sync rollback or automatic next-run recovery.
A failed or interrupted run may leave completed replacements with an older or
absent lockfile, an absent target during a directory swap, or temporary sibling
staging/previous-tree artifacts. Inspect targets, the lockfile, and reported
retained paths; rerun normally to identify preserved mismatches or unmanaged
targets. After reviewing or backing up valuable content in every declaration,
use `--force` to establish verified baselines. Inspect interrupted-run artifacts
before removing them; later syncs neither replay nor delete them automatically.

Existing `.ritebook/` files are ignored and left untouched. Before retiring old
state, finish any pending recovery with the previous Ritebook version or inspect
and reconcile it manually. A journal, transaction data, or sibling backup may be
the only copy of prior content. Once no old operation or recovery is pending,
remove only confirmed obsolete generated ledgers, lock files, and completed
recovery artifacts; preserve unrelated files. Do not delete the whole directory
without inspecting its contents. See the
[installation specification](docs/specs/skill-installation-spec.md) for the full
sync and direct-install contracts.

Removing an entry from `ritebook.toml` makes the next sync remove it from generated
lock state while leaving its directory untouched. Delete or archive an undeclared
skill directory when it is no longer wanted. If declared again later, the path is
unmanaged and requires `--force` to replace.

Older valid schema-v3 state may contain `desired: false` entries. Ritebook still
parses those files, but such entries do not establish ownership and disappear
from newly generated state unless the target is currently declared.

Schema-v1 and schema-v2 lockfiles and installation registries are rejected,
including with `--force`; they lack current ownership or canonical source-branch
provenance. Inspect and back up legacy state and targets, then move the rejected
state file aside before reinstalling. A fresh `skills sync` installs missing
targets and preserves existing directories until reviewed force replacement.
Shared `ritebook.lock` files have no forced private mode; Ritebook rejects
credential-bearing standard source URLs before writing.

Shared `ritebook.lock` entries require indexes registered from portable Git URLs.
An index registered from a local repository path remains available for browsing
and direct `skills install`, but `ritebook skills sync` rejects it before copying
because machine-local paths are not commit-safe. To migrate, register the same
published index from its Git URL, keeping the local alias when applicable, then
rerun `ritebook skills sync` to regenerate the lockfile.

## Contributing installed skill changes upstream

After editing a repo-local skill installed from `ritebook.toml`, prepare one
reviewable upstream contribution from its `ritebook.lock` provenance:

```bash
uv run ritebook skills contribute platform-skills/code-review
```

The reference must be `<local-alias>/<skill-path>` and resolves by exact indexed
path without falling back to `skill_name`. Collection-only references are not
expanded. By default, Ritebook reads `ritebook.lock` from the current working
directory and creates or reuses an isolated Ritebook-owned checkout under
`~/.cache/ritebook/contributions`. Tests and automation can override both paths:

```bash
uv run ritebook skills contribute platform-skills/code-review \
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
branch and commit. Branches use `ritebook/<skill-path-with-dashes>-<YYYYMMDDHHMMSS>`
in UTC. For a portable Git URL source with a usable `origin`, output resembles:

```text
Prepared contribution for platform-skills/code-review
Branch: ritebook/code-review-20260718201534
Commit: 0123456789abcdef0123456789abcdef01234567
Checkout: /path/to/contributions/0123456789abcdef/platform-skills-code-review-01234567
Next: cd /path/to/contributions/0123456789abcdef/platform-skills-code-review-01234567 && git push origin ritebook/code-review-20260718201534
```

Ritebook does not run the suggested command, push a branch, or open a merge
request or pull request. Inspect the checkout and commit before following it. The
[Skill Contribution specification](docs/specs/skill-contribution-spec.md) defines
provenance checks, checkout ownership, and failure behavior.

Contribution publishing accepts only desired schema-v3 lock entries with
`materialized` or `local_changes` status, an installed-tree digest, and a portable
`git_url` source. Schema-v1, schema-v2, issue-only, retained, and hand-written
`local_git_repo` entries fail before any contribution clone or Git operation,
with guidance to re-register by Git URL and regenerate the lockfile.

If the selected upstream skill path changed after the lockfile's
`source_revision`, Ritebook stops without merging or overwriting the upstream
change. Refresh/reinstall the skill and reconcile the changes manually
before retrying.

## Publishing

The GitHub Actions workflow in `.github/workflows/ci-cd.yaml` runs formatting,
linting, type checking, non-E2E tests, package builds, Docker E2E, patch
releases, and PyPI publishing. Docker E2E runs as a separate mandatory job in
parallel with the main quality-check job, and releases require both jobs to pass.

During initial development, releases stay on the `0.1.x` line and every
accepted push to `master` increments the patch version. The CI/CD workflow uses
Python Semantic Release to:

1. run the quality gate,
2. bump `pyproject.toml` from `0.1.x` to the next patch version,
3. update `uv.lock` to the same package version,
4. commit both version files together in a release commit,
5. atomically push that release commit to `master` with the matching `v0.1.x`
   tag,
6. publish a GitHub release without maintaining a changelog, and
7. publish the built distributions to PyPI in the same workflow run.

The release commit becomes the new `master` head, keeping repository metadata in
sync with Git tags and published packages. Its commit body contains `[skip ci]`,
so the generated push does not start another CI/CD workflow after the parent
commit has passed quality and Docker E2E. The release job also skips commits whose
message starts with `release: bump version to` to guard against release loops.
When the project is ready to move beyond patch-only `0.1.x` releases, the same
Semantic Release tooling can support normal commit-derived SemVer releases.

The default branch requires the stable `Quality checks` and `Docker E2E` status
checks. The repository owner retains an explicit ruleset bypass for the current
solo-maintainer direct-push workflow; other actors and pull requests remain
subject to the required checks. The release job uses a short-lived installation
token from the repository-scoped release GitHub App, which has an explicit
`Master` ruleset bypass. Before generating a release, the job verifies that
`origin/master` still identifies the triggering commit. It then uses a non-force,
atomic push for the generated release commit and tag, so a concurrent update fails
without partially publishing Git refs.

The GitHub App client ID is stored in the repository variable
`RITEBOOK_RELEASE_APP_CLIENT_ID`; its private key is stored as the `pypi`
environment secret `RITEBOOK_RELEASE_APP_PRIVATE_KEY`. The app must remain
installed only on this repository with `Contents: read and write` permission.

Publishing uses PyPI Trusted Publishing through GitHub Actions OIDC. Before the
first release, configure a trusted publisher for this repository in the PyPI
project settings:

- Repository owner: `ondrej-winter`
- Repository name: `ritebook`
- Workflow filename: `ci-cd.yaml`
- Environment name: `pypi`
