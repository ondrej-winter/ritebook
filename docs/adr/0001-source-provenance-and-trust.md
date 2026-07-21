# 0001. Bind Cached Indexes and Installed Skills to Git Commits

Date: 2026-07-21
Status: Accepted

## Context

Ritebook registers a Git-backed `ritebook-index.json`, caches the validated index,
and later installs skill directories from the remembered source repository. The
current data model remembers a mutable source locator and cache path, while
installation independently reads the source repository's current `HEAD`. A source
can therefore advance after index validation and cause Ritebook to install bytes
that the cached index never described.

The same ambiguity reaches generated installation state and the contribution
workflow. A lockfile revision captured at installation time does not prove that
the installed bytes came from the Git state whose index was validated. The
publisher index deliberately remains a small catalog and does not contain
per-skill content hashes.

Ritebook supports two Git source categories with different ownership:

- Git URL sources use Ritebook-owned managed clones.
- Local Git repository sources remain user-owned and must not be mutated by
  registration or installation.

The project is pre-release. Existing schema-v1 registry, installation-registry,
and lockfile files that lack the required provenance are rejected and must be
regenerated rather than migrated.

## Decision

Ritebook will bind every validated cached index to a provenance tuple containing
the source locator and type, the full Git commit object ID, and a SHA-256 digest
of the exact `ritebook-index.json` bytes read from that commit. Installation and
contribution workflows must consume and verify that same immutable binding.

### Canonical provenance fields

The persisted binding consists of:

- `source` and `source_type`: the operational locator and its source category;
- `source_revision`: the full, unshortened Git commit object ID selected during
  index validation; and
- `index_digest`: `sha256:<lowercase-hex>`, computed over the exact raw bytes of
  root `ritebook-index.json` read from `source_revision`.

`source_revision` identifies the repository state. `index_digest` independently
binds the cached artifact to the index file at that state and detects cache
corruption or incorrect pairing. Neither a branch name, tag, remote-tracking ref,
working-tree `HEAD`, generation timestamp, nor source path is an immutable source
identity.

### Capture and cache rules

For `add-index` and `update-index`, Ritebook must:

1. prepare or refresh the source without relying on a later installation-time
   refresh;
2. select and persist a full commit object ID;
3. read root `ritebook-index.json` from that commit rather than from mutable
   working-tree contents;
4. validate those exact index bytes;
5. compute their SHA-256 digest; and
6. commit the cached bytes, revision, digest, and registry metadata as one
   coherent logical state.

Managed Git URL clones may fetch and move mutable refs while preparing a new
candidate. The prior binding remains authoritative until the new candidate is
fully validated and committed. A failed fetch, revision lookup, index read,
validation, cache write, or registry write must not pair old metadata with a new
source state.

Local Git repository sources must have a clean working tree, including no staged,
unstaged, or untracked changes, when a binding is captured. Dirty local sources
are rejected with guidance to commit or discard changes. Ritebook reads committed
objects without checking out, resetting, cleaning, or otherwise mutating the
user-owned repository.

Detached `HEAD` is valid because the selected commit, not a branch, is the
identity. Force-pushed or otherwise rewritten refs do not change an existing
binding while its commit object remains available.

### Downstream verification

- Registry readers treat `source_revision` and `index_digest` as required schema-v1
  fields.
- Cached-index consumers verify `index_digest` before trusting cached metadata.
- Listing remains offline and does not refresh the source. A digest mismatch is a
  cache-integrity error, not permission to read a mutable working tree.
- Installation hashes both the exact cached index bytes and root
  `ritebook-index.json` read from `source_revision`. Both must match the same
  `index_digest` before Ritebook trusts cached metadata or copies the selected
  skill from that commit. Ritebook never copies from the source's current checkout
  merely because the path matches.
- `installations.json` and `ritebook.lock` record the verified
  `source_revision` and `index_digest` actually used for the copy.
- Contribution preparation requires the lockfile binding, verifies that the bound
  commit and index are available, and treats that commit as the installed
  baseline. It may prepare a change on a newer upstream base only after proving
  that the selected upstream skill path has not changed since the bound commit.

If a bound commit or source is unavailable, Ritebook fails before copying or
committing content and provides recovery guidance. A managed clone may fetch the
remembered source to recover the exact commit. Ritebook does not create snapshots
of user-owned local repositories; if a local repository is moved, deleted, or no
longer contains the object after history rewriting or garbage collection, the
user must restore the repository/object or explicitly refresh and reinstall from
a newly validated binding.

### Schema policy

The pre-release schema-v1 registry, installation-registry, and lockfile contracts
are updated in place to require the provenance fields. Files that lack them are
rejected with guidance to regenerate local state using `add-index` or
`update-index`, followed by installation as needed. Ritebook will not infer a
binding from the source's current `HEAD`, silently upgrade on first install, or
provide an automatic compatibility mode.

This policy is a deliberate pre-release exception. Future compatibility-sensitive
schema changes require an explicit version and migration decision.

## Consequences

### Positive

- Cached metadata, installed bytes, generated state, and contribution baselines
  identify one committed repository state.
- Mutable branches, tags, local working trees, and managed-clone `HEAD` cannot
  silently substitute unvalidated content.
- The publisher index remains compact and reviewable.
- Git provides immutable content addressing without introducing a Ritebook-owned
  source snapshot format.

### Negative

- Dirty local repositories cannot be registered or refreshed until their changes
  are committed or discarded.
- Local-source availability still depends on the user-owned repository retaining
  the bound commit object.
- Existing pre-release schema-v1 local state must be regenerated.
- Registry, installation, and contribution adapters need exact-commit read or
  checkout capabilities rather than ordinary working-tree copies.

### Neutral

- `source` remains a locator needed to retrieve objects; it is not elevated to a
  trust identity.
- SHA-256 protects the local cached-index binding but does not authenticate the
  publisher. Signatures, approvals, and organizational trust policy remain
  separate future concerns.
- Commit object IDs may use the repository's Git object format; they must always
  be stored in full rather than abbreviated.

## Alternatives considered

| Option | Reason rejected |
| ------ | --------------- |
| Mutable source locator plus installation-time `HEAD` | Does not bind validated metadata to installed content and is the failure this decision closes. |
| Git revision without an index digest | Identifies repository state but cannot independently detect a corrupted or incorrectly paired cached index. |
| Ritebook-owned snapshot for every source | Preserves availability but duplicates Git storage and lifecycle semantics; unnecessary for the current Git-only product. |
| Full content hashes without a Git revision | Can prove selected bytes but does not provide the repository base needed by contribution workflows. |
| Publisher-embedded per-skill hashes | Expands publisher schema and hashing policy without replacing the need for a Git contribution base. |
| Signed indexes or commits | Addresses publisher authenticity, which is distinct from binding locally validated metadata to installed bytes. |

## Related specifications

- [Consumer Git Index Registry](../specs/consumer-git-index-registry-spec.md)
- [Consumer Skill Installation](../specs/install-skill-spec.md)
- [Upstream Skill Contributions](../specs/upstream-skill-contributions-spec.md)
- [Publisher Skill Index Generation](../specs/publisher-index-generation-spec.md)
- [Consumer List Skills](../specs/list-skills-spec.md)
- [Docker E2E Integration Testing](../specs/docker-e2e-integration-testing-spec.md)
