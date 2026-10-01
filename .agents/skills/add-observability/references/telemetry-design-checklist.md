# Telemetry Design and Validation Checklist

Use this reference when a change adds permanent telemetry or changes dashboards,
alerts, sampling, export, retention, or operational interpretation. Keep only the
sections that apply to the workflow.

## Telemetry contract

Write one contract per signal or tightly related signal family.

| Concern | Decision |
| --- | --- |
| Operational question | `<question_the_signal_answers>` |
| Consumer and response | `<owner_or_consumer>`; `<decision_or_action>` |
| Workflow and boundary | `<workflow>`; `<emission_or_measurement_point>` |
| Signal | `<log_event_metric_span_or_profile>` |
| Name and meaning | `<stable_name>`; `<plain_language_semantics>` |
| Outcome semantics | `<success_failure_timeout_cancel_retry_rules>` |
| Value and unit | `<value>`; `<base_or_project_standard_unit>` |
| Attributes or labels | `<field>`: `<bounded_allowed_values_or_source>` |
| Correlation | `<request_trace_job_or_safe_domain_identifier>` |
| Aggregation or sampling | `<temporality_distribution_sampling_or_rollup>` |
| Missing-data behavior | `<zero_absent_delayed_dropped_or_unknown>` |
| Operational surface | `<query_dashboard_alert_runbook_or_analysis>` |
| Data handling | `<classification_redaction_retention_and_access>` |
| Expected volume | `<events_or_series_and_growth_assumptions>` |
| Validation evidence | `<test_scenario_query_or_capture_method>` |

Reject or redesign a proposed signal when its meaning changes by call site, its
values cannot be bounded or protected, or nobody can explain how it will be used.

## Logs

- Use a stable event name or message template; keep dynamic values in structured
  fields.
- Use the project's severity levels consistently. Severity should reflect the
  event's operational significance, not merely that an exception object exists.
- Include the event timestamp through the established logging API. Preserve an
  observed or ingestion timestamp separately when the stack supports it.
- Add trace, span, request, or job correlation through the project's standard
  context mechanism rather than passing ad hoc fields through every function.
- Record exception details where the error is handled, transformed, or reported.
  Avoid duplicate stack traces at every propagation layer.
- Prefer bounded categories such as error class, operation, dependency, or
  outcome over raw error text for filtering and aggregation.
- Do not log secrets, authentication data, full payloads, or unreviewed headers,
  URLs, query values, filenames, or user content.
- Estimate log volume on normal and failure paths. Avoid per-record or per-loop
  informational logs on high-throughput paths unless sampling or rate limiting is
  established.

## Metrics

- Give each metric one stable quantity and unit. Follow the project's naming and
  base-unit conventions.
- Choose the measurement type deliberately:
  - monotonic counter for completed events or accumulated amounts
  - gauge for state that can rise and fall
  - distribution or histogram for latency, size, age, and other value ranges
- Define the counting point. Completion-based counts often align with duration
  and outcome metrics, but the project's existing convention takes precedence.
- For ratios, ensure numerator and denominator cover the same population and time
  semantics. Expose the underlying counts when practical instead of only a
  precomputed percentage.
- For latency or size objectives, choose a distribution whose resolution or
  buckets distinguish acceptable from unacceptable outcomes. An average alone
  hides tail behavior.
- Initialize known bounded series when the stack supports it and zero versus
  absence changes query or alert behavior.
- Use labels only for dimensions with bounded, operationally useful value sets.
  Never use user IDs, email addresses, request IDs, timestamps, raw URLs, free-form
  errors, or other unbounded values as labels.
- Estimate worst-case active series from the combinations of label values,
  resources, and deployment scale. Start with fewer dimensions and add one only
  for a concrete query.
- Confirm the metric can be aggregated across processes or instances. Avoid
  client-side values whose meaning is lost when summed or averaged.

## Traces

- Create spans around meaningful operations, remote calls, and asynchronous
  producer or consumer work, not every helper function.
- Preserve incoming context and propagate outgoing context with the established
  mechanism. Use causal links when asynchronous work does not have a direct
  parent-child lifetime.
- Use the project's span kinds, names, status rules, semantic attributes, and
  error-recording conventions.
- Put stable query dimensions in attributes. Put time-ordered facts that belong to
  the operation in span events when supported.
- Avoid full payloads, unrestricted SQL or query text, credentials, personal data,
  and unbounded attributes.
- Document head, tail, probability, or rule-based sampling and its blind spots.
  Ensure errors and slow operations receive the intended treatment where the
  stack supports it.
- Keep unsampled metrics or another complete signal for exact traffic, success,
  and error totals.
- Check span volume, attribute size, fan-out, and exporter behavior under load.

## Profiles

- State the resource question: CPU time, allocations, retained memory, locks,
  contention, I/O wait, or another supported dimension.
- Capture a representative workload, duration, concurrency, data shape, runtime,
  and environment.
- Record warm-up, cache, sampling frequency, and build-mode assumptions.
- Protect profile artifacts because stack frames, paths, labels, and heap data may
  reveal sensitive implementation or user information.
- Compare like with like. A profile can localize cost but does not by itself prove
  a user-visible performance improvement.
- Remove temporary probes or convert them into justified permanent signals before
  handoff.

## Dashboards

- Lead with user-visible health: traffic or work volume, success or error rate,
  latency or freshness, and saturation where relevant.
- Add dependency and internal-cause panels that help explain those symptoms.
- Label units, aggregation, percentile, environment, region, service, and time
  window clearly.
- Mark deploys, configuration changes, or experiments when the platform supports
  annotations.
- Link to the owning service, alert, runbook, or trace and log views when useful.
- Test empty, partial, delayed, and high-volume states. A blank panel must not be
  indistinguishable from healthy zero traffic.

## Alerts

- Page for user-visible symptoms or imminent material risk, not every internal
  anomaly. Use lower-urgency follow-up for conditions that do not need immediate
  human action.
- Define owner, urgency, threshold or objective, evaluation window, minimum
  duration, recovery condition, and routing.
- Include enough context to identify scope and start diagnosis without embedding
  sensitive data.
- Link to a current runbook with verification, mitigation, escalation, and
  rollback or disablement steps.
- Account for low traffic, missing data, delayed ingestion, maintenance, and
  deployment transitions.
- Test that the alert fires for the intended condition, avoids duplicate pages for
  one incident, and resolves when service health recovers.
- Review alert volume after rollout. Repeated non-actionable alerts are defects,
  not background noise to accept indefinitely.

## End-to-end validation matrix

| Scenario | Evidence to capture |
| --- | --- |
| Success | Expected event, count, duration, status, and correlation |
| Expected rejection | Correct outcome category without false error severity |
| Failure | One owned error record and correct failure count or span status |
| Timeout or cancellation | Distinct semantics where operators need them |
| Retry | Attempts and logical operation are not accidentally double-counted |
| Partial completion | Completed and incomplete work can be distinguished |
| Concurrent work | Context does not leak across requests, jobs, or tenants |
| Export unavailable | Workflow remains correct; buffering, drop, and recovery are bounded |
| Sensitive input | Exported telemetry is redacted or omitted after the full pipeline |
| High-cardinality input | Labels remain bounded and volume stays within expectations |
| Representative load | Runtime overhead, event volume, and active series are acceptable |
| Dashboard or alert | Query displays correctly; alert triggers, deduplicates, and recovers |

Prefer automated tests for signal construction and counting semantics, plus at
least one integration or runtime check of the configured telemetry path when
practical. Report any backend, load, alert, or failure-mode validation that could
not be performed.
