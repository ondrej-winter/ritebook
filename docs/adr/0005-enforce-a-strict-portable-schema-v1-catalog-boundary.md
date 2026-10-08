# 0005. Enforce a Strict Portable Schema-v1 Catalog Boundary

Date: 2026-10-07
Status: Accepted

## Context

Ritebook's publisher, registry, installation, and contribution workflows exchange
the same schema-v1 `ritebook-index.json`, but their boundary checks have not all
been equivalent. The publisher constructs a narrow deterministic object, while
consumer reads have historically relied on permissive JSON decoding, cached-index
reads have parsed before independently checking the registered digest, and some
workflows have reconstructed catalog facts with secondary parsers.

That drift creates ambiguity around duplicate or unknown JSON members, resource
exhaustion, exact-byte provenance, alias intent, portable paths, and whether the
committed `SKILL.md` still agrees with the metadata selected from the index. A
schema-version bump would label the same intended catalog model as a different
format without solving the ownership problem: the publisher and every consumer
need one shared interpretation of schema v1.

## Decision

Ritebook will keep publisher and consumer catalogs at schema version 1 while
enforcing one closed, resource-bounded, portable validation contract at every
catalog boundary.

### Strict JSON and shared semantics

- Index bytes receive a bounded strict-JSON preflight before an object graph is
  constructed. Invalid UTF-8, a byte-order mark, input above 16 MiB, nesting above
  depth 32, non-standard numeric constants, duplicate object member names, and
  malformed JSON are rejected. Schema-v1 catalogs contain at most 10,000 skill
  entries.
- The schema-v1 root object, `index` object, and every skill object are closed:
  required members must be present and unknown members are rejected.
- Source admission and cached-index reads use the same semantic validator for
  schema version, timestamp, published name, skills root, skill entries, catalog
  structure, portable text, and portable paths.
- Publisher domain construction uses the same pure validation primitives before
  serialization, so output cannot rely on consumers to reject publisher-created
  invalid state.

### Exact bytes and cache trust

- The validated committed index remains exact `bytes`; Ritebook does not decode
  and re-encode it before computing its digest or writing the immutable cache.
- A cached index is checked against the registry entry's `index_digest` before
  UTF-8 decoding, JSON parsing, or semantic use.
- The registry file remains the atomic commit record. Cleanup of unreferenced
  candidate cache generations is best-effort and must not replace or obscure the
  result of the registry commit operation.

### Alias provenance

- Registry schema v1 persists `alias_origin` to distinguish a local alias derived
  from publisher `index.name` from one explicitly supplied by the consumer.
- Existing schema-v1 entries without `alias_origin` are migrated conservatively
  while reading: equality between `name` and `published_name` is treated as
  publisher-derived; a differing name is treated as explicit. The inferred value
  is persisted on the next successful registry write.

### Skill-header coherence

- The linter publishes a single-file validation application API in addition to
  whole-catalog linting. Both APIs return the same normalized description value.
- Installation validates the selected committed `SKILL.md` from the verified Git
  snapshot and requires its validated `name` and normalized `description` to
  equal the selected index entry before target planning, staging, or mutation.
- Contribution derives `skills_root` from its verified lockfile provenance and
  catalog selector. It does not maintain a permissive secondary JSON parser.

## Consequences

### Positive

- Publisher, source admission, cached reads, installation, and contribution use
  one schema-v1 interpretation.
- Duplicate or extension fields cannot be interpreted differently by different
  consumers.
- Cache corruption is detected before untrusted bytes are parsed.
- Installation cannot silently copy committed skill content whose portable header
  no longer matches the digest-bound index metadata.
- Explicit aliases remain distinguishable from aliases inherited from publisher
  metadata without changing the registry schema version.

### Negative

- Previously tolerated non-canonical schema-v1 documents may now be rejected and
  must be republished or re-registered.
- Strict preflight and committed-header validation add bounded parsing and file-read
  work to consumer workflows.
- Registry readers carry a narrow migration rule for legacy schema-v1 entries
  until those entries are rewritten.

### Neutral

- The publisher artifact does not gain content hashes, signatures, aliases, or
  installation-specific fields.
- Git commit and exact-index digest provenance remain governed by
  [ADR 0001](./0001-source-provenance-and-trust.md).
- The portable Agent Skills header remains governed by
  [ADR 0002](./0002-adopt-agent-skills-as-canonical-skill-schema.md).

## Alternatives considered

| Option | Reason rejected |
| ------ | --------------- |
| Introduce publisher schema version 2 | The intended catalog data model is unchanged; inconsistent validation does not justify a parallel wire format. |
| Keep permissive JSON decoding and validate selected fields | Duplicate and unknown members remain ambiguous, and resource bounds would still be applied too late. |
| Normalize and reserialize indexes before caching | Breaks the exact-byte digest binding and makes the cache a transformed artifact rather than the committed index. |
| Trust indexed headers without reading committed `SKILL.md` | A valid digest binds the index and commit but does not prove the selected committed header agrees with its index entry. |
| Let each feature parse the fields it needs | Recreates semantic drift and secondary permissive parsers. |

## Related specifications

- [Shared Catalog Contract](../specs/shared-catalog-contract-spec.md)
- [Skill Linter](../specs/skill-linter-spec.md)
- [Publisher](../specs/publisher-spec.md)
- [Index Registry](../specs/index-registry-spec.md)
- [Skill Installation](../specs/skill-installation-spec.md)
- [Skill Contribution](../specs/skill-contribution-spec.md)
