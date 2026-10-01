---
name: shipping-and-launch
description: Prepare production launches with risk-based readiness checks, staged rollout, monitoring, and an explicit recovery strategy. Use before deploying a feature, migration, or other production change.
metadata:
  version: "1.6.3"
  last-verified: "2026-10-01T09:34:17+02:00"
---

# Shipping and Launch

## Overview

Ship with confidence. The goal is not just to deploy, but to deploy safely, with
monitoring in place, a recovery plan ready, and a clear understanding of what
success looks like. Make each launch observable and incremental when the system
allows it. Define an explicit recovery strategy: rollback, disablement,
roll-forward, compensation, or documented irreversibility with accepted risk and
containment measures when no technical reversal is possible.

This workflow has two distinct outcomes. A launch plan can be completed without
changing production state when it records readiness gaps, rollout stages,
monitoring thresholds, decision owners, and recovery procedures; label it
planning-only and not deployed. An executed launch requires explicit
authorization and production access, followed by deployment and observed
post-launch evidence. If deployment was requested but authorization, access, or
required monitoring is unavailable, report the launch as blocked. Never present
a launch plan or pre-launch review as a completed deployment.

## When to Use

- Deploying a feature to production for the first time
- Releasing a significant change to users
- Migrating data or infrastructure
- Opening a beta or early access program
- Any deployment that carries risk (all of them)

Use `add-observability` when launch readiness requires new logs, metrics, traces,
dashboards, alerts, or troubleshooting notes. Use `performance-optimization` when
launch readiness depends on diagnosing and fixing a performance bottleneck. Use
`debugging-and-error-recovery` when a launch, rollout, or rollback exposes an
active failure that needs root-cause repair.

## Steps

1. Identify the release scope, production risk, owners, target users, and planned
   launch window.
2. Complete the pre-launch checklist sections that apply to the release.
3. Use the supporting reference checklists for deeper security, performance, or
   accessibility verification when those risks apply.
4. Define the rollout sequence, monitoring thresholds, recovery triggers, and
   recovery path before changing production state.
5. Deploy incrementally, verify post-launch signals, and hold or execute the
   recovery plan when thresholds are missed.
6. Record launch evidence, accepted residual risks, cleanup owners, and any
   follow-up work after the release.

## Pre-launch readiness

Before changing production state, confirm that:

- required tests, builds, static checks, artifact generation, and review pass
- temporary code, debug output, sensitive logging, and known blocking failures are resolved
- configuration, secrets, migrations, infrastructure, networking, and artifacts are ready
- health checks, telemetry, dashboards, alerts, and ownership are in place
- user, operator, API, integration, runbook, changelog, and decision documentation is current where relevant
- security, performance, and accessibility checks are complete when those risks apply

Use `references/launch-readiness-checklist.md` for the full cross-cutting
checklist and monitoring categories. Use the focused security, performance, and
accessibility references when those risks apply. Record skipped checks, reasons,
accepted risk, and owners.

## Runtime release control strategy

Use a feature flag, kill switch, or equivalent release control when release risk
justifies runtime control and the change can be isolated safely. Confirm that the
control reduces risk enough to justify its added state, branching, testing,
cleanup, and operational complexity. For static, very small, irreversible, or
already compartmentalized changes, use another explicit recovery strategy when a
runtime control would not materially improve safety.

### Release control lifecycle

1. Deploy with the control in its safest initial state.
2. Enable for an internal, beta, or canary cohort when that provides useful evidence.
3. Gradually roll out through risk-appropriate exposure stages.
4. Monitor release-specific health and user-outcome signals at each stage.
5. Remove the temporary control and dead branch after stabilization criteria pass.

### Release control rules

- Give each release control an owner and a removal condition or review date.
- Clean up temporary controls and dead branches after the stabilization criteria pass.
- Avoid nested controls unless the interaction is necessary, understood, and tested.
- Test each supported control state and transition at the level justified by its risk.

## Staged rollout

Define release-specific cohorts, observation windows, and advance, hold, or
recovery thresholds before launch. A common sequence is staging, production with
release control off, internal exposure, a small canary, increasing cohorts, and
full rollout. Advance only when representative evidence satisfies the defined
thresholds, and retain the ability to stop or reduce exposure at every stage.

Execute the recovery plan when a release-specific threshold is missed or a new
severe failure, data-integrity risk, or security issue appears. For a worked rollout
sequence and example decision table, see
`references/launch-planning-examples.md`.

## Monitoring and Observability

### What to monitor

Monitor signals that show user outcomes and system health: release-specific
business or workflow measures, errors, latency, traffic, resource saturation,
queue or dependency health, and client-side failures where relevant. Compare them
with the pre-launch baseline and the rollout thresholds.

### Error Reporting

When an error reaches a release boundary:

1. Record the exception type, operation, correlation ID, release version, and safe context.
2. Exclude secrets, credentials, raw personal data, and sensitive internals.
3. Return or display a safe recovery message to the user or caller.
4. Emit a metric or alert signal when the failure affects launch thresholds.
5. Preserve enough detail for operators to diagnose the issue from logs or traces.

### Post-Launch Verification

During the initial post-launch observation window:

1. Check the system's health, readiness, smoke, or equivalent operational signal.
2. Check the error monitoring dashboard for new error types.
3. Check the latency dashboard for regressions.
4. Test the critical user flow manually.
5. Verify logs are flowing and readable.
6. Confirm the recovery mechanism works, using a dry run if possible.

## Recovery strategy

Every deployment needs an explicit recovery strategy before it happens. Choose
rollback, disablement, roll-forward, compensation, or documented irreversibility
according to the release risk and system capabilities. If reversal is impossible,
record why, who accepts the risk, how exposure is limited, what state is preserved,
and how operators will contain or repair harm.

Document project-derived triggers, decision ownership, commands or runbooks, data
and state handling, verification, communication, and recovery or containment time
targets. Dry-run the mechanism when practical. For a reusable template, see
`references/launch-planning-examples.md`.

## See Also

- For the detailed cross-cutting readiness checklist, see
  `references/launch-readiness-checklist.md`
- For security pre-launch checks, see `references/security-checklist.md`
- For performance pre-launch checklist, see `references/performance-checklist.md`
- For accessibility verification before launch, see `references/accessibility-checklist.md`
- For worked rollout and recovery examples, see `references/launch-planning-examples.md`

## Common Rationalizations

| Rationalization                                   | Reality                                                                                                        |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| "It works in staging, it will work in production" | Production has different data, traffic patterns, and edge cases. Monitor after deploy.                         |
| "We do not need feature flags for this"           | Assess the risk. Use a runtime control when it materially improves safety; otherwise document another strategy. |
| "Monitoring is overhead"                          | Without monitoring, users may discover problems before operators do.                                           |
| "We will add monitoring later"                    | Add release-relevant signals before launch so the team can detect and diagnose regressions.                    |
| "Rolling back is admitting failure"               | Executing the chosen recovery strategy is responsible engineering; leaving a harmful release active is not.    |

## Red Flags

- Deploying without an explicit recovery strategy
- No monitoring or error reporting in production
- Big-bang releases (everything at once, no staging)
- Temporary release controls with no owner or removal condition
- No one monitoring the deploy during the initial observation window
- Production environment configuration done by memory, not code
- "It is Friday afternoon, let us ship it"

## Verification

For a planning-only result:

- [ ] Result is labeled planning-only and not deployed
- [ ] Readiness gaps, owners, rollout thresholds, and recovery strategy are recorded
- [ ] Required production access and post-launch evidence are identified

Before an executed deployment:

- [ ] Applicable pre-launch checklist sections completed
- [ ] Runtime release control configured (if applicable)
- [ ] Recovery strategy documented
- [ ] Monitoring views and alerts set up
- [ ] Team notified of deployment

After deploying:

- [ ] Health, readiness, smoke, or equivalent operational check passes
- [ ] Error rate is normal
- [ ] Latency is normal
- [ ] Critical user flow works
- [ ] Logs are flowing
- [ ] Recovery mechanism tested or verified ready
- [ ] Final status says deployed and verified, held, recovered, or blocked rather
      than treating an incomplete launch as successful
