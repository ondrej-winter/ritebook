---
name: author-agents-config
description: Initialize, audit, update, or synchronize a repository's coding-agent instructions and client adapters. Use for AGENTS.md, scoped instructions, CLAUDE.md, .clinerules, .cline/rules, Copilot instructions, or migrations between agent configuration layouts. Keep shared policy canonical and adapters minimal. Not for authoring reusable SKILL.md capabilities, defining agent personas, ordinary application changes, or configuring runtime permissions.
metadata:
  version: "1.2.1"
  last-verified: "2026-09-30T21:31:34+02:00"
---

# Author agents config

## Purpose

Create the smallest evidence-backed agent configuration that lets the selected
clients work consistently in this repository.

Author shared project instructions in `AGENTS.md` and, where justified, scoped
`AGENTS.md` files. Treat client-specific files as mostly static adapters, not
independent versions of project policy.

Preserve the target repository's established canonical skill source. For a fresh
setup, choose a source only from explicit project intent and verified client
support; `.agents/skills/` is a suitable default when Codex or a shared Agent
Skills layout is selected. Skill authoring belongs to `author-agent-skill`; do
not reproduce its methodology here.

## Read supporting material when needed

Paths below are relative to this skill's directory, not the target repository.

- Read [ownership.md](references/ownership.md) before authoring or moving policy.
- Read the relevant sections of [client-adapters.md](references/client-adapters.md)
  before changing client integration. Verify uncertain or version-sensitive facts.
- Read [validation.md](references/validation.md) before final verification.
- Use files in `assets/` only as scaffolds for new files, never as replacements
  for existing content. Omit unsupported sections and resolve all placeholders.
  The files in `assets/clinerules/` are an exact fresh-project scaffold: copy
  them byte-for-byte only when the corresponding target files are absent.

## 1. Establish intent and scope

Infer the mode from the request; the user does not need to name it explicitly.

| Mode | Permitted work |
| --- | --- |
| `init` | Establish missing canonical instructions and requested client support. Preserve existing configuration. |
| `update` | Improve shared instructions within the requested scope; reconcile affected adapters. |
| `sync` | Reconcile adapters and existing skill discovery wiring. Do not change canonical policy or skill content. |
| `audit` | Inspect and report only. Do not modify repository files or configuration. |

Resolve the repository/workspace boundary, selected clients and surfaces,
existing canonical sources for instructions and skills, and explicit constraints
from available context. Existing files are evidence, not permission to remove a
client, replace an established canonical source, or migrate it.

For a fresh setup with no selected clients, establish only shared configuration
and report that client selection remains unspecified. Do not scaffold every
known client. Where uncertainty affects only one adapter, leave it unchanged
and continue with independent, well-supported work.

For a fresh setup with Cline selected and no established instruction or skill
ownership, use root `AGENTS.md` for shared policy, `.agents/skills/` for reusable
task procedures, and the three files in [assets/clinerules](assets/clinerules/)
for Cline-only operating mechanics. Copy those files unchanged into root
`.clinerules/`, and merge `.tmp/cline/` into `.gitignore` without replacing
existing ignore rules. Treat the setup as fresh only when the destination files
are absent. If `AGENTS.md`, either Cline rules layout, or another canonical skill
root already exists, reconcile it under the preservation rules instead.

## 2. Inspect before editing

Read existing root and relevant scoped instructions, client adapters, and any
repository-local override files. Inspect the working tree and symlink targets.
Do not follow write targets outside the agreed workspace.

Read the relevant README/contribution guidance, package or build manifests,
test entry points, CI definitions, and architecture/domain documentation.
Inspect skill metadata only as needed to identify existing capabilities.
Do not load every skill or recursively consume the entire repository.

Distinguish explicit project requirements, configured behavior, observed
patterns, and proposed new policy. An observed pattern is not automatically a
mandatory rule. Do not invent commands, paths, architecture, or team decisions.

If sources conflict, use clear authoritative evidence where available. Otherwise
preserve the disputed content and report the decision needed. Do not silently
resolve policy conflicts by selecting whichever client file loads last.

## 3. Assign each concern one authoritative owner

- Shared obligations and essential operating context: root `AGENTS.md`.
- Narrower obligations: the appropriate scoped `AGENTS.md`.
- Reusable task procedures: skills, owned through `author-agent-skill`.
- Architecture explanations and domain facts: existing documentation/specifications.
- Client-only behavior and compatibility glue: client-specific adapters.
- Enforced restrictions and deterministic settings: runtime, tools, scripts, CI.
- Temporary goals, plans, and progress: the current task, not standing instructions.

Make a concise change plan separating policy edits from adapter edits. A
configuration request does not authorize weakening permissions, editing secrets,
installing clients, creating hooks, or changing application/CI behavior.

## 4. Author canonical instructions — init/update only

Keep only information that is important for correct work and not better owned
elsewhere. Include relevant orientation, supported command entry points,
non-obvious constraints, validation obligations, and completion evidence.

Use exact repository-relative paths and commands supported by inspected sources.
State prerequisites and working directories when material. Link to authoritative
configuration instead of restating all of its settings.

Give conditional references concrete triggers: "Before changing X, read Y."
Do not imply that a Markdown link automatically loads its target.

Create scoped files only for meaningful differences. Keep shared requirements
at the root; do not duplicate the root into each subtree or create one file per
folder. Define intended scope without inventing universal client precedence.

Use [agents.md.template](assets/agents.md.template) and, when needed,
[scoped-agents.md.template](assets/scoped-agents.md.template) as section prompts.
Remove empty sections, unsupported claims, and template placeholders.

For a fresh Cline setup, include an explicit Git and external-action boundary in
root `AGENTS.md`. The bundled template defaults to local inspection, editing, and
validation while requiring user authorization for commits, pushes, publication,
remote mutation, and destructive commands. Preserve stricter existing policy and
do not weaken a repository's established authorization model.

Do not insert generic personas, lengthy tutorials, a full skill catalog, task
logs, or speculative rules. Important policy must remain available independently
of optional skill activation.

When extracting a procedure is part of an authorized migration, use the existing
`author-agent-skill` capability if available. Otherwise report an extraction
handoff and preserve the source procedure; do not discard it or invent a
replacement skill. Unrelated skill authoring is outside this task.

## 5. Reconcile minimal client adapters

For each selected client, establish its actual surface, relevant version/settings,
and supported discovery behavior. Apply the smallest supported solution:

1. Native discovery of the canonical source: add nothing.
2. Supported import: add a thin importer.
3. Supported link/projection: expose the same source without independent authoring.
4. Generated copy: last resort, with deterministic regeneration and a drift check.

A plain instruction to "read AGENTS.md" is a behavioral fallback, not a proven
native import. Use it only when acceptable and report its limitations. Preserve
scope: do not inject every nested policy into the global context for convenience.

For Claude Code, test native `AGENTS.md` discovery first when the installed
version, session, settings, and applicable `CLAUDE.md` files permit it. Add the
[claude-adapter.md.template](assets/claude-adapter.md.template) import only as a
fallback. Do not assume either native root loading or a root import also exposes
every nested `AGENTS.md`.

For a fresh Cline setup, install the exact `assets/clinerules/` scaffold for
Cline-only mechanics even though Cline can also read shared `AGENTS.md` policy.
For an existing project, preserve `.clinerules/` and `.cline/rules/`; both are
supported and searched when present. Do not copy rules into both layouts or
overwrite existing files merely to match the scaffold.

Do not move skills out of the target repository's established canonical source
unless migration is explicitly requested and verified. Add discovery wiring only
where needed; check for duplicate discovery, broken relative resources, symlink
support, and portability. A directory link is not universally supported.
Current Cline implementation scans project `.agents/skills/`; use that existing
canonical source directly when target behavior is verified instead of creating a
second Cline skill tree. Consult the dated client reference because public Cline
documentation may lag implementation behavior.

Preserve client-specific content and unrelated user changes. Before deleting a
legacy rule, account for every retained obligation and verify replacement scope
and loading. If that cannot be established, retain the legacy file and report
migration as incomplete rather than silently losing coverage.

Do not create a manifest, installer, generator, or new configuration framework
merely to maintain a static importer. Use existing tooling where available.

## 6. Validate and report

Follow [validation.md](references/validation.md). Check paths, imports, scope,
policy duplication, placeholders, discovery wiring, and the final diff.

Distinguish static inspection, documentation-backed compatibility, and observed
runtime discovery. Test fresh-session loading where available and authorized.
Do not claim runtime verification from file existence or agent self-report alone.
Do not execute unsafe or expensive project commands just to document them.

Reconcile a second time conceptually or through existing checks: unchanged inputs
should require no further edits. Avoid timestamps, reordered sections, and prose
churn in otherwise unchanged adapters.

Report the mode, files changed or intentionally retained, substantive policy
changes, per-client loading approach and verification status, checks performed,
and unresolved decisions. Keep this report outside always-on instructions.
A verified no-op is a valid result.
