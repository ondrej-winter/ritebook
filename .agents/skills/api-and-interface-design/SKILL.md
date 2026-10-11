---
name: api-and-interface-design
description: Design or review stable APIs and interfaces that are explicit, compatible, and hard to misuse. Use when creating or changing HTTP, event, library, module, CLI, component, schema, configuration, plugin, or other durable integration contracts.
metadata:
  version: "1.3.2"
  last-verified: "2026-09-30T20:31:51+02:00"
---

# API and Interface Design

Use this skill for a boundary that another caller, component, service, team, user,
or automated process depends on. The goal is a contract that consumers can
understand, providers can verify, and maintainers can evolve without accidental
breakage.

The expected output is a contract proposal or change review that identifies the
boundary and consumers, defines observable behavior, classifies compatibility,
records unresolved decisions, and names consumer-facing verification.

Do not use this skill to standardize private helper shapes with no durable
consumer or independently observable behavior.

## Design rules

- Start from consumer tasks and failure recovery, not provider internals.
- Treat observable behavior as a compatibility surface, including defaults,
  errors, ordering, side effects, and documented timing or limits.
- Follow the boundary's established domain language and local conventions before
  introducing a new style.
- Prefer one evolvable contract over indefinitely maintained parallel versions.
- Make correct use obvious and incorrect use difficult or invalid.
- Validate untrusted data once at the boundary, then use trusted internal forms.
- Do not claim compatibility without evidence about affected consumers.

## Steps

### 1. Inspect the existing boundary before designing

Read the request and the smallest relevant set of current contracts, schemas,
code, tests, examples, generated clients, call sites, documentation, and runtime
evidence. Determine which artifact is authoritative and whether any file is
generated or synchronized from another source.

Separate what you find into:

- **Observed:** current behavior supported by code, tests, traffic, or consumer use.
- **Required:** behavior mandated by the request, accepted decisions, or an
  existing contract.
- **Proposed:** a design choice not yet established.
- **Unknown:** a fact or consumer expectation that still needs evidence.

Existing implementation proves current behavior, not that the behavior is
intentional or desirable. If an unknown changes compatibility, security,
correctness, or consumer work, surface it instead of guessing.

### 2. Write a boundary brief

Record enough context to constrain the design:

```md
Boundary: <name and kind>
Purpose: <one responsibility>
Consumers: <types, owners, and known versions or capabilities>
Stability: <private, internal cross-team, partner, or public>
Trust boundary: <trusted and untrusted sides>
Current source of truth: <schema, type, help text, docs, tests, or implementation>
Constraints: <latency, scale, availability, ordering, retries, rate limits, or none>
```

Name the consumer tasks and recovery paths the interface must support. Keep the
boundary cohesive; split unrelated responsibilities rather than creating a
single convenience interface.

### 3. Define the smallest complete contract

Use the project's established contract format, such as a type definition,
OpenAPI document, schema, protocol definition, command help text, component API,
ADR, README section, or executable fixture.

For each operation, message, command, or interaction, define:

- intent and preconditions
- required, optional, nullable, and mutually exclusive inputs
- output shape, generated fields, and ownership of values
- invariants, defaults, units, formats, and identifier semantics
- side effects, atomicity, concurrency, and ordering guarantees
- failure, timeout, cancellation, and retry behavior
- authorization or capability requirements when observable to the caller
- common, edge, and failure examples

A compact neutral record is often enough:

```md
Operation: <intent-oriented name>
Input: <fields, constraints, omission/null semantics>
Output: <result and system-owned fields>
Effects: <state changes, atomicity, ordering>
Failures: <stable code, condition, retryability, recovery>
Compatibility: <what consumers may ignore or must handle>
Examples: <success and representative failure>
```

Keep creation input, update input, returned output, and internal representation
separate when they have different ownership or constraints. Do not require
callers to send generated identifiers, timestamps, audit fields, or computed
values owned by the provider.

### 4. Make the contract predictable and hard to misuse

Use domain names rather than storage, framework, transport, or vendor terms.
Apply one convention for casing, tense, units, identifiers, booleans, operations,
and status values within the boundary.

Prefer designs that encode valid choices directly:

- use constrained domain values instead of loosely related flags
- distinguish absent, empty, null, zero, and default when their meanings differ
- avoid parameters whose meaning changes based on another hidden condition
- use safe defaults and require explicit opt-in for destructive behavior
- avoid exposing persistence models, SDK objects, framework responses, or mutable
  internals as public contract types
- define how consumers handle unknown fields, values, operations, or event types

Do not make consumers reconstruct domain meaning from message text or several
weakly related fields.

### 5. Define failures, retries, and side effects together

Choose one error strategy per boundary and apply it consistently. It may use
status plus a structured body, typed errors or result values, exit codes plus
output, rejected events, or another locally established mechanism.

For every caller-actionable failure, define:

- a stable machine-readable identifier
- the condition that produces it
- safe human-readable context
- whether retry is allowed and under what conditions
- whether work may already have completed or partially completed
- the caller's recovery action

Human-readable messages may change and should not be the only machine contract.
Do not expose secrets, stack traces, queries, paths, or provider internals.

If callers can retry a state-changing operation, define idempotency, deduplication,
or conflict behavior. A timeout or lost response does not prove that the provider
made no change.

### 6. Specify collections, updates, and concurrency

For list, search, stream, or batch operations, define limits, pagination or
streaming, filtering, sorting, empty results, stable ordering, page-token rules,
and consistency when data changes during iteration.

For updates, define:

- replacement versus partial-update semantics
- omitted versus explicit empty or null values
- which fields are caller-owned or system-owned
- idempotency and validation behavior
- conflict detection, version tokens, or last-write behavior
- atomicity across multiple changed fields or items

Do not promise a stable order, snapshot, or exactly-once effect unless the
implementation and verification can support it.

### 7. Assess compatibility from each consumer's perspective

Compare current and proposed observable behavior. Use a table when more than one
surface or consumer is affected:

```md
| Surface | Current | Proposed | Affected consumers | Classification | Evidence or mitigation |
| --- | --- | --- | --- | --- | --- |
| <surface> | <behavior> | <behavior> | <who> | <classification> | <proof or action> |
```

Use these classifications:

- **Compatible:** known supported consumers continue to work without changes.
- **Conditional:** safe only when a stated consumer behavior or capability holds.
- **Breaking:** a supported consumer must change or observable semantics regress.
- **Unknown:** evidence is insufficient; do not market the change as compatible.

Check names, types, meanings, units, requiredness, defaults, validation, errors,
ordering, side effects, idempotency, authorization, limits, and promised timing.
An additive change is not automatically compatible: strict decoders may reject
new fields, exhaustive consumers may fail on new enum values, and scripts may
parse human-readable CLI output.

Prefer additive evolution only when the consumer contract permits it. Do not use
versioning as the first response to an unclear design, or maintain parallel
versions without support windows and removal criteria. When a breaking change is
necessary, use `deprecation-and-migration` if available to plan migration and
removal.

### 8. Check concerns specific to the boundary kind

Read only the relevant section of `references/boundary-checklist.md` for HTTP or
RPC, messages and events, libraries and plugins, CLI, UI components, or schemas
and configuration. Local project and protocol conventions take precedence over
generic examples.

### 9. Verify from the consumer side

Use the narrowest checks that prove the promised contract:

- schema, type, protocol, or command-help validation
- provider contract tests for success and failure behavior
- consumer or compatibility tests against supported clients
- negative tests for malformed, unauthorized, conflicting, and out-of-range input
- retry, idempotency, timeout, duplicate, ordering, and pagination tests when relevant
- executable examples or fixtures that match actual behavior
- generated-client or downstream build checks when the contract drives them
- documentation review against the implemented surface

Test observable behavior rather than private implementation structure. If this is
a design-only task, provide a concrete verification plan and identify evidence
that cannot yet exist.

### 10. Hand off the contract and decisions

Return or update the canonical contract artifact and summarize:

```md
Boundary: <name>
Contract artifact: <path or proposed format>
Compatibility: <compatible, conditional, breaking, or unknown>
Key decisions: <settled semantics and rationale>
Unresolved: <question, impact, owner or evidence needed>
Verification: <checks passed or planned>
Migration: <none, or link/next step>
```

Do not hide unresolved compatibility behind vague wording. State what is known,
what is assumed, and what blocks implementation or release.

## Red flags

- the contract was inferred from provider code alone without checking consumers
- a generated or synchronized artifact is edited instead of its source
- inputs, outputs, errors, defaults, or side effects remain implicit
- error messages are parsed because no stable error identifier exists
- transport, framework, persistence, or vendor types leak across the boundary
- absence, empty, null, default, duplicate, or retry semantics are ambiguous
- collection results have no limit, pagination, streaming, or ordering strategy
- an additive change is called safe without checking consumer tolerance
- versioning creates permanent forks without migration and removal criteria
- examples and documentation disagree with executable behavior

## Verification checklist

- [ ] The boundary, purpose, consumers, stability, and source of truth are explicit.
- [ ] Observed, required, proposed, and unknown behavior are distinguishable.
- [ ] Inputs, outputs, ownership, effects, errors, and recovery are documented.
- [ ] Names, defaults, nullability, units, identifiers, and unknown-value behavior are clear.
- [ ] Collections, updates, concurrency, retries, and idempotency are covered when relevant.
- [ ] Compatibility is classified per affected consumer with evidence or mitigation.
- [ ] Breaking changes have a migration path rather than only a new version label.
- [ ] Consumer-facing tests, examples, schemas, or a concrete verification plan cover the contract.
- [ ] The handoff records unresolved decisions and does not overstate certainty.