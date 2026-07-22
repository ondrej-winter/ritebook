# Spec: Consumer Skill Installation

> **Status:** Active
> **Owner:** Ritebook maintainers
> **Spec version:** 1.0
> **Last reviewed:** 2026-07-22
> **Implementation state:** Implemented
> **Dependencies:** [Consumer Git Index Registry](consumer-git-index-registry-spec.md) and [Publisher Skill Index Generation](publisher-index-generation-spec.md)
> **Associated ADRs:** [ADR 0001: Source Provenance and Trust](../adr/0001-source-provenance-and-trust.md)

## Objective

Ritebook provides consumer-facing skill installation workflows for users who have
already registered one or more Git-backed skill indexes with `add-index`.

The workflow lets a user install a selected cached skill into an explicit target
path, and lets a repository declare desired skill installations in
`ritebook.toml`. Ritebook resolves those declarations, copies the skill
directories from registered sources, and writes a deterministic `ritebook.lock`
for reviewable repo-local install state.

## Implementation status

- Ritebook already supports publisher-side index generation through
  `publish-index`.
- Publisher indexes are root-level `ritebook-index.json` files with schema
  version `1`.
- Publisher schema v1 includes index metadata and skill entries with required
  `name`, `path`, `skill_file`, and non-empty `description`.
- Consumer registry functionality already exists in
  `src/ritebook/features/index_registry/`:
  - `add-index` registers a Git URL or local Git repository source.
  - `update-index` refreshes cached index contents.
  - `list-indexes` lists registered index metadata.
  - `list-skills` lists skills from locally cached registered indexes.
- Registry entries already store each index's local alias, remembered
  source, source type, source cache path for Git URL sources, and cached index
  path.
- Installation reads skill content from the commit bound to the validated cached
  index, as required by
  [ADR 0001](../adr/0001-source-provenance-and-trust.md), rather than from the
  source repository's mutable `HEAD` or working tree.
- The project follows hexagonal architecture with vertical feature slices under
  `src/ritebook/features/`.

## Desired behavior

### Install one skill

A user can install one skill by fully qualified local index alias and skill path:

```bash
uv run ritebook install-skill platform-skills/code-review --target .claude/skills/code-review
```

Requirements:

- The skill reference must be fully qualified as
  `<index-alias>/<skill-path>`.
- Index aliases must be single-segment kebab-case identifiers and must not contain
  `/`, so the separator before `<skill-path>` is unambiguous.
- The skill selector after the first slash is a safe relative POSIX path,
  such as `browser/runtime-verification`, for skills published in subfolders.
- Ritebook resolves only exact cached relative paths and never falls back to
  `skills[].name`. A root skill path such as `code-review` remains valid when that
  exact path exists.
- Duplicate skill names may coexist within one index when their relative paths
  differ; each is selected by its full path.
- `install-skill` requires a direct `--target <path>` and also accepts `--force`,
  `--registry-path`, and `--installation-registry-path`.
- `install-skill` does not accept target aliases, target kinds, or inferred
  default destinations.
- Ritebook reads the existing local consumer registry.
- Ritebook reads the selected registry entry's cached `ritebook-index.json`.
- Ritebook reads root `ritebook-index.json` from the registry entry's full
  `source_revision`, without substituting the current checkout or `HEAD`.
- Ritebook hashes both exact byte sequences and requires the cached index and the
  committed root index to match the registry entry's same `index_digest` before
  trusting cached metadata or copying content.
- Ritebook parses and validates the verified cached bytes, then resolves the
  selected skill entry from that same in-memory snapshot.
- Ritebook materializes the whole skill directory, not only `SKILL.md`, from the
  registry entry's full `source_revision` into the target path.
- Ritebook never substitutes the source repository's current checkout or `HEAD`
  for the bound commit.
- Ritebook creates missing target parent directories.
- Ritebook refuses to overwrite an existing target path unless `--force` is
  provided.
- Ritebook stages a complete copy beside the target before a forced replacement
  moves the existing target. A staging failure leaves the existing target intact.
- After staging, Ritebook moves the existing target to an installer-owned backup,
  moves the staged directory into place, and restores the backup if that final
  swap fails.
- A failed restore retains the backup and reports its exact path with recovery
  guidance. A successful swap removes installer-owned staging and backup paths;
  cleanup failure reports the retained backup without removing the new target.
- Ritebook constructs the complete timestamped installation entry and asks the
  installation-state adapter to validate the candidate update before copying.
- Ritebook writes generated installation state only after a successful copy.
- If the final atomic `installations.json` replacement fails, Ritebook reports
  failure rather than success, leaves the copied target in place, states that the
  registry was not updated, and directs the user to inspect the target and retry.

Example with overwrite:

```bash
uv run ritebook install-skill platform-skills/code-review \
  --target .claude/skills/code-review \
  --force
```

Example for a skill published under a subfolder:

```bash
uv run ritebook install-skill platform-skills/browser/runtime-verification \
  --target .claude/skills/runtime-verification
```

### Install from `ritebook.toml`

A repository can declare desired skill installations in a human-authored
`ritebook.toml` file:

```toml
[targets]
claude = ".claude/skills"
agents = ".agents/skills"
shared = "../shared-agent-skills"

[[skills]]
name = "platform-skills/code-review"
target = "claude"

[[skills]]
name = "platform-skills/test-driven-development"
target = "claude"

[[skills]]
name = "platform-skills/browser/runtime-verification"
target = "claude"

[[skills]]
name = "company-agents/security-review"
target = "shared"
```

A user can install all declared skills:

```bash
uv run ritebook install
```

The default requirements file is `ritebook.toml` in the current working
directory. A user can provide another file explicitly:

```bash
uv run ritebook install --file path/to/ritebook.toml
```

Requirements:

- `install` reads the TOML requirements file.
- `install` resolves each `[[skills]]` entry against existing cached registered
  indexes.
- For each selected registry entry, `install` verifies that both the exact cached
  index bytes and root `ritebook-index.json` read from the bound commit match the
  same `index_digest`.
- `install` parses and resolves requirements from the verified cached-byte
  snapshot and materializes each selected skill directory from that bound commit
  into the resolved target path.
- Before the first copy, `install` asks the filesystem adapter to canonicalize and
  validate every target without creating directories or otherwise mutating the
  filesystem. It rejects equivalent and parent-child target destinations as one
  conflicting plan.
- `install` writes or updates `ritebook.lock` after successful installation.
- `install` refuses existing target paths unless `--force` is provided.
- `install` fails without partially updating `ritebook.lock` when any declared
  install cannot be resolved, validated, or copied.
- `install` may leave already-copied target directories in place if a later copy
  fails; rollback is out of scope for v1 and the error must make that clear.
- Before the first copy, `install` constructs all timestamped lockfile entries and
  validates the complete candidate lockfile without filesystem mutation.
- If final atomic lockfile replacement fails after all copies, `install` reports
  failure rather than success, leaves copied targets in place, states that
  `ritebook.lock` was not updated, and directs the user to inspect the targets and
  retry.

### Generated-state commit and recovery semantics

The installation use cases use a retained-state recovery protocol rather than
attempting application-level deletion after a successful copy:

- Resolution, target planning, timestamp normalization, entry construction,
  existing-state parsing, conflict checks, provenance checks, and deterministic
  document construction occur before the first target mutation.
- A failure in any of those preparation steps is a full pre-mutation failure: no
  target is copied and no generated-state file is written.
- A first-copy failure is a full copy failure and does not write generated state.
- A later requirements-copy failure is a partial installation: earlier copied
  targets remain and `ritebook.lock` is not updated.
- If a forced replacement installs the new target but cannot remove its prior
  backup, the target and backup both remain, generated state is not written, and
  the diagnostic preserves the adapter's exact backup-recovery path.
- An `installations.json` or `ritebook.lock` atomic-write failure after copying is a
  generated-state commit failure: copied targets remain, the command exits with
  failure, and the diagnostic explicitly says which state file was not updated.
- If direct-install registry state changes between preflight and final commit, a
  new recorded-target conflict is also reported as a retained generated-state
  failure because the target has already been copied.
- The command never prints its success message unless the generated-state write
  completed.
- Ritebook does not automatically remove copied targets after a commit failure.
  A target may have replaced pre-existing user content under `--force`, and the
  installer has already finalized its private backup before returning success;
  blind deletion could therefore destroy valid user state.

Example with overwrite:

```bash
uv run ritebook install --force
```

### `ritebook.toml` format

The desired installation file uses TOML so Ritebook can parse it with Python's
standard-library `tomllib`.

`[targets]` defines optional target nicknames. Each target value is a base path:

```toml
[targets]
claude = ".claude/skills"
shared = "../shared-agent-skills"
```

`[[skills]]` entries declare desired skills:

```toml
[[skills]]
name = "platform-skills/code-review"
target = "claude"

[[skills]]
name = "company-agents/security-review"
target_path = "../shared-agent-skills/security-review"
```

Skill entry fields:

- `name`: required fully qualified `<index-name>/<skill-path>` reference or, for
  `install`, a folder selector that matches descendant skill paths.
- `target`: optional target nickname from `[targets]`.
- `target_path`: optional direct target path.

Target resolution rules:

- Each skill entry must define exactly one of `target` or `target_path`.
- `target` must reference a key in `[targets]`.
- `target = "nickname"` resolves to `<targets.nickname>/<final-skill-name>`.
- `target_path` is used as the exact target path for that skill entry.
- `[targets]` is optional when all skill entries use `target_path`.

Validation rules:

- The TOML document root must be a table.
- `[targets]`, when present, must be a table of non-empty string paths.
- Target nickname names must be simple identifiers using letters, numbers,
  underscores, and hyphens.
- `[[skills]]` must be an array of tables.
- Each skill `name` must be fully qualified as
  `<index-name>/<skill-path>`.
- Requirements-file `install` first resolves an exact skill path. When no exact
  skill exists, a selector may intentionally expand all descendants below that
  folder prefix in deterministic path order.
- Neither exact nor folder-prefix resolution falls back to `skills[].name`.
- Repeated `[[skills]]` entries with the same fully qualified `name` are rejected.
- Duplicate, canonically equivalent, and parent-child resolved target paths are
  rejected before the first copy. This includes lexical aliases using `.`, `..`,
  or relative versus absolute forms.
- Resolved target paths must not be empty, root-like, or otherwise dangerous.
- Existing symlinks in a target or any target ancestor are rejected during
  planning rather than followed.
- Canonical target comparison follows the host filesystem's path semantics. It
  detects case aliases when the host resolves them to the same existing path, but
  cannot portably prove that differently cased, entirely nonexistent paths will
  collide on every case-insensitive filesystem. Users must not declare such
  ambiguous targets.
- Unknown fields are rejected in v1 so mistakes fail fast.

### Lockfile

`ritebook.lock` is generated by Ritebook and should be committed when a
repository uses `ritebook.toml` to standardize repo-local agent skills.

The lockfile records resolved installation state rather than target nicknames.
It must be deterministic and reviewable.

Example schema v1:

```json
{
  "schema_version": 1,
  "requirements_file": "ritebook.toml",
  "skills": [
    {
      "requirement": "platform-skills/code-review",
      "index_name": "platform-skills",
      "skill_name": "code-review",
      "target": ".claude/skills/code-review",
      "target_ref": "claude",
      "source": "git@github.com:company/internal-skills.git",
      "source_type": "git_url",
      "source_revision": "0123456789abcdef0123456789abcdef01234567",
      "index_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "index_schema_version": 1,
      "skill_path": "skills/code-review",
      "skill_file": "skills/code-review/SKILL.md",
      "locked_at": "2026-07-10T21:00:00Z"
    }
  ]
}
```

Lockfile requirements:

- `schema_version` is required and must be `1` for v1.
- `requirements_file` records the requirements file path used by `install`.
- `skills` are sorted deterministically by `index_name`, then skill path.
- `target` stores the resolved target path written from the requirements file.
- `target_ref` is present only when the requirement used a `[targets]` nickname.
- `source_revision` is required and records the full commit object ID bound during
  index validation and actually used for installation.
- `index_digest` is required and records the verified digest of the cached index
  used to resolve the skill.
- `source` must be the safe persisted locator propagated from the registry. A
  standard URL containing authority user-info is rejected before lockfile writing.
- Shared lockfiles support `source_type = "git_url"` only. A registration backed by
  `local_git_repo` is valid for browsing and direct `install-skill`, but
  requirements installation rejects it during candidate lockfile validation before
  copying any target. Register the same index from a portable Git URL and rerun
  installation to generate commit-safe lock state.
- Pre-release schema-v1 lockfiles missing either provenance field are rejected and
  regenerated by rerunning installation; provenance is never inferred from the
  source's current `HEAD`.
- Relative, absolute, missing, and moved local repository paths are never written to
  `ritebook.lock`; Ritebook does not transform them into an ambiguous portable
  locator.
- The lockfile is replaced atomically enough for local CLI use after all planned
  installs have succeeded.
- `ritebook.lock` is intended for review and repository sharing, so Ritebook does
  not force mode `0600`; its source-safety boundary is rejection of secret-bearing
  standard URLs before serialization.

### User-level ad hoc installation state

When `install-skill` is used directly, Ritebook records generated user-level
installation state under Ritebook's own config directory instead of writing a
lockfile into arbitrary target directories:

```text
~/.config/ritebook/installations.json
```

Example schema v1:

```json
{
  "schema_version": 1,
  "installations": [
    {
      "requirement": "platform-skills/code-review",
      "index_name": "platform-skills",
      "skill_name": "code-review",
      "target": "/Users/me/.claude/skills/code-review",
      "source": "git@github.com:company/internal-skills.git",
      "source_type": "git_url",
      "source_revision": "0123456789abcdef0123456789abcdef01234567",
      "index_digest": "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "index_schema_version": 1,
      "skill_path": "skills/code-review",
      "skill_file": "skills/code-review/SKILL.md",
      "installed_at": "2026-07-10T21:00:00Z"
    }
  ]
}
```

Requirements:

- The user installation registry is generated state owned by Ritebook.
- The default path is `~/.config/ritebook/installations.json`.
- Tests and automation can override the path with an explicit CLI option or
  injected setting.
- Entries are sorted deterministically by `target`.
- Entries require the verified full `source_revision` and `index_digest` used for
  installation.
- Existing or candidate entries containing standard-URL authority user-info are
  rejected without echoing credentials. Unsafe existing state must be removed and
  regenerated by reinstalling.
- Replacement `installations.json` files receive POSIX mode `0600` where supported
  because this is user-owned local state.
- Existing pre-release schema-v1 registries containing entries without either
  provenance field are rejected with guidance to remove the generated registry
  and reinstall; Ritebook does not infer provenance from a mutable source.
- Reinstalling the same skill to the same target with `--force` replaces that
  entry.
- Installing a different skill to an already-recorded target is refused unless
  `--force` is provided.

### Source repository behavior

For a registered Git URL source:

- Ritebook uses the managed Git clone already associated with the registry entry.
- `install-skill` and `install` do not fetch or pull by default.
- Users should run `update-index` first when they want to refresh cached index
  contents and the managed clone.
- Ritebook verifies that the bound commit is available and reads the selected
  skill from that commit, even if the managed clone's current checkout has moved.
- Ritebook reads root `ritebook-index.json` from that commit and requires its exact
  bytes to match the same `index_digest` already verified against the cached index.
- If the commit is unavailable locally, Ritebook may fetch the remembered source
  to recover that exact object, but it must not advance the selected binding.

For a registered local Git repository source:

- Ritebook reads the remembered local repository path.
- Ritebook does not mutate the local repository.
- Ritebook reads committed objects at the bound `source_revision`, not the
  repository's working tree.
- Ritebook reads root `ritebook-index.json` from that commit and requires its exact
  bytes to match the same `index_digest` already verified against the cached index.
- Ritebook does not create an owned snapshot. If the repository or bound commit is
  unavailable, installation fails before copying and directs the user to restore
  it or explicitly refresh and reinstall.
- This source kind supports direct `install-skill` only. Requirements installation
  cannot generate the shared `ritebook.lock` contract from a machine-local path and
  fails before copying with guidance to register a Git URL.

For every source type, a missing bound commit, cached-index digest mismatch, or
bound-commit index digest mismatch is a provenance failure. Ritebook does not fall
back to mutable source bytes. It performs these checks before trusting cached
metadata, creating target paths, or copying content.

Standard Git URLs containing authority user-info are not valid persisted sources.
Installation and contribution lockfile readers reject such legacy state with a
non-secret error instead of using or displaying the value. scp-like SSH sources
remain valid.

### Path safety

Ritebook handles paths from three places:

1. target paths supplied by the user or `ritebook.toml`,
2. skill paths supplied by cached publisher indexes, and
3. source repository paths stored in the local registry.

Requirements:

- Cached index `path` and `skill_file` values are treated as untrusted external
  data and validated before use.
- Skill source paths must stay within the selected source repository.
- Target paths must be explicit, non-empty paths.
- Target paths must not resolve to filesystem root, the user's home directory
  itself, the current working directory itself, or another broad destructive
  destination.
- The resolved target must not equal, contain, or be contained by the resolved
  source skill directory. Both installation commands reject this overlap before
  deleting, creating, or copying any path, including when `--force` is provided.
- Parent directories may be created.
- Existing target paths are refused unless `--force` is provided.
- `--force` stages the complete source directory in a uniquely created path beside
  the target before changing the target. It then moves only the resolved target to
  an installer-owned backup and swaps the staged directory into place.
- Copy or backup-move failure preserves the prior target. Swap failure restores
  the backup when possible; restore failure retains the backup and reports its
  location for recovery.
- Successful replacement removes installer-owned staging and backup paths without
  deleting broader parent directories or unrelated similarly named paths.
- Symlink handling must avoid writing outside the intended target path. The first
  implementation may reject existing symlink targets rather than follow them.

### CLI and workflow requirements

Initial commands:

```bash
uv run ritebook install-skill <index-name>/<skill-path> --target <path> [--force]
uv run ritebook install [--file ritebook.toml] [--force]
```

Potential test/automation path overrides:

```bash
uv run ritebook install-skill <index-name>/<skill-path> \
  --target <path> \
  --registry-path <path-to-indexes.json> \
  --installation-registry-path <path-to-installations.json>

uv run ritebook install \
  --file <path-to-ritebook.toml> \
  --registry-path <path-to-indexes.json> \
  --lockfile <path-to-ritebook.lock>
```

Success output should be concise, for example:

```text
Installed platform-skills/code-review to .claude/skills/code-review
Installed 3 skill(s) from ritebook.toml
```

Error output should be clear and user-facing, for example:

```text
ritebook: error: target .claude/skills/code-review already exists; use --force to replace it
ritebook: error: unknown index: platform-skills
ritebook: error: unknown skill platform-skills/code-review
ritebook: error: target nickname claude is not defined in ritebook.toml
ritebook: error: skill entries must define exactly one of target or target_path
ritebook: error: installation copied target(s) .claude/skills/code-review, but installations.json was not updated; copied directories remain, so inspect them and retry the installation
```

## Project structure

The implementation uses the `skill_installation` vertical feature slice:

```text
src/ritebook/features/skill_installation/
├── application/
│   ├── dtos/
│   │   └── install_skill.py
│   ├── ports/
│   │   ├── install_skill.py
│   │   ├── install_from_requirements.py
│   │   ├── installation_manifest.py
│   │   ├── requirements_reader.py
│   │   ├── skill_catalog.py
│   │   ├── skill_source.py
│   │   └── skill_installer.py
│   └── use_cases/
│       ├── install_skill.py
│       └── install_from_requirements.py
└── adapters/
    └── outbound/
        ├── filesystem_installer/
        │   └── adapter.py
        ├── index_registry_catalog/
        │   └── adapter.py
        ├── json_installation_registry/
        │   └── adapter.py
        ├── json_lockfile/
        │   └── adapter.py
        ├── source_repository/
        │   └── adapter.py
        └── toml_requirements/
            └── reader.py
```

CLI integration and composition root:

- `src/ritebook/adapters/inbound/cli/parser.py`
- `src/ritebook/features/skill_installation/adapters/inbound/cli/commands.py`
- `src/ritebook/adapters/inbound/cli/adapter.py`
- `src/ritebook/cli.py`

Tests should mirror source ownership:

```text
tests/unit/features/skill_installation/
├── application/
│   ├── test_install_skill.py
│   └── test_install_from_requirements.py
└── adapters/outbound/
    ├── test_filesystem_installer.py
    ├── test_json_installation_registry.py
    ├── test_json_lockfile.py
    ├── test_source_repository.py
    └── test_toml_requirements_reader.py
```

## Conventions

- Keep application logic independent of filesystem, TOML, JSON, and Git details.
- Keep requirements parsing in an outbound adapter.
- Keep lockfile and user installation registry writing in outbound adapters.
- Keep skill directory copying in an outbound adapter.
- Use application-owned DTOs at application boundaries.
- Use explicit inbound and outbound ports.
- Validate external inputs at adapter boundaries.
- Use deterministic JSON output for generated state files.
- Use injected clocks for timestamps in tests.
- Validate timestamps and deterministic generated-state candidates before target
  mutation, then atomically commit generated state after successful copies.
- Do not log or print secrets, Git credentials, raw index contents, raw skill file
  contents, or copied file contents.

## Testing strategy

### Application tests

Cover:

- Installs one fully qualified exact skill path to an explicit target path.
- Resolves duplicate names by full relative path and rejects name-only shorthand
  for nested skills.
- Expands requirements-file folder selectors without using skill-name fallback.
- Rejects bare or malformed skill references.
- Rejects unknown indexes.
- Rejects unknown skills.
- Refuses existing targets without `force`.
- Allows replacement with `force`.
- Resolves TOML target nicknames to `<target-base>/<final-skill-name>`.
- Resolves TOML `target_path` as an exact target path.
- Rejects skill entries that define both `target` and `target_path`.
- Rejects skill entries that define neither `target` nor `target_path`.
- Rejects duplicate skill requirements.
- Rejects duplicate, canonically equivalent, and parent-child resolved targets
  before any install call while allowing safe siblings.
- Writes `ritebook.lock` only after successful requirements installation.
- Rejects naive clocks and deterministic generated-state validation failures before
  any install call.
- Reports retained copied targets without a success result when final
  `installations.json` or `ritebook.lock` persistence fails.
- Rejects an unavailable bound commit, cached-index digest mismatch, or
  bound-commit index digest mismatch before trusting metadata or copying.
- Proves that the cached index and root index at `source_revision` both match the
  same `index_digest` for direct and requirements-file installs.
- Records the verified revision and index digest rather than installation-time
  `HEAD`.

### TOML requirements reader tests

Cover:

- Reads valid `[targets]` and `[[skills]]` entries.
- Supports files where every skill uses `target_path` and `[targets]` is absent.
- Rejects invalid TOML.
- Rejects malformed `[targets]` values.
- Rejects unknown fields.
- Rejects missing or malformed skill references.
- Rejects unknown target nicknames.

### Filesystem installer tests

Cover:

- Copies a skill directory recursively into the target path.
- Creates target parent directories.
- Refuses existing targets without `force`.
- Replaces only the target path with `force`.
- Preserves the prior target on staging or backup failure.
- Restores the prior target on swap failure and retains it with recovery guidance
  when restoration fails.
- Cleans installer-owned staging and backup paths after successful replacement and
  reports a retained backup if cleanup fails.
- Rejects unsafe source paths from cached index metadata.
- Rejects equal, ancestor, and descendant source-target overlap before mutation
  while allowing safe sibling paths.
- Rejects dangerous target paths.
- Handles symlink targets and symlinked target ancestors safely by rejecting them
  during non-mutating planning in v1.

### Manifest writer tests

Cover:

- Writes deterministic `ritebook.lock` JSON.
- Requires and persists full `source_revision` and `index_digest` provenance.
- Preserves no stale entries for skills removed from `ritebook.toml` when running
  `install`.
- Writes deterministic `installations.json` for direct `install-skill` usage.
- Rejects credential-bearing source URLs in existing or candidate generated state
  without leaking the credential value.
- Writes replacement `installations.json` with POSIX mode `0600` where supported,
  while leaving the shareable `ritebook.lock` permission policy unchanged.
- Replaces matching installation entries on forced reinstall.
- Refuses conflicting target entries without `force`.

### CLI tests

Cover:

- `install-skill` maps CLI args into application command DTOs.
- `install-skill` requires `--target`.
- `install-skill` exposes `--force`.
- `install` uses default `ritebook.toml`.
- `install` maps `--file`, `--force`, `--registry-path`, and `--lockfile`.
- Success output is concise and deterministic.
- Application and adapter errors are rendered as concise
  `ritebook: error: ...` messages.
- Pre-mutation failures, partial copy failures, and post-copy generated-state
  commit failures have distinct exact diagnostics.

## Commands and validation

When changing this workflow, use focused tests first, then the full quality gate:

```bash
uv run pytest tests/unit/features/skill_installation/application
uv run pytest tests/unit/features/skill_installation/adapters/outbound
uv run pytest tests/unit/adapters/inbound/cli/test_adapter.py
uv run ruff format .
uv run ruff check .
uv run ty check src/ritebook
uv run pytest
uv build
```

### Implementation evidence

- Direct `install-skill` and requirements-file `install` are implemented in the
  `features/skill_installation` vertical slice.
- CLI E2E coverage exercises local-Git-backed registration, direct installation,
  requirements-file installation, copied directory contents, generated
  `installations.json`, generated `ritebook.lock`, and invalid requirements that
  do not write a lockfile.
- Target path danger checks are enforced at the filesystem installation adapter
  boundary, after TOML shape and application-level duplicate planning checks.
- Final audit handoff should include a fresh current-tree run of the full quality
  gate and Docker E2E command, or explicitly document any skipped validation.

## Boundaries

Always:

- Support direct `install-skill <index>/<skill-path> --target <path>`.
- Support `install` from `ritebook.toml`.
- Support TOML `[targets]` nicknames for requirements-file installs only.
- Require fully qualified `<index-name>/<skill-path>` skill references.
- Resolve direct installs only by exact relative skill path.
- Preserve requirements-file folder-prefix expansion without name-only fallback.
- Resolve install sources from locally registered and cached indexes.
- Verify that the cached index and root index at the bound Git commit both match
  the same digest before materializing skill content, as defined by
  [ADR 0001](../adr/0001-source-provenance-and-trust.md).
- Copy the whole skill directory.
- Refuse overwrites unless `--force` is provided.
- Write deterministic `ritebook.lock` for `install`.
- Write user installation state under `~/.config/ritebook/installations.json` for
  direct `install-skill`.
- Never report installation success unless the corresponding generated-state file
  has been committed.

Ask first:

- Adding target aliases or target kinds to `install-skill`.
- Adding default install destinations.
- Adding `sync`, `restore`, `update-skill`, or `uninstall-skill`.
- Installing directly from unregistered Git URLs.
- Refreshing, pulling, or fetching mutable refs during installation. A managed
  source may fetch solely to recover the already-bound commit object without
  changing the selected binding.
- Bulk install by skill name without an index namespace.
- Adding publisher-embedded per-skill hashes, signatures, approvals, or trust
  policy beyond the required local cached-index digest.
- Supporting dependency relationships between skills.

Never:

- Mutate source repositories during installation.
- Install from live remotes without cached registered indexes.
- Copy from a mutable working tree or current `HEAD` in place of the bound commit.
- Overwrite user files silently.
- Treat duplicate skill names across different indexes or at distinct paths in one
  index as an error.
- Print secrets, Git credentials, raw index contents, raw skill file contents, or
  copied file contents.
- Write repo lockfiles containing machine-specific absolute paths for repo-local
  installs.

## Success criteria

- `uv run ritebook install-skill <index>/<skill-path> --target <path>`
  installs the selected skill directory into the explicit target path.
- `install-skill` refuses existing targets unless `--force` is provided.
- Direct `install-skill` writes deterministic user installation state under
  Ritebook's config directory.
- `uv run ritebook install` reads `ritebook.toml`, resolves `[targets]` nicknames
  and `target_path` entries, installs all declared skills, and writes
  `ritebook.lock`.
- `ritebook.lock` records resolved target paths and the verified source revision
  and index digest deterministically.
- Installation fails before trusting metadata or copying when the bound source
  state is unavailable, the cached index does not match its digest, or the root
  index at the bound commit does not match that same digest.
- Unknown indexes, unknown skills, malformed TOML, undefined target nicknames,
  duplicate requirements, and duplicate targets fail with clear user-facing
  errors.
- Application, adapter, and CLI unit tests cover the behavior.
- README documents the new commands and file formats.
- `uv run ruff format .`, `uv run ruff check .`, `uv run ty check src/ritebook`,
  `uv run pytest`, and `uv build` pass before handoff.

## Out of scope

- `sync`, `restore`, `update-skill`, and `uninstall-skill` commands.
- Target aliases or target kinds for direct `install-skill`.
- Default install destinations.
- Installing from unregistered Git URLs.
- Refreshing, pulling, or fetching mutable refs during installation; exact-object
  recovery for an already-bound managed-source commit remains permitted.
- Non-Git HTTP index sources.
- Signed indexes, trust policy, approvals, and enterprise governance.
- Skill dependency resolution.
- Multiple lockfiles per requirements file.
- Machine-specific absolute paths in committed repo lockfiles.
