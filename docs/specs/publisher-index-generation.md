# Spec: Publisher Skill Index Generation

## Objective

Ritebook will provide a publisher-side workflow for corporate skill maintainers
to generate a deterministic index of approved internal agent skills from a
private repository. The index gives maintainers a reviewable catalog artifact
that can later support consumer-side listing, syncing, and installation without
requiring full repository syncs or ad hoc shell scripts.

The first user is a skill maintainer or curator inside a company. The first
business outcome is controlled internal skill curation; faster developer
installation is a later adoption benefit, not the first milestone.

## Current context

- Ritebook is currently a minimal Python package placeholder.
- Future business capabilities should be implemented as vertical feature slices
  under `src/ritebook/features/` with domain, application, ports, and adapters
  separated according to hexagonal architecture principles.
- The source idea is documented in `docs/ideas/internal-skill-distribution.md`.
- Python 3.13, `uv`, `ruff`, `mypy`, and `pytest` are the project tooling
  baseline.
- For the MVP, any directory containing `SKILL.md` is considered a skill
  directory.

## Desired behavior

Ritebook should generate or update a JSON index file for a maintainer-controlled
skills repository.

### Publisher workflow

1. A maintainer runs a Ritebook publisher command or application use case with an
   explicit skills root path.
2. Ritebook recursively scans the skills root for directories containing a file
   named `SKILL.md`.
3. Ritebook builds a deterministic catalog of discovered skills.
4. Ritebook writes the catalog to the canonical `ritebook-index.json` file.
5. The maintainer reviews and commits the generated index to the private skills
   repository through the normal pull request workflow.

### Skill discovery

- A skill is any directory containing `SKILL.md`.
- Discovery must be recursive under the explicit skills root.
- The generated index should use paths relative to the skills root so the index
  stays portable within the repository.
- Output ordering must be deterministic, sorted by relative skill path or another
  documented stable key.
- Hidden directories under the skills root are skipped by default in the MVP.
- Missing or unreadable skills root paths must produce clear user-facing errors at the
  adapter boundary.

### Index output

- The canonical output filename is `ritebook-index.json`.
- The index must be valid JSON.
- The index must include a schema version so future versions can evolve without
  ambiguity.
- The index must include enough data for future consumer commands to list and
  locate skills.
- The index must be pretty-printed with two-space indentation for pull request
  review.
- Schema v1 must not require a mandatory metadata block inside `SKILL.md`.
- Schema v1 must not include content hashes. Hashing can be added later if
  consumer caching or tamper detection requires it.

## Index schema v1

Schema v1 should stay small and describe discovered skill package boundaries.

```json
{
  "schema_version": 1,
  "generated_at": "2026-07-04T18:49:00Z",
  "skills_root": ".",
  "skills": [
    {
      "name": "example-skill",
      "path": "example-skill",
      "skill_file": "example-skill/SKILL.md",
      "title": "Example Skill"
    }
  ]
}
```

### Field requirements

- `schema_version`: integer schema version. MVP value is `1`.
- `generated_at`: timezone-aware UTC timestamp in ISO 8601 format. The timestamp
  source should be injectable or controllable in tests.
- `skills_root`: path that was scanned, represented in the output in a stable
  human-reviewable form based on the single explicit skills root path supplied by
  the user.
- `skills`: array of discovered skill entries sorted deterministically.
- `skills[].name`: stable skill identifier derived from the skill directory name.
- `skills[].path`: relative path from the skills root to the skill directory.
- `skills[].skill_file`: relative path from the skills root to `SKILL.md`.
- `skills[].title`: optional human-readable title derived from the first Markdown
  H1 in `SKILL.md` when available.

## CLI and workflow requirements

The first CLI shape should be simple and explicit:

```bash
uv run ritebook publish-index --skills-root <path>
```

Requirements:

- Require an explicit `--skills-root` for the first implementation.
- Support one skills root per command invocation; multiple roots are out of scope
  for the MVP.
- Always write the canonical `ritebook-index.json`; no output argument is needed.
- Overwrite an existing generated index only when the command is explicitly run;
  no background or implicit updates.
- Emit concise success output that includes discovered skill count and output
  path.
- Keep process environment access, filesystem traversal, CLI parsing, and JSON
  serialization in adapters or bootstrap code, not in domain models.

## Project structure

Implementation should follow the repository's hexagonal vertical-slice direction.

- `src/ritebook/features/skill_catalog/domain/`: pure catalog concepts such as
  skill entries and catalog invariants.
- `src/ritebook/features/skill_catalog/application/`: publisher use case,
  inbound port, outbound filesystem/catalog writer ports, and DTOs.
- `src/ritebook/features/skill_catalog/adapters/inbound/`: CLI adapter that maps
  command-line arguments to application DTOs.
- `src/ritebook/features/skill_catalog/adapters/outbound/`: filesystem scanner
  and JSON index writer adapters.
- `tests/unit/features/skill_catalog/`: focused unit tests mirroring the source
  structure.
- `docs/specs/publisher-index-generation.md`: this specification.

## Commands and validation

During implementation, use focused checks first, then the full local quality
gate before handoff.

- Format: `uv run ruff format .`
- Lint: `uv run ruff check .`
- Type check: `uv run mypy .`
- Test: `uv run pytest`
- Build: `uv build`

## Testing strategy

The MVP should be covered primarily with fast, deterministic unit tests.

- Domain tests verify catalog entry creation, deterministic ordering, and basic
  invariants.
- Application tests use fakes for skill discovery and index writing ports.
- Filesystem adapter tests use temporary directories to verify recursive
  `SKILL.md` discovery and relative path handling.
- JSON writer tests verify schema version, deterministic output, optional title
  behavior, two-space indentation, and valid JSON.
- CLI adapter tests verify argument mapping, clear errors for missing root paths, and
  user-facing success output.

Default tests must not rely on live external services, global developer state, or
network access.

## Boundaries

- Always keep business rules and catalog concepts independent of CLI, filesystem,
  and JSON serialization details.
- Always validate external inputs at adapter boundaries before invoking the
  application use case.
- Always keep output deterministic enough for pull request review.
- Always pretty-print generated JSON with two-space indentation.
- Ask before adding mandatory `SKILL.md` metadata requirements.
- Ask before adding consumer install, sync, or list commands to this milestone.
- Ask before adding content hashes, signatures, policy enforcement, or trust-chain
  behavior.
- Never scan a whole repository implicitly in the first MVP; require an explicit
  skills root.
- Never accept multiple skills roots in a single MVP command invocation.
- Never scan hidden directories by default in the MVP.
- Never log or print skill file contents by default.

## Success criteria

- A maintainer can run a publisher workflow against an explicit skills root and
  produce `ritebook-index.json`.
- The generated index lists every discovered directory containing `SKILL.md`.
- The generated index is deterministic for unchanged input except for the
  documented generation timestamp.
- The generated index uses schema version `1` and includes the fields documented
  in this spec.
- Missing or invalid input paths produce clear user-facing errors.
- Implementation follows the project's vertical-slice hexagonal architecture
  direction.
- Relevant unit tests cover discovery, index generation, JSON output, and CLI
  argument mapping.
- `uv run ruff format .`, `uv run ruff check .`, `uv run mypy .`, and
  `uv run pytest` pass before handoff.

## Open questions

- Should future consumer sync support Git URLs, raw HTTP index URLs, local paths,
  or all three?
- When consumer installation is added, should existing target skills be refused
  by default unless `--force` is provided?