# Spec: Publisher

> **Status:** Active
> **Owner:** Ritebook maintainers
> **Spec version:** 2.0
> **Last reviewed:** 2026-07-23
> **Implementation state:** Implemented
> **Dependencies:** [Shared Catalog Contract](shared-catalog-contract-spec.md) and [Skill Linter](linter-spec.md)
> **Associated ADRs:** [ADR 0001: Bind Cached Indexes and Installed Skills to Git Commits](../adr/0001-source-provenance-and-trust.md)

## Objective

Ritebook provides a publisher-side workflow for corporate skill maintainers
to generate a deterministic index of approved internal agent skills from a
private repository. The index gives maintainers a reviewable catalog artifact
that supports consumer-side listing and installation without ad hoc shell
scripts.

The primary user is a skill maintainer or curator inside a company. The workflow
supports controlled internal skill curation and downstream developer
installation.

## Implementation status

- Publisher and linter capabilities are implemented as separate vertical feature
  slices under `src/ritebook/features/`.
- Python 3.13, `uv`, `ruff`, `ty`, and `pytest` are the project tooling
  baseline.
- Discovery recursively identifies every directory containing `SKILL.md` as a
  candidate, validates its header, and enforces schema-v1 depth, canonical
  segments, duplicate-path, and mixed-node constraints before publication.

## Desired behavior

Ritebook generates or updates a JSON index file for a maintainer-controlled
skills repository.

### Publisher workflow

1. A maintainer runs a Ritebook publisher command from the repository root that
   will contain `ritebook-index.json`, with an explicit skills root path at or
   below that root.
2. Ritebook scans the skills root for directories containing a file named
   `SKILL.md` and validates that each candidate is either a root skill or an
   immediate child of one collection.
3. Ritebook builds a deterministic catalog of discovered skills.
4. Ritebook validates every discovered skill with the same rules used by the
   standalone skill lint workflow.
5. If validation succeeds, Ritebook writes the catalog to the canonical
   `ritebook-index.json` file.
6. If validation fails, Ritebook reports the validation issues, exits non-zero,
   and must not write or overwrite `ritebook-index.json`.
7. The maintainer reviews and commits the generated index to the private skills
   repository through the normal pull request workflow.

### Skill discovery

- Discovery applies the catalog structure and canonical identifier rules from the
  shared catalog contract.
- Directories and files inside a valid skill package remain unrestricted unless
  they contain another `SKILL.md`, which would declare an invalid nested candidate
  skill.
- Discovered skills are publishable only when the linter use case accepts every
  `SKILL.md`.
- The generated index uses skill-entry paths relative to the skills root and a
  `skills_root` relative to the repository root containing the index, so all
  serialized paths stay portable within the repository.
- Output ordering is deterministic by catalog path.
- Hidden directories under the skills root are skipped by default in the MVP.
- Missing or unreadable skills root paths must produce clear user-facing errors at the
  adapter boundary.
- Catalog-structure failures must identify the offending path and whether it is
  over-deep or combines skill and collection roles.

### Index output

- The canonical output filename is `ritebook-index.json`.
- The index must be valid JSON.
- The index must include a schema version so future versions can evolve without
  ambiguity.
- The index must include enough data for future consumer commands to list and
  locate skills.
- The index must be pretty-printed with two-space indentation for pull request
  review.
- Ritebook must serialize the complete index before creating or replacing output.
- Ritebook must create a uniquely named, permission-restricted temporary file in
  the output directory, write and flush the complete UTF-8 payload, synchronize
  the file, and atomically replace `ritebook-index.json` only after those steps
  succeed.
- The output directory path and existing `ritebook-index.json` must not contain
  symlinks. Unsafe output paths must be rejected without modifying the symlink
  target.
- Serialization, temporary-write, flush, synchronization, or replacement failure
  must leave prior valid index content unchanged. Ritebook-owned temporary files
  must be removed after handled failures.
- Schema v1 requires every published skill to have a valid `SKILL.md` header, but
  it does not need to include the full parsed header in `ritebook-index.json`.
- Schema v1 does not include publisher-generated per-skill or repository content
  hashes. After the generated index is committed, consumers compute an
  `index_digest` over the exact committed index bytes and bind it to that Git
  commit according to
  [ADR 0001](../adr/0001-source-provenance-and-trust.md).
- The consumer-owned digest is registry provenance; it does not change the
  publisher index schema or authenticate the publisher.

## CLI and workflow requirements

The CLI is simple and explicit:

```bash
uv run ritebook publish-index --skills-root <path> --index-name <published-name>
```

Requirements:

- Require an explicit `--skills-root`.
- Treat the invocation working directory as the repository and output root.
- Require `--skills-root` to resolve to that root or one of its descendants.
- Normalize relative and absolute `--skills-root` inputs to the same portable
  repository-relative `skills_root` value.
- Require an explicit stable kebab-case `--index-name` for `publish-index`.
- Support one skills root per command invocation; multiple roots are out of scope
  for the MVP.
- Always write the canonical `ritebook-index.json` in the invocation working
  directory; no output argument is needed.
- Overwrite an existing generated index only when the command is explicitly run;
  no background or implicit updates.
- `publish-index` must reuse the skill-header validation flow as a hard
  precondition and must not write or overwrite the index when validation fails.
- Emit concise success output that includes discovered skill count and output
  path.
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
- `tests/unit/features/publisher/`: focused tests mirroring source ownership.
- `docs/specs/publisher-spec.md`: this specification.
- `docs/specs/linter-spec.md`: the validation contract consumed by publisher.

## Commands and validation

When changing this workflow, use focused checks first, then the full local
quality gate before handoff.

- Format check: `uv run ruff format --check .`
- Lint: `uv run ruff check .`
- Type check: `uv run ty check src/ritebook`
- Non-E2E tests: `uv run pytest -m "not e2e"`
- Build: `uv build`
- Docker E2E: `docker build -f Dockerfile.e2e -t ritebook-e2e .` then
  `docker run --rm --network none ritebook-e2e`

Adding `PyYAML` for frontmatter parsing must update both `pyproject.toml` and
`uv.lock`.

## Testing strategy

The MVP should be covered primarily with fast, deterministic unit tests.

- Domain tests verify catalog entry creation, deterministic path ordering,
  duplicate names at distinct paths, and basic invariants.
- Application tests use fakes for skill discovery, skill validation, and index
  writing ports.
- Application tests verify `publish-index` does not call the writer when skill
  validation fails.
- Filesystem adapter tests use temporary directories to verify recursive
  `SKILL.md` candidate discovery, valid root and collected skill paths, ignored
  non-skill directories, over-deep path rejection, mixed skill/collection node
  rejection, frontmatter parsing, and path-scoped validation failures.
- JSON writer tests verify schema version, deterministic output, required
  description behavior, two-space indentation, valid JSON, atomic replacement,
  failure preservation and cleanup, permission-safe unique temporary files, and
  symlink rejection.
- CLI adapter tests verify argument mapping, clear errors for missing root paths,
  publisher show-stopper behavior, and user-facing success output.

Default tests must not rely on live external services, global developer state, or
network access.

## Boundaries

- Always keep business rules and catalog concepts independent of CLI, filesystem,
  and JSON serialization details.
- Always validate external inputs at adapter boundaries before invoking the
  application use case.
- Always validate skill headers before publishing an index.
- Always restrict published skill paths to `<skill>` or
  `<collection>/<skill>` relative to the explicit skills root.
- Always reject mixed skill/collection nodes and over-deep candidate paths before
  writing an index.
- Always keep output deterministic enough for pull request review.
- Always allow duplicate skill names at distinct relative paths in one index.
- Always pretty-print generated JSON with two-space indentation.
- Mandatory `SKILL.md` header validation is in scope for this milestone and must
  be shared by `lint-skills` and `publish-index`.
- Ask before adding consumer install, sync, or list commands to this milestone.
- Ask before adding content hashes, signatures, policy enforcement, or trust-chain
  behavior to the publisher artifact. The consumer-owned exact-index digest
  required by [ADR 0001](../adr/0001-source-provenance-and-trust.md) is not a
  publisher field.
- Never scan a whole repository implicitly in the first MVP; require an explicit
  skills root.
- Never accept multiple skills roots in a single MVP command invocation.
- Never scan hidden directories by default in the MVP.
- Never log or print skill file contents by default.

## Success criteria

- A maintainer can run a publisher workflow against an explicit skills root and
  produce `ritebook-index.json`.
- The generated index lists every structurally valid discovered directory
  containing `SKILL.md`.
- Root skills and immediate collection-child skills are indexed, while over-deep
  candidates and mixed skill/collection nodes fail with path-scoped errors.
- `publish-index` reuses the same validation flow and refuses to write or
  overwrite `ritebook-index.json` when validation fails.
- The generated index is deterministic for unchanged input except for the
  documented generation timestamp.
- The generated index uses schema version `1` and includes the fields documented
  in the shared catalog contract.
- The generated index remains compatible with consumer-side binding to its
  committed Git revision and exact-byte digest without embedding provenance
  fields in the publisher artifact.
- Missing or invalid input paths produce clear user-facing errors.
- Implementation follows the project's vertical-slice hexagonal architecture
  direction.
- Relevant unit tests cover discovery, index generation, JSON output, and CLI
  argument mapping.
- `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run ty check src/ritebook`, `uv run pytest -m "not e2e"`, `uv build`, and the
  network-disabled Docker E2E gate pass before handoff.
