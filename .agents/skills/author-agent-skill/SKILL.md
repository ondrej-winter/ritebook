---
name: author-agent-skill
description: Create, update, or review Agent Skill directories and SKILL.md files for valid frontmatter, structure, portability, progressive disclosure, and validation readiness.
metadata:
  version: "2.1.0"
  last-verified: "2026-10-15T11:05:37Z"
---

# Author Agent Skill

Create, revise, or review a skill that an agent can discover, follow without
hidden local context, and verify. A valid package is necessary; useful task
selection, instructions, and outputs also need evidence.

## Steps

### 1. Establish scope and ownership

Identify whether the request calls for creation, revision, or review only. For an
existing skill, inspect its instructions, supporting files, callers, applicable
repository rules, and working-tree changes before editing. Find the authored
source and any generated or installed copies. Preserve unrelated changes and
supported host settings; do not reinitialize an existing skill.

Define the task, expected result, inputs, prerequisites, and evidence of success.
Use actual requests, project artifacts, or demonstrated failures to decide what
belongs in the skill. Distinguish reusable guidance from repository-, language-,
or framework-specific requirements. Resolve material unknowns before dependent
work; do not require an interview when the request already supplies enough context.

Check nearby skill descriptions for overlap. Keep one coherent workflow and add
an exclusion only when it prevents likely misrouting. Repository-wide agent
policy and client configuration belong to `author-agents-config` when its trigger
matches; reusable task procedures belong here.

### 2. Write a discoverable, valid header

Start `SKILL.md` on the first line with YAML frontmatter. Follow the
[Agent Skills specification](https://agentskills.io/specification), then apply
any documented target-host extensions and repository conventions separately.
Do not reject a valid external skill merely for omitting this shelf's conventions.

The portable header requires:

- `name`: 1–64 lowercase letters, numbers, or hyphens; no leading, trailing, or
  consecutive hyphens. Match the directory name exactly. Prefer short,
  action-oriented ASCII kebab-case names for interoperability.
- `description`: a non-empty string of at most 1024 characters explaining what
  the skill does and when to select it. Include the terms a real request would use;
  put detailed procedure in the body.

Optional top-level fields are:

- `license`: a license name or reference to a bundled license file.
- `compatibility`: a 1–500-character string for meaningful environment requirements.
- `metadata`: a map of string keys to string values, without nested objects or lists.
- `allowed-tools`: an experimental, space-separated string of tool declarations.
  Use only when supported by the target host, consistent with the workflow and
  existing authorization. It does not override host permissions or user scope.

Quote YAML values when punctuation or implicit typing could change their meaning.
Keep custom fields only when the target host or repository tooling documents them;
label such dependencies rather than promising portability.

#### Shelf lifecycle conventions

This shelf additionally requires quoted strings for `metadata.version` and
`metadata.last-verified`. These are local conventions, not required format fields.

```md
---
name: skill-name
description: Brief description of what the skill does and when to use it.
metadata:
  version: "1.0.0"
  last-verified: "2026-10-01T20:08:01Z"
---
```

Replace the example values with the skill's own data. Increase the version when
instructions, metadata, scripts, references, or assets change:

- patch: clarifications, typo fixes, or validation-only updates
- minor: new guidance, optional resources, or compatible workflow improvements
- major: breaking changes to activation, required structure, workflow, or outputs

Advance `last-verified` only after checking the instructions and supporting files
for consistency, portability, and validation readiness. Use the actual review time
as an ISO 8601 timestamp with an explicit timezone. An edit, version bump, or commit
timestamp does not establish verification. Report the checks and their limits
separately; the timestamp does not certify runtime behavior in every host.

### 3. Write an executable workflow

Give the agent the context and decisions it would otherwise miss. State the
expected output and completion evidence, with steps where order matters. Match
detail to the task's fragility; avoid generic advice and repeated policy.

Place requirements beside the step that needs them: required inputs, tools,
dependencies, permissions, external services, and the working directory for
commands. Verify unfamiliar or changing APIs and host behavior against current
primary documentation. Identify platform-specific behavior explicitly.

Explain what to do when an input or capability is unavailable. A useful fallback
must name its limits, such as a review-only result with execution unverified.
If no useful fallback exists, report the affected step as blocked and continue
independent work. Never count skipped required execution as successful validation.

Keep actions within the user's scope and existing authorization. For workflows
that mutate external state or retry operations, make side effects and stopping
conditions clear. A skill must not silently authorize publication or other actions
beyond the request.

When another skill is relevant, describe the relationship and check availability:

- `route`: select it when its own trigger matches
- `handoff`: transfer a defined part of the workflow
- `verification`: use it to gather evidence
- `awareness`: coordinate with its constraints without automatic activation

Keep catalog-wide relationships in routing guidance. A mention does not activate
an optional skill recursively; its trigger or an explicit handoff must apply.
If a required skill is missing, report the dependency and use only a documented
fallback rather than inventing its instructions.

### 4. Package only useful supporting material

Keep essential instructions in `SKILL.md`. The specification recommends a body
under 5000 tokens and a file under 500 lines; aim for the shortest useful workflow,
not those limits. Use plain Markdown. This shelf uses one top-level heading after
frontmatter, concise sections, and no decorative formatting; the open format does
not mandate a body layout.

Add supporting files only when they improve execution or let the agent load
conditional detail on demand:

- `scripts/`: reusable executable helpers with dependencies, invocation, and failure
  behavior documented. Run new or changed helpers on representative safe inputs.
- `references/`: focused instructions or documentation, linked where needed with a
  clear condition for reading each file.
- `assets/`: templates, static inputs, and other resources used by the workflow or
  its output, rather than extra instructions to load by default.

Link resources from `SKILL.md` with paths relative to the skill root; avoid nested
reference chains. For executable commands, explain how to resolve those paths from
the installed skill location without assuming the shell starts there. Distinguish
skill resources from paths in the user's working project.

Use generic placeholders such as `<repo_name>` when examples do not require a real
project. Label necessary local details. Avoid private paths, usernames, empty
resource directories, unfinished scaffolding, and duplicated documentation.
Inspect references and callers before removing or relocating existing resources.

### 5. Validate structure and behavior separately

Run focused checks before broader repository validation. Fix relevant failures,
then rerun affected checks. Do not expand the task to unrelated audit findings.

**Package checks:** run the repository's configured skill/documentation checks and,
when available, the open reference validator:

```bash
skills-ref validate <path/to/skill-directory>
```

For this shelf, also run Ritebook lint using the supported command and scan root
from its help. When a validator is unavailable, manually check the format rules
above and report the missing automated check. A validator pass never substitutes
for content review; if its result conflicts with the current specification,
identify the tool/version limitation before changing valid content.

**Content checks:** inspect the final files and diff. Confirm header types and
limits, lifecycle metadata where required, resolvable links, usable commands,
necessary resources, and preservation of supported host settings. Read the workflow
from an unfamiliar agent's perspective: can it identify inputs, select the right
branch, produce the result, and verify completion without hidden context?

**Behavior checks:** for new or materially changed workflows, choose representative
requests that should activate the skill, a nearby request that should not, and a
relevant boundary such as missing input or unavailable tooling. For a small edit,
check the affected behavior only. Evaluate outcomes and scope, not exact wording.
Where practical, execute a harmless representative task and inspect the trace and
artifacts; run helpers in an isolated temporary workspace. Use an independent
agent when complexity or risk justifies it, supplying the request, skill, and
necessary inputs without coaching the expected answer.

Label a paper walkthrough as review evidence. Explicitly loading the skill does
not prove automatic discovery; a syntax check does not prove execution. Report
unavailable target-host testing as unverified, not as a passing behavioral check.

### 6. Reconcile copies and hand off

Edit the canonical source first, then synchronize declared installed or packaged
copies and verify byte parity. Review affected generated catalog state through the
repository workflow. Follow its authorization rules for regeneration, installation,
publication, commits, and remote updates; do not rewrite generated provenance by
hand or overwrite edited skills with an older published copy.

Report the changed skill and version, material findings and fixes, validation
commands and results, behavioral evidence, parity, and any unverified or deferred
work. For review-only requests, report findings without making edits. Keep
compatibility claims tied to documentation and distinguish them from behavior
observed in a target runtime.

## Authoring references

Consult the [format specification](https://agentskills.io/specification) for
interoperability rules and the [official authoring guidance](https://agentskills.io/skill-creation/best-practices)
for scope, progressive disclosure, and evaluation practices. Check the intended
host's primary documentation before relying on extensions or discovery behavior.
