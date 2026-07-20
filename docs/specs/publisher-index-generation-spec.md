# Spec: Publisher Skill Index Generation

## Objective

Ritebook provides a publisher-side workflow for corporate skill maintainers
to generate a deterministic index of approved internal agent skills from a
private repository. The index gives maintainers a reviewable catalog artifact
that supports consumer-side listing and installation without ad hoc shell
scripts.

The primary user is a skill maintainer or curator inside a company. The workflow
supports controlled internal skill curation and downstream developer
installation.

## Current context

- Publisher and linter capabilities are implemented as separate vertical feature
  slices under `src/ritebook/features/`, with domain, application, ports, and
  adapters separated according to hexagonal architecture principles.
- Python 3.13, `uv`, `ruff`, `ty`, and `pytest` are the project tooling
  baseline.
- For discovery, any directory containing `SKILL.md` is considered a candidate
  skill directory. Candidate skills must pass the skill-header validation flow
  before they are publishable.

## Desired behavior

Ritebook generates or updates a JSON index file for a maintainer-controlled
skills repository.

### Publisher workflow

1. A maintainer runs a Ritebook publisher command or application use case with an
   explicit skills root path.
2. Ritebook recursively scans the skills root for directories containing a file
   named `SKILL.md`.
3. Ritebook builds a deterministic catalog of discovered skills.
4. Ritebook validates every discovered skill with the same rules used by the
   standalone skill lint workflow.
5. If validation succeeds, Ritebook writes the catalog to the canonical
   `ritebook-index.json` file.
6. If validation fails, Ritebook reports the validation issues, exits non-zero,
   and must not write or overwrite `ritebook-index.json`.
7. The maintainer reviews and commits the generated index to the private skills
   repository through the normal pull request workflow.

### Skill lint workflow

Ritebook must provide a validation-only workflow for skill authors, maintainers,
and CI:

```bash
uv run ritebook lint-skills --skills-root <path>
```

Requirements:

- Require an explicit `--skills-root`.
- Discover candidate skill directories with the same traversal rules used by
  `publish-index`.
- Validate every discovered `SKILL.md` against the required Agent Skill header
  contract.
- Emit deterministic, path-scoped validation output suitable for CI logs.
- Exit with status code `0` only when all discovered skills are valid.
- Exit non-zero when one or more skills are invalid or the skills root cannot be
  inspected.
- Do not write or update `ritebook-index.json`.
- Share the validation implementation with `publish-index` so the lint and
  publishing rules cannot drift.

### Skill discovery

- A skill is any directory containing `SKILL.md`.
- Discovery must be recursive under the explicit skills root.
- Discovered skills are publishable only when their `SKILL.md` files satisfy the
  required skill-header validation contract.
- The generated index should use paths relative to the skills root so the index
  stays portable within the repository.
- Output ordering must be deterministic, sorted by relative skill path or another
  documented stable key.
- Hidden directories under the skills root are skipped by default in the MVP.
- Missing or unreadable skills root paths must produce clear user-facing errors at the
  adapter boundary.

### Skill header validation

Every discovered `SKILL.md` must begin with YAML frontmatter that follows the
Agent Skill header contract. The `conventional-commits` skill is the reference
example for the required shape:

```yaml
---
name: conventional-commits
description: Write, review, and validate Conventional Commits v1.0.0 messages with correct type, scope, description, body, footer, and breaking-change syntax.
metadata:
  version: "1.0.1"
  dependencies:
    tools:
      - name: git
        purpose: Inspect repository state while drafting or reviewing commits.
        required: false
    skills:
      - name: git-workflow-and-versioning
        purpose: Apply repository-safe Git workflow practices.
        required: false
---
```

Validation requirements:

- Frontmatter must start on the first line with `---`.
- Frontmatter must have a closing `---` delimiter before the Markdown body.
- Frontmatter must parse as YAML with `PyYAML` using `yaml.safe_load()` over the
  bounded frontmatter block.
- Parsed frontmatter must be a mapping.
- `name` is required.
- `name` must be a string using valid kebab-case:
  - 1 to 64 characters
  - lowercase ASCII letters, digits, and hyphens only
  - must not start or end with a hyphen
  - must not contain consecutive hyphens
- `name` must match the parent skill directory name.
- `description` is required, must be a non-empty string, and must be at most
  1024 characters.
- `metadata` is required and must be a mapping.
- `metadata.version` is required and must be a string.
- `metadata.dependencies` is required and must be a mapping.
- `metadata.dependencies.tools` is required and must be a list.
- `metadata.dependencies.skills` is required and must be a list.
- Every dependency list item must be a mapping with non-empty string `name` and
  `purpose` fields plus a boolean `required` field. Plain strings are rejected.

Validation output must identify the skill file path and the violated rule without
printing full skill file contents. Example:

```text
conventional-commits/SKILL.md: metadata.dependencies.skills must be a list.
```

### Index output

- The canonical output filename is `ritebook-index.json`.
- The index must be valid JSON.
- The index must include a schema version so future versions can evolve without
  ambiguity.
- The index must include enough data for future consumer commands to list and
  locate skills.
- The index must be pretty-printed with two-space indentation for pull request
  review.
- Schema v1 requires every published skill to have a valid `SKILL.md` header, but
  it does not need to include the full parsed header in `ritebook-index.json`.
- Schema v1 must not include content hashes. Hashing can be added later if
  consumer caching or tamper detection requires it.

## Index schema v1

Schema v1 stays small and describes discovered skill package boundaries.

```json
{
  "schema_version": 1,
  "index": {
    "name": "company-skills"
  },
  "generated_at": "2026-07-04T18:49:00Z",
  "skills_root": ".",
  "skills": [
    {
      "name": "example-skill",
      "path": "example-skill",
      "skill_file": "example-skill/SKILL.md",
      "description": "Helps users complete an example workflow."
    }
  ]
}
```

### Field requirements

- `schema_version`: integer schema version. MVP value is `1`.
- `index.name`: required stable kebab-case publisher index name.
- `generated_at`: timezone-aware UTC timestamp in ISO 8601 format. The timestamp
  source should be injectable or controllable in tests.
- `skills_root`: stable representation of the scanned root. Relative inputs are
  serialized as supplied; absolute inputs are serialized as `.`.
- `skills`: array of discovered skill entries sorted deterministically.
- `skills[].name`: skill metadata derived from the skill directory name.
- `skills[].path`: relative path from the skills root to the skill directory.
- `skills[].skill_file`: relative path from the skills root to `SKILL.md`.
- `skills[].description`: required non-empty human-readable description copied
  from the validated skill header `description` field.
- `skills[].path` is the unique identity and downstream resolution key within an
  index. Multiple entries may have the same `skills[].name` when their paths differ.

## CLI and workflow requirements

The CLI is simple and explicit:

```bash
uv run ritebook publish-index --skills-root <path> --index-name <name>
uv run ritebook lint-skills --skills-root <path>
```

Requirements:

- Require an explicit `--skills-root`.
- Require an explicit stable kebab-case `--index-name` for `publish-index`.
- Support one skills root per command invocation; multiple roots are out of scope
  for the MVP.
- Always write the canonical `ritebook-index.json`; no output argument is needed.
- Overwrite an existing generated index only when the command is explicitly run;
  no background or implicit updates.
- `publish-index` must reuse the skill-header validation flow as a hard
  precondition and must not write or overwrite the index when validation fails.
- `lint-skills` must run the same validation flow without writing an index.
- Emit concise success output that includes discovered skill count and output
  path.
- Emit concise lint success output that includes validated skill count.
- Keep process environment access, filesystem traversal, CLI parsing, and JSON
  serialization in adapters or bootstrap code, not in domain models.
- Keep YAML/frontmatter parsing in adapters; pass parsed plain data into
  application/domain validation.

## Project structure

The implementation follows the repository's hexagonal vertical-slice direction.

- `src/ritebook/features/publisher/domain/`: pure catalog concepts and invariants.
- `src/ritebook/features/publisher/application/`: publisher use case, ports, and
  DTOs.
- `src/ritebook/features/publisher/adapters/`: publisher CLI command, filesystem
  discovery, and JSON index writer adapters.
- `src/ritebook/features/linter/application/`: shared skill-header validation use
  cases and ports.
- `src/ritebook/features/linter/adapters/`: linter CLI, filesystem/frontmatter,
  and publisher-precheck adapters.
- `tests/unit/features/publisher/` and `tests/unit/features/linter/`: focused tests
  mirroring source ownership.
- `docs/specs/publisher-index-generation-spec.md`: this specification.

## Commands and validation

When changing this workflow, use focused checks first, then the full local
quality gate before handoff.

- Format: `uv run ruff format .`
- Lint: `uv run ruff check .`
- Type check: `uv run ty check src/ritebook`
- Test: `uv run pytest`
- Build: `uv build`

Adding `PyYAML` for frontmatter parsing must update both `pyproject.toml` and
`uv.lock`.

## Testing strategy

The MVP should be covered primarily with fast, deterministic unit tests.

- Domain tests verify catalog entry creation, deterministic path ordering,
  duplicate names at distinct paths, and basic invariants.
- Domain/application tests verify the skill-header validation contract, including
  valid metadata, missing frontmatter, malformed YAML, invalid names, name/path
  mismatches, missing required metadata, and invalid dependency list types.
- Application tests use fakes for skill discovery, skill validation, and index
  writing ports.
- Application tests verify `publish-index` does not call the writer when skill
  validation fails.
- Filesystem adapter tests use temporary directories to verify recursive
  `SKILL.md` discovery, relative path handling, frontmatter parsing, and
  path-scoped validation failures.
- JSON writer tests verify schema version, deterministic output, required
  description behavior, two-space indentation, and valid JSON.
- CLI adapter tests verify argument mapping, clear errors for missing root paths,
  `lint-skills` success/failure behavior, `publish-index` show-stopper behavior,
  and user-facing success output.

Default tests must not rely on live external services, global developer state, or
network access.

## Boundaries

- Always keep business rules and catalog concepts independent of CLI, filesystem,
  and JSON serialization details.
- Always validate external inputs at adapter boundaries before invoking the
  application use case.
- Always validate skill headers before publishing an index.
- Always keep output deterministic enough for pull request review.
- Always allow duplicate skill names at distinct relative paths in one index.
- Always pretty-print generated JSON with two-space indentation.
- Mandatory `SKILL.md` header validation is in scope for this milestone and must
  be shared by `lint-skills` and `publish-index`.
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
- `lint-skills` validates every discovered `SKILL.md` against the required header
  contract and exits non-zero on invalid skills.
- `publish-index` reuses the same validation flow and refuses to write or
  overwrite `ritebook-index.json` when validation fails.
- The generated index is deterministic for unchanged input except for the
  documented generation timestamp.
- The generated index uses schema version `1` and includes the fields documented
  in this spec.
- Missing or invalid input paths produce clear user-facing errors.
- Implementation follows the project's vertical-slice hexagonal architecture
  direction.
- Relevant unit tests cover discovery, index generation, JSON output, and CLI
  argument mapping.
- `uv run ruff format .`, `uv run ruff check .`, `uv run ty check src/ritebook`, and
  `uv run pytest` pass before handoff.

## Open questions

- None for the publisher workflow. Consumer registry and installation behavior
  are specified separately.
