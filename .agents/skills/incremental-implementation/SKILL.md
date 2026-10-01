---
name: incremental-implementation
description: Guide agents to deliver changes incrementally. Use when implementing a feature or change that touches more than one file, when a task feels too large to land in one step, or before writing a large amount of code at once.
metadata:
  version: "2.1.3"
  last-verified: "2026-10-01T09:34:17+02:00"
---

# Incremental Implementation

## Overview

Build in thin, independently verifiable increments. Prefer complete vertical slices that produce an observable outcome through the relevant path. For behavior-changing slices, apply test-first execution inside the increment: define one behavior, observe the focused test fail, implement the smallest passing change, then verify before expanding. Use contract-first or risk-first increments only when a complete vertical path is not yet the right unit, and label them explicitly. Each increment should leave the system in a working state.

Completing an increment requires access to make its changes and gather its named
verification evidence. If that execution is unavailable, return a bounded slice
proposal only when it is independently useful, label it design-only and
runtime-unverified, and leave the increment incomplete. If the request requires
implemented work, report the affected increment as blocked. Do not treat a
proposed slice, skipped command, or unobserved boundary as a completed increment.

## When to use

- Implementing any multi-file change
- Building a new feature from a task breakdown
- Refactoring existing code
- Any time an agent is tempted to write more than about 100 lines before testing

Do not use this skill for single-file, single-function changes where the scope is already minimal.

## Steps

Use this increment cycle for each slice:

```text
Define outcome -> Red when applicable -> Implement -> Verify -> Checkpoint -> Next slice
Repeat the cycle for each slice.
```

For each slice:

1. **Define the outcome**: name one observable behavior, contract milestone, or
   risk-reduction result and set the slice boundary before changing files.
2. **Red when applicable**: when the slice adds or changes behavior that
   automated tests can verify, write the narrowest relevant test first and confirm
   that it fails for the expected reason. Use `test-driven-development` for the
   detailed RED-GREEN-REFACTOR workflow when available. For a behavior-preserving
   refactor, identify and run the focused existing tests first to establish a green
   baseline instead. Do not use "when applicable" to justify adding tests after
   behavior-changing implementation.
3. **Implement**: make the smallest change that satisfies the defined outcome. For
   a test-driven slice, write only enough implementation to make the focused test
   pass, then refactor while it remains green.
4. **Verify**: run the focused test and any affected builds, type checks, static
   analysis, integration checks, or runtime verification. Confirm the observable
   outcome rather than only checking internal layers.
5. **Checkpoint**: save progress with the project's normal checkpoint or handoff
   mechanism, such as a descriptive commit when appropriate or an explicit
   progress note.
6. **Move to the next slice**: carry forward; do not restart.

For a behavior-preserving refactor, begin from focused passing tests and keep them
green. For documentation, formatting, static content, or pure configuration changes
with no behavioral effect, skip the RED step. Define the expected result before
editing and validate it with the relevant parser, schema check, linter, build, dry
run, or focused review. If behavior changes but no practical automated test can
verify it, record that limitation before implementation and name the runtime or
manual evidence that will verify the outcome.

## Slicing strategies

### Vertical slices (preferred)

Build one complete path through the stack:

```text
Slice 1: Create a record (<data_store> + <interface> + basic <user_surface>)
    Result: Tests pass, user can create a record through the primary surface

Slice 2: List records (<read_path> + <interface> + <user_surface>)
    Result: Tests pass, user can see saved records

Slice 3: Edit a record (<update_path> + <interface> + <user_surface>)
    Result: Tests pass, user can modify records

Slice 4: Delete a record (<delete_path> + <interface> + confirmation)
    Result: Tests pass, the complete lifecycle works
```

Each slice delivers working end-to-end functionality.

### Contract-first slicing

Contract-first increments are intentionally incomplete paths, not vertical slices.
Use them when producers and consumers need to develop in parallel:

```text
Slice 0: Define the contract artifact (<schema>, <interface>, <protocol>, or <spec>)
Slice 1a: Implement the producer against the contract + contract tests
Slice 1b: Implement the consumer against representative test data
Slice 2: Integrate and test the complete path
```

### Risk-first slicing

Risk-first increments may be intentionally incomplete paths, not vertical slices.
Use them to resolve a named technical or product uncertainty before investing in
the complete path:

```text
Slice 1: Prove the riskiest integration point works
Slice 2: Build the first user-visible behavior on the proven integration
Slice 3: Add resilience behavior such as retry, fallback, or recovery
```

If Slice 1 fails, you discover it before investing in Slices 2 and 3.

Storage-only, producer-only, consumer-only, infrastructure-only, or discovery work
is not a vertical slice. Classify producer or consumer boundary work as
contract-first. Classify an infrastructure proof, spike, or discovery increment as
risk-first only when it resolves a named uncertainty. For every intentionally
incomplete increment, state the evidence it must produce and the next integration
or vertical slice that will turn it into observable value.

## Implementation rules

### Rule 0: Simplicity first

Before writing any code, ask: "What is the simplest thing that could work?"

After writing code, review it against these checks:

- Can this be done in fewer lines?
- Are these abstractions earning their complexity?
- Would an experienced reviewer ask why this was not implemented more directly?
- Am I building for hypothetical future requirements, or the current task?

```text
SIMPLICITY CHECK:
Avoid: Generic event pipeline for one notification
Prefer: Direct call or the simplest local coordination mechanism

Avoid: Abstract factory pattern for two similar implementations
Prefer: Two straightforward implementations with shared helpers only where useful

Avoid: Config-driven builder for three small variants
Prefer: Three clear variants with duplication removed only when the shared concept is proven
```

Three similar lines of code is better than a premature abstraction. Implement the naive, obviously-correct version first. Optimize only after correctness is proven with tests.

### Rule 0.5: Scope discipline

Touch only what the task requires.

Do not:

- "Clean up" code adjacent to your change
- Refactor imports in files you're not modifying
- Remove comments you don't fully understand
- Add features not in the spec because they "seem useful"
- Modernize syntax in files you're only reading

If you notice something worth improving outside your task scope, note it instead of fixing it:

```text
NOTICED BUT NOT TOUCHING:
- <module_path> has an unused dependency (unrelated to this task)
- The <boundary_or_component> could use clearer error messages (separate task)
```

Capture these as follow-up notes or separate tasks only if requested.

### Rule 1: One thing at a time

Each increment changes one logical thing. Don't mix concerns:

Avoid: One checkpoint that adds a new component, refactors an existing one, and updates the build config.

Prefer: Three separate checkpoints, one for each change.

### Rule 2: Keep it working

After each increment, run the checks affected by the change and keep the project in
a working state. Run broader tests and builds when the slice can affect them. Do not
leave the codebase broken between slices.

### Rule 3: Feature flags for incomplete features

If a feature isn't ready for users but you need to merge increments:

```text
if feature flag is enabled:
    show the new behavior
else:
    keep the existing behavior
```

This lets you merge small increments to the main branch without exposing incomplete work.

### Rule 4: Safe defaults

New code should default to safe, conservative behavior:

```text
create record with notify defaulting to false:
    save the record
    send notification only when notify is explicitly enabled
```

### Rule 5: Rollback-friendly

Each increment should be independently revertible:

- Additive changes (new files, new functions) are easy to revert
- Modifications to existing code should be minimal and focused
- Data migrations should have corresponding rollback or recovery plans
- Avoid deleting something in one commit and replacing it in the same commit — separate them

## Working with agents

When directing an agent to implement incrementally:

```text
"Let's implement the smallest complete create-record path from Task 3.

Include the minimum storage change, external interface, and basic user-facing
surface needed for a user to create one record and observe success. Before
implementation, define that behavior and add a focused failing test when automated
testing can verify it.

Do not add listing, editing, deletion, bulk actions, or visual polish in this
increment. After implementation, run `<focused_test_command>` and
`<build_command>`, then verify record creation through the primary surface."
```

Be explicit about the observable outcome, slice classification, and what remains
out of scope. If the requested increment deliberately stops at a producer,
consumer, infrastructure, or discovery boundary, call it contract-first or
risk-first and state why; do not call it a vertical slice.

## Increment checklist

After each increment, verify:

- [ ] The work unit is identified as a vertical slice, contract-first increment,
      risk-first increment, behavior-preserving refactor, or non-behavioral change
- [ ] The expected observable outcome or evidence was defined before editing
- [ ] A focused test failed before implementation for testable new or changed behavior
- [ ] A behavior-preserving refactor started from a focused green baseline
- [ ] Any skipped RED step has a documented reason and named validation method
- [ ] The change completes its declared behavior, contract milestone, or risk proof
- [ ] Relevant tests pass (`<test_command>`)
- [ ] The build succeeds when applicable (`<build_command>`)
- [ ] Type or contract checking passes when applicable (`<type_check_command>`)
- [ ] Linting or static analysis passes when applicable (`<lint_command>`)
- [ ] The declared outcome or evidence was observed through the relevant boundary
- [ ] The change is checkpointed with a descriptive message or handoff note
- [ ] Any unavailable required execution leaves the increment incomplete; a useful
      proposal is labeled design-only and runtime-unverified, otherwise blocked

**Note:** Run each verification command after a change that could affect it. After a successful run, don't repeat the same command unless the code has changed since — re-running on unchanged code adds no information.

## Common rationalizations

- "I'll test it all at the end." Bugs compound. A bug in Slice 1 makes
  Slices 2-5 wrong. Test each slice.
- "I'll implement first, then add the test." For behavior-changing work, that
  reverses the test-first discipline. Observe the focused failure before coding.
- "I'll build the backend now and add the surface later." That is not a vertical
  slice. Either deliver the smallest complete path or label and justify the work
  as contract-first or risk-first.
- "It's faster to do it all at once." It feels faster until something breaks
  and you can't find which of 500 changed lines caused it.
- "These changes are too small to checkpoint separately." Small checkpoints are
  cheap. Large checkpoints hide bugs and make rollbacks painful.
- "I'll add the feature flag later." If the feature isn't complete, it
  shouldn't be user-visible. Add the flag now.
- "This refactor is small enough to include." Refactors mixed with features make
  both harder to review and debug. Separate them.
- "Let me run the build command again just to be sure." After a successful run,
  repeating the same command adds nothing unless the code has changed since. Run
  it again after subsequent edits, not as reassurance.

## Red flags

- Behavior-changing code written before observing the focused test fail when TDD applies
- Layer-only work described as a vertical slice
- A user-facing surface deferred without a contract-first or risk-first rationale
- More than 100 lines of code written without running tests
- Multiple unrelated changes in a single increment
- "Let me just quickly add this too" scope expansion
- Skipping the test/verify step to move faster
- Build or tests broken between increments
- Large uncommitted changes accumulating
- Building abstractions before the third use case demands it
- Touching files outside the task scope "while I'm here"
- Creating new utility files for one-time operations
- Running the same build/test command twice in a row without any intervening code change

## Verification

After completing all increments for a task:

- [ ] Each work unit's execution mode was identified, individually verified, and checkpointed
- [ ] Behavior-changing increments used a failing test first whenever automated testing applied
- [ ] Each vertical slice produced an observable end-to-end outcome
- [ ] Contract-first or risk-first increments were labeled, justified, and linked to a follow-up integration or vertical slice
- [ ] The full test suite passes when practical and relevant to the change
- [ ] The build is clean when the project has an applicable build step
- [ ] The feature works end-to-end as specified
- [ ] The final handoff clearly explains validation evidence and any uncommitted or uncheckpointed changes
- [ ] No design-only or runtime-unverified increment is reported as implemented or complete
