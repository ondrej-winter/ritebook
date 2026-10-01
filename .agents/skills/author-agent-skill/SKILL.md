---
name: author-agent-skill
description: Create, update, or review Agent Skill directories and SKILL.md files for valid frontmatter, structure, portability, progressive disclosure, and validation readiness.
metadata:
  version: "2.0.0"
  last-verified: "2026-09-30T20:31:51+02:00"
---

# Author Agent Skill

Use this skill when creating, updating, or reviewing an Agent Skill. The goal is
to keep each skill valid, easy for agents to discover, portable across projects,
and concise enough to load only the guidance needed for the task.

The expected outcome is a skill directory that can be copied into a compatible
agent environment, discovered from its metadata, followed without hidden local
context, and validated or reviewed with clear evidence before handoff.

## When to use this skill

Use this skill when:

- creating a new skill directory
- editing an existing `SKILL.md`
- reviewing skill metadata, naming, or structure
- deciding what belongs in `scripts/`, `references/`, or `assets/`
- checking whether a skill remains reusable outside its current repository

## Steps

### 1. Confirm the skill purpose

Define the task the skill helps an agent perform. Prefer a focused workflow over
a broad collection of unrelated guidance.

Confirm:

- the user-facing task or decision the skill supports
- when an agent should use the skill
- whether the skill is generic, language-specific, framework-specific, or
  repository-specific
- whether examples and commands can stay portable

### 2. Choose a valid skill name

Use a short, descriptive, kebab-case directory name. The frontmatter `name` must
match the parent directory exactly.

The name must:

- be 1 to 64 characters
- use only lowercase letters, numbers, and hyphens
- not start or end with a hyphen
- not contain consecutive hyphens

Prefer action-oriented names such as `write-adr`, `run-local-quality-gate`, or
`author-agent-skill`.

### 3. Add the skill header

`SKILL.md` must start on the first line with YAML frontmatter. Treat this
frontmatter as the skill header. The Agent Skills format requires `name` and
`description`. This shelf also requires string-valued `metadata.version` for
skill lifecycle tracking and `metadata.last-verified` for verification
freshness.

Use this required shape:

```md
---
name: skill-name
description: Brief description of what the skill does and when to use it.
metadata:
  version: "1.0.0"
  last-verified: "2026-10-01T20:08:01Z"
---
```

The description should explain both:

- what the skill helps with
- when an agent should use it

Keep the description non-empty, specific, and no longer than 1024 characters.

Use `metadata.version` to track skill revisions. Increase the version whenever
the skill behavior, instructions, metadata, assets, scripts, or references
change. Prefer semantic versioning:

- patch for clarifications, typo fixes, or validation-only updates
- minor for new guidance, checklist items, optional supporting files, or
  backward-compatible workflow improvements
- major for breaking changes to when or how the skill should be used, required
  structure, or expected outputs

Use `metadata.last-verified` to record when the skill instructions and
supporting files were most recently checked for internal consistency,
portability, and validation readiness. Store it as a quoted ISO 8601
timestamp with an explicit timezone, for example
`"2026-10-01T20:08:01Z"`. Advance it only when that verification was
actually performed; an ordinary edit or version bump does not by itself
prove verification. When introducing the field to an existing collection with
no prior verification record, a documented one-time migration may seed it from
the most recent commit timestamp for each `SKILL.md`.

### 4. Document requirements and tool access portably

Do not put nested objects or sequences under `metadata`. The Agent Skills format
defines `metadata` as a map from string keys to string values, so structures such
as `metadata.dependencies.tools` and `metadata.dependencies.skills` are not
portable.

Use `compatibility` for concise environment requirements that matter before the
skill is selected:

```md
compatibility: Requires Git and permission to run local validation commands.
```

Describe detailed runtime capabilities, permissions, external services, fallback
behavior, and related-skill handoffs in the instructions. Keep requirements near
the step that needs them so an agent can distinguish mandatory execution from a
conditional enhancement.

When the skill participates in a catalog, express workflow relationships in the
catalog's routing or composition guidance. This collection uses these relationship
terms in prose:

- `route`: select the referenced skill when its own trigger matches
- `handoff`: transfer a defined part of the workflow when instructed
- `verification`: use the referenced skill to gather evidence
- `awareness`: coordinate with its constraints without automatic activation

An optional related skill is not recursively activated merely because a catalog
mentions it. Its trigger or an explicit handoff must be present.

If the target agent format supports pre-approved tool declarations, add
`allowed-tools` as a top-level frontmatter field. Treat it as an experimental
space-separated string and keep it consistent with the tool usage documented in
the instructions.

### 5. Use only supported optional frontmatter fields

Add optional fields only when they are useful and supported by the skill format.
For this shelf, required metadata includes string-valued `metadata.version` and
`metadata.last-verified`; additional metadata keys remain optional and must
also have string values.

Supported optional top-level fields are:

- `license`
- `compatibility`
- `allowed-tools`

Keep optional fields concise and format them according to the target Agent Skills
specification. Use `compatibility` only for meaningful environment requirements,
`allowed-tools` only when tool pre-approval is supported by the target
environment.

Additional keys under `metadata` are optional. Include them only when they provide
useful string-valued metadata supported by the target environment.

Do not add custom frontmatter fields unless the target skill system or repository
tooling explicitly requires them.

### 6. Structure the skill body

After frontmatter, include one top-level heading that names the skill in a
human-readable form.

A practical structure is:

```md
---
name: skill-name
description: Brief description of what the skill does and when to use it.
metadata:
  version: "1.0.0"
  last-verified: "2026-10-01T20:08:01Z"
---

# Skill Name

Short explanation of when and why to use the skill.

## Steps

1. First action
2. Second action
3. Validation or handoff action
```

Use section headings only when they improve navigation. Use `## Steps` for a
repeatable workflow.

### 7. Apply progressive disclosure

Keep the main `SKILL.md` concise and self-contained. Move detailed or rarely used
material into optional directories when needed:

- `scripts/` for executable helper code
- `references/` for focused supporting documentation
- `assets/` for templates, static files, schemas, or examples

Only add these directories when they reduce main-file complexity or provide
content an agent can load on demand. Do not create empty optional directories or
split short guidance just to mirror the directory convention.

When referencing supporting files, use relative paths from the skill root. Prefer
simple one-level references where practical.

### 8. Keep reusable skills portable

For reusable skills, avoid local repository paths, private project names, local
usernames, or commands that only make sense in one repository.

Prefer placeholders such as:

- `<package_name>`
- `<app_name>`
- `<repo_name>`
- `<python_version>`

If a section must be repository-specific, label it clearly so readers can tell it
is not part of the portable guidance.

### 9. Keep formatting plain

Use plain Markdown that improves navigation and correctness. Avoid emojis,
decorative separators, banners, ornamental callouts, and visual-only formatting.

Prefer:

- concise headings
- short paragraphs
- simple bullet lists
- minimal examples in fenced code blocks

### 10. Validate before handoff

Run the repository's skill or documentation validation command when available. If
the target environment provides an Agent Skills validator, use it for the changed
skill directory.

When no validator is available, manually check the review checklist below.

In the handoff, report what changed, which skill directory was validated, which
commands passed, and any validation that was skipped with the reason.

## Review checklist

- `SKILL.md` exists in the skill directory
- frontmatter starts at the first line
- frontmatter includes `name`, `description`, `metadata`, `metadata.version`,
  and `metadata.last-verified`
- `name` matches the parent directory exactly
- `name` is valid kebab-case
- `description` explains both what the skill does and when to use it
- `metadata.version` is present, quoted, and increased when the skill changed
- `metadata.last-verified` is present, quoted, includes an ISO 8601 timezone,
  and advances only when verification was actually performed
- every `metadata` key and value is a string; nested objects and sequences are
  absent
- environment requirements use `compatibility` or clear instructions when needed
- related-skill routing and handoffs are explained in catalog or body guidance
- `allowed-tools`, when present, is a space-separated string consistent with the
  documented tool usage
- unsupported frontmatter fields are absent
- supported optional frontmatter fields are correctly shaped and necessary
- exactly one top-level heading follows the frontmatter
- instructions explain when and how to use the skill
- examples are generic and portable unless clearly marked otherwise
- optional `scripts/`, `references/`, and `assets/` content is necessary,
  non-empty, and referenced clearly when relevant
- formatting is plain and free of decorative noise
- validation was run or any skipped validation is documented
