# Code Review Template

Use this optional template to record the result after following the core review
workflow in `SKILL.md`. Remove sections that do not apply.

```md
## Review: <change title>

### Context

- [ ] I understand what this change does and why
- [ ] Affected boundaries, workflows, or interfaces are clear

### Correctness

- [ ] Change matches requirements
- [ ] Edge cases and error paths are handled
- [ ] Tests or examples cover changed behavior

### Readability and architecture

- [ ] Names and structure follow project conventions
- [ ] No unnecessary complexity or coupling
- [ ] Public interfaces remain compatible or have a migration plan

### Security and performance

- [ ] Trust boundaries and secrets are handled safely
- [ ] External data is validated before use
- [ ] Hot paths and data-volume risks are bounded

### Verification

- [ ] Relevant validation was run
- [ ] Skipped validation is explained
- [ ] Manual evidence is included when needed

### Verdict

- [ ] Approve
- [ ] Request changes
- [ ] Need more context
```
