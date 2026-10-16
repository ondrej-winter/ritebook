---
name: ci-cd-and-automation
description: Design, review, or improve CI/CD and automation workflows for quality gates, deployment safety, rollback readiness, secrets handling, and feedback loops across any technology stack.
metadata:
  version: "1.7.0"
  last-verified: "2026-10-15T11:28:40Z"
---

# CI/CD and Automation

Design, review, or change workflows that build, test, release, deploy, or maintain
a project. Make verification repeatable, failures actionable, and side effects
recoverable. Use the project's tools and provider without assuming a language,
package manager, repository host, or deployment platform.

## Execution boundary

Establish whether the request is for review, design, implementation, or execution.
Review-only work produces findings and evidence without edits. A design may use
explicit placeholders for unknown commands or provider details; an executable
configuration must resolve them.

Local edits and validation can be completed without provider access. Report them
as implemented and locally validated, with provider execution unverified. Claim
runtime verification only for behavior actually observed at the relevant
revision and environment. If requested execution is unavailable, mark that step
blocked, explain what is missing, and continue independent work.

Before dispatching or rerunning a workflow, inspect its downstream effects.
Publishing, deployment, cleanup, credential changes, and remote policy changes
must fit the user's scope and existing authorization. A request to edit or audit
automation does not by itself authorize those operations. Use safe local checks
or an authorized disposable environment where possible.

## Steps

### 1. Inspect the existing workflow and its consumers

Read repository instructions, the working-tree diff, canonical workflow sources,
reusable jobs and callers, project commands, and recent failure evidence when
available. Identify generated configuration before editing it. Preserve unrelated
changes, established tooling, and required-check names used by other systems.

Record the intended events and source revision, target environments, inputs,
runner constraints, permissions, artifacts, failure owners, and success signal.
Inspect branch or merge protections and deployment policies when accessible;
configuration files alone do not prove that a gate is enforced. If a check name
or contract must change, coordinate its consumers within authorized scope and
record any remaining external change.

Verify provider-specific syntax, event behavior, permissions, and plan/version
limits against current primary documentation. Keep reusable guidance portable;
use concrete provider configuration in the target project.

### 2. Define quality gates

Choose gates appropriate to the change: formatting, linting, type/schema/contract
checks, tests, builds, security scans, migrations, or generated-file drift. Use
existing project commands and declared dependency versions, with an explicit
working directory and setup. Do not assume globally installed checkers or replace
an established checker as incidental CI cleanup. Resolve missing tooling choices
before making the gate executable.

Define which results are required and how they block merging or deployment.
Preserve command exit codes through wrappers and log collection. Required failures
must not become success through tolerated errors, pipelines, or aggregate jobs.

For each required gate, account for failure, cancellation, missing results, and
unexpected skips. If using an aggregate gate, it must evaluate expected upstream
outcomes even when dependencies fail or are skipped. Define exclusions explicitly
and ensure branch/path filters and merge-queue events, when used, still produce
the required signal. Provider skip semantics differ; for example, consult
[GitHub's required-check guidance](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks)
when targeting GitHub Actions.

Prefer fast deterministic feedback before expensive or mutating stages; run
independent checks in parallel where useful. Do not disable gates to make a run
green. Record temporary exceptions with the risk, owner, and expiry condition.

### 3. Separate untrusted work from privileged operations

Trace who controls the source, event inputs, dependencies, artifacts, caches, and
runner state consumed by each job. A successful upstream run does not establish
trust. Keep untrusted builds and tests away from production credentials, write
tokens, privileged runners, and deployment networks. Inspect effective permissions
on downstream workflows too; they may differ from the initiating job.

- Use least-privilege job permissions and separate test and production identities.
  Prefer short-lived workload credentials when supported, constrained to the
  intended repository, workflow/ref, audience, and environment.
- Retrieve secrets from the project's secret store. Keep them out of source, logs,
  caches, artifacts, and client output; masking alone is not a security boundary.
- Treat event text and user inputs as data. Pass validated values through safely
  quoted arguments or environment variables; do not interpolate them into scripts.
- Pin third-party actions, plugins, and images to reviewed immutable versions
  where supported, with an explicit update process.
- Isolate persistent or self-hosted runners and shared writable state by trust
  level. Prevent untrusted producers from supplying executable inputs to
  privileged consumers through caches or artifacts.

Apply the provider's current rules rather than assuming fork defaults are enough.
For GitHub Actions, consult its
[secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use)
and the permissions of the actual workflow events.

### 4. Make jobs reproducible and failures actionable

Specify the source revision, runtime/toolchain versions, locked dependency
installation, commands, job dependencies, and timeout. Caches are optional
accelerators; a cold run must still work. Select cache keys and access boundaries
that account for dependency locks, runtime/platform compatibility, and trust.

Collect useful logs and test/build reports on failure without masking the original
result. Record the failing command, relevant environment details, local
reproduction steps, and the next diagnostic action. Set artifact access and
retention appropriate to their contents; redact sensitive evidence before sharing.

Retry only identified transient failures with a bound and a reason. Preserve
failure evidence and distinguish infrastructure failures from deterministic or
flaky checks. Do not rerun until green or treat a pass after retry as proof that
flakiness is fixed. For operations with side effects, establish that replay is
safe; otherwise reconcile or recover partial state before deciding whether to retry.

### 5. Make deployments safe to promote, stop, and recover

Apply this step when the workflow releases or deploys. Identify the immutable
artifact, source revision, producing run, and digest or equivalent identity.
Verify the trusted producer and required checks before promotion; promote the
same verified artifact between environments. An artifact name or successful
download alone does not prove provenance.

Define environment approvals, migration ordering and compatibility, smoke/health
checks, monitoring thresholds and window, and the owner who acts on failure.
Specify recovery: rollback, disablement, roll-forward, or compensation. Check
that the recovery version remains compatible with migrated data; an application
rollback does not necessarily reverse a migration. Where reversal is impossible,
record the accepted risk and containment plan.

Serialize operations that share deployment state across all entry points. Before
mutation, check that the run is still eligible to deploy; serialization alone
does not stop an older queued run from replacing a newer release. Treat an
intentional rollback separately from stale-run prevention.

Cancel superseded verification jobs only when safe. For deployments and other
writes, define safe interruption, cleanup, and resumption before enabling automatic
cancellation or retries. Provider ordering and cancellation controls vary; see
[GitLab's deployment-safety guidance](https://docs.gitlab.com/ci/environments/deployment_safety/)
when targeting GitLab CI/CD.

Use previews, staged rollouts, canaries, or feature flags when they reduce the
identified risk. Assign cleanup ownership and an expiry condition to temporary
environments, flags, and release switches.

### 6. Bound maintenance automation

For dependency updates, scheduled suites, drift checks, reports, and cleanup,
define the schedule/event, owner, allowed targets, expected output, and failure
signal. For writes, define review requirements, duplicate-run behavior, recovery,
and how to stop the automation. Prevent bot-triggered update loops.

Exercise mutations in a dry run or disposable environment before enabling them
against real resources. Check both intended changes and protected resources that
must remain untouched. If safe execution is unavailable, keep writes disabled or
default to a dry run in the configuration, and report the unverified behavior.

### 7. Optimize without weakening enforcement

Use measured queue time, job duration, and failure patterns to select changes.
Consider caching, parallel jobs, sharding, or runner capacity. Selective checks
must cover affected dependencies; fall back to broader checks when impact is
uncertain. Verify that path filters and cache hits cannot bypass required gates.

Move non-critical work to scheduled runs only with an explicit coverage tradeoff
and ownership. Preserve required checks for each proposed change. Record any
deferred gate with its risk, owner, and follow-up or expiry condition.

### 8. Verify configuration, behavior, and enforcement separately

Start with the smallest relevant local checks: diff review, provider syntax/schema
linting where available, and the project's affected commands. Inspect the rendered
configuration when templates or reusable workflows affect what runs. A parse or
lint pass proves neither provider execution nor policy enforcement.

Within authorized scope, exercise representative paths in a safe environment:

| Path | Evidence to inspect |
| --- | --- |
| Intended event and successful change | Correct revision, jobs, commands, and artifacts run. |
| Deliberate failure in an isolated fixture | Failure reaches the blocking gate; deployment remains blocked. |
| Filtered, skipped, cancelled, or missing work | Only defined exclusions pass; unexpected omissions cannot pass the gate. |
| Untrusted contribution or downstream handoff | Effective permissions and input handling preserve the trust boundary. |
| Duplicate, stale, retried, or interrupted mutation | No unintended replay, overlap, partial-state loss, or stale deployment. |
| Unhealthy deployment | Health evidence reaches the owner and the recovery path works where safely testable. |

Choose paths relevant to the change. Do not inject failures into production or
reveal real credentials to test a boundary. Inspect merge/deployment policy as
well as job results before claiming enforcement. Record the revision/run and
observed outcomes; distinguish executed checks from documentation review or a
paper walkthrough. Missing provider access leaves runtime behavior unverified.

### 9. Hand off the result and its limits

Summarize findings or changed files, workflow triggers, required gates, permissions,
side effects, recovery, and failure ownership as relevant. Include validation
commands/results and provider-run evidence when available. State the outcome:

- review-only, with findings and supporting evidence
- design-only and runtime-unverified, with unresolved inputs/placeholders
- implemented and locally validated, with provider execution unverified
- implemented and runtime-verified, naming the observed revision and environment

If local validation is incomplete, say so instead of selecting a validated label.
List blocked or deferred steps with the reason, risk, owner if known, and follow-up
condition. Do not invent owners or claim a proposed workflow is working automation.

## Related workflows

When available and their own triggers apply, route active failure diagnosis to
`debugging-and-error-recovery`, use `run-local-quality-gate` for local verification,
and hand off production launch readiness and execution to `shipping-and-launch`.
These relationships do not automatically activate other skills. If unavailable,
continue the CI/CD work supported here and report any unfulfilled dependency.
