# 0002. Adopt Agent Skills as the Canonical Skill Schema

Date: 2026-10-02
Status: Accepted

## Context

Ritebook validates, publishes, installs, and contributes Agent Skill directories.
The portable skill format is defined outside this repository, while Ritebook also
enforces product-specific catalog path constraints and validation behavior.

Ritebook already accepts the minimal Agent Skills header and the standard optional
fields. Some independently maintained skill collections use additional lifecycle
or routing conventions, but the Agent Skills specification defines `metadata` as
a flat string-to-string mapping. Ritebook needs an explicit rule for accepting
compatible extensions without taking ownership of external collection policy.

A durable precedence rule is needed so local conventions can add useful policy
without creating a competing skill schema or silently changing when the upstream
specification evolves.

## Decision

Ritebook will treat the
[Agent Skills specification](https://agentskills.io/specification) as the
canonical baseline for portable skill directories and `SKILL.md` headers.
Ritebook-specific profiles and extensions may add policy only when the resulting
skill remains valid under that canonical specification and the addition can be
ignored safely by clients that implement only the standard.

The portable header contract is:

- `name` and `description` are the only required frontmatter fields.
- `license`, `compatibility`, `metadata`, and experimental `allowed-tools` are the
  supported optional frontmatter fields.
- `metadata` remains a flat mapping from string keys to string values. Local keys
  should be reasonably unique when collision is possible.
- Structured requirements, related-skill routing, and workflow relationships
  belong in the Markdown body or optional supporting files, not nested metadata.
- Ritebook does not add custom top-level frontmatter fields.

An independently maintained repository or skill collection may define a stricter
contribution profile using standard optional fields. Requirements such as
string-valued `metadata.version` and `metadata.last-verified` do not change
portable Agent Skills validity and are not imposed by the general Ritebook linter.

The `.agents/skills` directory in this repository contains externally sourced
skills. Their owning collections are responsible for validating them, so Ritebook
does not use that installed tree as a local, pre-commit, or CI quality-gate input.

Ritebook catalog layout, path depth, and canonical identifier constraints remain
separate product contracts. They may be stricter than the portable skill header
without redefining the Agent Skills schema.

Upstream specification changes are adopted deliberately through a reviewed update
to the active Ritebook specification, tests, authoring guidance, and validation
evidence. A remote documentation change does not silently alter released Ritebook
behavior. The upstream `skills-ref` validator may be used as compatibility
evidence, but it is not a Ritebook runtime dependency.

## Consequences

### Positive

- Skills remain portable across clients that implement the Agent Skills format.
- Ritebook can accept compatible flat lifecycle metadata without defining a
  competing schema.
- Focused tests enforce validator behavior without making Ritebook responsible for
  externally sourced installed skills.
- Rich dependency and routing explanations remain available in human-readable
  skill instructions and references.

### Negative

- Structured dependency metadata cannot be queried directly from frontmatter.
- Collection-specific profile requirements need separate review or tooling when
  they are stricter than portable validity.
- Upstream schema changes require an explicit maintenance change rather than being
  adopted automatically.

### Neutral

- Existing flat string metadata such as `version` and `last-verified` remains valid.
- `allowed-tools` remains experimental and agent-dependent.
- Ritebook catalog path rules continue to be validated independently.

## Alternatives considered

| Option                                                     | Reason rejected                                                                                                                                      |
| ---------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Keep nested `metadata.dependencies`                        | It violates the canonical flat metadata contract and prevents portable validation.                                                                   |
| Define a Ritebook-only top-level extension namespace       | Unknown top-level fields are not part of the canonical schema and would reduce client compatibility.                                                 |
| Encode structured dependencies as JSON strings in metadata | Technically flat but opaque, difficult to maintain, and unnecessary when body guidance and supporting files are available.                           |
| Make the upstream reference validator a runtime dependency | The local validator already owns deterministic product behavior, and the reference implementation is better used as optional compatibility evidence. |

## Related specifications

- [Skill Linter](../specs/skill-linter-spec.md)
- [Shared Catalog Contract](../specs/shared-catalog-contract-spec.md)
