# Code Review Template

Use this optional report after the core workflow. Follow a requested output schema
instead when provided. Remove inapplicable sections, replace placeholders with
evidence, and choose one verdict. Do not create a file unless the task calls for it.

```md
## Review: <change title>

### Findings

- <Label> — <short actionable title> — <file:line or supplied excerpt identifier>
  - Trigger and impact: <realistic condition and observable consequence>
  - Evidence: <code path, reproduction, contract, or source; baseline attribution>
  - Disposition: <blocking or optional; focused remedy when useful>

<If none: No actionable findings in the reviewed scope.>

### Scope

- Target and baseline: <revisions, worktree scope, or supplied snapshot>
- Intent and boundaries reviewed: <behavior, requirements, files, consumers>
- Coverage limits: <sampling, exclusions, or unavailable context>

### Verification

- Ran: <command or manual check; tested state/environment; result>
- Reported evidence: <author or CI source; revision; result; not rerun locally>
- Static reasoning: <what inspection established and what it cannot establish>
- Not run: <check; reason; effect on confidence>

### Open questions and residual risks

- <Unresolved question or risk; missing evidence and next step>
- <Accepted risk only if an owner actually accepted it; decision reference>

### Verdict

<Approve | Request changes | Defer judgment> — <reason tied to findings and evidence>
```
