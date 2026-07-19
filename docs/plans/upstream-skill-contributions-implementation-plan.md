# Implementation Plan: Upstream Skill Contributions

## Overview

Implement the MVP workflow from
`docs/specs/upstream-skill-contributions-spec.md`: a developer can run
`ritebook publish-skill-change <index-name>/<skill-path-or-name>` to prepare a
reviewable upstream contribution for one repo-local installed skill. Ritebook
must resolve the installed skill from `ritebook.lock`, compare it with the
current upstream source skill, prepare changes in a Ritebook-owned isolated Git
checkout, validate the skill, regenerate `ritebook-index.json`, create a local
commit, and print next-step instructions. Ritebook must not push, open merge
requests, mutate managed index cache clones, or mutate user-owned local source
repositories.

## Goal

- Support `ritebook publish-skill-change <index-name>/<skill-path-or-name>`.
- Support test/automation overrides for `--lockfile` and `--contribution-root`.
- Resolve exactly one publishable skill from repo-local `ritebook.lock`
  provenance.
- Detect no-op skill changes and exit successfully with concise output.
- Prepare changed skill contents in an isolated Ritebook-owned checkout.
- Fail clearly when upstream source content changed since the locked revision.
- Validate changed skills and regenerate `ritebook-index.json` before committing.
- Create a local Git branch and commit, then print checkout, branch, commit, and
  push instructions.

## Non-goals

- Do not add `--push`.
- Do not add `--open-mr` or provider-specific GitHub/GitLab/Gitea integrations.
- Do not add `--base <branch-or-ref>`.
- Do not support batch contributions.
- Do not support ad hoc direct `install-skill` installs without `ritebook.lock`.
- Do not change lockfile schema or installation provenance without separate
  approval.
- Do not add cleanup/pruning/deletion for contribution checkouts.
- Do not attempt automatic conflict resolution.

## Deliverables

- New vertical slice: `src/ritebook/features/skill_contribution/`.
- Application DTOs, ports, errors, and use case for publishing one skill change.
- Outbound adapters for lockfile reading, isolated contribution Git checkout,
  upstream workspace inspection, directory comparison/copy, validation, and
  index regeneration.
- CLI parser, command handler, and composition-root wiring for
  `publish-skill-change`.
- Unit tests mirroring source ownership.
- README/spec updates documenting usage, behavior, and resolved MVP decisions.
- Final quality gate evidence.

## Success Criteria

- `uv run ritebook publish-skill-change <index-name>/<skill-path-or-name>` reads
  `ritebook.lock` and resolves one installed repo-local skill.
- Missing lockfile, missing selected entry, ambiguous selected entry, missing
  installed target, and incomplete provenance fail with clear
  `ritebook: error: ...` messages.
- The command reports a concise no-op when installed and current upstream skill
  directories are identical.
- Changed skill contents are prepared in a Ritebook-owned isolated checkout, not
  in a managed index cache clone or user-owned source repository.
- Upstream changes to the skill path since `source_revision` fail clearly in the
  MVP.
- Skill validation and index regeneration run before commit creation.
- Invalid skills or index regeneration failures prevent commit creation.
- Successful contribution preparation prints skill reference, branch, commit,
  checkout, and appropriate next-step push or manual review guidance.
- Application, adapter, and CLI tests cover the behavior.
- `uv run ruff format .`, `uv run ruff check .`,
  `uv run ty check src/ritebook`, `uv run pytest`, and `uv build` pass before
  handoff.

## Resolved MVP Decisions

### Contribution checkout strategy

Use reusable deterministic contribution clones under a Ritebook-owned
contribution root. The default root should be under Ritebook's cache area, for
example `~/.cache/ritebook/contributions`. Test and automation workflows may
override it with `--contribution-root`.

The checkout path should include collision-resistant source identity and a safe
skill-reference segment, for example:

```text
<contribution-root>/<source-hash>/<index-name>-<skill-path-slug>/
```

Before preparing a new branch, the Git adapter may reset and clean only this
Ritebook-owned checkout. Successful checkouts must remain in place so developers
can inspect, amend, push, or delete them manually.

### Upstream-changed behavior

Treat upstream changes to the selected source skill path since locked
`source_revision` as a hard failure in the MVP. The error should tell the user
to update/reinstall the skill or reconcile the upstream changes manually. Do not
attempt automatic conflict resolution.

### Branch naming

Generate branch names with a Ritebook prefix, safe skill slug, and injected UTC
timestamp:

```text
ritebook/<skill-path-slug>-<YYYYMMDDHHMMSS>
```

Example:

```text
ritebook/browser-runtime-verification-20260718201534
```

### Commit message

Use an imperative generated commit message:

```text
Update <skill-name> skill from Ritebook contribution
```

Example:

```text
Update code-review skill from Ritebook contribution
```

### Publisher index name provenance

The current lockfile provenance stores the effective consumer `index_name`, but
not a distinct publisher index name. The MVP should use the lockfile
`index_name` when regenerating `ritebook-index.json` and document this
assumption. If this proves incorrect for curated upstream repositories, pause
and update both specs before changing lockfile provenance.

### Selector strictness

Use a stricter one-entry contribution selector than requirements-file install
prefix expansion. `publish-skill-change` must resolve exactly one lockfile entry
under the requested `index_name` by exact `requirement`, exact `skill_path`, or a
unique flat `skill_name`. Do not expand path prefixes into multiple skills for
the MVP because batch contribution is intentionally out of scope.

### Push next-step behavior

Print a concrete `git push origin <branch>` next step only when the contribution
checkout has a usable `origin` remote. For local Git repository sources without a
usable remote, print the checkout, branch, and commit plus manual guidance
instead of a broken push command.

### Default contribution root testability

Resolve the default contribution root at the adapter or composition boundary so
tests can avoid real user cache state. Default behavior may use Ritebook's cache
area, but automated tests must use `--contribution-root` or a monkeypatched cache
root resolver and must not write to real `~/.cache` or other developer-global
paths.

### Reusable checkout concurrency

Reusable deterministic contribution checkouts are acceptable for the MVP, but
concurrent `publish-skill-change` runs for the same source/skill are not
guaranteed safe unless a future locking mechanism is added. Document this as a
deferred operational limitation rather than adding locking in the first pass.

## Architecture Decisions

- Add a new `features/skill_contribution/` vertical slice rather than extending
  `skill_installation`, because contribution publishing owns a distinct use case,
  Git workspace policy, validation/commit ordering, and user-facing workflow.
- Keep application orchestration independent of Git commands, JSON parsing,
  filesystem copying, directory comparison, and CLI output formatting.
- Define contribution-owned DTOs and ports even when existing installation,
  linter, or publisher slices provide adjacent behavior.
- Reuse existing linter and publisher application ports through adapter-side
  composition rather than shelling out to `ritebook`.
- Keep concrete adapter wiring in `src/ritebook/cli.py`.
- Use injected clocks and injectable Git runners for deterministic tests.
- Treat lockfile paths, target paths, source paths, skill paths, branch names,
  and Git remote values as untrusted at adapter boundaries.

## Proposed Source Layout

```text
src/ritebook/features/skill_contribution/
├── __init__.py
├── application/
│   ├── __init__.py
│   ├── errors.py
│   ├── dtos/
│   │   ├── __init__.py
│   │   └── publish_skill_change.py
│   ├── ports/
│   │   ├── __init__.py
│   │   ├── publish_skill_change.py
│   │   ├── contribution_checkout.py
│   │   ├── contribution_lockfile.py
│   │   ├── skill_change_detector.py
│   │   ├── skill_directory.py
│   │   ├── skill_source_workspace.py
│   │   ├── skill_validator.py
│   │   └── index_regenerator.py
│   └── use_cases/
│       ├── __init__.py
│       └── publish_skill_change.py
└── adapters/
    ├── __init__.py
    ├── inbound/
    │   ├── __init__.py
    │   └── cli/
    │       ├── __init__.py
    │       └── commands.py
    └── outbound/
        ├── __init__.py
        ├── contribution_checkout/
        │   ├── __init__.py
        │   └── adapter.py
        ├── git_workspace/
        │   ├── __init__.py
        │   └── adapter.py
        ├── json_lockfile/
        │   ├── __init__.py
        │   └── reader.py
        ├── skill_directory/
        │   ├── __init__.py
        │   └── adapter.py
        ├── index_regeneration/
        │   ├── __init__.py
        │   └── adapter.py
        └── validation/
            ├── __init__.py
            └── adapter.py
```

## Application Model

### DTOs

Create `application/dtos/publish_skill_change.py` with focused dataclasses or
enums/literals such as:

- `PublishSkillChangeCommand`
  - `skill_reference: str`
  - `lockfile_path: str | None = None`
  - `contribution_root: str | None = None`
- `ContributionSkillReference`
  - parsed `<index-name>/<skill-path-or-name>` using the same selector shape as
    installation.
- `ContributionLockfileEntry`
  - `requirement`
  - `index_name`
  - `skill_name`
  - `target`
  - `source`
  - `source_type`
  - `source_revision`
  - `skill_path`
  - `skill_file`
  - `index_schema_version`
- `ContributionWorkspace`
  - checkout path, source root/path, current base revision, locked revision.
- `SkillChangeStatus`
  - `NO_CHANGES`
  - `CHANGED`
  - `UPSTREAM_CHANGED`
- `SkillChangeComparison`
  - status plus safe summary metadata.
- `PreparedContribution`
  - `skill_reference`, `checkout_path`, `branch_name`, `commit_hash`,
    `push_command`.
- `PublishSkillChangeResult`
  - no-op or prepared result shape.

### Errors

Create `application/errors.py` with user-facing errors:

- `SkillContributionError`
- `InvalidContributionSkillReferenceError`
- `ContributionLockfileReadError`
- `ContributionLockfileEntryNotFoundError`
- `AmbiguousContributionSkillReferenceError`
- `IncompleteContributionProvenanceError`
- `MissingInstalledSkillTargetError`
- `UpstreamSkillChangedError`
- `SkillContributionValidationError`
- `ContributionIndexRegenerationError`
- `ContributionGitError`
- `UnsafeContributionPathError`

Error messages should be concise and suitable for CLI rendering as
`ritebook: error: ...`. They must not include secrets, Git credentials, raw skill
contents, raw index contents, or copied file contents.

### Ports

Define small `Protocol`s under `application/ports/`:

- `PublishSkillChangePort`: inbound application use-case contract.
- `ContributionLockfilePort`: read and resolve contribution lockfile entries.
- `SkillSourceWorkspacePort`: prepare an isolated current-base source workspace
  and inspect the locked revision.
- `SkillChangeDetectorPort`: compare installed/current upstream content and
  detect upstream skill-path changes since `source_revision`.
- `SkillDirectoryPort`: copy installed skill directory into the checkout safely.
- `SkillValidatorPort`: validate skills before commit.
- `IndexRegeneratorPort`: regenerate `ritebook-index.json` before commit.
- `ContributionCheckoutPort`: clone/reuse/reset/fetch/branch/stage/commit and
  return Git metadata.

Adapter-side wrappers around existing application ports should keep DTO mapping
explicit:

- `SkillValidatorPort` should call the existing linter application boundary with
  a `LintSkillsCommand`. The default MVP scope should be the contribution
  checkout root so validation matches the publisher-index root that will be
  regenerated next; if selected-skill-only validation is chosen during
  implementation, update this plan and tests first.
- `IndexRegeneratorPort` should call the existing publisher application boundary
  with `PublishIndexCommand(index_name=<lockfile index_name>,
  skills_root=<checkout root>)` and rely on the documented MVP publisher-index
  name assumption.

## Application Workflow

`PublishSkillChange.execute(command)` should orchestrate this sequence:

1. Parse and validate the fully qualified skill reference.
2. Read the selected lockfile through `ContributionLockfilePort`.
3. Resolve exactly one entry for the requested selector.
4. Validate required contribution provenance, especially `source_revision`,
   `target`, `source`, `source_type`, `skill_path`, and `skill_file`.
5. Prepare or refresh an isolated contribution checkout through Git/workspace
   ports.
6. Detect whether the selected upstream skill path changed since
   `source_revision`; fail in the MVP if it did.
7. Compare the installed target skill directory against the current upstream
   source skill directory.
8. Return a no-op result when directories are identical.
9. Create/reset the contribution branch from the current upstream base.
10. Copy installed skill contents into the source skill path in the isolated
    checkout.
11. Validate the changed skill through the validation port.
12. Regenerate `ritebook-index.json` through the index-regeneration port.
13. Create a local commit through the contribution checkout port.
14. Return prepared contribution metadata for CLI rendering.

## Task List

### Phase 1: Application contracts and use-case orchestration

#### Task 1: Add DTOs, errors, and ports

**Description:** Create the contribution application boundary: command/result
DTOs, lockfile-entry DTOs, comparison/workspace DTOs, errors, and ports.

**Acceptance criteria:**

- [x] Command validates fully qualified skill references and optional path
      overrides.
- [x] Lockfile-entry DTO requires the provenance needed by the MVP.
- [x] Result DTO distinguishes no-op and prepared contribution outcomes.
- [x] Errors have concise user-facing messages.
- [x] Ports are small `Protocol`s under
      `features/skill_contribution/application/ports/`.
- [x] Package `__init__.py` files remain lightweight and expose intentional APIs
      only.

**Verification:**

- [x] Add focused DTO validation tests in
      `tests/unit/features/skill_contribution/application/test_publish_skill_change.py`.
- [x] Run:
      `uv run pytest tests/unit/features/skill_contribution/application/test_publish_skill_change.py`.

**Status:** Completed on 2026-07-18.

**Validation evidence:**

- `uv run ruff format src/ritebook/features/skill_contribution tests/unit/features/skill_contribution`
- `uv run ruff check src/ritebook/features/skill_contribution tests/unit/features/skill_contribution`
- `uv run ty check src/ritebook/features/skill_contribution tests/unit/features/skill_contribution`
- `uv run pytest tests/unit/features/skill_contribution/application/test_publish_skill_change.py`
  - Result: 31 passed.

**Dependencies:** None

**Files likely touched:**

- `src/ritebook/features/skill_contribution/application/dtos/publish_skill_change.py`
- `src/ritebook/features/skill_contribution/application/errors.py`
- `src/ritebook/features/skill_contribution/application/ports/*.py`
- `tests/unit/features/skill_contribution/application/test_publish_skill_change.py`

**Estimated scope:** Medium

#### Task 2: Implement application use case with fakes

**Description:** Implement `PublishSkillChange` orchestration using fake ports,
without real Git, filesystem, JSON, validation, or index writing.

**Acceptance criteria:**

- [x] Missing/malformed skill references are rejected.
- [x] Missing lockfile entries are rejected.
- [x] Ambiguous selectors are rejected.
- [x] Missing required provenance is rejected before checkout preparation.
- [x] Missing installed target is surfaced through the correct error path.
- [x] Upstream-changed comparisons fail before copy/validation/commit.
- [x] No-op comparison returns success without branch/copy/validate/commit.
- [x] Changed comparison runs branch, copy, validation, regeneration, and commit
      in order.
- [x] Validation failure prevents index regeneration and commit.
- [x] Index regeneration failure prevents commit.
- [x] Result includes checkout path, branch name, commit hash, and next step.

**Verification:**

- [x] Application tests cover all acceptance criteria with fakes.
- [x] Run:
      `uv run pytest tests/unit/features/skill_contribution/application/test_publish_skill_change.py`.

**Status:** Completed on 2026-07-19.

**Validation evidence:**

- `uv run ruff format src/ritebook/features/skill_contribution tests/unit/features/skill_contribution`
- `uv run ruff check src/ritebook/features/skill_contribution tests/unit/features/skill_contribution`
- `uv run ty check src/ritebook/features/skill_contribution tests/unit/features/skill_contribution`
- `uv run pytest tests/unit/features/skill_contribution/application/test_publish_skill_change.py`
  - Result: 43 passed.

**Dependencies:** Task 1

**Files likely touched:**

- `src/ritebook/features/skill_contribution/application/use_cases/publish_skill_change.py`
- `src/ritebook/features/skill_contribution/application/use_cases/__init__.py`
- `tests/unit/features/skill_contribution/application/fakes.py`
- `tests/unit/features/skill_contribution/application/test_publish_skill_change.py`

**Estimated scope:** Medium

### Checkpoint: Application behavior complete

- [ ] Application tests pass.
- [ ] Use case has no Git, JSON, filesystem, or CLI formatting details.
- [ ] Validation/regeneration/commit ordering is guarded by tests.

### Phase 2: Lockfile reader and selector resolution

#### Task 3: Implement contribution lockfile reader

**Description:** Add a contribution-owned JSON reader for `ritebook.lock` that
validates schema and resolves publishable entries.

**Acceptance criteria:**

- [x] Default path is `ritebook.lock`; `--lockfile` overrides it.
- [x] Invalid JSON fails clearly.
- [x] Missing lockfile fails clearly.
- [x] Unsupported `schema_version` fails clearly.
- [x] Missing or malformed `skills` fails clearly.
- [x] Missing required publishable fields fails clearly.
- [x] Resolution supports exact `requirement`, exact `skill_path`, and unique
      flat `skill_name` selectors under the requested `index_name`.
- [x] Resolution does not perform install-style prefix expansion or batch
      matching.
- [x] Ambiguous flat selectors fail clearly.
- [x] The reader does not mutate files or inspect target/source repositories.

**Verification:**

- [x] Unit tests cover schema, invalid JSON, missing fields, exact/path/flat
      selectors, no match, and ambiguity.
- [x] Run:
      `uv run pytest tests/unit/features/skill_contribution/adapters/outbound/test_json_lockfile_reader.py`.

**Status:** Completed on 2026-07-19.

**Validation evidence:**

- `uv run pytest tests/unit/features/skill_contribution/adapters/outbound/test_json_lockfile_reader.py`
  - Result: 24 passed.
- `uv run ruff format src/ritebook/features/skill_contribution tests/unit/features/skill_contribution`
- `uv run ruff check src/ritebook/features/skill_contribution tests/unit/features/skill_contribution`
- `uv run ty check src/ritebook/features/skill_contribution tests/unit/features/skill_contribution`
- `uv run pytest tests/unit/features/skill_contribution`
  - Result: 67 passed.

**Dependencies:** Task 1

**Files likely touched:**

- `src/ritebook/features/skill_contribution/adapters/outbound/json_lockfile/reader.py`
- `tests/unit/features/skill_contribution/adapters/outbound/test_json_lockfile_reader.py`

**Estimated scope:** Medium

### Phase 3: Filesystem comparison and copy-back

#### Task 4: Implement skill directory adapter

**Description:** Compare installed and upstream skill directories
deterministically and copy installed content back into the isolated checkout.

**Acceptance criteria:**

- [x] Validates installed target exists and is a directory.
- [x] Validates source `skill_path` and `skill_file` are safe relative POSIX
      paths.
- [x] Validates checkout source paths stay inside the isolated checkout.
- [x] Rejects missing source skill directory or `SKILL.md`.
- [x] Rejects symlink patterns that could escape intended roots.
- [x] Directory comparison is deterministic and does not print raw contents.
- [x] Copy-back removes/replaces only the selected source skill directory inside
      the checkout.

**Verification:**

- [x] Unit tests cover identical directories, changed directories, missing
      target, unsafe source paths, traversal, symlinks, and copy-back behavior.
- [x] Run:
      `uv run pytest tests/unit/features/skill_contribution/adapters/outbound/test_skill_directory_adapter.py`.

**Status:** Completed on 2026-07-19.

**Validation evidence:**

- `uv run pytest tests/unit/features/skill_contribution/adapters/outbound/test_skill_directory_adapter.py`
  - Result: 15 passed.
- `uv run ruff format src/ritebook/features/skill_contribution tests/unit/features/skill_contribution`
- `uv run ruff check src/ritebook/features/skill_contribution tests/unit/features/skill_contribution`
- `uv run ty check src/ritebook/features/skill_contribution tests/unit/features/skill_contribution`
- `uv run pytest tests/unit/features/skill_contribution`
  - Result: 82 passed.

**Dependencies:** Task 1

**Files likely touched:**

- `src/ritebook/features/skill_contribution/adapters/outbound/skill_directory/adapter.py`
- `tests/unit/features/skill_contribution/adapters/outbound/test_skill_directory_adapter.py`

**Estimated scope:** Medium

### Phase 4: Git contribution checkout and upstream inspection

#### Task 5: Implement contribution Git checkout adapter

**Description:** Add subprocess-backed Git behavior for isolated clone/reuse,
fetch, branch creation, staging, commit creation, and commit metadata. Use an
injectable runner for tests.

**Acceptance criteria:**

- [x] Uses deterministic Ritebook-owned checkout paths under contribution root.
- [x] Clones Git URL sources into contribution root when missing.
- [x] For local Git repo sources, creates a separate Ritebook-owned clone or
      equivalent isolated checkout without mutating the user working tree.
- [x] Does not use managed index cache clones as writable contribution workspaces.
- [x] Fetches origin when origin exists.
- [x] Selects current upstream base for MVP.
- [x] Resets/cleans only Ritebook-owned checkouts before branch preparation.
- [x] Creates safe branch names.
- [x] Handles missing or unusable `origin` by returning metadata that lets the CLI
      print manual next-step guidance rather than a broken push command.
- [x] Stages only the changed skill directory and `ritebook-index.json`.
- [x] Creates commit only after validation and index regeneration have succeeded.
- [x] Reports missing Git commit identity or commit failure clearly without
      leaking raw stderr; the prepared checkout remains inspectable.
- [x] Reports Git failures without leaking credentials or raw command stderr that
      may contain secrets.
- [x] Runs Git non-interactively with argument lists, not shell strings.
- [x] Default contribution-root resolution is testable without writing to real
      developer cache directories.

**Verification:**

- [x] Unit tests with fake runners verify Git command sequencing and failure
      behavior.
- [x] Temporary local-repository tests verify no mutation of user-owned local
      source working tree.
- [x] Tests cover missing/unusable `origin`, commit identity failure, and default
      contribution-root resolution without touching real user cache state.
- [x] Run:
      `uv run pytest tests/unit/features/skill_contribution/adapters/outbound/test_contribution_checkout.py tests/unit/features/skill_contribution/adapters/outbound/test_git_workspace.py`.

**Status:** Completed on 2026-07-19.

**Validation evidence:**

- `uv run pytest tests/unit/features/skill_contribution/adapters/outbound/test_contribution_checkout.py tests/unit/features/skill_contribution/adapters/outbound/test_git_workspace.py -q`
  - Result: 13 passed.
- `uv run ruff check src/ritebook/features/skill_contribution/adapters/outbound/contribution_checkout src/ritebook/features/skill_contribution/adapters/outbound/git_workspace tests/unit/features/skill_contribution/adapters/outbound/test_contribution_checkout.py tests/unit/features/skill_contribution/adapters/outbound/test_git_workspace.py`
- `uv run ty check src/ritebook/features/skill_contribution tests/unit/features/skill_contribution`
- `uv run pytest tests/unit/features/skill_contribution -q`
  - Result: 95 passed.
- `uv run ruff format .`
  - Result: 220 files left unchanged; the configured non-failing `COM812`
    formatter compatibility warning was emitted.
- `uv run ruff check .`
- `uv run ty check src/ritebook`
- `uv build`
  - Result: source distribution and wheel built successfully.
- `uv run pytest`
  - Result: 426 passed and 2 unrelated publisher tests failed.
  - Existing failures: the publisher integration test passes an absolute
    `skills_root` rejected by `SkillCatalog`, and the root-skill discovery test
    derives a non-kebab-case skill name from pytest's temporary directory.

**Notes:**

- Task 6 remains deferred: this task prepares the current-base workspace but does
  not yet inspect the selected skill path between the locked and current base
  revisions.
- The full-suite publisher failures are outside the Task 5 files and do not affect
  the focused contribution checks; they were not changed to keep this slice
  scoped.

**Dependencies:** Tasks 1–2

**Files likely touched:**

- `src/ritebook/features/skill_contribution/adapters/outbound/contribution_checkout/adapter.py`
- `src/ritebook/features/skill_contribution/adapters/outbound/git_workspace/adapter.py`
- `tests/unit/features/skill_contribution/adapters/outbound/test_contribution_checkout.py`
- `tests/unit/features/skill_contribution/adapters/outbound/test_git_workspace.py`

**Estimated scope:** Large

#### Task 6: Implement upstream-change detection

**Description:** Detect whether the upstream source skill path changed between
locked `source_revision` and the selected current upstream base.

**Acceptance criteria:**

- [ ] Uses Git inspection inside the isolated checkout.
- [ ] Compares only the selected source `skill_path` for upstream-change checks.
- [ ] Hard-fails the MVP when upstream changed since `source_revision`.
- [ ] Error message gives remediation guidance without dumping contents.
- [ ] Missing locked revision is treated as incomplete provenance.

**Verification:**

- [ ] Unit tests cover unchanged upstream, changed upstream, missing revision,
      and Git failure.
- [ ] Run:
      `uv run pytest tests/unit/features/skill_contribution/adapters/outbound/test_git_workspace.py`.

**Dependencies:** Task 5

**Files likely touched:**

- `src/ritebook/features/skill_contribution/adapters/outbound/git_workspace/adapter.py`
- `tests/unit/features/skill_contribution/adapters/outbound/test_git_workspace.py`

**Estimated scope:** Medium

### Checkpoint: Git and filesystem adapters complete

- [ ] Lockfile, filesystem, and Git adapter tests pass. Lockfile, filesystem, and
      Task 5 Git adapter tests currently pass; Task 6 tests remain pending.
- [x] No tests require network access or developer global state for completed
      lockfile, filesystem, and Task 5 Git adapter coverage.
- [ ] Git adapters do not leak raw credential-bearing output. Task 5 sanitization
      coverage passes; Task 6 remains pending.

### Phase 5: Validation and index regeneration adapters

#### Task 7: Implement validation adapter

**Description:** Reuse existing linter/application validation behavior through
an injected application port to validate changed skills in the contribution
checkout before commit creation.

**Acceptance criteria:**

- [ ] Runs validation after copy-back and before index regeneration.
- [ ] Maps to `LintSkillsCommand(skills_root=<checkout root>)` for the MVP so
      validation scope matches index regeneration scope.
- [ ] Converts validation issues into `SkillContributionValidationError`.
- [ ] Does not shell out to `ritebook`.
- [ ] Does not print raw skill contents.

**Verification:**

- [ ] Unit tests cover validation success and failure.
- [ ] Run:
      `uv run pytest tests/unit/features/skill_contribution/adapters/outbound/test_validation_adapter.py`.

**Dependencies:** Task 1

**Files likely touched:**

- `src/ritebook/features/skill_contribution/adapters/outbound/validation/adapter.py`
- `tests/unit/features/skill_contribution/adapters/outbound/test_validation_adapter.py`

**Estimated scope:** Small-Medium

#### Task 8: Implement index regeneration adapter

**Description:** Reuse existing publisher application behavior through an
injected publisher port to regenerate `ritebook-index.json` in the contribution
checkout before commit creation.

**Acceptance criteria:**

- [ ] Runs after validation and before commit creation.
- [ ] Uses checkout root as `skills_root`.
- [ ] Uses lockfile `index_name` for the MVP publisher index name assumption.
- [ ] Maps to `PublishIndexCommand(index_name=<lockfile index_name>,
      skills_root=<checkout root>)`.
- [ ] Converts publisher failures into `ContributionIndexRegenerationError` or
      validation errors as appropriate.
- [ ] Does not shell out to `ritebook`.

**Verification:**

- [ ] Unit tests cover regeneration success and failure.
- [ ] Run:
      `uv run pytest tests/unit/features/skill_contribution/adapters/outbound/test_index_regeneration_adapter.py`.

**Dependencies:** Task 7

**Files likely touched:**

- `src/ritebook/features/skill_contribution/adapters/outbound/index_regeneration/adapter.py`
- `tests/unit/features/skill_contribution/adapters/outbound/test_index_regeneration_adapter.py`

**Estimated scope:** Small-Medium

### Phase 6: CLI and composition root wiring

#### Task 9: Add CLI parser and command handler

**Description:** Add `publish-skill-change` to the shared CLI parser and route
it to a contribution-slice inbound CLI command handler.

**Acceptance criteria:**

- [ ] Parser accepts positional `skill_reference`.
- [ ] Parser accepts `--lockfile`.
- [ ] Parser accepts `--contribution-root`.
- [ ] CLI handler maps args into `PublishSkillChangeCommand`.
- [ ] No-op output is concise and deterministic.
- [ ] Success output includes skill reference, branch, commit, checkout, and next
      step.
- [ ] Success output prints `git push origin <branch>` only when a usable `origin`
      exists; otherwise it prints manual push/review guidance.
- [ ] Application/adapter errors render as `ritebook: error: ...`.
- [ ] Existing commands continue to route correctly.

**Verification:**

- [ ] CLI unit tests cover arg mapping, success, no-op, overrides, and error
      rendering.
- [ ] Run: `uv run pytest tests/unit/adapters/inbound/cli/test_adapter.py`.

**Dependencies:** Tasks 1–2

**Files likely touched:**

- `src/ritebook/adapters/inbound/cli/parser.py`
- `src/ritebook/adapters/inbound/cli/adapter.py`
- `src/ritebook/features/skill_contribution/adapters/inbound/cli/commands.py`
- `tests/unit/adapters/inbound/cli/test_adapter.py`

**Estimated scope:** Medium

#### Task 10: Wire composition root

**Description:** Instantiate contribution use case and adapters in
`src/ritebook/cli.py`, reusing existing linter and publisher use cases through
adapter-side composition.

**Acceptance criteria:**

- [ ] `main()` wires `PublishSkillChange` with lockfile reader, Git checkout,
      workspace/change detection, skill directory, validation, regeneration, and
      injected UTC clock.
- [ ] Existing command wiring remains unchanged.
- [ ] No application layer imports outbound adapters.
- [ ] CLI help includes the new command.

**Verification:**

- [ ] Run CLI adapter tests.
- [ ] Run help smoke checks:

```bash
uv run ritebook --help
uv run ritebook publish-skill-change --help
```

**Dependencies:** Tasks 3–9

**Files likely touched:**

- `src/ritebook/cli.py`
- relevant `__init__.py` exports under `features/skill_contribution/`

**Estimated scope:** Small-Medium

### Checkpoint: CLI flow wired

- [ ] CLI adapter tests pass.
- [ ] `ritebook --help` includes `publish-skill-change`.
- [ ] Composition root remains the only concrete wiring location.

### Phase 7: Workflow coverage, documentation, and final validation

#### Task 11: Add focused workflow coverage

**Description:** Add deterministic local-only workflow coverage for a successful
contribution preparation using temporary local Git repositories and explicit
temporary paths.

**Acceptance criteria:**

- [ ] Workflow registers/installs or otherwise prepares a lockfile-backed local
      skill fixture.
- [ ] A changed installed skill produces a contribution checkout branch and
      commit.
- [ ] No-change workflow reports no-op.
- [ ] Upstream-changed workflow fails clearly.
- [ ] Tests use explicit temporary registry/cache/lock/contribution paths.
- [ ] Tests do not require network access.
- [ ] Tests do not write to real home, config, or cache directories.

**Verification:**

- [ ] Run focused workflow tests, likely under `tests/e2e/` or a local-only
      integration-style unit test.
- [ ] Run: `uv run pytest tests/e2e -q` if E2E coverage is added.

**Dependencies:** Tasks 3–10

**Files likely touched:**

- `tests/e2e/test_cli_workflows.py` or a focused integration-style test module

**Estimated scope:** Medium

#### Task 12: Update README and spec notes

**Description:** Document user-facing contribution workflow and record resolved
MVP decisions in the spec or plan. Finalize examples after CLI smoke checks or
workflow tests confirm the exact output.

**Acceptance criteria:**

- [ ] README documents `publish-skill-change` usage.
- [ ] README explains the command prepares a local branch/commit only and does
      not push or open an MR/PR.
- [ ] README documents default lockfile behavior and contribution-root override.
- [ ] README includes concise no-op and success examples.
- [ ] Spec or plan records checkout strategy, branch naming, and upstream-change
      hard-fail behavior.
- [ ] README examples match parser options and observed CLI output, including
      no-origin/manual next-step output when relevant.

**Verification:**

- [ ] Review docs against parser options and CLI output.

**Dependencies:** Tasks 9–11

**Files likely touched:**

- `README.md`
- `docs/specs/upstream-skill-contributions-spec.md` if spec updates are needed
- `docs/plans/upstream-skill-contributions-implementation-plan.md`

**Estimated scope:** Small

#### Task 13: Run final quality gate

**Description:** Run formatting, linting, type checking, tests, and build before
handoff.

**Acceptance criteria:**

- [ ] Formatting applied.
- [ ] Ruff lint passes.
- [ ] Ty passes.
- [ ] Pytest passes.
- [ ] Package build succeeds.

**Verification:**

```bash
uv run ruff format .
uv run ruff check .
uv run ty check src/ritebook
uv run pytest
uv build
```

This repository currently uses `ty` as the configured type checker in
`pyproject.toml`; do not substitute an unconfigured type checker in the final
handoff gate.

**Dependencies:** All implementation and docs tasks

**Files likely touched:** None beyond formatting updates

**Estimated scope:** Small

## Testing Strategy

- Prefer application tests with hand-written fakes for orchestration and ordering.
- Keep outbound adapter tests focused on boundaries: JSON, filesystem, Git,
  validation, and publisher integration wrappers.
- Use temporary directories and temporary local Git repositories.
- Inject clocks and Git runners for deterministic branch names, timestamps, and
  command assertions.
- Do not rely on live remotes, developer global state, real user cache/config
  directories, or network access.
- Assert user-facing errors without asserting raw private data, raw Git stderr,
  raw skill contents, or raw index contents.

## Validation Commands

Focused checks during implementation:

```bash
uv run pytest tests/unit/features/skill_contribution/application
uv run pytest tests/unit/features/skill_contribution/adapters/outbound
uv run pytest tests/unit/adapters/inbound/cli/test_adapter.py
```

Full quality gate before handoff:

```bash
uv run ruff format .
uv run ruff check .
uv run ty check src/ritebook
uv run pytest
uv build
```

CLI smoke checks after wiring:

```bash
uv run ritebook --help
uv run ritebook publish-skill-change --help
```

## Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Publisher index name may differ from consumer effective `index_name` | Medium | Use current lockfile `index_name` for MVP, document the assumption, and pause before schema changes. |
| Reusable contribution checkout may contain stale state | High | Reset/clean only Ritebook-owned checkout before branch preparation; keep successful checkout inspectable after completion. |
| Accidentally mutating user-owned local source repo | High | Always clone local Git sources into the contribution root or use an isolated managed worktree; test that source working tree is unchanged. |
| Accidentally mutating managed index cache clone | High | Never use registry/cache clone as writable contribution workspace; clone into contribution root. |
| Upstream default branch detection varies by repository | Medium | Prefer origin default branch when available; add local-repo tests with and without origin. |
| Git error output may leak credentials | High | Raise generic Git errors and avoid echoing raw remote URLs or raw stderr in CLI messages. |
| Git commit identity may be missing | Medium | Surface a clear commit-failed message, keep the checkout inspectable, and avoid leaking raw stderr. |
| Local source clone may not have a usable push remote | Medium | Print manual next-step guidance instead of a broken `git push origin ...` command. |
| Symlink/path traversal during copy-back | High | Validate paths at filesystem adapter boundary and reject symlinks that could escape intended roots. |
| Validation/regeneration ordering regression | Medium | Guard order in application tests and fake-port assertions. |
| Concurrent runs may race on reusable checkouts | Medium | Document MVP limitation; defer checkout locking unless concurrent usage becomes required. |
| CLI adapter growth | Low | Keep command handler in contribution slice and shared adapter routing minimal. |

## Open Questions

None blocking for the MVP if the resolved decisions above are accepted. These
remain intentionally deferred:

- Whether future versions should use fresh clones, reusable clones, or worktrees.
- Whether reusable contribution checkouts should add file locking for concurrent
  publish attempts.
- Whether upstream changes can become warnings with manual conflict support.
- Whether future MR bodies should include validation evidence.
- Whether `--base <branch-or-ref>` should be added for teams that do not target
  the source default branch.
- Whether `--open-mr` should support GitHub, GitLab, Gitea, `gh`, or `glab`
  first.

## Parallelization Opportunities

- Task 3 lockfile reader and Task 4 skill directory adapter can proceed after
  Task 1 DTOs stabilize.
- Task 7 validation and Task 8 index regeneration can proceed once their port
  shapes are stable.
- README updates can start after CLI shape is stable, but examples should be
  checked after Tasks 9–11.

## Final Handoff Checklist

- [ ] Every task has acceptance criteria.
- [ ] Every task has verification steps.
- [ ] Task dependencies are ordered.
- [ ] Checkpoints exist between major phases.
- [ ] Resolved MVP decisions are documented.
- [ ] Open questions and assumptions are captured.
- [ ] Validation commands are explicit.
