# Interview Examples

Use these scenarios after loading the path-selection, turn-presentation, and
interview-loop rules in `SKILL.md`. Adapt the content to the user's evidence; do
not copy assumptions.

## Normative scenario matrix

Use this matrix to check that every turn remains oriented while ceremony still
scales with material uncertainty.

| Scenario | Current picture | Current question | Expansion trigger | Stop behavior |
| --- | --- | --- | --- | --- |
| Short ambiguity | Compact light picture on the clarification and confirmation turns | One focused unknown, then one approval question | Escalate if the answer exposes interacting material unknowns | Show `ready-for-confirmation`, summarize the resolved scope, and request approval |
| Medium ambiguity | Compact light picture initially; expanded full picture immediately after escalation | Ask one material question at a time | Expand when competing outcomes, users, constraints, or solution paths emerge | Continue in full mode until the model is sufficient for confirmation |
| High ambiguity or explicit interview | Expanded full picture first; compact full picture on unchanged turns | Ask sequential high-information questions | Expand again after a decision-relevant model change or on request | Reach `ready-for-confirmation`, present the full artifact, and request approval |

## Short ambiguity: remain light

Request:

```text
Add CSV export to the report page.
```

The outcome and interface are sufficiently clear, but the row boundary is
material. Keep the picture compact and ask one question:

```md
### Current picture

- **Mode / status:** Light · narrowing
- **Outcome:** Add CSV export to the existing report
- **Confirmed:** The report already supports filters
- **Open:** Whether the export follows the current filters

### Current question

- **Focus:** Resolve the exported row boundary
- **Context:** The report can represent either the filtered rows or the complete result set
- **Why it matters:** This determines the contents of the exported file
- **Question:** Should the CSV include all rows or only the rows matching the current filters?
- **Working guess:** Only the currently filtered rows, because that usually matches what the user is viewing; please reject that if the export is meant as a complete extract
```

If the user answers `Only the filtered rows`, stop interviewing and orient the
confirmation turn rather than switching to bare prose:

```md
### Current picture

- **Mode / status:** Light · ready-for-confirmation
- **Outcome:** Export the currently filtered report rows to CSV
- **Confirmed:** Existing report columns, filters, and permissions remain unchanged
- **Open:** None
- **Changed this turn:** The export boundary is now limited to the current filtered result set

### Current question

- **Focus:** Confirm the resolved scope
- **Context:** The only material ambiguity was which rows the CSV should contain
- **Why it matters:** Approval makes the intent ready for implementation planning
- **Question:** Proceed with that scope?
```

Do not add the complete X/Y evidence model merely to formalize this single
resolved boundary.

## Medium ambiguity: start light, then escalate

Request:

```text
Build a dashboard for support leads.
```

Start light because a focused contrast may identify the primary outcome:

```md
### Current picture

- **Mode / status:** Light · exploring
- **Outcome:** Help support leads make a recurring support decision
- **Confirmed:** Support leads are the named audience and review support work regularly
- **Open:** Whether the primary decision is daily triage or recurring-issue analysis
- **Risks / assumptions:** A dashboard is still a candidate solution because its required outcome is unconfirmed

### Current question

- **Focus:** Identify the primary decision
- **Context:** Daily triage and recurring-issue analysis require different data and workflows
- **Why it matters:** The answer determines the primary outcome and whether a dashboard is an appropriate solution
- **Question:** Should it primarily help leads triage today's tickets or identify recurring product issues?
- **Working guess:** Triage is the first priority because the audience works from the queue regularly; please reject that if trend analysis is more valuable
```

Suppose the user replies:

```text
Both. Leads need live triage, and product managers need weekly trend reports from the same dashboard.
```

This answer introduces a second user, cadence, outcome, and information boundary.
Escalate and show the decision-relevant delta in an expanded picture:

```md
The answer introduces two interacting workflows, so I am switching to the full interview model before treating one dashboard as the required solution.

### Current picture

- **Mode / status:** Full · narrowing
- **Stated solution (Y):** One dashboard shared by support leads and product managers
- **Underlying outcome (X):** Support daily ticket triage and weekly product-issue analysis; partially confirmed
- **XY-risk:** High — the two users may require different data, cadence, permissions, and interfaces
- **Hypothesis:** The required outcome is coordinated operational and product insight; one shared dashboard remains a candidate rather than a confirmed constraint
- **Confirmed evidence:** Support leads need live triage; product managers need weekly trend reports
- **Open / high-impact unknowns:** Which outcome is primary; whether one interface is required; data freshness and access boundaries
- **Changed this turn:** A second user and weekly analysis outcome were added, making the one-dashboard assumption materially uncertain

### Current question

- **Focus:** Determine whether one shared interface is a binding constraint
- **Context:** The two audiences make different decisions on different cadences but may share underlying data
- **Why it matters:** The answer changes the workflow, permissions, and information architecture
- **Question:** Must both users work from one shared interface, or may the solution provide separate views over the same data?
- **Working guess:** Separate views over shared data are acceptable because the users have different decisions and cadences; please reject that if one shared interface is required
```

## High ambiguity or explicit interview: start full

Request:

```text
Interview me about building a dashboard for metrics.
```

The explicit interview request requires the full path. The solution is also
conventional while its user and decision are unknown:

```md
### Current picture

- **Mode / status:** Full · exploring
- **Stated solution (Y):** Build a dashboard for metrics
- **Underlying outcome (X):** Track active experiments and decide which need attention; hypothesized
- **XY-risk:** High — the user, decision, and success signal for the dashboard are unconfirmed
- **Hypothesis:** The user needs a view of active experiments and their early results; a dashboard is a candidate interface, not a confirmed requirement
- **Confirmed evidence:** The request asks for an interview about a dashboard for metrics
- **Open / high-impact unknowns:** Who uses it; which recurring decision it supports; what metrics matter; what is out of scope

### Current question

- **Focus:** Identify the primary user and recurring decision
- **Context:** Neither a shared audience nor a reporting obligation has been established
- **Why it matters:** The user and decision determine the relevant evidence, success signals, and whether a dashboard is useful
- **Question:** Who needs to make which recurring decision with this information?
- **Working guess:** The requester is the primary user because no team or external stakeholder was named; please reject that if this is for someone else
```

Suppose the user confirms that they personally review experiments every morning
to decide which ones need investigation, but does not yet identify a success
threshold. That evidence narrows the model without materially changing its core
interpretation, so keep orientation compact:

```md
### Current picture

- **Mode / status:** Full · narrowing
- **Outcome:** Help the requester identify experiments that need investigation during a morning review
- **Confirmed:** The requester is the primary user; the review happens every morning
- **Open:** What observable condition makes an experiment require attention; which experiment data is available
- **Risks / assumptions:** A dashboard remains a candidate interface rather than a confirmed constraint

### Current question

- **Focus:** Define the attention threshold
- **Context:** The user and recurring decision are confirmed, but `needs investigation` is not yet observable
- **Why it matters:** The threshold determines the required metrics and success signal
- **Question:** What observable change or threshold should make an experiment require investigation?
```

Continue with one highest-information question at a time. Move from `exploring`
to `narrowing` only when the primary interpretation is established. Move to
`ready-for-confirmation` only when all remaining material unknowns are resolved,
accepted explicitly, or recorded as blockers.

## Material change during a full interview

If the previous user instead says that the dashboard is for executives to decide
which experiments receive more funding, the primary user and decision have
changed. Expand the picture and name that delta:

```md
### Current picture

- **Mode / status:** Full · exploring
- **Stated solution (Y):** Build a dashboard for experiment metrics
- **Underlying outcome (X):** Help executives allocate additional funding among experiments; confirmed
- **XY-risk:** High — the dashboard format and relevant metrics remain unconfirmed for the newly established decision
- **Hypothesis:** Executives need comparative evidence for funding allocation rather than an operational monitoring view
- **Confirmed evidence:** Executives are the primary users; their decision is which experiments receive more funding
- **Open / high-impact unknowns:** Funding criteria; decision cadence; comparison set; whether executives need direct interaction or a prepared report
- **Changed this turn:** The primary user changed from the requester to executives, and the decision changed from investigation to funding allocation

### Current question

- **Focus:** Identify the funding criterion with the highest decision value
- **Context:** Executives are comparing experiments for additional funding, but the basis for that comparison is unknown
- **Why it matters:** The criterion determines the evidence and may make a prepared report more suitable than an interactive dashboard
- **Question:** What result should most strongly determine whether an experiment receives more funding?
```

## Challenging a conventional solution

This is a full-mode first turn, so use the expanded picture:

```md
### Current picture

- **Mode / status:** Full · exploring
- **Stated solution (Y):** Use the named conventional artifact
- **Underlying outcome (X):** The decision or result the artifact must enable; unconfirmed
- **XY-risk:** High — the artifact is specified while its purpose and necessity are unknown
- **Hypothesis:** The desired outcome matters more than preserving the named solution
- **Confirmed evidence:** The request names a conventional solution
- **Open / high-impact unknowns:** The underlying outcome; whether the artifact is required; which alternatives could satisfy the outcome
- **Risks / assumptions:** Treating convention as a requirement could commit to the wrong artifact

### Current question

- **Focus:** Separate the desired result from the named solution
- **Context:** The artifact is specified, but the decision or outcome it should enable is not
- **Why it matters:** Confirming the result prevents an untested solution from becoming a requirement
- **Question:** If you did not need to justify the conventional solution, what result would you actually choose?
- **Working guess:** The outcome matters more than preserving the named solution because the request describes an artifact rather than a decision it enables
```

## Manual dry-run observations

When reviewing a revision to this skill, walk these scenarios and confirm the
observable results:

- the short clarification and its confirmation both show a compact current
  picture followed by one current question
- the medium request starts light and expands immediately after interacting users
  and outcomes appear
- the explicit interview starts with an expanded picture and ordinal readiness
- an unchanged full-mode turn remains oriented through a compact picture without
  repeating the complete operating model
- a material full-mode change expands the picture and identifies the
  decision-relevant delta
- no current question contains more than one independent question
