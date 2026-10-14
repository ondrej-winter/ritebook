# ritebook

Ritebook is a Python CLI for validating, publishing, registering, browsing, and
installing Agent Skill indexes. It supports publisher workflows that generate
reviewable `ritebook-index.json` files and consumer workflows that install skills
from registered Git-backed indexes.

## Specifications

[`docs/specs/`](docs/specs/README.md) is the canonical source for Ritebook's
product, shared-contract, and supported-workflow requirements. This README
provides setup and usage guidance; when its examples need more detail, the owning
specification defines the contract.

## Requirements

- Python 3.13 or newer
- [uv](https://docs.astral.sh/uv/) 0.13.0 or newer for host development and CI
  dependency management and command execution
- GNU Make for the shared local and CI task interface

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

Run the pre-commit hooks across the full repository when changing the hook
configuration or before opening a PR:

```bash
make pre-commit
```

Pre-commit provides fast local feedback for file hygiene, Ruff formatting and
linting, ty type checking, Import Linter architecture contracts, and tests. It
complements, but does not replace, the full local quality gate.

Run the standard local quality gate:

```bash
make quality
```

This checks formatting, Ruff linting, ty types, Import Linter architecture
contracts, and the default non-E2E pytest suite. Use `make help` to list the
corresponding leaf targets and explicit formatting or lint-fix commands.

Plain pytest execution deselects Docker E2E tests by default. The Docker image
explicitly opts into them with `--run-e2e -m e2e`; direct host opt-in is rejected
because it cannot establish the clean installed-wheel boundary.

Run the complete local verification gate before handoff:

```bash
make verify
```

`make verify` runs the standard quality gate, checks lockfile freshness, builds
the package distributions, and builds and runs Docker E2E. It fails if Docker is
unavailable rather than silently omitting E2E. `make docker-e2e` runs only the
Docker build and test steps.

`Dockerfile.e2e` is a clean installed-wheel test boundary, not production
packaging. It builds a wheel from the current source, installs that wheel and its
declared runtime dependencies into a consumer environment, and runs the E2E suite
from a separate locked test-tool environment. The final image contains the E2E
harness but not the project source, `pyproject.toml`, or `uv.lock`, so the tests
invoke the installed `ritebook` console script directly. Tests run as an
unprivileged user with a controlled writable home and use local Git repositories,
explicit registry files, and explicit cache directories. Normal container
networking is allowed, but the image receives no credentials or developer-local
Ritebook state. Docker is the only supported E2E execution path. CI/CD uses the
same build and run commands and runs Docker E2E as a mandatory quality gate in
parallel with the non-E2E quality checks.

Build the package distributions without running the other gates:

```bash
make build
```

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

Maintainers can validate skill headers and generate a reviewable skill catalog
index from an explicit skills root:

```bash
uv run ritebook skills lint --root <path>
```

The `skills lint` command iteratively finds visible `SKILL.md` candidates so
invalid nested declarations are reported, then enforces the schema-v1 catalog
layout. It does not follow symlinked skill directories or files; visible
symlinked candidates are reported as validation issues.
A skill must be either `<skill>/SKILL.md` at the catalog root or
`<collection>/<skill>/SKILL.md` one level below an implicit collection. Every
catalog segment must be a canonical kebab-case identifier. A node cannot be both
a root skill and a collection, and a `SKILL.md` directly at the skills root is
invalid. The [Agent Skills specification](https://agentskills.io/specification) is
the canonical baseline for portable skill headers. The minimal accepted header
contains only `name` and `description`; Ritebook also supports the standard
optional `license`, `compatibility`, `metadata`, and `allowed-tools` fields.
Compatible collection profiles may require standard optional flat metadata, but
nested metadata is invalid and every `metadata` value must be a string. YAML
mapping keys must be unique. Frontmatter may span any number of lines but must be
valid UTF-8 and at most 65,536 bytes including its delimiters and line endings.
An empty catalog is valid. Successful lint runs report `Checked N skill(s)` using
the regular-file candidate count without writing an index file. See the
[`Skill Linter` specification](docs/specs/skill-linter-spec.md) for the complete
header and diagnostic contract.

The repository's `.agents/` directory contains skills sourced from other
repositories. Their owning collections validate them, so Ritebook's local,
pre-commit, and CI quality gates exclude that tree from formatting, linting, type
checking, tests, and file-hygiene hooks. The directory remains Git-tracked.

```bash
uv run ritebook indexes publish --skills-root <path> --name <published-name>
```

Run `indexes publish` from the repository directory that will contain the generated
index. Ritebook always writes `ritebook-index.json` in that current directory.
The required `--skills-root` may be relative or absolute, but it must resolve to
that directory or one of its descendants. Ritebook serializes it as a portable
repository-relative `skills_root`; equivalent relative and absolute inputs
produce the same index paths. The `--name` option is required and must be a
stable single-segment kebab-case identifier such as `company-skills`; slashes are
not allowed because skill references use `<local-alias>/<skill-path>`. This
published name is written to `ritebook-index.json` as `index.name` and becomes the
default consumer local alias.
The `indexes publish` command reuses the same validation flow as `skills lint` and
refuses to write or overwrite `ritebook-index.json` when any discovered skill is
invalid. When validation succeeds, publication consumes the exact immutable
snapshot produced by that validation pass; it does not rescan skill files or
reparse frontmatter. The success message reports the canonical output path
`ritebook-index.json` relative to the invocation directory.

Review the generated `ritebook-index.json` before committing it with the related
skill changes. Schema v1 is a closed portable contract: consumers reject unknown
or duplicate JSON members, non-standard JSON constants, unsafe or non-portable
paths, invalid canonical UTC timestamps, non-normalized descriptions, excessive
input above 16 MiB, nesting above depth 32, and catalogs above 10,000 skills.

## Consumer index registry

Users can register, refresh, browse, and install skills from Git-backed Ritebook
skill indexes.

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
Registry schema v1 records whether an alias came from the published name or an
explicit `--alias`. Existing entries are inferred conservatively and gain the
explicit origin on their next successful registry write.

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
For local repository registrations, it re-reads the clean committed repository but
never deletes or mutates it. The previous coherent registry/cache binding remains
usable if rebuilding fails. A superseded managed clone is removed only after no
other registry alias references it. This flag repairs consumer state; it does not
generate or publish an upstream index.

List skills from all locally cached registered indexes:

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

The `skills list` command is offline-first: it reads the local registry and each
selected registry entry's cached `ritebook-index.json` file only. It does not
clone, fetch, pull, scan publisher skill directories, or read raw `SKILL.md`
files. Ritebook verifies each cached file's exact bytes against its registered
SHA-256 digest before decoding or parsing it.

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
after the local alias into `skills install`. With `--show-description`, Ritebook
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

Ritebook installs skills from registered Git-backed indexes. Direct `skills
install` is offline against the currently registered commit-and-index binding.
Repository `skills sync` refreshes every referenced local alias before resolving
requirements and aborts without target or installation-state mutation if any
refresh fails.

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

`skills install` resolves that path exactly and never expands a collection. A
shorthand such as
`platform-skills/runtime-verification` does not select
`platform-skills/browser/runtime-verification`.

Ritebook copies the whole skill directory and creates missing target parent
directories. Without `--force`, an existing target is preserved and direct
install exits nonzero. With `--force`, Ritebook transactionally replaces the
exact existing directory even when it is unmanaged or locally edited. The
previous tree is retained for rollback until ownership state commits. Symlinks,
regular files, special files, dangerous paths, unsafe ancestry, and targets that
change after inspection are still rejected:

Before planning or mutating targets, Ritebook validates the selected committed
`SKILL.md` and requires its name and normalized description to match the
digest-bound index entry.

```bash
uv run ritebook skills install platform-skills/code-review \
  --target .claude/skills/code-review \
  --force
```

Direct `skills install` runs write generated user-level installation state to:

```text
~/.config/ritebook/installations.json
```

Direct installation state uses strict schema version 3 and includes ownership,
verified commit, canonical-branch, and index-digest provenance, and the canonical
installed-tree digest. On POSIX platforms, Ritebook writes both `indexes.json`
and `installations.json` with mode
`0600`. Persisted source values never include standard-URL user-info, and `indexes
list` defensively removes such user-info from displayed sources. Legacy or unsafe
generated installation state is rejected and must be inspected and regenerated.

Tests and automation can override both the index registry and direct-install
state paths:

```bash
uv run ritebook skills install platform-skills/code-review \
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
`target_path` is used exactly as the target path for that skill entry. Each skill
entry must use exactly one of `target` or `target_path`. Sync targets are portable
paths relative to the requirements-file directory; absolute paths and parent
traversal are rejected.

In `ritebook.toml` only, a one-segment selector may select an implicit
first-level collection. For example, `platform-skills/browser` expands to the
indexed immediate children `browser/<skill>` in deterministic catalog-path order.
A collection requirement must use `target`, so each child is installed below the
target base by its final skill name; it cannot use `target_path`. Expansion never
matches deeper descendants or searches by `skills[].name`. Direct `skills install`
and `skills contribute` commands remain exact-only and never expand collections.

Sync transactionally writes strict schema-v3 generated state to `ritebook.lock`
and local ownership state to `.ritebook/installations.json`. Commit
`ritebook.lock` when a repository uses `ritebook.toml`; do not commit `.ritebook/`.
The generated files record only current declarations, their installed-tree
digests, materialization status, and any current processing issues. Complete
no-change syncs produce byte-identical lock state. Partial processing preserves
independent successful changes, writes truthful `state = "partial"` data,
reports each issue, and exits nonzero.

Sync never deletes a directory merely because its entry was removed from
`ritebook.toml`. The next sync leaves that directory untouched and removes it from
generated sync ownership and lock state. Delete or archive an undeclared skill
directory explicitly when it is no longer wanted. If the same path is declared
again later, it is unmanaged and requires `--force` to replace.

Older valid schema-v3 state may contain `desired: false` entries. Ritebook still
parses those files, but such entries do not establish ownership and disappear
from newly generated state unless the target is currently declared.

`--force` is destructive for selected targets: it discards unmanaged contents and
local edits at the exact selected directory after race-safe inspection. Review or
back up valuable changes before using it.

Schema-v1 and schema-v2 lockfiles and installation registries are rejected
without automatic migration because they lack current ownership or canonical
source-branch provenance. Inspect and remove or relocate legacy targets, then
rerun `skills sync` to generate schema-v3 state. Because `ritebook.lock` is
shared, Ritebook does not force a private file mode; it rejects
credential-bearing standard source URLs before
writing instead.

Each lock entry's `requirement` stores the exact catalog-qualified selector, such
as `platform-skills/browser/runtime-verification`. Its `skill_path` and
`skill_file` are different: they are safe paths relative to the source repository
and include the published `skills_root`, such as
`skills/browser/runtime-verification` and
`skills/browser/runtime-verification/SKILL.md`.

Shared `ritebook.lock` entries require indexes registered from portable Git URLs.
An index registered from a local repository path remains available for browsing
and direct `skills install`, but `ritebook skills sync` rejects it before copying because
relative, absolute, missing, or moved machine-local paths are not commit-safe. To
migrate, register the same published index from its Git URL (using the same local
alias when applicable), then rerun `ritebook skills sync` to regenerate the lockfile.

## Contributing installed skill changes upstream

After editing a repo-local skill installed from `ritebook.toml`, prepare one
reviewable upstream contribution from its `ritebook.lock` provenance:

```bash
uv run ritebook skills contribute platform-skills/code-review
```

The reference must be `<local-alias>/<skill-path>` and resolves by exact indexed
path without falling back to `skill_name`. Collection-only references are not
expanded. By default, Ritebook reads
`ritebook.lock` from the current working directory and creates or reuses an isolated,
Ritebook-owned checkout under `~/.cache/ritebook/contributions`. Tests and
automation can override both paths:

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

Contribution publishing accepts only desired schema-v3 lock entries with
`materialized` or `local_changes` status, an installed-tree digest, and a portable
`git_url` source. Schema-v1, schema-v2, issue-only, retained, and hand-written
`local_git_repo` entries fail before any contribution clone or Git operation,
with guidance to re-register by Git URL and regenerate the lockfile.

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
are rejected instead of guessing a name.

## Publishing

The GitHub Actions workflow in `.github/workflows/ci-cd.yaml` runs formatting,
linting, type checking, non-E2E tests, package builds, Docker E2E, patch
releases, and PyPI publishing. Docker E2E runs as a separate mandatory job in
parallel with the main quality-check job, and releases require both jobs to pass.

During the early project lifecycle, releases stay on the `0.1.x` line and every
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
commit has already passed quality and Docker E2E. The release job also skips
commits whose message starts with `release: bump version to` as defense in depth
against a release loop. When the project is ready to move beyond patch-only
`0.1.x` releases, the same Semantic Release tooling can be used for normal
commit-derived SemVer releases.

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

## Architecture direction

Future business capabilities should be implemented as vertical feature slices
under `src/ritebook/features/`, keeping domain, application ports/use cases, and
adapters separated according to hexagonal architecture principles.
