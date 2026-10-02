# Agent Skill schema policy

Use this rule when changing Ritebook's Agent Skill schema, validator, or related
documentation.

## Canonical baseline

- **Must** treat the
  [Agent Skills specification](https://agentskills.io/specification) as the
  canonical portable schema for skill directories and `SKILL.md`.
- **Must** require only `name` and `description` for portable header validity.
- **Must** limit optional top-level frontmatter to `license`, `compatibility`,
  `metadata`, and experimental `allowed-tools` unless a future canonical
  specification revision is adopted deliberately.
- **Must** keep Ritebook catalog path and layout rules separate from portable
  header validity.

## Compatible extensions

- **Must** keep every extension valid under the canonical schema and safely
  ignorable by clients that implement only the standard.
- **Must** keep `metadata` as a flat string-to-string mapping.
- **Should** use reasonably unique metadata keys when collision is possible.
- **Must not** add nested metadata, sequences, or custom top-level frontmatter
  fields.
- **Should** place structured requirements, related-skill routing, and workflow
  relationships in the Markdown body or optional supporting files.
- **May** define a stricter repository contribution profile using standard optional
  fields, but **must not** present that profile as the portable validity baseline.
- **Must** use `allowed-tools` only for supported tool pre-approval and not as a
  general dependency manifest.

## Change management and enforcement

- **Must** review upstream specification changes before changing Ritebook behavior;
  remote documentation changes do not silently redefine the active contract.
- **Must** use `author-agent-skill` for detailed authoring and review mechanics.
- **Must** enforce Ritebook validator behavior with focused automated tests.
- **Must not** use the installed `.agents/skills` tree as a repository quality-gate
  input; those skills are sourced from and validated by their owning collections.
- **Should** use the upstream reference validator as optional compatibility
  evidence, not as a required Ritebook runtime dependency.

This policy records
[ADR 0002](../docs/adr/0002-adopt-agent-skills-as-canonical-skill-schema.md).
