# Spec: Consumer Skill Installation

## Objective

Ritebook provides consumer-facing skill installation workflows for users who have
already registered one or more Git-backed skill indexes with `add-index`.

The workflow lets a user install a selected cached skill into an explicit target
path, and lets a repository declare desired skill installations in
`ritebook.toml`. Ritebook resolves those declarations, copies the skill
directories from registered sources, and writes a deterministic `ritebook.lock`
for reviewable repo-local install state.

## Current context

- Ritebook already supports publisher-side index generation through
  `publish-index`.
- Publisher indexes are root-level `ritebook-index.json` files with schema
  version `1`.
- Publisher schema v1 includes index metadata and skill entries with required
  `name`, `path`, and `skill_file`, plus optional `description`.
- Consumer registry functionality already exists in
  `src/ritebook/features/index_registry/`:
  - `add-index` registers a Git URL or local Git repository source.
  - `update-index` refreshes cached index contents.
  - `list-indexes` lists registered index metadata.
  - `list-skills` lists skills from locally cached registered indexes.
- Registry entries already store each index's local effective name, remembered
  source, source type, source cache path for Git URL sources, and cached index
  path.
- The project follows hexagonal architecture with vertical feature slices under
  `src/ritebook/features/`.

## Desired behavior

### Install one skill

A user can install one skill by fully qualified effective index name and skill
path:

```bash
uv run ritebook install-skill platform-skills/code-review --target .claude/skills/code-review
```

Requirements:

- The skill reference must be fully qualified as
  `<index-name>/<skill-path-or-name>`.
- Index names must be single-segment kebab-case identifiers and must not contain
  `/`, so the separator before `<skill-path-or-name>` is unambiguous.
- The skill selector after the first slash may be a safe relative POSIX path,
  such as `browser/runtime-verification`, for skills published in subfolders.
- For backward compatibility and convenience, flat skill names such as
  `code-review` remain valid selectors when they resolve to one cached skill.
- `install-skill` requires a direct `--target <path>` and also accepts `--force`,
  `--registry-path`, and `--installation-registry-path`.
- `install-skill` does not accept target aliases, target kinds, or inferred
  default destinations.
- Ritebook reads the existing local consumer registry.
- Ritebook reads the selected registry entry's cached `ritebook-index.json`.
- Ritebook resolves the selected skill entry from that cached index.
- Ritebook copies the whole skill directory, not only `SKILL.md`, from the
  source repository into the target path.
- Ritebook creates missing target parent directories.
- Ritebook refuses to overwrite an existing target path unless `--force` is
  provided.
- Ritebook writes generated installation state after a successful copy.

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
- `install` copies each selected skill directory into its resolved target path.
- `install` writes or updates `ritebook.lock` after successful installation.
- `install` refuses existing target paths unless `--force` is provided.
- `install` fails without partially updating `ritebook.lock` when any declared
  install cannot be resolved, validated, or copied.
- `install` may leave already-copied target directories in place if a later copy
  fails; rollback is out of scope for v1 and the error must make that clear.

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

- `name`: required fully qualified `<index-name>/<skill-path-or-name>` reference.
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
  `<index-name>/<skill-path-or-name>`.
- Repeated `[[skills]]` entries with the same fully qualified `name` are rejected.
- Duplicate resolved target paths are rejected.
- Resolved target paths must not be empty, root-like, or otherwise dangerous.
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
      "source_revision": "abc123",
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
- `source_revision` is included when the source repository revision can be
  determined.
- Absolute local machine paths should not be written for repo-relative installs.
- The lockfile is replaced atomically enough for local CLI use after all planned
  installs have succeeded.

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
      "source_revision": "abc123",
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

For a registered local Git repository source:

- Ritebook reads the remembered local repository path.
- Ritebook does not mutate the local repository.
- Whether the local repository is up to date is the user's responsibility.

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
- Parent directories may be created.
- Existing target paths are refused unless `--force` is provided.
- `--force` replacement removes only the resolved target path, not a broader
  parent directory.
- Symlink handling must avoid writing outside the intended target path. The first
  implementation may reject existing symlink targets rather than follow them.

### CLI and workflow requirements

Initial commands:

```bash
uv run ritebook install-skill <index-name>/<skill-path-or-name> --target <path> [--force]
uv run ritebook install [--file ritebook.toml] [--force]
```

Potential test/automation path overrides:

```bash
uv run ritebook install-skill <index-name>/<skill-path-or-name> \
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
- Do not log or print secrets, Git credentials, raw index contents, raw skill file
  contents, or copied file contents.

## Testing strategy

### Application tests

Cover:

- Installs one fully qualified skill to an explicit target path.
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
- Rejects duplicate resolved targets.
- Writes `ritebook.lock` only after successful requirements installation.

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
- Rejects unsafe source paths from cached index metadata.
- Rejects dangerous target paths.
- Handles symlink targets safely by rejecting them in v1.

### Manifest writer tests

Cover:

- Writes deterministic `ritebook.lock` JSON.
- Preserves no stale entries for skills removed from `ritebook.toml` when running
  `install`.
- Writes deterministic `installations.json` for direct `install-skill` usage.
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

Current implementation status:

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

- Support direct `install-skill <index>/<skill-path-or-name> --target <path>`.
- Support `install` from `ritebook.toml`.
- Support TOML `[targets]` nicknames for requirements-file installs only.
- Require fully qualified `<index-name>/<skill-path-or-name>` skill references.
- Resolve install sources from locally registered and cached indexes.
- Copy the whole skill directory.
- Refuse overwrites unless `--force` is provided.
- Write deterministic `ritebook.lock` for `install`.
- Write user installation state under `~/.config/ritebook/installations.json` for
  direct `install-skill`.

Ask first:

- Adding target aliases or target kinds to `install-skill`.
- Adding default install destinations.
- Adding `sync`, `restore`, `update-skill`, or `uninstall-skill`.
- Installing directly from unregistered Git URLs.
- Fetching or pulling during installation.
- Bulk install by skill name without an index namespace.
- Adding content hashes, signatures, approvals, or trust policy.
- Supporting dependency relationships between skills.

Never:

- Mutate source repositories during installation.
- Install from live remotes without cached registered indexes.
- Overwrite user files silently.
- Treat duplicate skill names across different indexes as an error.
- Print secrets, Git credentials, raw index contents, raw skill file contents, or
  copied file contents.
- Write repo lockfiles containing machine-specific absolute paths for repo-local
  installs.

## Success criteria

- `uv run ritebook install-skill <index>/<skill-path-or-name> --target <path>`
  installs the selected skill directory into the explicit target path.
- `install-skill` refuses existing targets unless `--force` is provided.
- Direct `install-skill` writes deterministic user installation state under
  Ritebook's config directory.
- `uv run ritebook install` reads `ritebook.toml`, resolves `[targets]` nicknames
  and `target_path` entries, installs all declared skills, and writes
  `ritebook.lock`.
- `ritebook.lock` records resolved target paths and source metadata
  deterministically.
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
- Fetching or pulling during installation.
- Non-Git HTTP index sources.
- Signed indexes, trust policy, approvals, and enterprise governance.
- Skill dependency resolution.
- Multiple lockfiles per requirements file.
- Machine-specific absolute paths in committed repo lockfiles.
