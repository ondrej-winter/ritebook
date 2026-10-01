# Launch Readiness Checklist

Use this detailed checklist after the core launch workflow in `SKILL.md`. Complete
only sections relevant to the release, and record skipped checks, accepted risks,
and owners.

## Code Quality

- [ ] Required tests pass, including unit, integration, contract, workflow, or end-to-end checks where relevant
- [ ] Build, package, migration, or deployment artifact generation succeeds with no unexpected warnings
- [ ] Static analysis, linting, schema checks, or type checks pass where used
- [ ] Code reviewed and approved
- [ ] No TODO comments, temporary flags, or debug-only paths that should be resolved before launch
- [ ] No ad hoc debugging output, sensitive logging, or noisy diagnostics left in production paths
- [ ] Error handling covers expected failure modes

## Security

- [ ] No secrets in code or version control
- [ ] Dependency, image, package, or artifact checks show no unacceptable release-blocking vulnerabilities
- [ ] Input validation covers user-facing, partner-facing, batch, and integration entry points
- [ ] Authentication and authorization checks are in place where identity or permissions are involved
- [ ] Transport, browser, API, and platform security controls are configured where relevant
- [ ] Abuse controls, rate limits, quotas, or backpressure are configured for sensitive operations
- [ ] Cross-origin, network, and integration access is restricted to intended consumers

## Performance

- [ ] User-facing responsiveness, request latency, or job processing time meets launch targets
- [ ] Critical paths avoid repeated, unbounded, or unexpectedly expensive work
- [ ] Payloads, assets, artifacts, and transferred data stay within release budgets
- [ ] Data access paths, indexes, partitions, or storage patterns are ready for expected production volume
- [ ] Caching, batching, pagination, or queueing behavior is configured where relevant
- [ ] Resource use and saturation limits are understood for expected traffic or data volume

## Accessibility

- [ ] Keyboard or non-pointer navigation works for interactive surfaces where applicable
- [ ] Assistive technologies can convey content, structure, and state for user interfaces
- [ ] Text, icons, and meaningful visual states meet contrast and non-color communication expectations
- [ ] Focus management works for dialogs, dynamic content, and workflow transitions
- [ ] Errors and recovery instructions are descriptive and connected to the affected action or input
- [ ] Automated or manual accessibility checks have no unresolved launch-blocking findings

## Infrastructure

- [ ] Production configuration, environment variables, and secrets are set through the approved mechanism
- [ ] Data migrations, schema changes, or infrastructure changes are applied or ready to apply safely
- [ ] Routing, networking, certificate, and access configuration are ready where relevant
- [ ] Static assets, packages, images, or deployment artifacts are published and cache behavior is understood
- [ ] Logging, metrics, tracing, and error reporting are configured
- [ ] Health, readiness, smoke, or equivalent verification checks exist and respond

## Documentation

- [ ] README updated with any new setup requirements
- [ ] User, operator, API, integration, or runbook documentation is current where relevant
- [ ] ADRs or decision records written for durable architectural or operational decisions
- [ ] Changelog updated
- [ ] User-facing documentation updated (if applicable)

## What to Monitor

Application metrics:

- Error rate (total and by endpoint)
- Response time (p50, p95, p99)
- Request volume
- Active users
- Key business metrics (conversion, engagement)

Infrastructure metrics:

- CPU and memory utilization
- Database connection pool usage
- Disk space
- Network latency
- Queue depth (if applicable)

Client metrics:

- Frontend responsiveness or page load time, for browser-facing products
- Client-side, device-side, or edge errors
- API, integration, or synchronization failures from the consumer perspective
- Accessibility, usability, or workflow completion signals where relevant
