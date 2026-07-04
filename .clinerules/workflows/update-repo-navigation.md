# Workflow: update repo navigation

Use this workflow when adapting the reusable hexagonal vertical-slice Python rules to a specific project.

## Goal

Produce a short, project-specific navigation guide outside `.clinerules/` so contributors can quickly find package roots, feature slices, entry points, adapters, and tests.

When documenting reusable navigation workflows, prefer cross-platform examples based on IDE search or `rg`/`rg --files`.

## Recommended output location

- `docs/repo-navigation.md`
- or another discoverable project-owned path near the main developer docs

## Steps

1. Identify the package root (`src/<package_name>/` or the top-level package directory).
2. Locate entry points and composition-root/bootstrap files (`__main__.py`, `cli.py`, ASGI/WSGI app factories, worker startup modules, etc.).
3. Map the feature slices under the documented slice root, commonly `features/`.
4. For each important slice, map the hexagonal layers it owns:
   - `domain/`
   - `application/use_cases/`
   - `application/ports/`
   - `application/dtos/`
   - `adapters/inbound/`
   - `adapters/outbound/`
5. Map shared kernel, composition-root, and adapter-only infrastructure modules, if present.
6. Map the test layout (`tests/unit/features/`, `tests/integration/features/`, `tests/e2e/`, shared fixtures, contract tests).
7. Record the most useful project-specific search commands for slices, ports, adapters, entry points, and tests.
8. Save the navigation guide outside `.clinerules/` and update it whenever the structure changes significantly.

## Suggested template

```md
# Project navigation

## Package roots

- `src/<package_name>/`

## Entry points / composition root

- `src/<package_name>/cli.py`
- `src/<package_name>/bootstrap.py`

## Feature slices

- `src/<package_name>/features/<feature_name>/`
  - `domain/`
  - `application/use_cases/`
  - `application/ports/`
  - `application/dtos/`
  - `adapters/inbound/`
  - `adapters/outbound/`

## Shared kernel

- `src/<package_name>/shared_kernel/`

## Shared infrastructure

- `src/<package_name>/bootstrap/`

## Tests

- Unit: `tests/unit/features/`
- Integration: `tests/integration/features/`
- E2E: `tests/e2e/`

## Useful search commands

- `rg --files src/<package_name>/features/`
- `rg "Protocol|ABC|abstractmethod" src/<package_name>/features/`
- `rg --files src/<package_name>/features/ | rg "/application/dtos/"`
- `rg --files src/<package_name>/features/ | rg "/adapters/(inbound|outbound)/"`
- `rg --files -g "pyproject.toml"`
- `rg --files src/<package_name>/ | rg "(^|/)(__main__|cli)\.py$"`
```
