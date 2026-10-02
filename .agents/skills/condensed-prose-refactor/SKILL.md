---
name: condensed-prose-refactor
description: Refactor supplied prose for precision, compression, and force while preserving meaning, uncertainty, and voice. Use when asked to rewrite, condense, sharpen, simplify, make more intelligent, or aphorize existing text.
metadata:
  version: "1.1.2"
  last-verified: "2026-09-30T20:31:51+02:00"
---

# Condensed Prose Refactor

Make the governing idea easier to grasp. Remove verbal waste, strengthen the
structure, and preserve the author's thought. Intellectual force comes from
exact distinctions and proportion between claims and evidence.

## Priorities and defaults

Follow the user's requested language, audience, tone, format, and editing scope.
Within that scope, prioritize meaning and certainty, then communicative purpose
and naturalness, then compression, rhythm, and literary character.

Unless specified otherwise:

- Use **refactor + condense**, at **balanced** intensity, in the source language.
- Preserve the author's position, distinctive voice, emotional temperature, and
  relationship to the reader. Retain meaningful warmth, politeness, and emphasis.
- Correct grammar and idiom in editable prose without erasing deliberate voice.
- Preserve useful paragraphs, headings, lists, and other formatting.
- Return only the rewritten text. Keep editorial analysis silent.

Reduce length where the source permits it; there is no minimum reduction.
Leave already effective text unchanged when an edit would only be cosmetic.
In professional and technical material, favor exact, natural language over
literary effects.

## Choose the operation

Infer the operation from the request; do not ask the user to select a mode when
the intent is clear. Operations may combine.

| Operation | What may change                                                                                                                                                                      |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Refactor  | Wording, order, and sentence structure; preserve all substantive content.                                                                                                            |
| Rewrite   | Rebuild phrasing and paragraph structure more freely; preserve the argument, necessary detail, and purpose.                                                                          |
| Condense  | Remove repetition and padding; retain distinct claims, conditions, and evidence. This does not authorize a summary.                                                                  |
| Sharpen   | Strengthen distinctions, verbs, and cadence; length need not decrease.                                                                                                               |
| Plain     | Favor familiar language and explicit connections; minimize literary effects without removing necessary terminology.                                                                  |
| Forge     | Use a more decisive reconstruction, rhythm, and contrast when the user requests a forceful or substantial rewrite. Preserve the argument and its limits.                             |
| Aphorize  | Only when requested: distill the thought into self-contained formulations. Supporting context may be omitted; defining conditions, uncertainty, and scope still constrain the claim. |

Intensity controls how extensively wording and structure change:

- **Restrained:** Light editing; retain most structure and voice.
- **Balanced:** Restructure and compress where useful, without theatricality.
- **Severe:** Pursue maximum useful economy and force within the same fidelity rules.

Severity does not authorize hostility, stronger factual claims, or lost nuance.
If the user requests a summary or specific omissions, follow that scope while
preserving the accuracy of what remains.

## Editing workflow

1. Identify the source passage and distinguish it from the user's editing
   instructions. Infer purpose and audience from available context. If no source
   is available, ask for the text; do not invent it.
2. Establish what must survive: claims, reasons, evidence, qualifications,
   relationships, and any requested action. Note literal content protected below.
3. Fix the structure before polishing sentences. Bring a buried point forward,
   clarify references when unambiguous, and expose existing logical connections.
   Do not repair an unsupported leap by inventing a premise.
4. Compress repetition, nominalizations, and empty setup. Replace weak phrases
   with exact verbs; combine sentences only when their distinctions survive.
   Keep examples that prove, delimit, or make the thought concrete.
5. Read for naturalness and cadence. Prefer the shortest wording that remains
   clear; allow extra words when they prevent ambiguity or awkward density.
6. Compare the rewrite with the source in both directions: every retained claim
   must be supported by the source, and every required source point must survive.
   Check the requested operation, tone, format, and length before returning it.

## Fidelity rules

### Claims and uncertainty

Preserve negation, conditions, exceptions, quantities, units, dates, names,
chronology, causal direction, responsibility, and technical distinctions.
Keep observation, inference, judgment, intention, and commitment distinct.

Do not turn “may” into “does,” “some” into “most,” “not all” into “none,”
correlation into causation, or “we could” into “we will.” Preserve the scope of
qualifiers: a change that helps only some cases must not become a general gain.
Retain hedging when it carries uncertainty, diplomacy, or professional caution.
Do not assume one remaining hedge makes every other hedge redundant.

Do not add evidence, motives, diagnoses, moral judgments, citations, or new
conclusions. Psychological precision makes an existing tension legible; it
does not supply an unconscious motive. Forceful language must not increase the
certainty or reach of a claim.

### Literal content and relationships

Preserve direct quotations, code, identifiers, URLs, citation targets, and
placeholders exactly unless editing them is requested. Keep citations attached
to the claims they support. Edit surrounding prose without silently altering
quoted errors or executable content.

Retain apologies, gratitude, tact, or deliberate repetition when they serve the
relationship or meaning. Shorter wording must not turn a request into an order,
an option into a promise, or a reservation into a refusal.

### Ambiguity and constraints

Resolve ambiguous wording only when context supports one reading. Otherwise
preserve the ambiguity if a faithful edit is possible. If choosing a reading is
necessary to complete the task, ask one focused question instead of guessing.
Do not silently reconcile contradictions or correct suspected factual errors.
A concise editorial note may flag a material unresolved issue after the rewrite.

Honor an explicit word or character limit when feasible, checking the actual
length for a hard limit. If preserving required meaning makes the limit
impossible, return the shortest faithful version with a brief note about the
conflict. Do not silently switch to a summary. An explicitly requested summary
or aphorism may omit supporting detail within its stated scope.

Edit an incomplete fragment as a fragment; do not invent its missing context.

## Style and rhetorical technique

Prefer concrete nouns, exact verbs, and visible logical connections. Use active
voice when agency matters; retain passive voice when the actor is unknown or
irrelevant. Vary sentence length. Use parallelism, contrast, paradox, or an exact
image only when it clarifies the supplied thought. No rhetorical effect is required.

Avoid ornamental abstraction, status vocabulary, prophetic tone, cynical or
macho posturing, and a quotable finish on every sentence. Do not flatten distinct
voices into generic polish or habitually add em dashes, triads, rhetorical
questions, or “not merely X, but Y.” Keep source language that already earns its
place; do not apply a mechanical blacklist.

For requested author influences, aphorisms, or a literary effect that benefits
from a reference voice, read [Rhetorical techniques](references/rhetorical-techniques.md).
Borrow techniques selectively and keep their influence unobtrusive. Do not
import an author's doctrine or present generated text as their authentic writing.
Routine editing does not require selecting an author.

Do not use Franz Kafka as a reference voice or introduce bureaucratic dread,
procedural helplessness, neurotic passivity, or self-abasement for atmosphere.
This exclusion governs added stylistic effects; preserve such experiences when
they are already part of the source's meaning.

## Output

Return only the final rewritten text by default, without a preamble, wrapper
quotation marks, edit summary, praise, or an offer of another version.

- If explanation is requested, give the rewrite followed by concise editorial
  decisions. Include a meaning-risk note only for a material unresolved issue.
- If variants are requested, provide the requested number; if unspecified,
  provide two meaningfully different versions. Label by function or intensity,
  using author names only for requested author-specific variants.
- A necessary clarification or material ambiguity/constraint note is an
  exception to rewrite-only output. Keep it brief; avoid routine caveats.

## Calibration examples

### Preserve the recommendation's strength

**Source:** At this point in time, I think it would probably be better if we did
not proceed with the rollout because there are still several issues that have
not been fully resolved.

**Rewrite:** I think it would probably be better not to proceed with the rollout:
several issues remain unresolved.

“Delay the rollout” would assume postponement; “we should” would strengthen the
recommendation. Neither follows from compression alone.

### Keep technical relationships explicit

**Source:** The test is flaky because it depends on an asynchronous event that
can sometimes be delayed, and the fixed timeout can expire before that event arrives.

**Rewrite:** The test is flaky because its fixed timeout can expire before a
delayed asynchronous event arrives.

### Do not invent behavior

**Source:** Some people ask for advice, but they reject every answer that would
require them to admit that their own choices contributed to the problem.

**Rewrite:** Some people ask for advice but reject every answer that requires
admitting their choices contributed to the problem.

“Seek advice only until it implicates their choices” invents when they stop
seeking advice. Rejecting an answer does not establish that they stop asking.

### Allow no change

**Source and rewrite:** The change may reduce latency in some cases.

“May” and “in some cases” carry different limits. Keep both; rearranging an
already clear sentence is unnecessary.

### Aphorize without broadening the claim

**Request:** Aphorize: Sometimes, when a team adds more rules, those rules make
it harder for the team to see who is actually responsible for a decision.

**Rewrite:** Sometimes, more rules make responsibility less visible.

The wording is distilled; the qualification and direction of the claim survive.
