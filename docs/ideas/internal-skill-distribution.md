# Ritebook Internal Skill Distribution

## Problem Statement

How might we help corporate teams curate, standardize, and selectively distribute
private agent skills without relying on brittle bash scripts or unnecessary full
repository syncs?

## Confirmed Intent

Ritebook should become a lightweight internal distribution tool for corporate
agent skills. The first useful capability is a publisher-side flow that creates
or updates an index of approved skills from a private repository.

The first user is the skill maintainer or curator inside a company. Later users
are developers and teams consuming curated skills into user-level or repo-local
agent environments.

The priority order is:

1. Help maintainers control and curate approved internal skills.
2. Help teams standardize agent behavior across repositories.
3. Help developers install skills faster.

Developer convenience matters, but it is the adoption mechanism rather than the
primary reason for the product.

## Recommended Direction

Start with a Git-native publisher workflow. Maintainers keep internal skills in a
private repository and run Ritebook to generate or update an index file from that
repository. For now, any directory containing `SKILL.md` counts as a skill.

The generated index should be committed to the private repository so changes are
reviewable, auditable, and easy to integrate into normal pull request workflows.
That index later becomes the source that consumer machines can mirror locally,
similar in spirit to how package installers consult an index before downloading
artifacts.

Consumer installation is the next proof point after the publisher flow. It should
eventually allow developers or repository maintainers to list available skills
from a cached index and install selected skills into flexible destinations such
as `~/.agents/skills/`, `~/.claude/skills/`, or `repo/.agents/skills/`.

## Key Assumptions to Validate

- [ ] Directories containing `SKILL.md` are a sufficient package boundary for the
      first internal skill catalog.
- [ ] Maintainers are comfortable treating a generated index file as part of the
      private skills repository and reviewing changes in pull requests.
- [ ] Publisher-first delivery creates enough value before the consumer install
      workflow is complete.
- [ ] A simple index can support future metadata requirements without forcing an
      early mandatory metadata schema.
- [ ] Flexible install targets will cover user-level and repo-local agent skill
      locations once the consumer workflow is implemented.

## MVP Scope

The first MVP should focus on the publisher-side index generation flow:

- Discover skills by scanning a source tree for directories containing
  `SKILL.md`.
- Require the maintainer to provide one explicit skills root directory; do not
  infer or scan the whole repository by default.
- Generate a deterministic index file from discovered skills.
- Keep the index format simple and versioned so it can evolve later.
- Include enough information for future consumer commands to list and locate
  skills.
- Fit normal private-repository workflows where the generated index is committed
  alongside the skills.

The follow-up MVP can add consumer-side behavior:

- Mirror or cache the index locally.
- List skills from the cached index.
- Install a selected skill into an explicit target path.

## Not Doing and Why

- Homebrew packaging — future distribution channel, not needed to validate the
  internal catalog model.
- PyPI release automation beyond keeping the package structure compatible — the
  immediate need is product shape and publisher workflow.
- Mandatory skill metadata schema — useful later, but `SKILL.md` presence is the
  only package contract for now.
- Policy enforcement, signatures, approvals, and trust chains — important for
  mature corporate distribution, but premature before the index workflow is
  proven.
- General non-skill assets — future direction, but skills are the first concrete
  asset type.
- Full consumer installation UX — important next step, but the first milestone is
  publisher index generation.

## Open Questions

- What should the first index file be named: `index.json`, `ritebook-index.json`,
  or another name?
- Which fields must index schema v1 include to support later consumer listing and
  installation without overcommitting to metadata policy?
- Should generated index entries include content hashes from day one?
- Should future consumer sync support Git URLs, raw HTTP index URLs, local paths,
  or all three?
- When consumer installation is added, should existing target skills be refused
  by default unless `--force` is provided?