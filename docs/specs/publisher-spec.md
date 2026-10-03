# Specification: Publisher

## Status

- State: Active
- Revision: 2.1
- Acceptance basis: Existing Active repository contract; format normalized under the user's October 2, 2026 instruction without changing normative behavior.
- Accepted by / on: Original accepting person and date were not recorded.
- Owner: Ritebook maintainers
- Last reviewed: 2026-08-27
- Implementation state: Implemented
- Dependencies: [Shared Catalog Contract](shared-catalog-contract-spec.md) and [Skill Linter](skill-linter-spec.md)
- Associated ADRs: [ADR 0001: Bind Cached Indexes and Installed Skills to Git Commits](../adr/0001-source-provenance-and-trust.md)
- Supersedes: None

## Objective and Context

Ritebook provides a publisher-side workflow for corporate skill maintainers
to generate a deterministic index of approved internal agent skills from a
private repository. The index gives maintainers a reviewable catalog artifact
that supports consumer-side listing and installation without ad hoc shell
scripts.

The primary user is a skill maintainer or curator inside a company. The workflow
supports controlled internal skill curation and downstream developer
installation.

### Current-state evidence

- Publisher and linter capabilities are implemented as separate vertical feature
  slices under `src/ritebook/features/`.
- Python 3.13, `uv`, `ruff`, `ty`, and `pytest` are the project tooling
  baseline.
- Discovery recursively identifies every directory containing `SKILL.md` as a
  candidate, validates its header, and enforces schema-v1 depth, canonical
  segments, duplicate-path, and mixed-node constraints before publication.

## Scope

- In scope: Publishing one deterministic schema-v1
  `ritebook-index.json` from an explicit skills root, shared lint validation,
  catalog discovery, safe atomic output, and the publisher CLI contract.
- Out of scope: Consumer registration, listing, installation, synchronization,
  publisher-embedded provenance hashes or signatures, and implicit whole-repository
  or multiple-root discovery.

## Requirements

The following requirement groups preserve the normative publisher contract of revision 2.1.

Ritebook generates or updates a JSON index file for a maintainer-controlled
skills repository.

### R1 — Publisher workflow

**Basis:** Existing active Ritebook contract and the dependencies recorded in the Status section.

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

### R2 — Skill discovery

**Basis:** Existing active Ritebook contract and the dependencies recorded in the Status section.

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

### R3 — Index output

**Basis:** Existing active Ritebook contract and the dependencies recorded in the Status section.

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

### R4 — CLI and workflow requirements

**Basis:** Existing active Ritebook contract and the dependencies recorded in the Status section.

The CLI is simple and explicit:

```bash
uv run ritebook indexes publish --skills-root <path> --name <published-name>
```

Requirements:

- Require an explicit `--skills-root`.
- Treat the invocation working directory as the repository and output root.
- Require `--skills-root` to resolve to that root or one of its descendants.
- Normalize relative and absolute `--skills-root` inputs to the same portable
  repository-relative `skills_root` value.
- Require an explicit stable kebab-case `--name` for `indexes publish`.
- Support one skills root per command invocation; multiple roots are out of scope
  for the MVP.
- Always write the canonical `ritebook-index.json` in the invocation working
  directory; no output argument is needed.
- Overwrite an existing generated index only when the command is explicitly run;
  no background or implicit updates.
- `indexes publish` must reuse the skill-header validation flow as a hard
  precondition and must not write or overwrite the index when validation fails.
- Emit concise success output that includes discovered skill count and output
  path.
- Keep process environment access, filesystem traversal, CLI parsing, and JSON
  serialization in adapters or bootstrap code, not in domain models.
- Keep YAML/frontmatter parsing in adapters; pass parsed plain data into
  application/domain validation.

## Implementation and Verification Evidence

### Project structure

The implementation follows the repository's hexagonal vertical-slice direction.

- `src/ritebook/features/publisher/domain/`: pure catalog concepts and invariants.
- `src/ritebook/features/publisher/application/`: publisher use case, ports, and
  DTOs.
- `src/ritebook/features/publisher/adapters/`: publisher CLI command, filesystem
  discovery, and JSON index writer adapters.
- `tests/unit/features/publisher/`: focused tests mirroring source ownership.
- `docs/specs/publisher-spec.md`: this specification.
- `docs/specs/skill-linter-spec.md`: the validation contract consumed by publisher.

### Conventions

- Keep discovery, filesystem writes, and JSON serialization in adapters.
- Keep publisher orchestration independent of CLI and filesystem details.
- Render path-scoped diagnostics without logging raw skill-file contents.

### Commands and validation

When changing this workflow, use focused checks first, then the full local
quality gate before handoff.

- Format check: `uv run ruff format --check .`
- Lint: `uv run ruff check .`
- Type check: `uv run ty check src/ritebook`
- Default tests: `uv run pytest` (Docker E2E is deselected unless explicitly enabled)
- Build: `uv build`
- Docker E2E: `docker build -f Dockerfile.e2e -t ritebook-e2e .` then
  `docker run --rm ritebook-e2e`

Adding `PyYAML` for frontmatter parsing must update both `pyproject.toml` and
`uv.lock`.

### Testing strategy

The MVP should be covered primarily with fast, deterministic unit tests.

- Domain tests verify catalog entry creation, deterministic path ordering,
  duplicate names at distinct paths, and basic invariants.
- Application tests use fakes for skill discovery, skill validation, and index
  writing ports.
- Application tests verify `indexes publish` does not call the writer when skill
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

## Constraints and Execution Boundaries

### Binding constraints

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
  be shared by `skills lint` and `indexes publish`.

### Changes requiring specification approval

- Adding consumer install, sync, or list behavior to the publisher slice.
- Adding content hashes, signatures, policy enforcement, or trust-chain
  behavior to the publisher artifact. The consumer-owned exact-index digest
  required by [ADR 0001](../adr/0001-source-provenance-and-trust.md) is not a
  publisher field.

### Exclusions and prohibited behavior

- Never scan a whole repository implicitly in the first MVP; require an explicit
  skills root.
- Never accept multiple skills roots in a single MVP command invocation.
- Never scan hidden directories by default in the MVP.
- Never log or print skill file contents by default.

## Acceptance Checks

| ID | Requirement | Conditions and action | Expected observable result | Verification method |
| --- | --- | --- | --- | --- |
| AC1 | R1 | A maintainer publishes from an explicit valid or invalid skills root. | A valid root produces `ritebook-index.json`; validation failure exits non-zero and does not create or overwrite the prior index. | Publisher use-case and CLI tests. |
| AC2 | R2 | Discovery encounters root skills, collection children, duplicate names at distinct paths, hidden directories, over-deep candidates, or mixed nodes. | Valid catalog paths are indexed deterministically; hidden directories are skipped; over-deep and mixed structures fail with path-scoped errors. | Discovery adapter and application tests. |
| AC3 | R3 | Ritebook serializes and replaces an index, including simulated write, flush, sync, replacement, or unsafe-symlink failures. | Schema-v1 fields and required descriptions are emitted with two-space deterministic JSON; failures preserve prior content and clean owned temporary files; no publisher provenance fields are embedded. | JSON writer and schema tests. |
| AC4 | R4 | Invoke `indexes publish` with valid arguments, missing or invalid roots, and validation failures. | Arguments map to one explicit skills root and published name, success output is concise, and errors are actionable without exposing skill contents. | CLI adapter tests. |
| AC5 | R1-R4 | Review source ownership and execute focused publisher tests. | The implementation follows vertical-slice hexagonal boundaries and covers discovery, generation, output, and CLI behavior. | Import-boundary checks and `uv run pytest tests/unit/features/publisher`. |
| AC6 | R1-R4 | Run the documented implementation handoff gates. | Formatting, linting, type checking, non-E2E tests, package build, and network-disabled Docker E2E all succeed. | Commands recorded under Implementation and Verification Evidence. |

## Assumptions

- Publisher-maintained skills repositories are Git repositories with a reviewable
  root `ritebook-index.json` artifact.
- Schema version `1` and the shared catalog contract remain the compatibility
  baseline.
- Material unresolved assumptions: None.

## Open Questions

None.

## Revision and Handoff Notes

- October 2, 2026: Reformatted revision 2.1 to the current
  spec-driven-development template under the user's instruction. Requirement
  meaning, lifecycle state, and revision number were preserved.
- Next authorized step: Treat this Active revision as canonical. Consumer
  workflows or publisher artifact trust fields require their owning specification
  or an approved revision before implementation.
