# Upstream Skill Contributions

## Problem Statement

How might we let developers contribute improvements made to repo-local installed
skills back to the original curated skill repository without unsafe overwrites,
lost provenance, or unmanaged local forks?

## Recommended Direction

The long-term product direction should be a Git-hosted merge request workflow. A
developer edits a skill installed into a repository, then runs a Ritebook command
that uses `ritebook.lock` to trace the installed skill back to its source index
repository. Ritebook prepares the changed skill as a normal reviewed
contribution and, when access and provider support are available, opens a merge
request or pull request automatically.

The preferred command name is `publish-skill-change`:

```bash
uv run ritebook publish-skill-change platform-skills/code-review
uv run ritebook publish-skill-change platform-skills/code-review --push
uv run ritebook publish-skill-change platform-skills/code-review --open-mr
```

The command should publish a reviewable proposed change, not directly mutate the
canonical source branch. To keep the workflow safe, Ritebook should create an
isolated contribution clone or worktree that it owns, fetch the source `origin`,
branch from the current upstream base, apply the repo-local skill changes, run
validation, regenerate `ritebook-index.json`, and commit the result. Automatic
merge request creation can then sit on top of that Git-native core.

Provider-specific merge request creation should initially use external CLIs such
as `gh` and `glab` where available. This delegates authentication and provider
specific behavior to tools the developer already controls, while keeping
Ritebook's application core provider-neutral.

## Key Assumptions to Validate

- [ ] `ritebook.lock` contains enough provenance to map an installed target path
      back to the source index, source repository, source revision, and skill
      path. Test by tracing one installed skill from `ritebook.toml` through
      `ritebook.lock` into the registered source repository.
- [ ] Developers actually make useful local improvements to installed repo skills
      and want to upstream them. Test with a manual workflow: edit one repo-local
      skill, prepare a branch in the source repo, and see whether this saves
      meaningful effort.
- [ ] A Ritebook-owned isolated contribution clone or worktree is the safest
      contribution location. Test that it avoids mutating the managed cache clone
      and user-owned local source repositories while still allowing branch,
      validation, index regeneration, commit, push, and review.
- [ ] Comparing against the current source `origin` is better than comparing only
      against the locked source revision. Test by installing a skill, changing the
      upstream source, editing the local install, and verifying the contribution
      warning or conflict behavior is understandable.
- [ ] Automatic MR creation is worth provider-specific complexity. Test after the
      branch/commit workflow exists by adding one external CLI adapter, likely
      `gh` or `glab`, and measuring whether it removes real friction.

## MVP Scope

The MVP should implement the platform-neutral contribution core.

In scope:

- Only skills installed through `ritebook.toml` and recorded in `ritebook.lock`.
- One skill contribution per command.
- Resolve installed target path and source skill path from `ritebook.lock`.
- Fetch the source `origin` in a Ritebook-owned contribution clone or worktree.
- Compare the installed repo-local skill against the current source skill at the
  selected upstream base.
- Exit clearly when there are no local skill changes to publish.
- Warn when upstream changed since the locked install revision.
- Create a Git contribution branch in the isolated contribution checkout.
- Copy the repo-local installed skill back to its source skill directory.
- Run existing skill validation.
- Regenerate `ritebook-index.json`.
- Create a local commit with a clear generated message.
- Print push and MR instructions.

Out of scope for the MVP:

- Opening MRs/PRs automatically.
- Provider API integration.
- Batch contribution of multiple skills.
- Supporting ad hoc `install-skill` installs without `ritebook.lock`.
- Direct writes to the source default branch.
- Conflict resolution beyond clear failure messages.

## Not Doing and Why

- Automatic MR/PR creation in the first slice — this is the long-term direction,
  but provider APIs, auth, fork behavior, and permission errors should sit behind
  a proven Git contribution core.
- Native GitHub, GitLab, or Gitea API adapters at first — external CLIs such as
  `gh` and `glab` can handle authentication and provider-specific behavior with
  less secret-handling risk inside Ritebook.
- Reusing the managed index cache clone as the contribution checkout — cache state
  should remain read/update infrastructure, not a workspace for unpublished local
  changes.
- Mutating a user-owned local source repository by default — it can contain
  unrelated work, local branches, or uncommitted changes that Ritebook should not
  disturb.
- Ad hoc install contribution support — `ritebook.lock` gives safer provenance;
  arbitrary target paths do not.
- Batch upstreaming all changed skills — useful later, but single-skill
  contribution is easier to review and safer to validate.
- Directly mutating the canonical source branch — too risky and bypasses the
  review workflow this feature is meant to support.
- Enterprise governance, approvals, signatures, or trust policy — important
  later, but premature before the contribution path exists.

## Open Questions

- Should `publish-skill-change` eventually support `--base <branch-or-ref>` for
  teams that do not want to target the source repository's default branch?
- Should the isolated contribution checkout be a fresh clone for every change, a
  reusable clone per index, or a Git worktree attached to a managed clone?
- Should `--open-mr` support GitHub first, GitLab first, or detect `gh` and `glab`
  based on the source remote?
- What should the generated branch naming convention be?
- What exact validation evidence should Ritebook include in the generated commit
  or MR body?
