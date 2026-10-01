---
name: hexagonal-vertical-slices
description: Design, review, or refactor systems that use hexagonal architecture organized by vertical feature slices, keeping business logic isolated from frameworks and infrastructure.
metadata:
  version: "1.2.1"
  last-verified: "2026-10-01T22:08:01+02:00"
---

# Hexagonal Vertical Slices

Use this skill when designing, reviewing, or refactoring a codebase that should
combine hexagonal architecture with vertical feature slices.

This skill is technology-agnostic. Follow the target project conventions for
language, framework, naming, packages, and testing when they are more specific
than the examples here.

The expected output is an architecture decision or review that identifies slice
ownership, boundary contracts, dependency direction, consistency and failure
semantics, migration steps when refactoring, and verification evidence.

## When to use this skill

Use this skill when you need to:

- place new behavior inside an explicit architectural boundary
- design a feature slice around a business capability or use case
- decide whether code belongs in domain, application, ports, adapters, shared
  kernel, infrastructure, or a composition root
- review dependency direction, data ownership, and cross-slice collaboration
- refactor framework, I/O, persistence, or transport concerns out of business
  logic
- make consistency, failure, and migration choices explicit

Do not use this skill as a substitute for a project-specific implementation
workflow. When their own triggers are present, combine it with:

- `incremental-implementation` for a multi-file or non-minimal change
- `test-driven-development` for behavior that automated tests can verify
- `api-and-interface-design` for a durable or multi-consumer boundary
- `documentation-and-adrs` when the decision needs a durable record
- a language- or framework-specific skill for implementation mechanics

## Core model

Hexagonal architecture protects business behavior from external details.
Vertical slices align ownership with business capabilities and user-visible
outcomes.

The two ideas work together:

- A slice owns one business capability or a cohesive use-case family end to end.
- Domain and application policy stay independent of delivery and infrastructure.
- Dependencies point inward toward application contracts and domain behavior.
- External systems connect through adapters at explicit boundaries.
- Cross-slice collaboration uses published contracts rather than private internals.

Treat layers as responsibilities, not mandatory directories or classes. A simple
slice may have a thin application use case and no rich domain model. Do not add an
interface, service, DTO, or folder only to make the layout symmetrical.

One possible physical shape is:

```text
<slice_root>/<feature_name>/
  domain/
  application/
    ports/
    use_cases/
    boundary_types/
  adapters/
    inbound/
    outbound/
```

Follow the target project structure when it preserves the same ownership and
dependency rules. Small slices may omit empty directories. Query-heavy slices may
use application-owned read models or projections without loading rich domain
objects when no domain behavior requires them.

## Vocabulary

- Domain: business entities, value objects, aggregates, domain services, domain
  events, invariants, policies, and domain errors. Domain code is independent of
  frameworks and I/O.
- Application: use-case orchestration, business authorization policy, required
  atomicity, coordination of domain behavior, and translation between use-case
  outcomes and outbound dependencies.
- Port: an application-owned contract at a system boundary. An inbound port is the
  callable use-case contract. An outbound port describes a dependency the
  application needs. A separate interface type is optional when the language or
  project does not need one.
- Adapter: an edge implementation that translates between an external system and
  an application contract. HTTP, CLI, UI, database, messaging, filesystem, SDK,
  clock, and external-service integrations are adapters.
- Composition root: startup or bootstrap code that selects concrete adapters and
  wires them into application use cases.
- Feature slice: a package, module, directory, namespace, deployable component, or
  ownership boundary for a business capability.
- Shared kernel: a deliberately small set of stable, pure domain concepts whose
  meaning and lifecycle are jointly owned by multiple slices.
- Published boundary: the documented application API, event, or contract that
  other slices may depend on. It is smaller and more stable than slice internals.

## Dependency rules

Allowed dependencies:

- Domain to domain concepts in the same slice and approved shared-kernel concepts.
- Application to its own domain model, boundary types, and application-owned ports.
- Adapters to the application contracts and boundary types they call or implement.
- Composition root to application and adapter implementations for wiring.
- Cross-slice collaboration through published application APIs, inbound ports,
  integration events, or other documented contracts.
- Shared kernel to shared-kernel concepts only.

Forbidden dependencies:

- Domain depending on application, adapters, frameworks, infrastructure, or I/O.
- Application depending on adapters, concrete infrastructure, transport schemas,
  persistence models, SDK objects, or framework request and response objects.
- Adapters bypassing an application boundary to orchestrate domain workflows or
  call another adapter as a substitute for a port.
- One slice importing another slice's private domain objects, application services,
  repositories, DTOs, adapters, database models, or helpers.
- Shared kernel importing from feature slices, application layers, adapters, or
  infrastructure.

Quick dependency reference:

```text
inbound adapter  ->  inbound contract / application use case  ->  domain
application      ->  outbound port
outbound adapter ->  outbound port
composition root ->  application + adapters
```

Calls may flow back through return values, callbacks, or events, but source-code
dependencies still point toward the owning core contracts. Never let the core
depend on an edge implementation.

## Steps

### 1. Inspect the existing system and constrain the change

Read the request, repository instructions, architecture documents, and the
smallest relevant set of code, tests, contracts, imports, and composition wiring.
Determine:

- the business outcome and actor
- the current entry points, state owners, dependencies, and published contracts
- where invariants, authorization, transactions, and failures are handled
- whether the work is a greenfield design, extension, or refactor
- which local structure, naming, testing, and architecture checks govern the work

Separate observed facts, required behavior, proposed decisions, and unknowns. Do
not impose the generic folder shape on an existing system or treat current code as
proof that its boundaries are intentional.

### 2. Define the slice and its ownership

Name the slice in business language and state the outcome it owns. Identify:

- use cases that belong together because they share business meaning, invariants,
  data ownership, or change cadence
- the data and mutations the slice exclusively owns
- published capabilities that other slices may call or observe
- internals that must remain private
- the decision owner for the boundary

Split a slice when parts have different business meaning, owners, lifecycles, or
consistency needs. Keep them together when splitting would create chatty, cyclic,
or transactionally codependent boundaries. Do not create a slice for every class
or technical layer.

### 3. Model behavior and assign responsibilities

For each meaningful decision, type, operation, or side effect, classify its
responsibility:

- Business identity, value, invariant, policy, or state transition: domain.
- Use-case sequencing, business authorization, and required atomicity:
  application.
- Caller or dependency contract: application boundary or port.
- External format translation, persistence, network, filesystem, messaging, or SDK
  integration: adapter.
- Concrete selection, configuration, and process startup: composition root.
- Stable pure concept with the same meaning and joint ownership across slices:
  shared kernel.

Keep identity extraction and transport authentication at the edge. Keep business
authorization where the use case or domain can enforce it consistently. The
application decides what must be atomic; a transaction or unit-of-work adapter
implements the technical mechanism.

When classification is unclear, prefer the innermost responsibility that can own
the behavior without importing an external detail. Do not force business behavior
into an entity when a stateless domain service or application policy is clearer.

### 4. Define boundary contracts and ports deliberately

Create a boundary when the application must be called from, or depend on,
something outside its owned core. Do not create an interface for every class.

For each boundary, define:

- business intent and owner
- inputs, outputs, and observable side effects
- failure categories and recovery expectations
- idempotency, concurrency, or ordering semantics when relevant
- timeout, retry, and cancellation expectations when relevant
- stability, consumers, and compatibility obligations

Use domain or application boundary types in signatures. Keep transport schemas,
ORM models, SDK objects, framework types, and vendor errors out. Shape outbound
ports around operations the use case needs rather than mirroring a driver, SDK,
generic repository, or CRUD API.

An inbound use case may be the published contract directly; a separate interface
type is not mandatory. Use `api-and-interface-design` when the boundary is durable,
compatibility-sensitive, or has multiple consumers.

### 5. Model state, consistency, time, and side effects

Keep each slice's mutable state under one clear owner. Other slices may consume
published read models or maintain projections, but they should not write the
owner's storage directly.

Define the consistency boundary for each use case:

- Keep invariants that must hold immediately within an aggregate or other explicit
  transactional boundary.
- Prefer eventual consistency for cross-slice propagation when the business can
  tolerate it.
- Do not assume a distributed transaction. If atomic cross-slice updates seem
  necessary, reconsider the boundary or document coordination and recovery costs.
- Use an outbox, idempotency keys, deduplication, or compensation when reliable
  asynchronous delivery requires them.

Domain events record facts inside the owning model. Translate them into stable
integration events at the published boundary when external consumers should not
depend on private domain shapes.

Place clocks, randomness, identifier generation, and other nondeterministic or
effectful capabilities behind outbound ports when business behavior depends on
them. Do not abstract them when they are irrelevant to policy or testability.

### 6. Keep adapters and composition at the edge

Inbound adapters should:

- parse, authenticate, and validate external shape or protocol requirements
- translate input into application boundary types
- call an inbound contract or application use case
- translate the outcome or failure back to the caller's format

Outbound adapters should:

- implement outbound ports
- contain database, filesystem, network, messaging, SDK, serialization, and
  vendor-specific details
- translate external data and errors into the types and failures the port promises
- apply technical timeouts, retries, or bulkheads only when the port contract and
  operation semantics make them safe

Keep dependency injection, concrete service construction, environment lookups,
secret loading, framework startup, and process lifecycle in the composition root
or adapter-owned infrastructure. Do not let containers, service locators,
framework globals, environment access, or persistence sessions leak into the core.

### 7. Design cross-slice collaboration

Choose the smallest explicit integration that fits the business semantics:

- Call a published inbound contract or application API for an immediate result.
- Publish an integration event for decoupling, fan-out, or asynchronous processing.
- Coordinate from an application process or external orchestrator when a flow spans
  slices but does not belong to one domain model.
- Extract a shared-kernel concept only when multiple slices genuinely share its
  meaning, invariants, ownership, and change lifecycle.

For each integration, define ownership, compatibility, failure propagation,
timeouts, retries, idempotency, ordering, and consistency expectations when they
are relevant. Prevent cyclic slice dependencies. Do not create a shared kernel or
global services package merely to make imports easier.

### 8. Plan a safe implementation or refactor

For a new capability, deliver the smallest end-to-end slice that proves the
boundary and business behavior. Add ports and adapters only when that increment
needs them.

For an existing system:

1. Establish behavioral and contract characterization checks.
2. Create one explicit seam at a time, starting with the highest-risk coupling.
3. Move decisions into the owning domain or application boundary before swapping
   external details.
4. Adapt old entry points to the new boundary when a big-bang migration is risky.
5. Remove the old path only after the new path and rollback or recovery strategy
   are verified.

Do not refactor every slice or introduce a repository-wide abstraction to deliver
one change. Preserve external behavior unless the request explicitly changes it.

### 9. Verify and hand off the decision

Use the narrowest checks that prove the design and behavior:

- domain and application unit tests without real infrastructure
- adapter tests for mapping, protocol, error translation, and infrastructure
  integration
- contract tests for published APIs, ports, events, schemas, and consumers
- import, package, or architecture rules that enforce dependency direction
- use-case or system tests for inputs, outputs, and important failure paths
- runtime or operational evidence when the boundary introduces concurrency,
  retries, messaging, or other distributed behavior
- documentation or an ADR for significant boundaries, consistency tradeoffs, or
  intentional deviations

For a design- or review-only task, provide a concrete verification plan and label
unobserved runtime behavior as unverified. Do not infer compliance from folder
names alone.

Hand off the result in this shape:

```md
Capability and owner: <business outcome and owning slice>
Core decisions: <domain, application, ports, and adapters>
Published boundaries: <calls, events, read models, or none>
State and consistency: <owner, atomicity, and cross-slice propagation>
Failure semantics: <errors, timeouts, retries, idempotency, and recovery>
Migration: <increments, compatibility, and rollback when refactoring>
Verification: <evidence observed or planned>
Deviations or unknowns: <reason, risk, and next decision>
```

## Review checklist

- [ ] The slice is named by a business capability and has a clear owner.
- [ ] The design follows project conventions or documents a reasoned deviation.
- [ ] Domain and application code are independent of frameworks, I/O, persistence,
      transport, and vendor types.
- [ ] Business invariants, authorization, and atomicity have explicit owners.
- [ ] Ports exist only at real boundaries and use domain or application types.
- [ ] Adapters translate external details and do not own business workflows.
- [ ] Each unit of mutable state has one clear owner; other slices do not bypass it.
- [ ] Cross-slice calls and events use published contracts without cyclic
      dependencies.
- [ ] Consistency, failure, idempotency, ordering, and retry semantics are explicit
      when relevant.
- [ ] The shared kernel remains small, pure, stable, and jointly owned.
- [ ] Composition code owns concrete wiring, configuration, and process startup.
- [ ] Core behavior is verified without real infrastructure, and edges have focused
      adapter or contract checks.
- [ ] Intentional deviations, migration risks, and unverified behavior are reported.

## Red flags

- Folder names are treated as proof of the architecture.
- Every use case, dependency, or class gets an interface even when no boundary or
  substitution need exists.
- Domain imports a web framework, UI framework, ORM, SDK, filesystem, network, or
  environment API.
- Application creates concrete database clients, HTTP clients, queues, framework
  responses, or persistence sessions.
- Ports expose transport schemas, persistence models, SDK objects, vendor errors,
  or framework types.
- An outbound port mirrors an entire driver, SDK, generic repository, or CRUD API.
- An inbound adapter enforces business policy or calls repositories and outbound
  adapters directly.
- One slice writes another slice's tables, imports its private modules, or depends
  on its ORM models.
- A domain event is published as an external contract without considering consumer
  compatibility.
- A cross-slice workflow assumes a distributed transaction or has no failure and
  recovery plan.
- A global `services`, `utilities`, `common`, or `helpers` package mixes unrelated
  slice behavior.
- The shared kernel grows because it is convenient rather than genuinely shared.
- Dependency wiring or environment access is scattered through domain or
  application code.
- Business-rule tests require real infrastructure to run.
