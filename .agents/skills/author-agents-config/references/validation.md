# Validation

Separate package correctness, repository reconciliation, and actual client
behavior. Passing one layer does not prove the others.

## Static repository checks

Inspect the final diff and actual files, not just the planned changes.

1. Every introduced command/path has a source. Material working directories and
   prerequisites are explicit. Generated instructions contain no template tokens.
2. Each shared obligation has one authored owner. Client-only exceptions remain
   intact. A moved obligation retains both meaning and intended scope.
3. Imports/links resolve relative to the correct file. They do not cycle, escape
   the allowed workspace, overwrite unrelated files, or reference missing content.
4. Native discovery has not been accompanied by a redundant adapter or second skill
   copy. An existing projection has not been mistaken for an independently authored
   source or overwritten through its target.
5. Scoped rules are not copied into every folder or hoisted globally without need.
   Relevant overrides and loader limitations have been accounted for.
6. Generated copies, if unavoidable, have real regeneration and drift checks. Static
   importers have not acquired an unnecessary generation framework.
7. `sync` has left canonical policy and skill content unchanged. `audit` has written
   no repository files. All modes preserve unrelated working-tree changes.
8. No secrets, personal/global settings, approvals, hooks, application behavior,
   or CI behavior were changed outside explicit scope.
9. A fresh Cline bootstrap copied all three bundled rule files byte-for-byte,
   established root `AGENTS.md` and canonical `.agents/skills/`, and merged
   `.tmp/cline/` into existing ignore rules without replacing them.
10. An existing Cline configuration was reconciled rather than overwritten. No
    duplicate rules or skill projection was added when native discovery sufficed.

Commands found in source are **configured**, not **executed successfully**. Use
that wording in reports. Do not run deployment, destructive, costly, or external
service commands simply to verify a documentation task.

## Loading verification

Record one or more separate evidence levels for each client/scope:

| Evidence | What it establishes |
| --- | --- |
| Static | Files, syntax, local targets, and intended structure were inspected. |
| Documented | Official documentation supports the mechanism for a stated surface. |
| Source-backed | Current official implementation source supports behavior not yet reflected in published documentation. Record the source revision and target surface. |
| Runtime observed | A fresh target-client session exposes the intended source in loader/context diagnostics, or equivalent observable evidence. |
| Behavioral sample | A harmless task exhibits the expected behavior; useful supporting evidence, not proof of universal compliance. |
| Unverified/deferred | The required client, version, setting, permission, or observation was unavailable. |

Where the client is available, start or inspect an authorized fresh session without
bypassing approvals or trust controls. Use its available instruction/rule/context
views and skill discovery output. Check the canonical source, any intended adapter,
and a relevant scoped file separately.

A model saying "I read AGENTS.md" without observable corroboration is insufficient
for a runtime-observed claim. Explicitly attaching a file also does not prove that
it would have been discovered automatically.

For scoped configurations, test launch/work from the root and within a relevant
subtree as applicable. Confirm whether scope depends on startup directory or later
file access. Check that irrelevant subtree policy is not globally injected.

For skills, confirm the canonical capability is discoverable through the selected
mechanism and its resources remain reachable. Avoid activating unrelated skills
merely to demonstrate that every skill can be loaded.

If runtime verification is unavailable, complete static/documented checks and say
so. Do not delete an existing working loading path while replacement coverage
remains unresolved.

## Idempotence

With the same sources and selected clients, a repeat reconcile should require no
further edits. Compare before/after file contents using existing repository tools.
Do not regenerate dates, arbitrary identifiers, ordering, or commentary on each run.

For a generated adapter, run the concrete generator twice and confirm the second
run leaves no content change; run its drift check as well. For an importer, verify
that its already-correct content is retained rather than stylistically rewritten.
A conceptual second pass is weaker evidence than an executed repeat; report which
was performed.

## Behavioral acceptance cases for this skill

These are evaluation cases, not tests already executed by including this file.
Run them against disposable repositories or safe fixtures with an actual agent.

| Case | Expected result |
| --- | --- |
| Fresh repository; no clients specified | Evidence-backed shared instructions only; no kitchen-sink client scaffolding. |
| Fresh repository; Codex selected | Native canonical paths; no redundant Codex policy adapter. |
| Fresh repository; Cline selected | Root `AGENTS.md`, canonical `.agents/skills/`, exact three-file `.clinerules/` scaffold, and `.tmp/cline/` ignore coverage. |
| Fresh Cline bootstrap repeated | Scaffold, shared policy, skill root, and ignore entry remain unchanged. |
| Add Claude Code; native AGENTS.md supported and selected | No adapter; canonical policy and skill content unchanged. |
| Add Claude Code; native AGENTS.md unavailable or displaced | Thin `@AGENTS.md` fallback; canonical policy and skill content unchanged. |
| Existing `.clinerules/` or `.cline/rules/` | Existing path and content preserved; no scaffold overwrite or speculative migration. |
| Both Cline rule layouts exist | Combined loading and conflicts inspected; rules are not copied between layouts. |
| Cline version includes `.agents/skills/` scanning | Canonical skills used directly; no `.cline/skills/` or `.clinerules/skills/` projection. |
| Cline documentation and implementation source differ | Difference reported with source revision; runtime support not overstated. |
| Audit requested with writable tools available | Findings only; no repository writes or "helpful" repairs. |
| Existing CLAUDE.md mixes shared and client-only content | Authorized update moves shared policy without losing Claude-specific behavior. |
| Long workflow in existing rules; author-agent-skill unavailable | Procedure retained; extraction handoff reported; no silent deletion. |
| Nested AGENTS.md; client starts at root | Actual discovery inspected; root import not assumed to expose all descendants. |
| Copilot surface unspecified | No universal support claim; ambiguous adapter changes deferred. |
| Contradictory policies without an authoritative decision | Conflict reported and disputed content preserved, not settled by invented precedence. |
| Existing skill symlink, dirty files, or external link target | No duplicate copy, unrelated overwrite, or out-of-workspace write. |
| Existing canonical skill root is not `.agents/skills/` | Existing ownership is preserved unless an explicit, verified migration is requested. |
| Existing `AGENTS.md` or Cline rules contain project policy | Existing obligations reconciled individually; generic templates do not replace them. |
| Current correct configuration run twice | No adapter timestamp/prose churn and no newly redundant files. |
| "Fix this application test" with no config request | This skill is not selected merely because AGENTS.md exists. |
| Sync requested but AGENTS.md is missing | Missing canonical dependency reported; no silent policy authoring. |

## Completion report

Keep the completion report in the task response or an explicitly requested report,
not in always-on instructions. A useful compact format is:

```text
Mode and scope:
Canonical sources:
Changed / retained files:
Substantive policy changes:
Client and surface | Loading mechanism | Evidence level | Remaining gap
Checks actually performed:
Conflicts, deferred migrations, or handoffs:
```

Say "no changes required" when the requested state already exists and specify
what was checked. Avoid unsupported claims such as "all agents now follow the
same rules" or "production actions are blocked" based solely on Markdown.
