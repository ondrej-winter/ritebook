# author-agents-config

Sibling of `author-agent-skill` for authoring shared repository instructions and
maintaining minimal client adapters. It preserves the target repository's
established canonical skill source instead of imposing a client-specific layout.
For a fresh Cline project with no established ownership, it can bootstrap root
`AGENTS.md`, canonical `.agents/skills/`, and a small exact `.clinerules/`
scaffold while keeping shared policy out of client-only files.

## Install

For a Codex-compatible or shared Agent Skills installation, place this folder at:

```text
.agents/skills/author-agents-config/
```

The ZIP contains `author-agents-config/` as its top-level folder. Extract it into
the selected client's documented skill root, not the repository root. Preserve
any existing folder of the same name rather than overwriting it blindly. Clients
that do not discover `.agents/skills/` may require a supported projection or a
different installation root.

An installation location is not automatically the target repository's canonical
authoring source. Preserve an established source and use the relevant client
adapter reference to expose it where needed. Installing this package does not
itself change AGENTS.md, existing skills, or client files.

## Example requests

```text
Use author-agents-config to initialize this repository for Codex, Cline in
VS Code, and Claude Code. Keep .agents/skills as canonical.
```

```text
Use author-agents-config to add Claude Code support. Sync adapters only;
do not change AGENTS.md or existing skills.
```

```text
Use author-agents-config to audit the current setup without changing files.
Focus on duplicated policy, scoped instructions, and client discovery.
```

```text
Use author-agents-config to consolidate shared instructions into AGENTS.md.
Preserve client-only behavior and use author-agent-skill for any authorized
procedure extraction.
```

These are natural-language task examples, not a universal slash-command syntax.
The agent infers init, update, sync, or audit from intent.

## Package

- `SKILL.md`: activation, scope, workflow, and completion contract.
- `references/ownership.md`: policy/procedure/adapter placement and migration rules.
- `references/client-adapters.md`: dated official-source compatibility notes.
- `references/validation.md`: verification levels and behavioral acceptance cases.
- `assets/*.template`: section prompts and the fallback Claude import adapter.
- `assets/clinerules/`: three exact Cline operating files for fresh projects.

For a fresh Cline project, copy the three bundled files unchanged into root
`.clinerules/`, create a project-specific root `AGENTS.md`, use
`.agents/skills/` as the canonical skill root, and merge `.tmp/cline/` into the
project's ignore rules. If any corresponding project configuration already
exists, reconcile it instead of overwriting it with the scaffold.

No automatic installer, runtime configuration, third-party dependencies, or
cross-client generator is included. The core task needs repository-specific
judgment; the static scaffold does not justify a separate framework.

## Validation status

The package is designed for static format/link checks and live evaluation using
the cases in `references/validation.md`. Actual loading depends on the selected
client, version, settings, and workspace. See the accompanying delivery report
for checks actually performed; do not treat packaged acceptance cases as executed
runtime tests.
