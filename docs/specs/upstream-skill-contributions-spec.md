# Spec: Upstream Skill Contributions

> **Status:** Active
> **Owner:** Ritebook maintainers
> **Spec version:** 1.1
> **Last reviewed:** 2026-07-22
> **Implementation state:** Partially implemented
> **Dependencies:** [Consumer Skill Installation](install-skill-spec.md), [Consumer Git Index Registry](consumer-git-index-registry-spec.md), and [Publisher Skill Index Generation](publisher-index-generation-spec.md)
> **Associated ADRs:** [ADR 0001: Source Provenance and Trust](../adr/0001-source-provenance-and-trust.md)

## Objective

Ritebook provides a safe contribution workflow for developers who improve
repo-local installed skills and want to propose those changes back to the
original curated skill repository.

The first workflow is a platform-neutral Git contribution core exposed through a
`publish-skill-change` command. It prepares a reviewable branch and local commit
in a Ritebook-owned isolated checkout. It prints a suggested `git push` command
when a usable origin exists, or manual inspection guidance otherwise. It must not
directly mutate canonical source branches, managed index cache clones, or
user-owned local source repositories.

## Implementation status

- Ritebook already supports Git-backed index registration and updates through
  `add-index`, `update-index`, and `list-indexes`.
- Ritebook already supports skill installation through direct `install-skill` and
  requirements-file `install` workflows.
- `ritebook.toml` can declare desired repo-local installed skills.
- Generated `ritebook.lock` records installed-skill provenance, including
  `requirement`, `index_name`, `target`, `source`, `source_type`,
  `source_revision`, `index_digest`, `skill_path`, and `skill_file` for
  requirements-file installs.
- Installation persists the same commit and index-digest binding verified during
  index registration and source resolution, as required by
  [ADR 0001](../adr/0001-source-provenance-and-trust.md).
- Existing publisher workflows can validate skills and regenerate
  `ritebook-index.json`.
- The workflow is implemented in the `skill_contribution` feature slice.
- Exact qualified-requirement resolution exists; rejecting collection selectors
  and over-deep catalog selectors remains to be implemented.
- The project follows hexagonal architecture with vertical feature slices under
  `src/ritebook/features/`.

## Desired behavior

### Publish one installed skill change

A developer can prepare a contribution for one repo-local installed skill:

```bash
uv run ritebook publish-skill-change platform-skills/code-review
```

The command publishes a proposed change for review. It does not publish directly
to the upstream default branch.

Requirements:

- The skill reference must be fully qualified as
  `<local-alias>/<catalog-selector>` and must exactly match a lockfile entry's
  stored `requirement`.
- The catalog selector must be `<skill>` or `<collection>/<skill>`, with every
  segment using the canonical 1–64 character Ritebook kebab-case identifier form.
  A collection selector is not a skill and cannot be used as a contribution
  target.
- The command only supports skills installed from `ritebook.toml` and recorded in
  `ritebook.lock` for the MVP.
- Ritebook reads `ritebook.lock` from the current working directory by default.
- Ritebook resolves exactly one lockfile entry for the requested skill reference.
- Ritebook uses the lockfile entry to locate:
  - the installed repo-local target path,
  - the source repository,
  - the source type,
  - the locked source revision,
  - the exact cached-index digest used for installation,
  - the source skill directory path, and
  - the source `SKILL.md` path.
- Ritebook fails clearly when no matching lockfile entry exists, the target path
  is missing, or the lockfile does not contain enough provenance.
- Ritebook verifies that the locked commit and index binding are available before
  comparing the installed repo-local skill directory with the source skill
  directory at the selected upstream base.
- Ritebook exits successfully with a concise no-op message when there are no local
  skill changes to contribute.
- Ritebook creates a contribution branch in an isolated Ritebook-owned checkout
  when local changes exist.
- Ritebook copies the installed repo-local skill directory back to the source
  skill directory inside the isolated checkout.
- Ritebook runs existing skill validation before creating a commit.
- Ritebook regenerates `ritebook-index.json` before creating a commit.
- Before reading or regenerating the index, Ritebook rejects a symlinked
  `ritebook-index.json` or any symlink component in the contribution checkout
  path. Rejection occurs before publisher execution and must not modify an
  external symlink target.
- Ritebook creates a local Git commit with a generated message.
- Ritebook prints the contribution checkout path, branch name, commit hash, and
  either suggested push instructions or manual inspection guidance.

### CLI shape

Initial command:

```bash
uv run ritebook publish-skill-change <local-alias>/<skill-path>
```

Path overrides:

```bash
uv run ritebook publish-skill-change <local-alias>/<skill-path> \
  --lockfile <path-to-ritebook.lock> \
  --contribution-root <path-to-ritebook-owned-contribution-checkouts>
```

The following command shapes are uncommitted future ideas. Ritebook maintainers
must approve a new specification or tracked implementation plan before adding
them; they should remain compatible with the core workflow:

```bash
uv run ritebook publish-skill-change platform-skills/code-review --push
uv run ritebook publish-skill-change platform-skills/code-review --open-mr
uv run ritebook publish-skill-change platform-skills/code-review --base <branch-or-ref>
```

Success output should be concise, for example:

```text
Prepared contribution for platform-skills/code-review
Branch: ritebook/code-review-20260718201534
Commit: 0123456789abcdef0123456789abcdef01234567
Checkout: /Users/me/.cache/ritebook/contributions/0123456789abcdef/platform-skills-code-review-01234567
Next: cd /Users/me/.cache/ritebook/contributions/0123456789abcdef/platform-skills-code-review-01234567 && git push origin ritebook/code-review-20260718201534
```

No-change output should be concise, for example:

```text
No local changes to publish for platform-skills/code-review
```

Error output should be clear and user-facing, for example:

```text
ritebook: error: no lockfile entry found for platform-skills/code-review
ritebook: error: installed skill target .agents/skills/code-review does not exist
ritebook: error: lockfile skill entry at position 0 is missing verified source_revision; regenerate ritebook.lock by running ritebook install
ritebook: error: locked source revision is unavailable; restore the source history or reinstall the skill to regenerate ritebook.lock
ritebook: error: upstream changed since locked revision; resolve the source changes and retry
ritebook: error: skill validation failed; contribution commit was not created
```

### Contribution checkout behavior

Ritebook must prepare the change in an isolated checkout it owns.

Requirements:

- Do not use the managed index cache clone as the contribution workspace.
- Do not mutate user-owned local source repositories by default.
- For Git URL sources, create or reuse a Ritebook-owned contribution clone under a
  dedicated contribution cache root.
- Fetch source `origin` before selecting the upstream base when the source has an
  origin remote.
- Require the full locked `source_revision` to exist in the isolated checkout and
  verify that root `ritebook-index.json` at that commit matches `index_digest`.
- Branch from the current upstream base for the MVP.
- Warn or fail clearly when the current upstream base differs from the locked
  `source_revision` and the source skill changed upstream since installation.
- Keep contribution checkout paths deterministic enough to be discoverable but
  avoid unsafe collisions between indexes, sources, and skill paths.
- Leave the prepared checkout in place after success so the developer can inspect,
  push, amend, or discard it manually.

The MVP uses reusable deterministic contribution clones under the Ritebook-owned
contribution root. Each checkout path combines a source digest with the local
alias, skill-path slug, and requirement digest. Ritebook marks owned clones,
rejects unmarked directories at a reusable checkout path, and resets/cleans only
those marked clones before preparing another contribution. The default root is
`~/.cache/ritebook/contributions`; `--contribution-root` overrides it for tests
and automation.

### Upstream comparison behavior

The locked `source_revision` is the verified installed baseline. Ritebook may
compare and contribute against the current upstream base only after proving the
selected skill path has not changed between that locked commit and the current
base.

Requirements:

- If the installed skill and current upstream source skill are identical, report a
  no-op.
- If the installed skill differs and upstream did not change since the locked
  revision for that skill path, prepare the contribution normally.
- If upstream changed since the locked revision, report the condition clearly.
- If the locked commit is unavailable or its index bytes do not match
  `index_digest`, fail before copying installed content or creating a branch
  commit. Do not substitute a current branch or tag.
- The MVP fails instead of attempting automatic conflict resolution.
- The error should include enough guidance for the developer to update/reinstall
  the skill or manually reconcile the upstream change without dumping raw skill
  contents.

### Commit behavior

Ritebook creates a normal Git commit in the isolated contribution checkout.

Requirements:

- The generated branch name uses
  `ritebook/<skill-path-with-dashes>-<YYYYMMDDHHMMSS>` with a UTC timestamp.
- Collected skill paths replace `/` with `-` in the branch slug.
- The generated commit message must be clear and imperative.
- The commit should include the changed skill directory and regenerated
  `ritebook-index.json` when validation succeeds.
- Ritebook must not create a commit when validation or index regeneration fails.
- Ritebook must not push by default.

Example generated commit message:

```text
Update code-review skill from Ritebook contribution
```

## Data and provenance requirements

The MVP depends on the end-to-end provenance contract in
[ADR 0001](../adr/0001-source-provenance-and-trust.md) and on lockfile provenance
from requirements-file installation.

Required lockfile fields for each publishable entry:

- `requirement`: exact fully qualified catalog selector resolved during
  installation. Contribution selection compares the requested local alias and
  catalog selector to this field as one qualified value.
- `index_name`: compatibility-sensitive schema-v1 field containing the local alias
  from `requirement`; it is not publisher `index.name`.
- `skill_name`: resolved skill name.
- `target`: repo-local installed skill target path.
- `source`: portable Git URL propagated from requirements installation.
- `source_type`: must be `git_url`; shared lockfiles do not support
  `local_git_repo` entries.
- `source_revision`: required full commit object ID bound during index validation
  and used for installation.
- `index_digest`: required SHA-256 digest that both the exact cached index used to
  resolve the installation and root `ritebook-index.json` at `source_revision`
  were verified to match.
- `skill_path`: source skill directory path relative to the source repository.
- `skill_file`: source `SKILL.md` path relative to the source repository.
- `index_schema_version`: publisher index schema version used at install time.

Catalog depth and segment validation applies to the selector encoded in
`requirement`, not to `skill_path` or `skill_file`. The latter include the
published `skills_root`, may contain additional safe segments, and remain subject
to repository-relative path validation before checkout or comparison.

Pre-release schema-v1 lockfiles missing `source_revision` or `index_digest` are
rejected with guidance to refresh registration and reinstall. Ritebook does not
infer missing provenance from the source's current `HEAD`.

Legacy or hand-written lock entries with `source_type = "local_git_repo"` are
rejected at lockfile ingestion before contribution workspace or Git operations.
The diagnostic does not echo the machine-local path and directs the user to
register the index from a Git URL and reinstall to regenerate `ritebook.lock`.

## Project structure

The implementation uses the `skill_contribution` vertical feature slice:

```text
src/ritebook/features/skill_contribution/
├── application/
│   ├── dtos/
│   │   └── publish_skill_change.py
│   ├── ports/
│   │   ├── publish_skill_change.py
│   │   ├── contribution_checkout.py
│   │   ├── contribution_lockfile.py
│   │   ├── skill_change_detector.py
│   │   ├── skill_directory.py
│   │   ├── skill_source_workspace.py
│   │   ├── skill_validator.py
│   │   └── index_regenerator.py
│   └── use_cases/
│       └── publish_skill_change.py
└── adapters/
    └── outbound/
        ├── contribution_checkout/
        │   └── adapter.py
        ├── git_workspace/
        │   └── adapter.py
        ├── index_regeneration/
        │   └── adapter.py
        ├── json_lockfile/
        │   └── reader.py
        ├── skill_directory/
        │   └── adapter.py
        └── validation/
            └── adapter.py
```

CLI integration and composition root:

- `src/ritebook/adapters/inbound/cli/parser.py`
- `src/ritebook/features/skill_contribution/adapters/inbound/cli/commands.py`
- `src/ritebook/adapters/inbound/cli/adapter.py`
- `src/ritebook/cli.py`

Tests should mirror source ownership:

```text
tests/unit/features/skill_contribution/
├── application/
│   └── test_publish_skill_change.py
└── adapters/outbound/
    ├── test_contribution_checkout.py
    ├── test_git_workspace.py
    ├── test_index_regeneration_adapter.py
    ├── test_json_lockfile_reader.py
    ├── test_skill_directory_adapter.py
    └── test_validation_adapter.py
```

## Conventions

- Keep application logic independent of Git commands, filesystem copying, JSON
  parsing, and CLI output formatting.
- Use application-owned DTOs at application boundaries.
- Use explicit inbound and outbound ports.
- Validate external inputs at adapter boundaries.
- Treat lockfile paths and publisher index paths as untrusted external data until
  validated.
- Run Git commands non-interactively and disable paging.
- Do not log or print secrets, Git credentials, raw skill contents, raw index
  contents, or copied file contents.
- Keep generated branch names, output paths, and commit messages deterministic
  enough for tests and review.

## Testing strategy

### Application tests

Cover:

- Resolves one fully qualified skill from lockfile provenance.
- Rejects missing or malformed skill references.
- Rejects missing lockfile entries.
- Rejects lockfile entries missing required provenance fields.
- Rejects an unavailable locked commit or index-digest mismatch before preparing
  a contribution.
- Reports no-op when installed skill content matches upstream source content.
- Prepares a contribution branch when local installed content differs.
- Refuses to create a commit when validation fails.
- Refuses or warns clearly when upstream changed since `source_revision`.
- Includes contribution checkout path, branch name, and commit hash in the result.

### Lockfile reader tests

Cover:

- Reads valid `ritebook.lock` entries.
- Rejects invalid JSON.
- Rejects unsupported lockfile schema versions.
- Rejects missing required fields for contribution publishing.
- Resolves only exact qualified `requirement` values and does not fall back to
  `skill_name` or repository-relative `skill_path`.
- Rejects collection selectors and catalog selectors deeper than
  `<collection>/<skill>`.
- Allows duplicate skill names at distinct lockfile paths.

### Contribution checkout and Git adapter tests

Cover:

- Creates or opens a Ritebook-owned isolated checkout.
- Does not mutate a user-owned local repository working tree.
- Does not use the managed index cache clone as a writable contribution
  workspace.
- Fetches source remotes non-interactively where applicable.
- Resolves the full locked commit and verifies its exact index digest.
- Creates safe branch names.
- Creates commits only after validation and index regeneration succeed.
- Rejects symlinked index files and symlinked checkout ancestors before invoking
  the publisher, while preserving external symlink targets.
- Reports Git failures without leaking credentials.

### Skill directory tests

Cover:

- Compares installed and source skill directories deterministically.
- Copies the installed skill directory into the source skill path.
- Rejects source paths that escape the contribution checkout.
- Rejects target paths that are missing or unsafe.
- Avoids following symlinks in a way that writes outside intended directories.

### CLI tests

Cover:

- `publish-skill-change` maps CLI args into application command DTOs.
- `publish-skill-change` accepts `--lockfile` and `--contribution-root` test
  overrides.
- Success output includes the skill reference, branch, commit, checkout, and next
  step.
- No-op output is concise and deterministic.
- Application and adapter errors are rendered as concise
  `ritebook: error: ...` messages.

Default tests must not rely on live external services, global developer state, or
network access. Git behavior should use temporary local repositories or fakes in
the default suite.

## Commands and validation

When changing this workflow, use focused tests first, then the full quality gate:

```bash
uv run pytest tests/unit/features/skill_contribution/application
uv run pytest tests/unit/features/skill_contribution/adapters/outbound
uv run pytest tests/unit/adapters/inbound/cli/test_adapter.py
uv run ruff format --check .
uv run ruff check .
uv run ty check src/ritebook
uv run pytest -m "not e2e"
uv build
docker build -f Dockerfile.e2e -t ritebook-e2e .
docker run --rm --network none ritebook-e2e
```

## Boundaries

Always:

- Support one skill contribution per command.
- Require `ritebook.lock` provenance for the MVP.
- Treat the verified locked revision and index digest as the installed baseline.
- Resolve contribution references by exact qualified lockfile `requirement`.
- Never expand a collection selector into multiple contributions.
- Prepare contributions in a Ritebook-owned isolated checkout.
- Fetch or inspect the current upstream base before preparing a contribution.
- Validate the changed skill before committing.
- Regenerate `ritebook-index.json` before committing.
- Create a reviewable local Git branch and commit.
- Print clear next steps for inspecting and optionally pushing the contribution.

Ask first:

- Adding `--push` behavior.
- Adding `--open-mr` behavior.
- Adding provider-specific `gh`, `glab`, GitHub, GitLab, or Gitea adapters.
- Adding `--base <branch-or-ref>`.
- Supporting batch contributions.
- Supporting ad hoc direct `install-skill` installs without `ritebook.lock`.
- Changing lockfile schema or installation provenance.
- Adding cleanup, pruning, or automatic deletion of contribution checkouts.

Never:

- Directly mutate the source default branch.
- Mutate the managed index cache clone as a contribution workspace.
- Mutate user-owned local source repositories by default.
- Substitute current upstream state when the locked commit or index binding is
  unavailable.
- Push branches without an explicit future opt-in.
- Open MRs or PRs without an explicit future opt-in.
- Attempt automatic conflict resolution in the MVP.
- Print secrets, Git credentials, raw skill contents, or raw index contents.

## Success criteria

- `uv run ritebook publish-skill-change <local-alias>/<skill-path>` reads
  `ritebook.lock` and resolves one installed repo-local skill.
- Root and collected skills can be contributed by exact path; collection selectors
  are rejected rather than expanded.
- The command fails clearly when the lockfile, selected entry, installed target,
  or required provenance is missing.
- The command detects and reports when there are no local skill changes to
  publish.
- The command prepares changed skill contents in a Ritebook-owned isolated
  checkout rather than mutating source branches, managed cache clones, or
  user-owned source repositories.
- The command warns or fails clearly when upstream source content changed since
  the locked install revision.
- The command fails safely when the locked commit is unavailable or its root index
  does not match the locked digest.
- The command runs skill validation and refuses to commit invalid skill content.
- The command regenerates `ritebook-index.json` and creates a local Git commit
  when validation succeeds.
- The command prints branch, commit, checkout, and next-step instructions for the
  developer.
- Application, adapter, and CLI unit tests cover the behavior.
- `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run ty check src/ritebook`, `uv run pytest -m "not e2e"`, `uv build`, and the
  network-disabled Docker E2E gate pass before implementation handoff.

## Out of scope

- Automatic push support.
- Automatic MR/PR creation.
- Provider API integration.
- Native GitHub, GitLab, Gitea, `gh`, or `glab` adapters.
- Batch contribution of multiple skills.
- Contribution support for ad hoc direct `install-skill` installs without
  `ritebook.lock` provenance.
- Direct writes to source default branches.
- Automatic conflict resolution.
- Enterprise governance, approvals, signatures, or trust policy.
- Skill dependency publishing or multi-repository contribution orchestration.

## Future considerations

These questions are not commitments. Ritebook maintainers own their disposition,
and each requires an approved specification or tracked implementation plan before
implementation:

- What validation evidence should Ritebook include in a future MR body?
- Should `publish-skill-change` eventually support `--base <branch-or-ref>` for
  teams that do not want to target the source repository's default branch?
- Should `--open-mr` support GitHub first, GitLab first, or detect `gh` and
  `glab` based on the source remote?
