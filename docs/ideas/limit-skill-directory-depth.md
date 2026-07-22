# Limit Skill Directory Depth

## Problem Statement

How might we keep individual and collection-based skill installation predictable for skill consumers without allowing repository taxonomies to make selectors ambiguous?

## Recommended Direction

Allow a skill directory to appear at one of two depths relative to the published `skills_root`: directly below the root as `<skill>`, or below one optional collection as `<collection>/<skill>`. A collection selector installs the skills that are its immediate children.

The final path segment always identifies the skill directory containing `SKILL.md`. A collection is organizational and installable as a group, but is not itself a skill. A directory must not be both a skill and a collection, because exact-match precedence would make its selector ambiguous. Files and directories inside an individual skill, such as `scripts/`, `references/`, and assets, remain unrestricted by this rule.

```text
<skills-root>/
├── code-review/
│   └── SKILL.md
└── browser/
    ├── runtime-verification/
    │   └── SKILL.md
    └── accessibility-review/
        └── SKILL.md
```

## Key Assumptions to Validate

- [ ] Existing published indexes do not rely on skill paths deeper than `<collection>/<skill>`; inspect representative indexes before treating the rule as compatible.
- [ ] Consumers benefit from installing a named collection as a unit; confirm this against actual requirements-file workflows rather than preserving prefix expansion only because it already exists.
- [ ] Rejecting directories that are both a skill and a collection is clearer than retaining exact-skill precedence; test the proposed error and migration guidance with maintainers.
- [ ] One optional collection level provides enough useful organization for expected repositories; review current repository layouts for counterexamples.

## MVP Scope

Define and enforce a portable directory contract in which a skill path relative to `skills_root` contains one or two safe path segments. Support exact installation of root and collected skills, and collection installation of immediate child skills. Reject over-deep skill paths and mixed skill/collection directories with clear, path-scoped validation errors.

Apply the same structural rule during linting, index publication, cached-index reading, direct installation, requirements-file expansion, and contribution workflows so malformed or legacy metadata cannot bypass the boundary. Add migration guidance if existing published indexes contain unsupported layouts.

## Not Doing and Why

- Arbitrarily nested collections — they make prefix selectors difficult to interpret and weaken the promise of predictable bulk installation.
- Collection metadata or dedicated collection manifest files — the directory name and immediate children are sufficient to test the structural idea first.
- Restrictions on a skill's internal directory tree — scripts, references, templates, and assets are skill contents rather than catalog hierarchy.
- Inferred or name-only skill lookup — exact relative paths remain the unambiguous identity of published skills.
- Immediate implementation changes — this brief records the direction first; specifications and code should change only after the assumptions are checked.

## Open Questions

- Should collection installation remain implicit when a selector does not exactly match a skill, or should the CLI require an explicit collection-install form?
- Should an empty collection be ignored or reported as an invalid repository structure?
- Should non-skill directories be permitted at either catalog level when they contain documentation or repository tooling?
- Is this a breaking schema contract requiring an index schema-version change, or can publisher and consumer validation introduce it within the current version with migration guidance?
