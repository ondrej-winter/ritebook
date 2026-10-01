---
name: interview-me
description: Reduce uncertainty about a user's underlying intent through an adaptive XY-problem interview that scales from concise clarification to a full evidence-based model. Use when an ask is underspecified, solution-led, has material unresolved trade-offs, or the user explicitly requests an interview before idea refinement, specification, planning, or implementation.
metadata:
  version: "2.0.1"
  last-verified: "2026-10-01T21:27:59+02:00"
---

# Interview Me

Use this skill before planning, specification, or implementation when a stated
request may be a proxy for a different desired outcome. Treat intent discovery as
iterative uncertainty reduction: apply the XY gate, choose an interview depth
proportionate to the ambiguity, ask the question with the highest expected
decision value, and do not proceed on unrecorded assumptions.

## When to use this skill

Use this skill when:

- the ask lacks a material fact about the user, problem, outcome, success measure,
  scope boundary, constraint, decision owner, or deadline
- the request names a conventional solution, such as a dashboard, rewrite, AI
  feature, or scalable architecture, but not the outcome it must produce
- plausible interpretations lead to materially different requirements or paths
- the user asks to be interviewed, grilled, challenged, or stress-tested
- you would otherwise fill a material requirement gap with an unstated assumption

Do not use this skill when the outcome and boundaries already suffice for the
next decision, or for a mechanical edit, direct information request, typo, rename,
formatting operation, or similarly precise task. Use `idea-refine` when intent is
known but the option space needs exploration. Use `spec-driven-development` when
intent is known and requirements need definition.

## XY gate

Before treating a requested mechanism as a requirement, distinguish the stated
solution (Y) from the underlying outcome or problem it is meant to address (X).
The gate prevents optimizing a proposed answer before establishing the question.

1. State Y: the named artifact, technology, workflow, or implementation approach.
2. State X: the user outcome, decision, or problem; mark it as confirmed or
   hypothesized.
3. Set `XY-RISK` to `high` when X is missing or inferred, multiple plausible X
   values could justify Y, another solution could satisfy X with materially
   different cost, scope, risk, or architecture, or the user cannot name the
   decision or success signal Y enables.
4. Set `XY-RISK` to `medium` when X is plausible but material outcome, success,
   or constraint details remain unconfirmed.
5. Set `XY-RISK` to `low` only when the user has confirmed X and explained why Y
   is a required mechanism or constraint rather than a preferred option.

For high or medium risk, write the hypothesis in terms of X, retain Y as a
candidate option or constraint, and ask the highest-information-gain question
about X. Do not investigate, design, or commit to Y as though it were confirmed.
For low risk, record why Y is required and continue only if a material unknown
still blocks the next decision.

## Choose the interview depth

Use the light path for one or two ordinary, independent ambiguities when the
likely answers will not change the overall route. Use the full path when:

- the user explicitly asks to be interviewed, grilled, challenged, or
  stress-tested
- `XY-RISK` is high
- multiple material unknowns interact, such as competing users, outcomes,
  constraints, or success signals
- an answer reveals a materially different objective or solution path
- the light path cannot resolve the ambiguity within one or two clarification
  rounds

Start light when the selection is not obvious. Escalate as soon as the conditions
for the full path appear; do not prolong a nominally light interview through a
series of disconnected questions. Do not use the full path merely to make a
straightforward clarification look rigorous.

### Light path

Keep the interaction concise. Apply the XY gate and track the relevant evidence
and unknowns, but show only a compact current picture rather than the complete
operating model. Use readiness in the compact status so the user can see whether
the interview is still narrowing or is ready for confirmation. Include a
falsifiable working guess only when it makes correction materially easier.

When the answer resolves the only material ambiguity, present a concise intent
restate in a ready-for-confirmation turn. If the answer exposes interacting
material unknowns, explain the escalation briefly and continue with the full
path using an expanded current picture.

### Full path

Maintain the complete operating model below. Show it through an expanded current
picture on the first full-mode turn, immediately after escalation, and whenever
an answer materially changes the hypothesis, XY-risk, primary user, outcome,
route, or structure of the high-impact unknowns. A readiness step based on
expected evidence does not by itself require expansion. Use the compact current
picture on intervening turns where the core model remains stable so orientation
stays visible without repeating the whole model.

```text
STATED SOLUTION (Y): <requested mechanism, artifact, or approach>
UNDERLYING OUTCOME (X): <confirmed or hypothesized problem, decision, or result>
XY-RISK: <low | medium | high> — <reason>
HYPOTHESIS: <current best statement of the intended outcome>
READINESS: <exploring | narrowing | ready-for-confirmation> — <evidence-based reason>
EVIDENCE: <facts stated or confirmed by the user>
HIGH-IMPACT UNKNOWNS: <variables that could change the next decision>
```

Readiness describes whether the intent model is sufficient for the next decision.
It is not psychological certainty and does not replace user confirmation.

| Readiness                | Meaning                                                                                                      | Required action                                           |
| ------------------------ | ------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------- |
| `exploring`              | The primary user, problem, outcome, or relationship between X and Y is materially unclear.                   | Test the core interpretation before discussing solutions. |
| `narrowing`              | The direction is understood, but a material success signal, boundary, constraint, or owner remains unresolved. | Ask the highest-information-gain question.                |
| `ready-for-confirmation` | The model is sufficient for the next decision and every remaining material unknown is resolved, accepted, or blocked explicitly. | Present the intent artifact and request confirmation.     |

Change readiness only when evidence resolves, bounds, contradicts, or explicitly
accepts a material unknown. More conversation alone is not evidence of progress.

`I don't know` is a valid observation, not a sufficient state. Translate it into
named unknowns, their decision impact, and the next question most likely to
reduce that uncertainty.

## Present every turn clearly

Every response that continues the interview or asks for confirmation must contain
a `Current picture` followed by a separate `Current question`. This includes the
first turn, unchanged turns, escalation turns, and ready-for-confirmation turns.
After the user confirms the intent, the downstream handoff does not need to
repeat this presentation.

Use Markdown headings and bullets for scanability. Keep each bullet to the
smallest useful summary, avoid repeating unchanged history, and never hide a
material unknown merely to keep the overview short.

### Compact current picture

Use this form on every light-mode turn and on full-mode turns where the model has
not materially changed:

```md
### Current picture

- **Mode / status:** <Light | Full> · <exploring | narrowing | ready-for-confirmation>
- **Outcome:** <current understanding of the desired result>
- **Confirmed:** <important facts established so far>
- **Open:** <remaining material unknowns, or none>
- **Risks / assumptions:** <material risk or accepted assumption; omit when none>
- **Changed this turn:** <material update caused by the previous answer; omit on the first or an unchanged turn>
```

`Open` may summarize multiple unknowns so the user can see the whole interview,
but the current question must select exactly one of them, or request one approval
when the model is ready for confirmation.

### Expanded current picture

In full mode, expand the picture on the first turn, immediately after escalation,
after a material model change, or when the user asks for the complete state:

```md
### Current picture

- **Mode / status:** Full · <exploring | narrowing | ready-for-confirmation>
- **Stated solution (Y):** <requested mechanism, artifact, or approach>
- **Underlying outcome (X):** <confirmed or hypothesized problem, decision, or result>
- **XY-risk:** <low | medium | high> — <reason>
- **Hypothesis:** <current best statement of the intended outcome>
- **Confirmed evidence:** <facts stated or confirmed by the user>
- **Open / high-impact unknowns:** <variables that could change the next decision>
- **Risks / assumptions:** <other material risk or accepted assumption; omit when none>
- **Changed this turn:** <material update caused by the previous answer; omit on the first turn>
```

`Changed this turn` reports the decision-relevant delta, not a transcript summary.
Omit it when the answer only confirms existing state or no previous answer exists.

### Current question

After the current picture, isolate the active question from the whole-interview
state:

```md
### Current question

- **Focus:** <the one unknown or confirmation decision being resolved now>
- **Context:** <only the confirmed facts and labeled hypothesis needed to answer>
- **Why it matters:** <the route, scope, requirement, or trade-off this resolves>
- **Question:** <exactly one focused, answerable question>
- **Working guess:** <optional falsifiable prediction, rationale, and permission to reject it>
```

The focus and context explain why this question is next; they must not introduce
unsupported evidence. A contrast between options may appear inside one question,
but do not batch independent questions. Omit `Working guess` when it would add
noise, steer the user, or merely repeat the context.

## Interview loop

### 1. Apply the XY gate and choose a path

Identify Y, X, XY-risk, and the material unknowns before asking implementation
questions. A hypothesis must be specific enough to be wrong. Choose light or full
mode using the criteria above; an explicit request for an interview always uses
the full path.

Do not invent evidence. Label inferences as guesses and user statements as
evidence. See `references/interview-examples.md` for the normative scenario
matrix and worked examples.

### 2. Choose the next question by information gain

Ask exactly one question. Prefer the question whose possible answers would most
change the next decision: route, scope, requirements, success criteria,
constraint, or implementation approach.

Render the selected question through the `Current question` structure above.
Make it self-contained for a user who may not remember the full conversation or
source material. Provide only the confirmed facts, current hypothesis, or
unresolved distinction needed to answer it. State why the answer matters when
the decision impact is not obvious.

Prioritize unknowns in this order unless context shows another unknown has more
decision value:

1. primary user and problem or job to be done
2. intended outcome and observable success signal
3. binding scope boundary, constraint, risk, deadline, or decision owner
4. trade-off between plausible directions
5. implementation detail that remains material after the preceding items

A working guess must be falsifiable, evidence-based where possible, and
non-manipulative. It tests the model; it does not steer the user toward a preferred
answer. Do not batch questions. Wait for the answer before selecting the next
highest-value unknown.

### 3. Update from evidence and escalate when needed

After each answer:

1. distinguish confirmed evidence from inference
2. revise the hypothesis when evidence changes it
3. add, remove, or re-rank material unknowns
4. update readiness only to the degree the evidence warrants
5. escalate from light to full mode when the selection criteria are met
6. choose compact or expanded presentation from the significance of the change
7. ask another question only if a material unknown remains

Challenge ambiguous labels such as "scalable", "clean", "modern", or "best
practice" by asking for the decision, threshold, failure mode, or trade-off they
represent. When convention may be masking preference, ask what result the user
would choose if the named solution were not required.

When a user delegates a material choice with "whatever you think is best," record
the delegation as evidence, present the relevant options and consequences, then
ask them to choose or explicitly authorize an assumption. Delegation alone does
not resolve the trade-off.

### 4. Separate intent questions from factual questions

Clarify what the user wants before researching whether a technology, framework,
or external system can provide it. If a fact determines whether an otherwise
clear option is viable, record it as a dependency and use
`source-driven-development` or repository evidence to verify it.

```text
INTENT DECISION: The workflow must support offline use.
FACT TO VERIFY: Whether <platform_or_version> supports the required local storage and synchronization behavior.
```

Do not use a guessed technical fact to manufacture user intent, and do not turn a
user preference into a fact-finding exercise.

### 5. Restate and confirm intent

When no further question could materially change the downstream route or
artifact, stop asking questions and present the intent for confirmation.

Use a `ready-for-confirmation` current picture followed by a `Current question`
whose focus is confirming the resolved intent and whose only question requests
approval. For the light path, summarize the outcome, resolved boundary, accepted
assumptions or blockers, and next step in the current picture without introducing
the full artifact.

For the full path, use an expanded current picture and include this artifact
between the overview bullets and the `Current question`:

```text
INTENT STATUS: <confirmed | confirmation required | blocked>
XY-RISK: <low | medium | high> — <resolution or remaining reason>
OUTCOME: <what must change or become possible>
PRIMARY USER: <who benefits or decides>
TRIGGER / WHY NOW: <event, pain, or opportunity>
SUCCESS SIGNALS: <observable, testable indicators>
CONSTRAINTS: <binding limits, risks, compatibility, deadline, or owner>
IN SCOPE: <required capabilities or decisions>
OUT OF SCOPE: <explicit exclusions>
ACCEPTED ASSUMPTIONS: <user-authorized assumptions, or none>
OPEN QUESTIONS / BLOCKERS: <unresolved items and impact, or none>
NEXT STEP: <idea-refine | spec-driven-development | source-driven-development | other>
```

Ask for direct confirmation. A clear approval of the concrete restate, including
"yes," "approved," or "sounds good; proceed," is confirmation. If the response
adds a material refinement, update and re-confirm. Silence is not approval.

## Stop condition

The interview is ready for confirmation when all of the following are true:

- the primary user and intended outcome are sufficient for the next decision
- the relevant success signals, constraints, and scope boundaries are known
- every remaining material unknown is resolved, explicitly accepted as an
  assumption, or recorded as a blocker with its impact
- no further question has enough decision value to change the downstream route
  or artifact materially

Successful completion requires explicit user confirmation. Without confirmation,
label the result `Intent draft — confirmation required`, identify the blocker or
unconfirmed decisions, and do not present implementation or an accepted
specification as ready.

If several rounds fail to reduce uncertainty, report the current model, identify
the foundational unknown, and ask whether to change the decision, provide more
context, or proceed with an explicitly bounded assumption.

## Non-interactive contexts

This skill requires a live, responsive user for confirmation. Do not simulate an
interview in CI, scheduled jobs, autonomous runs, or other non-interactive
contexts. Instead, produce an `Intent draft — confirmation required` artifact
listing evidence, assumptions, high-impact open questions, and the fact that
implementation or accepted specification work is blocked pending confirmation.

## Verification and handoff

Before handing off, verify that:

- the selected interview depth was proportionate to the ambiguity
- an explicit interview request, high XY-risk, or interacting material unknowns
  used the full path
- every active or confirmation turn displayed a current picture followed by a
  separate current question
- a light-path turn used the compact picture, omitted the complete operating
  model, and escalated if complexity emerged
- a full-path first turn and each materially changed full-mode turn used the
  expanded picture with ordinal readiness and clearly separated evidence,
  hypotheses, and guesses
- an unchanged full-mode turn retained orientation through the compact picture
- `Changed this turn` appeared only for a decision-relevant model change
- a high- or medium-risk stated solution remained a candidate until the
  underlying outcome and its relationship to that solution were confirmed
- every current question selected exactly one unknown or requested one approval,
  was self-contained, and was selected for expected decision value
- every guess was falsifiable and did not present inference as user evidence
- every material unknown was resolved, accepted explicitly, or recorded as a
  blocker with its impact
- the final restate matched the selected path and requested direct confirmation
- confirmation is explicit, or the result is labeled as an unconfirmed draft
- the downstream skill follows the confirmed intent, not the original
  solution-shaped request

Use `idea-refine` when the outcome is confirmed but competing concepts or MVP
boundaries need exploration. Use `spec-driven-development` when the outcome is
confirmed and concrete requirements need definition. Use
`source-driven-development` when a verified external or version-specific fact is
needed to evaluate an identified option. Use `doubt-driven-development` after a
decision or downstream artifact exists and needs adversarial review.
