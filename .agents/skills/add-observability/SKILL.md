---
name: add-observability
description: Add logs, metrics, traces, profiling, or operational notes when a workflow needs better runtime visibility or measurable evidence without unsupported performance claims.
metadata:
  version: "1.3.3"
  last-verified: "2026-10-01T09:34:17+02:00"
---

# Add Observability

Use this skill to make runtime behavior diagnosable and operationally useful with
the smallest safe set of logs, metrics, traces, profiles, dashboards, alerts, or
runbook notes.

## Execution boundary

A completed observability change requires access to the relevant source or
configuration plus representative runtime evidence showing that the signal is
emitted, exported, queryable, safe, and operationally useful. Without that access,
an observability contract or review may still be independently useful; label it
design- or review-only and runtime-unverified, and do not implement speculative
instrumentation or claim end-to-end validation. If the request requires working
signals rather than a proposal, report the workflow as blocked.

## When to use this skill

Use this skill when you need to:

- add or improve runtime signals around a meaningful workflow
- make success, failure, latency, load, retries, saturation, or resource use
  measurable
- correlate activity across requests, jobs, queues, processes, or services
- create or revise an operational dashboard, alert, or troubleshooting path
- profile a representative workload to gather diagnostic evidence

Do not use this skill to justify toy benchmarks, noisy logs, speculative
performance claims, or telemetry with no identified consumer or action.

Use `performance-optimization` when the goal is to fix a measured bottleneck. Use
`debugging-and-error-recovery` when an active failure first needs reproduction
and root-cause repair. Use `shipping-and-launch` when observability is a release,
rollout, or rollback gate. Use `security-and-hardening` when telemetry changes
sensitive-data collection, retention, access, or trust boundaries.

## Steps

### 1. Define the operational question and response

Identify the workflow, who needs the signal, the question it must answer, and the
action that follows the answer. Examples include:

- Are users completing `<workflow>` successfully?
- Which dependency or processing stage accounts for slow requests?
- Are retries recovering transient failures or amplifying load?
- Is queue age or resource saturation approaching an operational limit?

Define the relevant outcomes, including success, expected rejection, failure,
timeout, cancellation, retry, and partial completion where applicable. Prefer no
new permanent signal when there is no concrete diagnostic, operational, product,
or compliance use for it.

### 2. Inspect the existing observability path

Before designing instrumentation, inspect the repository and runtime conventions
for:

- established loggers, metric clients, tracing APIs, profilers, and semantic names
- automatic instrumentation and existing middleware or boundary hooks
- correlation and context-propagation mechanisms
- exporters, collectors, ingestion paths, dashboards, alerts, and runbooks
- environment-specific configuration, sampling, retention, access, and cost limits
- tests or local tools used to capture and inspect telemetry

Prefer the existing stack and naming conventions. Do not introduce a new
observability dependency or vendor-specific system unless the project already
uses it or the user explicitly requests it. Identify generated, user-controlled,
or sensitive values before they enter telemetry.

### 3. Write the telemetry contract

Define each proposed signal before implementing it. Record:

- stable name and signal type
- exact emission or measurement point
- value, unit, severity, status, and success or failure semantics
- attributes or labels and their allowed value sets
- correlation or propagation behavior
- counting, aggregation, sampling, and missing-data behavior
- expected query, dashboard, alert, investigation, or decision
- owner and operational documentation when applicable

Be explicit about retries and multi-stage work: decide whether the signal measures
attempts, logical operations, completed operations, or more than one of these.
Use `references/telemetry-design-checklist.md` for a reusable contract template
and signal-specific review guidance.

### 4. Instrument meaningful boundaries

Prefer boundaries where a maintainer can localize behavior or take action:

- incoming request, command, or workflow completion
- external service, database, filesystem, or network calls
- queue enqueue, dequeue, processing, and completion
- retry, timeout, circuit-breaker, and fallback boundaries
- long-running or resource-intensive processing stages
- process, worker, scheduler, or batch-job lifecycle events

Cover every relevant exit path without changing the workflow's control flow or
error semantics. Choose start- or completion-based counting deliberately and use
it consistently. Propagate context across process boundaries and link causally
related asynchronous work when the project supports it.

Avoid low-value helper spans, per-iteration logs, or instrumentation already
provided by automatic libraries. Check for duplicate counting and duplicate error
reporting before adding manual signals.

### 5. Implement the smallest useful signal set

Choose signals according to the question rather than adding every signal type.

- **Logs:** Use stable event names, structured fields, intentional severity, and
  safe correlation context. Log decisions, state transitions, and actionable
  failures. Record an exception at the boundary that owns handling or reporting
  it instead of repeating it at every layer.
- **Metrics:** Measure quantities that can be aggregated and acted on. Define one
  quantity and unit per metric, keep label values bounded, and use distributions
  for latency or size when tails or objective thresholds matter. Do not rely on
  averages alone for skewed behavior.
- **Traces:** Create spans for meaningful units of work and remote or asynchronous
  boundaries. Preserve parentage or causal links, record relevant status and
  events, and keep attributes purposeful. Do not use sampled traces as the sole
  source for exact totals or error-rate denominators.
- **Profiles:** Capture representative, time-bounded CPU, memory, allocation, or
  contention evidence. Avoid permanent request-level profiling unless the
  platform and project explicitly support it safely.

Use shared identifiers only when they are safe and useful. Keep high-cardinality
identifiers out of metric labels; put diagnostic context in access-controlled
logs or traces only when project policy permits it.

### 6. Protect data and production behavior

Collect only data needed for the stated purpose. Exclude secrets, credentials,
session values, raw authorization data, unnecessary request or response bodies,
and personal or regulated data. Treat free-form error messages, URLs, headers,
query values, file paths, and payload fields as potentially sensitive and
high-cardinality. Hashing a predictable identifier does not necessarily make it
anonymous.

Review telemetry emitted by automatic instrumentation and third-party libraries,
not only fields added directly by the change. Apply redaction or allowlisting as
early as practical and verify the exported result after processors or collectors.

Telemetry must not silently become a new availability dependency. Use established
bounded buffering, timeout, retry, sampling, and drop behavior. Exporter or
collector failure should normally degrade visibility rather than fail the user
workflow unless an explicit requirement says otherwise. Assess expected event
volume, series cardinality, storage, retention, and runtime overhead.

### 7. Connect signals to operations

Make new signals usable:

- dashboards state scope, units, time window, expected range, and relevant release
  or environment context
- alerts identify user-visible symptoms or imminent operational risk, have an
  owner and response, and define threshold, duration, urgency, and recovery
- subcritical conditions go to dashboards or ticketed follow-up rather than
  repeatedly interrupting responders
- runbooks explain likely causes, diagnostic queries, mitigation, escalation, and
  known blind spots

Document sampling, aggregation, retention, and missing-data limitations. Use
`update-project-docs` for durable project-facing changes.

### 8. Validate end to end

Exercise representative success and failure paths plus timeout, retry,
cancellation, or partial-completion paths when relevant. Confirm:

- the signal is emitted at the intended boundary and not duplicated
- values, units, severity, status, timestamps, and correlation are correct
- labels and fields remain stable, bounded, and free of sensitive data
- metrics can be queried and aggregated as intended, including zero or missing
  behavior
- trace context survives relevant boundaries and sampling behaves as documented
- telemetry still reaches the intended local or configured backend
- telemetry pipeline failure does not break or materially delay the workflow
- volume, cardinality, and overhead are acceptable under representative load
- changed dashboards and alerts display, trigger, deduplicate, and recover as
  intended when practical

Record the commands, scenarios, queries, or captured output used as evidence.
State what was not validated and why. If claiming a performance or reliability
improvement, preserve comparable before-and-after measurements and their limits;
otherwise describe the result as improved visibility.

## Common failure modes

- adding fields or signals without a concrete query, consumer, or response
- using raw paths, user identifiers, free-form errors, or payload values as metric
  labels
- treating sampled traces as complete traffic counts
- logging the same exception at every layer
- manually duplicating automatic instrumentation
- paging on internal causes with no user impact or actionable response
- allowing exporter latency or failure to affect the business path
- claiming improvement when only instrumentation changed

## Output checklist

- operational question, workflow, consumer, and response are explicit
- existing stack, automatic instrumentation, and data boundaries were inspected
- signal contracts define names, semantics, units, attributes, and counting rules
- instrumentation covers meaningful boundaries without duplicates
- sensitive data, cardinality, volume, cost, and failure behavior were reviewed
- dashboards, alerts, runbooks, and ownership were updated when needed
- success, failure, correlation, export, and degradation behavior were validated
- measurement claims include comparable evidence and limitations
- the result is labeled implemented and verified, design- or review-only and
  runtime-unverified, or blocked; a proposed signal is not reported as operational
