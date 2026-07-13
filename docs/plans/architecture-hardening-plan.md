# Architecture hardening plan

## Goal

Capture the first audit plan for hardening Ritebook's hexagonal vertical-slice
architecture after the recent CLI, index registry, publisher, linter, skill
installation, CI, and E2E work.

The plan focuses on architecture boundaries, dependency direction, adapter
ownership, test coverage, and documentation alignment. It is intentionally
incremental: preserve current behavior first, then reduce boundary ambiguity.

## Scope

### In scope

- Composition-root cleanup in `src/ritebook/cli.py`.
- Cross-slice boundary between `index_registry` and `skill_installation`.
- CLI inbound adapter dependency cleanup.
- CLI command module structure.
- Install path-safety test coverage.
- README and architecture documentation alignment.

### Out of scope

- Rewriting existing feature slices.
- Changing public CLI behavior unless required by boundary cleanup.
- Reworking Docker E2E scenarios beyond promoting the existing workflow into CI.
- Introducing new runtime dependencies.

## Current audit summary

Ritebook is broadly aligned with the intended architecture direction:

- Business capabilities live under `src/ritebook/features/`.
- Use cases and ports are explicit in application layers.
- Most filesystem, Git, JSON, TOML, and subprocess behavior is isolated in
  adapters.
- `src/ritebook/cli.py` acts as the composition root.
- Tests mirror feature-slice ownership and include unit plus E2E coverage.

The main hardening need is not a rewrite. The next step should make several
important boundaries more explicit before more CLI features are added.

## Plan

### Task 1: Extract the installation catalog bridge from the composition root

**Priority:** Required

**Status:** Complete.

**Completed notes:** The catalog bridge now lives in the
`skill_installation` outbound adapter package:

```text
src/ritebook/features/skill_installation/adapters/outbound/index_registry_catalog/
├── __init__.py
└── adapter.py
```

`src/ritebook/cli.py` wires `IndexRegistrySkillCatalogAdapter` but no longer
contains catalog DTO mapping logic. Focused adapter tests cover successful index
mapping, missing indexes, and cached skill mapping.

**Problem:** `src/ritebook/cli.py` currently contains `_InstallationCatalogAdapter`,
which maps index-registry data into skill-installation DTOs. The mapping itself
is good boundary hygiene, but the implementation is adapter logic living in the
composition root.

**Target design:** Move the bridge into a skill-installation-owned outbound
adapter package, likely:

```text
src/ritebook/features/skill_installation/adapters/outbound/index_registry_catalog/
├── __init__.py
└── adapter.py
```

**Implementation steps:**

1. Create `IndexRegistrySkillCatalogAdapter` in the new outbound adapter package.
2. Keep mapping into installation-owned DTOs:
   - `RegisteredSkillIndex`
   - `InstallableSkill`
3. Type the adapter against the installation-owned `SkillCatalogPort`.
4. Keep `src/ritebook/cli.py` responsible only for wiring.
5. Add focused unit tests under
   `tests/unit/features/skill_installation/adapters/outbound/`.

**Acceptance criteria:**

- [x] `src/ritebook/cli.py` no longer contains catalog mapping logic.
- [x] The cross-slice bridge is owned by `skill_installation` as an outbound
      adapter.
- [x] Unit tests cover successful mapping and missing-index behavior.
- [x] Existing CLI behavior is unchanged.

**Verification:**

```bash
uv run pytest tests/unit/features/skill_installation/adapters/outbound -q
uv run pytest tests/unit/adapters/inbound/cli -q
```

### Task 2: Clean CLI error boundaries

**Priority:** Required

**Status:** Complete.

**Completed notes:** CLI command handlers now catch linter and publisher
application-level error families instead of concrete filesystem or JSON adapter
exceptions. Filesystem discovery and JSON writer adapters translate concrete I/O
failures into application-owned errors while preserving the original exception as
the cause.

**Problem:** CLI command handlers catch some concrete outbound adapter exceptions,
including filesystem discovery and JSON index writing errors. The CLI is an
inbound adapter and should primarily translate application-level errors, not know
about specific outbound adapter implementations.

**Implementation steps:**

1. Review publisher and linter application error modules.
2. Introduce or reuse application-level errors for discovery/write failures where
   needed.
3. Translate outbound adapter failures at the use-case boundary while preserving
   exception context with `from err`.
4. Update CLI handlers to catch application error families plus DTO validation
   `ValueError` where appropriate.
5. Add or update CLI tests for affected error paths.

**Acceptance criteria:**

- [x] CLI command handlers do not depend on concrete outbound adapter exception
      classes where an application-level error is appropriate.
- [x] User-facing error messages remain clear and safe.
- [x] Error tests cover the translated paths.

**Verification:**

```bash
uv run pytest tests/unit/adapters/inbound/cli -q
uv run pytest tests/unit/features/publisher tests/unit/features/linter -q
```

### Task 3: Make the `index_registry` ↔ `skill_installation` boundary explicit

**Priority:** Suggested

**Status:** Complete.

**Boundary decision:** `skill_installation` owns the bridge from registered
indexes to installation catalogs as an outbound adapter. That bridge may depend
on published `index_registry.application.ports` contracts and their
port-approved DTOs, then must map into installation-owned DTOs before calling
installation use cases. It must not import `index_registry` adapters, use cases,
or private internals directly.

**Completed notes:** The chosen pattern is visible in the
`index_registry_catalog` outbound adapter package and documented here as the
allowed cross-slice path for installation catalog reads.

**Problem:** Skill installation depends on registered cached indexes. The current
mapping avoids sharing DTOs directly, but the intended cross-slice collaboration
pattern should be explicit before more slices depend on each other.

**Implementation steps:**

1. Decide whether `index_registry` exposes a stable application-facing API for
   registered cached skill catalogs, or whether `skill_installation` owns bridge
   adapters over index-registry ports/adapters.
2. Keep installation-owned DTOs as the installation boundary types.
3. Avoid importing index-registry private internals from skill installation.
4. Document the chosen pattern if it becomes durable.

**Acceptance criteria:**

- [x] The boundary decision is visible in code structure or documentation.
- [x] Future cross-slice imports have a clear allowed path.
- [x] No feature slice imports another slice's private internals ad hoc.

### Task 4: Split the growing CLI command module

**Priority:** Suggested

**Status:** Complete.

**Completed notes:** The CLI command handlers now live in a `commands/` package
grouped by feature family:

```text
src/ritebook/adapters/inbound/cli/commands/
├── __init__.py
├── index_registry.py
├── installation.py
├── linter.py
└── publisher.py
```

The package `__init__.py` preserves the existing handler exports used by
`adapter.py`, so the split is structural and behavior-preserving.

**Problem:** `src/ritebook/adapters/inbound/cli/commands.py` has grown to cover
multiple feature areas. It remains readable, but it is now a natural split point.

**Implementation steps:**

1. Split by command family, for example:
   - `commands/linter.py`
   - `commands/publisher.py`
   - `commands/index_registry.py`
   - `commands/skill_installation.py`
   - `commands/rendering.py` if needed
2. Keep the first split mechanical and behavior-preserving.
3. Preserve existing imports through package exports if needed.
4. Avoid mixing the split with behavior changes.

**Acceptance criteria:**

- [x] CLI command handlers are grouped by feature family.
- [x] Existing CLI tests pass without behavior changes.
- [x] The adapter package remains easy to navigate as new commands are added.

**Verification:**

```bash
uv run pytest tests/unit/adapters/inbound/cli -q
```

### Task 5: Audit install path-safety coverage

**Priority:** Suggested

**Status:** Complete.

**Completed notes:** Filesystem installer tests now cover existing targets,
force replacement for directories and files, broad target rejection, unsafe
source metadata, symlink targets, symlink source paths, symlinks inside source
directories, and traversal attempts represented by unsafe source metadata.

**Problem:** The current design intentionally keeps concrete filesystem danger
checks in the filesystem installer adapter. That boundary is acceptable, but the
adapter tests should prove the important safety cases.

**Coverage to confirm:**

- [x] Existing target behavior.
- [x] `--force` replacement behavior.
- [x] Filesystem root rejection.
- [x] Unsafe source paths.
- [x] Symlink rejection or safe handling.
- [x] Traversal attempts.

**Implementation steps:**

1. Review `tests/unit/features/skill_installation/adapters/outbound/test_filesystem_installer.py`.
2. Add adapter-level tests only where gaps exist.
3. Keep path-safety policy at the filesystem adapter boundary unless a rule is
   technology-agnostic business policy.

**Verification:**

```bash
uv run pytest tests/unit/features/skill_installation/adapters/outbound/test_filesystem_installer.py -q
```

### Task 6: Polish project-facing docs

**Priority:** Suggested

**Status:** Complete.

**Completed notes:** The README intro now describes Ritebook's current publisher
and consumer CLI workflows without presenting the project as only a PyPI package
placeholder.

**Problem:** The README intro still describes Ritebook as a minimal placeholder,
while the rest of the README documents real CLI workflows.

**Implementation steps:**

1. Update the README intro to reflect the current CLI capabilities without
   over-claiming maturity.
2. Keep registry, install, and E2E documentation aligned with current behavior.
3. Add a short architecture note only if the cross-slice boundary decision needs
   durable documentation.

**Acceptance criteria:**

- [x] README onboarding text matches the current project state.
- [x] Documentation remains concise and user-facing.

### Task 7: Promote Docker E2E into CI/CD quality gate

**Priority:** Complete

**Current state:** Docker E2E now runs as a mandatory job in the main CI/CD
workflow, in parallel with the non-E2E quality-check job.

**Completed notes:** Patch releases and publishing require both `quality` and
`docker-e2e` jobs to pass. The manual Docker E2E workflow remains available for
explicit rerun/debug use.

## Final validation checklist

Run focused checks while iterating. Before handoff for code changes, run:

```bash
uv run ruff format .
uv run ruff check .
uv run ty check src/ritebook
uv run pytest -m "not e2e"
```

Run E2E directly when iterating on CLI workflows:

```bash
uv run pytest tests/e2e -q
```

Run the clean-room Docker E2E gate before handoff:

```bash
docker build -f Dockerfile.e2e -t ritebook-e2e .
docker run --rm ritebook-e2e
```
