# Client adapters

Sources checked: **2026-10-15**. These are documentation- or source-backed
starting points, not observations of the user's installed clients. Recheck every
affected official source when changing compatibility guidance, introducing a
client, migrating a layout, or encountering behavior that conflicts with this
reference. Preserve working configuration when evidence is unclear.

Keep compatibility facts here, not duplicated throughout `SKILL.md` or every
repository's always-on instructions. Advance the review date only after a real
compatibility review; do not refresh dates or files on a no-op sync.

## Starting points

| Client/surface | Shared instructions | Canonical skill exposure |
| --- | --- | --- |
| Codex | Native `AGENTS.md`; inspect startup scope and overrides. | Native `.agents/skills/` discovery. |
| Claude Code | Native `AGENTS.md` when version, session, settings, and applicable `CLAUDE.md` files permit; import fallback otherwise. | Documented project location is `.claude/skills/`; per-skill directory symlinks are documented. |
| Cline | Documented `AGENTS.md` support; exact `.clinerules/` bootstrap adds Cline-only mechanics for fresh projects. | Configuration docs list `.agents/skills/`; the Skills page lists `.clinerules/skills/`, `.cline/skills/`, and `.claude/skills/`. |
| GitHub Copilot | Depends on IDE, feature, and agent harness. VS Code documents `AGENTS.md` support with harness-specific settings. | Documented project roots include `.github/skills/`, `.claude/skills/`, and `.agents/skills/`; confirm the selected surface. |

Sources and qualifications follow. The design preference is native discovery,
then actual import, then supported projection, then managed generated content.
A textual request to read a file is not the same as any of those mechanisms.

## Codex

Use canonical `AGENTS.md` directly. The documented instruction chain is built at
startup from project root to working directory. `AGENTS.override.md` can replace
`AGENTS.md` at the same level, and a configured size limit applies. Inspect
existing overrides rather than declaring the visible root file authoritative
for the effective prompt without checking.

Codex documents repository skills under `.agents/skills/`. Do not add a second
skill location when the canonical location is already discovered. Test from both
the repository root and a relevant subdirectory when scoped instructions matter;
do not equate initial discovery with automatic loading on every later file edit.

Sources:
- [Codex instruction discovery](https://developers.openai.com/codex/agent-configuration/agents-md)
- [Codex skill discovery](https://developers.openai.com/codex/build-skills)

## Claude Code

Claude Code 2.1.277 and later can load `AGENTS.md` directly. Before 2.1.281,
some sessions such as Amazon Bedrock or telemetry-disabled sessions could not use
that support, so verify the actual version and session. Native loading is the
first candidate when no `CLAUDE.md`, `.claude/CLAUDE.md`, or `CLAUDE.local.md`
exists in the working directory or above it. Inspect `/config`: the default
`claude-md-or-agents-md` selects `AGENTS.md` only in that absence, while
`claude-md-and-agents-md` loads both families. `claude-md` and `managed-only` do
not load project `AGENTS.md` directly.

Use `/memory` to inspect loaded instruction paths where the installed version
supports that display. If direct loading is unavailable, or an applicable
`CLAUDE.md` is retained under `claude-md-or-agents-md` or `claude-md`, use the
bundled `@AGENTS.md` adapter as a fallback. `managed-only` excludes that project
adapter too. Neither native root loading nor root import itself loads every
descendant instruction file. Native nested `AGENTS.md` loads when the Read tool
opens a file in that subtree; under the default setting, applicable Claude files
can displace it. Test scoped behavior separately.

When migrating away from an import, removing only `@AGENTS.md` while retaining
`CLAUDE.md` still suppresses native loading under `claude-md-or-agents-md`.
Remove an otherwise unnecessary adapter file only within an authorized migration,
after accounting for Claude-only content, ancestor files, and sessions needing
the fallback. Otherwise retain the working import.

Project skills are documented under `.claude/skills/`. Per-skill symlinked
directories are supported in the documented project location. Keep authored
content in the target repository's established canonical source; project it only
when needed and portable for the intended environment. Do not generalize this
support to every plugin/packaging surface or every other client.

Preserve real Claude-only instructions. Inspect existing settings and trust or
import-consent behavior without weakening them. A valid import line is a static
check, not proof that the file entered a particular running session.

Sources:
- [Claude Code memory and AGENTS.md imports](https://code.claude.com/docs/en/memory)
- [Claude Code skill locations](https://code.claude.com/docs/en/skills)

## Cline

The Rules documentation lists `AGENTS.md` as a supported source and describes
rule toggles. Prefer verified native loading instead of another shared-policy
file. Root support alone does not establish nested scope semantics.

The Rules documentation says VS Code, Desktop, and CLI search and combine both
`.clinerules/` and `.cline/rules/` when present. Verify the installed version's
loading; documented support alone does not establish runtime coverage.
Preserve the project's existing choice; do not duplicate rules between the two
directories. For a genuinely fresh Cline project, this package installs the
exact `.clinerules/` scaffold for client-only mechanics while shared policy
remains in `AGENTS.md`.

The Skills page lists `.clinerules/skills/`, `.cline/skills/`, and
`.claude/skills/` as project roots. The configuration directory documentation
also lists project `.agents/skills/` and global `~/.agents/skills/`. These pages
differ in coverage; do not infer scan order or older-release support from them.
When applicable to the target version and surface, use canonical `.agents/skills/`
directly. Verify loading when available and avoid a duplicate Cline projection.

Sources:
- [Cline Rules](https://docs.cline.bot/customization/cline-rules)
- [Cline Skills](https://docs.cline.bot/customization/skills)
- [Cline configuration directories](https://docs.cline.bot/getting-started/config#configuration-directory-layout)

## GitHub Copilot

Treat "Copilot" as incomplete compatibility information: identify the IDE,
feature, and selected agent harness, such as VS Code chat with its Local harness,
code review, GitHub.com chat, cloud agent, or CLI. The official support matrix
differs across these surfaces. VS Code documents harness-specific instruction
settings; Local-harness nested `AGENTS.md` support is experimental and controlled
by `chat.useNestedAgentsMdFiles`, disabled by default. Do not generalize that
setting to every harness.

Do not create `.github/copilot-instructions.md` automatically for a surface that
already consumes the canonical source. For a surface that requires it, verify the
available reference/import semantics; do not use Claude's `@` syntax as a generic
cross-client import. A plain link or reading instruction must be labelled a
behavioral fallback unless the specific implementation documents stronger behavior.

GitHub documents project agent skills under `.github/skills/`, `.claude/skills/`,
and `.agents/skills/` across supported surfaces. If the selected surface already
discovers canonical `.agents/skills/`, do not create another projection. Agent
skill support varies by IDE and surface, and some entries remain in preview.

Sources:
- [Copilot support by surface](https://docs.github.com/en/copilot/reference/custom-instructions-support)
- [Copilot customization cheat sheet](https://docs.github.com/en/copilot/reference/customization-cheat-sheet)
- [VS Code custom instructions](https://code.visualstudio.com/docs/agent-customization/custom-instructions)

## Projections and generated copies

Confirm link support for the actual OS, checkout, sandbox, and client. Prefer
relative links when supported. Verify resource paths from the linked skill's
location, prevent loops and out-of-workspace targets, and avoid overwriting
existing directories. Do not assume a link to the whole skills root behaves like
a supported per-skill entry.

If no adequate indirection exists, generated content must have a concrete,
repeatable regeneration path and a check that detects source drift. Reuse existing
repository tooling first. Calling a language model again is not deterministic
regeneration. A "generated" comment without a generator/check is insufficient.

Map each source and scope explicitly. Preserve the intended meaning of relative
references at the destination and respect client context limits. Do not flatten
all nested policies into a global adapter. If the requested scope cannot safely
include the necessary generation/checking work, report that limitation instead
of creating an independently maintained copy.

## Format source

The Agent Skills specification requires `name` and `description`; this shelf also
uses string-valued version metadata for local lifecycle checks. Runtime
requirements belong in `compatibility` or the instructions, while skill routing
and composition belong in catalog or workflow prose. Supporting `references/`
and `assets/` remain portable, and tool-specific pre-approval frontmatter is
intentionally not required by the core package.

- [Agent Skills specification](https://agentskills.io/specification)
