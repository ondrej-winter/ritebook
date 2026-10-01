---
name: deprecation-and-migration
description: Plan and execute safe deprecations, migrations, replacements, and removals by measuring usage, supporting consumers, preserving compatibility, and making evidence-based removal decisions.
metadata:
  version: "1.2.3"
  last-verified: "2026-10-01T09:34:17+02:00"
---

# Deprecation and Migration

Use this skill when replacing, retiring, consolidating, or removing a system,
interface, feature, dependency, workflow, configuration surface, or documented
behavior. The goal is to reduce long-term maintenance cost without surprising
active consumers or breaking compatibility-sensitive paths.

Deprecation is the decision and communication process. Migration is the work of
moving consumers safely from the old path to the new one. Removal happens only
after usage evidence, observation limits, and residual risk have been evaluated.

This workflow has distinct completion states. A deprecation or migration plan may
be complete when it records evidence gaps, owners, support windows, migration
steps, removal gates, and verification methods; label it planning-only and not
executed. An executed migration requires changing each in-scope consumer and
verifying compatibility. A removal requires the applicable evidence, approvals,
cleanup, and post-removal validation. If execution was requested but the required
repository, telemetry, consumer, or approval access is unavailable, report the
affected phase as blocked. Never report a plan as a completed migration or
removal.

## When to use this skill

Use this skill when:

- replacing an old implementation, API, library, adapter, workflow, or feature
- consolidating duplicate behavior
- removing dead or unowned code that may still have consumers
- migrating users, services, modules, data, configuration, or documentation
- deciding whether to maintain a legacy path or invest in removal
- designing a new interface and planning how it could be retired later

Do not use this skill to remove behavior just because it is inconvenient. First
verify ownership, usage, replacement readiness, and migration risk.

## Principles

- Code and operational surfaces carry maintenance cost. Remove what no longer
  earns its keep, but do it safely.
- Observable behavior becomes a contract when consumers depend on it, even if it
  was undocumented.
- Deprecation without a usable replacement is usually abandonment, not migration.
- Consumers need clear timelines, compatibility notes, tooling, and support.
- Removal is complete only when code, tests, docs, configuration, monitoring, and
  references are cleaned up.

## Steps

### 1. Decide whether deprecation is justified

Answer:

- What unique value does the old path still provide?
- Who or what consumes it?
- What observable behavior do consumers rely on?
- What replacement exists, and is it ready?
- What is the migration cost for each consumer group?
- What is the cost or risk of keeping the old path?
- What happens if migration is delayed?

If active consumers remain and no replacement exists, build or identify the
replacement before announcing removal.

### 2. Measure usage and ownership

Do not rely on guesses. Gather evidence from available sources such as metrics,
logs, dependency analysis, repository search, configuration, support tickets,
runtime traces, docs, and owner interviews.

Record:

- active consumers and owners
- removal owner and decision maker
- whether the consumer population is controlled or open-ended
- known undocumented dependencies
- usage volume and criticality
- measurement coverage, observation window, and telemetry blind spots
- compatibility-sensitive behaviors
- data, configuration, or integration points affected
- unknowns that require follow-up

### 3. Choose advisory or compulsory deprecation

Use advisory deprecation when migration is optional or the old path can remain
stable for a while. Use compulsory deprecation only when risk, cost, security,
compliance, or blocking complexity justifies a deadline.

For compulsory deprecation, provide:

- deadline and rationale
- working replacement
- migration guide
- support path
- verification method
- exception process when needed

### 4. Prepare the replacement and migration path

Before broad announcement, confirm the replacement:

- covers critical use cases
- has parity or intentionally documented differences and compatibility limits
- is validated in representative environments
- has rollback or fallback guidance when applicable
- exposes enough observability to compare old and new behavior and prove usage
  decline on the old path
- includes migration tooling or examples when migration is repetitive

Use incremental migration patterns when risk is high, such as parallel run,
adapter, compatibility shim, feature flag, canary, staged rollout, or staged
consumer migration.

### 5. Announce and document

Write a concise notice:

```md
## Deprecation notice: <old_surface>

Status: <advisory or compulsory>
Replacement: <new_surface>
Reason: <why this is changing>
Removal owner: <owner or decision maker>
Migration deadline: <date or none>
Affected consumers: <known scope>
Removal criteria: <evidence, support window, approvals, and risk acceptance>
Evidence classification: <proven zero usage, no known active consumers, or remaining usage cannot be observed>
Migration steps:

1. <step>
2. <step>

Verification: <how to prove migration worked>
Support or escalation: <contact or process>
```

Keep the notice close to the old surface and in durable project documentation.

### 6. Migrate incrementally

For each consumer:

1. Identify old-path touchpoints.
2. Move to the replacement.
3. Verify behavior and compatibility.
4. Remove references to the old path.
5. Record completion or remaining risk.

If you own the deprecated surface, prefer helping or automating consumer migration
over leaving consumers to infer the work.

### 7. Make an evidence-based removal decision

Before removal, classify the strongest conclusion the available evidence supports:

- **Proven zero usage:** the consumer population is controlled, measurement is
  sufficiently complete, and a representative observation window shows no active
  usage.
- **No known active consumers:** available telemetry, dependency checks, repository
  searches, records, and owner outreach found no active consumer, but coverage is
  incomplete.
- **Remaining usage cannot be observed:** consumers may exist outside available
  telemetry or organizational control, such as public APIs, offline clients,
  distributed installations, or externally owned integrations.

Do not claim proven zero usage when the consumer population or measurement coverage
is incomplete. Record the evidence sources, observation window, blind spots, and
classification in the removal decision.

For every classification, verify:

- fallback or rollback expectations are clear
- replacement behavior is stable under representative usage
- tests cover the replacement and no longer depend on the old behavior
- stakeholders accept the removal timing

Require proven zero usage when consumers are controlled and measurement is
sufficiently complete. Otherwise, removal may proceed only when:

- the documented support window and migration deadline have elapsed
- affected audiences received reasonable migration notice through available
  channels
- the replacement and migration guidance are ready
- the removal owner approves the decision
- unresolved exceptions are closed or explicitly accepted
- residual risk, including potentially unobserved usage, is documented and
  explicitly accepted by the decision maker

Then remove code, tests, configuration, feature flags, compatibility shims, and
obsolete references from alerts, dashboards, docs, examples, and generated files.
Retain any durable migration or historical notice that consumers still need.

## Red flags

- removal announced without usage evidence or documented observation limits
- no working replacement or migration guide
- active consumers with no owner or support path
- deprecated path keeps receiving new features
- advisory deprecation remains unresolved indefinitely
- compatibility behavior changed without notice
- evidence labeled as proven zero usage despite uncontrolled consumers or
  incomplete measurement
- incompletely observable path removed without an elapsed support window, owner
  approval, and explicit residual-risk acceptance
- documentation and configuration still reference removed behavior

## Output checklist

- result status and completed phase are explicit: planning-only, migration
  executed and verified, removal executed and verified, or blocked
- deprecation rationale and scope are explicit
- active usage, ownership, measurement coverage, and blind spots were assessed
- removal owner and decision maker are known
- replacement readiness is verified
- advisory or compulsory status is documented
- migration guide and support path exist
- consumers are migrated incrementally where needed
- removal evidence is classified as proven zero usage, no known active
  consumers, or remaining usage cannot be observed
- proven zero usage is required where consumers and measurement are controlled;
  otherwise the support window, notice, approval, and residual-risk gates are met
- old code, tests, docs, configuration, and notices are cleaned up
- planning-only results identify required execution and evidence without claiming
  that consumers migrated or the old surface was removed
