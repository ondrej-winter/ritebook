---
name: code-review-and-quality
description: Review code, tests, documentation, and configuration across correctness, readability, architecture, security, performance, maintainability, and verification before merging or handing off a change.
metadata:
  version: "1.4.0"
  last-verified: "2026-10-15T12:14:55Z"
---

# Code Review and Quality

Review a proposed change or an explicitly scoped audit. Identify actionable
issues, test the evidence behind them, and give a verdict proportional to the
risk. Apply the same standard to human- and agent-written work, including your
own. Favor improvements that meet project requirements without demanding
perfection or blocking on personal preference.

Use this workflow for review of code, tests, refactoring, migrations, dependencies,
configuration, or documentation. A request only to run checks belongs to
`run-local-quality-gate`; a request to implement a feature does not by itself
require a separate review artifact.

## Steps

### 1. Establish the review scope

Read the request, applicable repository instructions, and relevant acceptance
criteria. Identify the intended behavior, preserved contracts, and requested
review format. Inspect existing working-tree changes before validation or editing.

Identify the exact target and comparison baseline: a patch, commit, branch range,
staged changes, working-tree changes, or named files for an audit. For a branch
review, verify the intended base and merge base instead of assuming the default
branch or comparing with an arbitrary recent commit. Distinguish staged,
unstaged, and relevant untracked files; preserve unrelated work. Record revisions
where available, or describe the supplied snapshot and its limits.

Use available context to resolve intent. If a material ambiguity remains, ask a
focused question and continue independent inspection. If the repository or base
is unavailable, review the supplied material and state which integration or
regression claims cannot be checked.

A review request authorizes inspection and appropriate local validation. Make
fixes only when requested or already authorized. A verdict is a recommendation;
posting comments, submitting remote approval, merging, publishing, or creating
commits requires authorization under the current task. Return the review in the
requested channel; do not create a report file by default.

### 2. Map the change and its evidence

Read the full diff and enough surrounding code, callers, configuration, and
contracts to understand affected behavior. Trace important inputs through state
changes, outputs, and error paths. For an audit, map the requested component and
its boundaries instead of inventing a change baseline.

Inspect tests and reported validation early. Determine what they actually prove:

- Do assertions check observable outcomes and fail for the relevant regression?
- Do mocks or fixtures bypass the boundary at risk?
- Are important failure, boundary, concurrency, and compatibility cases covered?
- Do commands, CI results, or manual evidence apply to the reviewed revision and
  relevant environment?

Use risk to choose depth. Existing coverage or a focused manual check may suffice
for a low-impact change; do not demand new tests for every edit. A bug fix needs
evidence that catches the original failure, with any coverage gap explained.

Cover all changed handwritten logic within scope. For generated or mechanical
changes, inspect the source, generation process, and representative output;
state any sampling. Recommend splitting when unrelated work or mechanical churn
obscures behavior enough to prevent a reliable review. Size or the need for
several reviewers alone is not a defect. Record any area you could not assess.

### 3. Inspect the relevant quality axes

Use these prompts where the reviewed code or change presents risk; do not invent
a finding in each category.

- **Correctness:** requirements, empty or malformed inputs, boundaries, repeated
  operations, error recovery, resource cleanup, concurrency, and data integrity.
- **Readability and simplicity:** clear names and control flow, useful comments,
  cohesive responsibilities, and abstractions justified by present needs.
- **Architecture and compatibility:** dependency direction, public interfaces,
  consumers, serialization, defaults, rollout order, migration safety,
  observability, and documentation that matches behavior.
- **Security:** trust boundaries, identity, authorization, secrets,
  untrusted input, dependencies, or deployment settings. Read the
  [security checklist](references/security-checklist.md) when these apply.
- **Performance:** hot paths, queries, rendering, startup, data volume, queues,
  caches, or artifacts. Read the
  [performance checklist](references/performance-checklist.md) when these apply.
- **Verification:** whether automated checks, manual observations, and static
  reasoning address the actual failure modes and project requirements.

For dependency or runtime changes, inspect resolved versions and lockfiles,
compatibility, maintenance status, license constraints, and build or operational
cost. Check current advisories against the exact package and version using
authoritative sources or configured tooling. Report unavailable evidence; do not
claim a dependency is safe because no advisory was found. Consider an existing
utility or platform feature when it meets the requirement without a new dependency.

For removals and migrations, check callers, exports, configuration, dynamic
registration, and supported consumers before calling code unused. A text search
alone does not prove it is dead. Report uncertain cleanup separately; it blocks
only when it causes a concrete problem or violates an applicable requirement.
Do not expand the review into unrelated cleanup.

### 4. Verify suspected issues

Before reporting a defect, establish:

1. The specific location and realistic input, state, or sequence that triggers it.
2. The affected behavior, user, consumer, or project requirement and concrete impact.
3. Evidence from the code path, a focused reproduction, a contract, or relevant
   documentation. Check surrounding guards, callers, and framework behavior that
   might invalidate the concern.
4. For a change review, how the change introduces, exposes, or worsens it compared
   with the baseline. Keep unrelated pre-existing issues outside the verdict;
   an explicitly requested audit may include existing defects.

For maintainability or verification gaps, identify the specific complexity,
unprotected failure mode, or unmet requirement rather than inventing runtime
breakage. Verify unfamiliar or changing API behavior against primary
documentation. Separate observations from inference and unresolved questions.

Run the narrowest relevant local checks when practical, after inspecting their
commands and side effects. Use an isolated temporary workspace when reproduction
could disturb user work. Avoid auto-fix modes during review-only work and keep
destructive or external operations within existing authorization.

Record commands, results, and the tested state. Distinguish checks you ran from
author-reported or CI evidence, static reasoning, and checks not run. Investigate
failures and attribute them to the change, baseline, environment, or an unresolved
cause. An unavailable tool or service permits a static review with execution
explicitly unverified; it is neither a passing check nor proof of a defect.

Discard concerns contradicted by evidence. If a plausible concern remains
unresolved, state the question and missing evidence separately from confirmed
findings. Do not fill a findings quota or turn hypothetical risks into blockers.
Missing evidence warrants deferral when it prevents assessing a material risk.

### 5. Prioritize actionable findings

Use the project's required severity or priority scheme. Otherwise retain these
simple labels, stating impact separately from whether the feedback blocks:

- `Critical`: an urgent blocker with evidence of severe consequences, such as
  exploitable security exposure, substantial data loss, or widespread outage.
- `Required`: a concrete defect or unmet requirement that must be addressed before
  merge or handoff, without implying critical impact.
- `Suggestion`: a useful improvement that does not block.
- `Nit`: optional style or wording feedback; omit unless useful or requested.
- `FYI`: relevant context, not a defect or required action.

Rank findings by impact and urgency. Give each a short title, precise file and
line location when available, trigger, consequence, and supporting evidence.
Explain why a blocker matters; include a focused remedy or decision path when
helpful. Keep locations narrow, preferably on the changed lines responsible for
the issue. For supplied excerpts, use their identifiers without inventing lines.

Report one finding per root cause, combining repeated manifestations where useful.
Keep questions and optional improvements distinct. Uncertainty changes the claim
and evidence needed; it does not automatically increase severity. Avoid vague
warnings, speculative redesign, or personal preferences presented as requirements.

### 6. Give the verdict and hand off

Honor the requested output format, including structured schemas and findings-only
requests. Otherwise lead with prioritized findings, then concise evidence,
limitations, and one verdict:

- **Approve:** no blocking findings remain and evidence is sufficient for the
  reviewed scope and risk. Nonblocking suggestions may remain.
- **Request changes:** confirmed blocking defects or unmet requirements remain.
- **Defer judgment:** missing context, coverage, or verification prevents a
  responsible decision about a material risk. Name what would resolve it.

If no actionable findings remain, say so explicitly. This is not a claim that the
change is bug-free. State the reviewed scope, checks run and their outcomes,
reported evidence, unreviewed areas, and relevant residual risks. Attribute risk
acceptance only to an actual owner decision; otherwise describe it as unresolved.

Use the [review template](references/review-template.md) when a reusable Markdown
report helps. Adapt it to the task; omit empty sections without hiding limitations.
If fixes are authorized, re-review the resulting diff and rerun affected checks.
If the target changes during review, refresh affected evidence before the verdict.

## Focused follow-up

Check availability and route to related skills only when their own triggers apply:

- `security-and-hardening` for deeper security analysis.
- `performance-optimization` for measurement-driven performance diagnosis.
- `code-simplification` for authorized behavior-preserving cleanup.
- `run-local-quality-gate` for broader configured checks, or
  `browser-runtime-verification` for browser behavior evidence.

These are optional routes, not automatic remediation. If unavailable, continue
the review within your evidence and report any material limitation.
