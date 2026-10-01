# Agnostic Skill Catalog Reference

Use this reference after the main routing guide when a task needs lifecycle
composition guidance or a full catalog scan.

Routing entries in the catalog advertise available destinations rather than
activating all listed skills. A task should activate only the workflows whose own
triggers are present. Other skill-to-skill relationships are described as
`handoff`, `verification`, or `awareness` in the owning workflow instructions.

## Conditional Lifecycle Composition

There is no universal ordered lifecycle. Compose only the branches whose triggers
are present, and let each routed skill's narrower activation rules override this
summary. A complete feature can move through this graph:

```
Clarify only when needed
  unclear intent -> interview-me
  rough or undecided concept -> idea-refine

Define only when requirements need durable agreement
  incomplete, conflicting, or scattered requirements -> spec-driven-development
  precise fix or small edit with clear acceptance criteria -> continue from request

Plan when the work benefits from decomposition
  planning-and-task-breakdown -> optional review-implementation-plan

Prepare according to the task's evidence needs
  missing context -> context-engineering
  source-sensitive decision -> source-driven-development
  high-stakes or unfamiliar decision -> doubt-driven-development in-flight

Implement
  multi-file or non-minimal work -> incremental-implementation
    for each behavior slice that automated tests can verify:
      test-driven-development RED -> smallest implementation -> GREEN -> REFACTOR -> verify
    for non-behavioral slices:
      edit -> relevant parser, schema, lint, build, or review check
  minimal testable behavior change -> test-driven-development directly
  apply specialized architecture, UI, API, security, or performance workflows only when triggered

Review and ship only as needed
  focused review -> code-review-and-quality
  unnecessary complexity -> code-simplification
  project documentation or durable decisions -> documentation-and-adrs
  version-control, CI/CD, migration, or release work -> the matching shipping workflow
```

`test-driven-development` is not a phase after implementation. When activated, its
RED-GREEN-REFACTOR cycle governs the implementation portion of each relevant
slice. A focused bug fix might use `debugging-and-error-recovery` to reproduce and
localize the failure, then use TDD inside the smallest fix slice before review.

## Quick Reference

| Phase  | Skill                        | One-Line Summary                                                                                     |
| ------ | ---------------------------- | ---------------------------------------------------------------------------------------------------- |
| Define | interview-me                 | Surface what the user actually wants before any plan, spec, or code exists                           |
| Define | idea-refine                  | Refine ideas through structured divergent and convergent thinking                                    |
| Define | spec-driven-development      | Durable requirements and acceptance criteria when the task needs a specification                      |
| Plan   | planning-and-task-breakdown  | Decompose into small, verifiable tasks                                                               |
| Plan   | review-implementation-plan   | Review a plan for gaps, risks, sequencing, dependencies, and validation readiness                    |
| Build  | incremental-implementation   | Thin verifiable slices, with TDD inside behavior changes that automated tests can verify                           |
| Build  | source-driven-development    | Verify against official docs before implementing                                                     |
| Build  | doubt-driven-development     | Adversarial fresh-context review of every non-trivial decision                                       |
| Build  | context-engineering          | Right context at the right time                                                                      |
| Build  | frontend-ui-engineering      | Production-quality UI with accessibility                                                             |
| Build  | api-and-interface-design     | Stable interfaces with clear contracts                                                               |
| Build  | hexagonal-vertical-slices    | Hexagonal architecture with business-owned vertical feature slices                                   |
| Build  | test-driven-development      | RED-GREEN-REFACTOR execution discipline inside each relevant implementation slice                    |
| Verify | browser-runtime-verification | Real-browser verification of UI behavior, console output, network activity, and accessibility basics |
| Verify | run-local-quality-gate       | Discover and run local formatting, linting, static analysis, test, and build checks                  |
| Verify | debugging-and-error-recovery | Reproduce, localize, fix, and guard                                                                  |
| Review | add-observability            | Add useful logs, metrics, traces, profiling, alerts, or dashboards                                   |
| Review | code-review-and-quality      | Five-axis review with quality gates                                                                  |
| Review | code-simplification          | Preserve behavior while reducing unnecessary complexity                                              |
| Review | security-and-hardening       | OWASP prevention, input validation, least privilege                                                  |
| Review | performance-optimization     | Measure first, optimize only what matters                                                            |
| Ship   | git-workflow-and-versioning  | Atomic commits, clean history                                                                        |
| Ship   | conventional-commits         | Conventional Commits message syntax, semantics, and breaking-change notation                         |
| Ship   | ci-cd-and-automation         | Automated quality gates on every change                                                              |
| Ship   | deprecation-and-migration    | Remove old systems and migrate users safely                                                          |
| Ship   | documentation-and-adrs       | Document the why, not just the what                                                                  |
| Ship   | update-project-docs          | Keep project-facing documentation aligned with behavior, configuration, or workflow changes          |
| Ship   | write-adr                    | Record durable architectural decisions with context and consequences                                 |
| Ship   | shipping-and-launch          | Pre-launch checklist, monitoring, rollback plan                                                      |
| Skill  | author-agent-skill           | Create, update, or review Agent Skill directories and SKILL.md files                                 |
| Config | author-agents-config         | Create, audit, update, or synchronize repository agent instructions and client adapters              |
