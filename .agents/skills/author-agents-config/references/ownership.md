# Ownership and authoring decisions

This is the design contract for this skill, not a claim that all clients implement
an identical instruction hierarchy.

## Separate authoring from reconciliation

`author-agents-config` authors and maintains the repository's ambient instruction
contract. Its adapter step exposes that contract to clients. It does not own the
project's engineering decisions and must not create new obligations simply to
fill a template.

`author-agent-skill` authors reusable capabilities: task selection, methodology,
specialized judgment, supporting resources, and task-specific outputs. The two
skills are siblings. This skill can request a narrowly scoped extraction through
that capability, but neither should recursively invoke the other without a
specific unresolved task.

`sync` is deliberately narrower than `update`. Requests such as "add Claude
support without touching our policy" must leave canonical policy unchanged.
When a required canonical source is missing, report the dependency; do not
silently turn a sync into policy authoring.

The target repository owns its canonical skill source. Preserve an existing
authored root such as `.agents/skills/`, `.claude/skills/`, `.cline/skills/`, or
another documented project location unless migration is explicitly requested.
Client discovery locations may be projections of that source; their existence
does not make each projection independently authoritative. For a fresh setup,
choose a source from explicit project intent and verified selected-client support.

When Cline is selected for a genuinely fresh project with no existing ownership
decision, this package defaults to root `AGENTS.md`, canonical `.agents/skills/`,
and the exact bundled `.clinerules/` scaffold. `AGENTS.md` owns shared repository
policy; `.clinerules/` owns only Cline-specific operating mechanics. The bundled
scaffold is a derived distribution asset, not an additional policy authority.
After initialization, the target repository owns its copied files.

## Placement test

| Question | Owner |
| --- | --- |
| What must acceptable work satisfy here, regardless of skill activation? | Root or scoped `AGENTS.md` |
| What specialized method helps complete this class of task? | A skill |
| What is true about the system, and why was it designed this way? | Documentation or specifications |
| What is different specifically because this client is being used? | Client adapter or client-only instructions |
| What must be executed or enforced mechanically? | Tooling/runtime configuration, scripts, CI |
| What is the objective or current state of this one task? | Task prompt, issue, or working plan |

The fresh Cline scaffold depends on root `AGENTS.md` containing an explicit Git
and external-action authorization boundary and on `.tmp/cline/` being ignored.
These prerequisites belong to shared policy and repository ignore configuration,
not to duplicated project rules inside `.clinerules/`.

A subject can appear in multiple layers with different responsibilities. For
example: a policy requires regression evidence; a skill describes investigation;
a specification defines expected behavior; CI executes applicable tests.
Do not copy the same obligation independently into every layer.

## Evidence discipline

Prefer explicit user decisions and authoritative project policy for obligations.
Use manifests, scripts, and CI to establish configured commands and prerequisites.
Use architecture/domain documents for system claims. Use code samples as evidence
of observed practice, not proof of team-wide policy.

Check for stale documentation against current executable definitions. A command
present in CI is configured, not necessarily suitable for local execution or
verified to pass. Record such distinctions in the completion report.

If a policy decision is genuinely missing, omit it from persistent instructions
and identify the open question. Do not promote a suggestion into mandatory policy.
Small evidence-backed instructions are better than an invented complete handbook.

## Writing rules

Write short, actionable statements whose scope is evident. Include concise
rationale where it prevents a likely mistake; put full rationale in documentation.
Preserve existing terminology and formatting unless they impede correctness.

Use essential command entry points rather than copying every pipeline stage.
Do not duplicate formatter options, dependency versions already pinned elsewhere,
or large repository trees that will drift. Avoid "be senior," "write clean code,"
and other personality or quality slogans without operational meaning.

A reference should identify when it is needed. For example, a project with an
existing order lifecycle specification might require reading it before changing
order transitions. Do not introduce that rule or document path in repositories
where no such requirement/source exists.

## Scoping

Place universal requirements at the root. Add a scoped file only for a distinct
subsystem or work category with genuine additional requirements. A scoped file
should contain the difference, not a copied parent contract.

A scoped exception to a shared rule must be intentional and supported by a project
decision. Do not assume that filename proximity will resolve contradictions.
Investigate actual client loading behavior separately.

Where a client cannot discover scoped policy natively, prefer a supported scoped
adapter. A short root reading obligation can be a fallback, but it remains a
behavioral fallback, not automatic scope enforcement. State the limitation.

## Migration without information loss

For each existing instruction, record mentally or in the change plan whether it
is retained, moved, intentionally superseded, or unresolved. This mapping should
cover client-specific exceptions as well as shared policy.

Do not delete a procedural rule before its destination exists and the requested
migration has accounted for discovery. Without `author-agent-skill`, preserve the
procedure and provide an extraction brief: intended trigger, destination concept,
source location, and obligations that must remain ambient.

Do not apply the fresh Cline scaffold over an existing `AGENTS.md`, `.clinerules/`,
or `.cline/rules/` tree. Reconcile each existing file, preserve client-specific
content, and require an explicit migration decision before changing layout or
canonical skill ownership.

Avoid turning an uncertain migration into another permanent active policy copy.
Where replacement loading cannot be established, keep the existing path and
report precisely what is deferred. A no-op or partial independent improvement is
preferable to unverified destructive cleanup.

## Change boundaries

Repository instructions do not grant new permissions. Do not modify global
profiles, personal memories, secrets, tool approvals, hooks, MCP registration,
agent personas/subagents, application code, or CI configuration merely because
these are adjacent to agent configuration.

An explicitly requested extension can be handled separately using the appropriate
capability. Preserve unrelated changes and do not write through a symlink into a
user/global directory or another repository.
