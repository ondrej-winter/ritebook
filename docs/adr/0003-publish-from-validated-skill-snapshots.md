# 0003. Publish from Validated Skill Snapshots

Date: 2026-10-06
Status: Accepted

## Context

Ritebook validates skill paths and `SKILL.md` headers before generating a
publisher index. The previous publisher flow ran the linter as a precondition,
then independently rediscovered the same files and reparsed their frontmatter to
build index entries.

That two-pass design created a time-of-check/time-of-use boundary: files could
change between validation and publication, and the publisher's parser and path
mapping could drift from the linter contract. It also duplicated filesystem and
YAML responsibilities across feature slices.

The linter already owns discovery, parsing, catalog-path validation, and portable
header validation. The publisher owns catalog construction, timestamping, and
safe JSON output. Ritebook needs one explicit application boundary between those
responsibilities.

## Decision

The skill-linter application boundary will return an immutable, deterministic
publication snapshot only when the complete lint operation succeeds. Publisher
prechecks will map that snapshot to publisher-owned `SkillEntry` values, and the
publisher will generate the index from exactly those values without rediscovering
files or reparsing YAML.

The snapshot contains only the validated catalog data needed by the publisher:

- catalog-relative skill path;
- validated skill name;
- catalog-relative `SKILL.md` path; and
- normalized description.

If discovery, parsing, path validation, or header validation reports any issue,
the lint result and publisher precheck expose no partial snapshot. Empty valid
catalogs remain successful and produce an empty snapshot.

Filesystem traversal and YAML parsing remain linter-side outbound adapter
responsibilities. Publisher adapters retain only publisher-owned I/O such as
safe JSON index writing. Cross-slice mapping occurs at the publisher precheck
adapter, not through imports of linter adapter internals.

## Consequences

### Positive

- The index describes the exact application data that passed validation.
- Publication has no second filesystem read or YAML parse after the precheck.
- Lint and publication cannot silently diverge in discovery or header mapping.
- Filesystem and YAML concerns have one owning adapter path.
- Application tests can prove publication from a supplied immutable snapshot
  without filesystem test doubles.

### Negative

- Successful lint results carry additional immutable application data.
- Changes to published index-entry fields require coordinated linter snapshot and
  publisher boundary changes.
- A failed lint cannot expose otherwise valid entries for partial publication.

### Neutral

- The publisher still applies its own domain invariants when constructing a
  `SkillCatalog`.
- The snapshot is an in-process application contract, not a persisted schema or a
  new portable Agent Skills field.
- This decision does not add content hashes or protect against changes after the
  index has been written; committed-source provenance remains governed by
  [ADR 0001](./0001-source-provenance-and-trust.md).

## Alternatives considered

| Option | Reason rejected |
| ------ | --------------- |
| Validate, then rediscover and reparse in the publisher | Creates a time-of-check/time-of-use gap and duplicates boundary logic. |
| Move all discovery and parsing into the publisher | Makes standalone lint depend on publisher concerns and reverses feature ownership. |
| Return filesystem paths and let the publisher read them | Retains the second-read race and leaks adapter concepts into the application boundary. |
| Persist a temporary validated manifest | Adds lifecycle and cleanup complexity without benefit for the current in-process workflow. |

## Related specifications

- [Skill Linter](../specs/skill-linter-spec.md)
- [Publisher](../specs/publisher-spec.md)
- [Skill Contribution](../specs/skill-contribution-spec.md)
