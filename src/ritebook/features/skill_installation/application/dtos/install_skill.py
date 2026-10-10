"""DTOs for direct skill installation workflows."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from ritebook.shared_kernel import (
    normalize_portable_description,
    require_canonical_git_branch,
    require_index_name,
    require_kebab_case_identifier,
)
from ritebook.shared_kernel.catalog_paths import validate_catalog_path

SCHEMA_VERSION = 1
TARGET_NICKNAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
GIT_OBJECT_ID_PATTERN = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
INDEX_DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
STATE_SCHEMA_VERSION = 3


class InstallationWorkflow(StrEnum):
    """Workflow that owns an installed target."""

    DIRECT = "direct"
    SYNC = "sync"


class InstallationStatus(StrEnum):
    """Truthful current state of an owned installation."""

    MATERIALIZED = "materialized"
    LOCAL_CHANGES = "local_changes"
    RETAINED = "retained"


@dataclass(frozen=True)
class SkillReference:
    """A qualified skill reference split into local alias and skill selector."""

    requirement: str
    index_name: str
    skill_path: str
    skill_name: str

    def __post_init__(self) -> None:
        """Validate parsed reference components."""
        _require_non_empty(self.requirement, field_name="Skill reference")
        require_index_name(self.index_name, field_name="Local alias")
        validate_catalog_path(self.skill_path)
        require_kebab_case_identifier(self.skill_name, field_name="Skill name")

    @classmethod
    def parse(cls, value: str) -> SkillReference:
        """Parse a `<local-alias>/<skill-path>` reference."""
        _require_non_empty(value, field_name="Skill reference")
        if "/" not in value:
            msg = (
                "Skill reference must be fully qualified as <local-alias>/<skill-path>."
            )
            raise ValueError(msg)
        index_name, skill_path = value.split("/", maxsplit=1)
        catalog_path = validate_catalog_path(skill_path)
        return cls(
            requirement=value,
            index_name=index_name,
            skill_path=skill_path,
            skill_name=catalog_path.skill_name,
        )


@dataclass(frozen=True)
class InstallSkillCommand:
    """Command for installing one cached skill into an explicit target path."""

    skill_reference: str
    target: str
    force: bool = False
    registry_path: str | None = None
    installation_registry_path: str | None = None

    def __post_init__(self) -> None:
        """Validate command shape after initialization."""
        SkillReference.parse(self.skill_reference)
        _require_non_empty(self.target, field_name="Target")
        _require_optional_non_empty(self.registry_path, field_name="Registry path")
        _require_optional_non_empty(
            self.installation_registry_path,
            field_name="Installation registry path",
        )


@dataclass(frozen=True)
class InstallFromRequirementsCommand:
    """Command for installing all skills declared in a requirements file."""

    requirements_file: str = "ritebook.toml"
    force: bool = False
    registry_path: str | None = None
    lockfile_path: str | None = None

    def __post_init__(self) -> None:
        """Validate requirements-install command shape."""
        _require_non_empty(self.requirements_file, field_name="Requirements file")
        _require_optional_non_empty(self.registry_path, field_name="Registry path")
        _require_optional_non_empty(self.lockfile_path, field_name="Lockfile path")


@dataclass(frozen=True)
class SkillRequirement:
    """One parsed skill requirement from a requirements file."""

    name: str
    target: str | None = None
    target_path: str | None = None

    def __post_init__(self) -> None:
        """Validate a parsed requirement entry."""
        SkillReference.parse(self.name)
        _require_optional_non_empty(self.target, field_name="Target nickname")
        _require_optional_non_empty(self.target_path, field_name="Target path")
        if (self.target is None) == (self.target_path is None):
            msg = "Skill entries must define exactly one of target or target_path."
            raise ValueError(msg)
        if self.target is not None and not TARGET_NICKNAME_PATTERN.fullmatch(
            self.target,
        ):
            msg = (
                "Target nickname must contain only ASCII letters, digits, "
                "underscores, or hyphens."
            )
            raise ValueError(msg)


@dataclass(frozen=True)
class SkillRequirements:
    """Parsed requirements-file content for application planning."""

    targets: dict[str, str]
    skills: tuple[SkillRequirement, ...]

    def __post_init__(self) -> None:
        """Validate parsed requirements content."""
        for nickname, target_base in self.targets.items():
            if not TARGET_NICKNAME_PATTERN.fullmatch(nickname):
                msg = (
                    "Target nickname must contain only ASCII letters, digits, "
                    "underscores, or hyphens."
                )
                raise ValueError(msg)
            _require_non_empty(target_base, field_name="Target path")


@dataclass(frozen=True)
class RegisteredSkillIndex:
    """Installation-owned summary of a registered cached skill index."""

    name: str
    source: str
    source_type: str
    source_revision: str
    source_branch: str
    index_digest: str
    source_cache_path: str | None
    cached_index_path: str
    index_schema_version: int

    def __post_init__(self) -> None:
        """Validate registered index metadata used by installation."""
        require_index_name(self.name, field_name="Local alias")
        _require_non_empty(self.source, field_name="Index source")
        _require_non_empty(self.source_type, field_name="Index source type")
        if not GIT_OBJECT_ID_PATTERN.fullmatch(self.source_revision):
            msg = "Source revision must be a full lowercase Git object ID."
            raise ValueError(msg)
        require_canonical_git_branch(self.source_branch, field_name="Source branch")
        if not INDEX_DIGEST_PATTERN.fullmatch(self.index_digest):
            msg = "Index digest must use sha256:<64 lowercase hex>."
            raise ValueError(msg)
        _require_optional_non_empty(
            self.source_cache_path,
            field_name="Source cache path",
        )
        _require_non_empty(self.cached_index_path, field_name="Cached index path")
        if self.index_schema_version != SCHEMA_VERSION:
            msg = f"unsupported index schema_version: {self.index_schema_version}"
            raise ValueError(msg)


@dataclass(frozen=True)
class CommittedSkillHeader:
    """Validated portable header values read from a committed skill file."""

    name: str
    description: str

    def __post_init__(self) -> None:
        """Validate normalized committed header metadata."""
        require_kebab_case_identifier(self.name, field_name="Committed skill name")
        normalized = normalize_portable_description(
            self.description,
            field_name="Committed skill description",
        )
        if normalized != self.description:
            msg = "Committed skill description must be normalized."
            raise ValueError(msg)


@dataclass(frozen=True)
class InstallableSkill:
    """Cached skill metadata needed to install a skill directory."""

    name: str
    path: str
    skill_file: str
    description: str
    source_root: str = "."

    def __post_init__(self) -> None:
        """Validate installable skill metadata."""
        require_kebab_case_identifier(self.name, field_name="Skill name")
        _require_non_empty(self.path, field_name="Skill path")
        _require_non_empty(self.skill_file, field_name="Skill file")
        normalized = normalize_portable_description(
            self.description,
            field_name="Skill description",
        )
        if normalized != self.description:
            msg = "Skill description must be normalized."
            raise ValueError(msg)
        _require_non_empty(self.source_root, field_name="Skill source root")


@dataclass(frozen=True)
class ResolvedSkillSource:
    """Resolved source repository metadata for an installation."""

    source: str
    source_type: str
    repository_path: str
    source_revision: str
    source_branch: str
    index_digest: str

    def __post_init__(self) -> None:
        """Validate resolved source repository metadata."""
        _require_non_empty(self.source, field_name="Index source")
        _require_non_empty(self.source_type, field_name="Index source type")
        _require_non_empty(self.repository_path, field_name="Repository path")
        _require_source_revision(self.source_revision)
        require_canonical_git_branch(self.source_branch, field_name="Source branch")
        _require_index_digest(self.index_digest)


@dataclass(frozen=True)
class PlannedInstallTarget:
    """A requested install target paired with its canonical filesystem identity."""

    requested_target: str
    canonical_target: str

    def __post_init__(self) -> None:
        """Validate target planning output returned by an installer adapter."""
        _require_non_empty(self.requested_target, field_name="Requested target")
        _require_non_empty(self.canonical_target, field_name="Canonical target")


@dataclass(frozen=True)
class GeneratedStateFile:
    """One complete generated-state file candidate for atomic commit."""

    path: str
    content: bytes
    private: bool
    expected_digest: str | None = None

    def __post_init__(self) -> None:
        """Validate generated-state commit input."""
        _require_non_empty(self.path, field_name="Generated state path")
        if self.expected_digest is not None:
            _require_index_digest(self.expected_digest)


@dataclass(frozen=True)
class InstallationStateSnapshot:
    """Parsed ownership entries paired with the exact source-byte digest."""

    entries: tuple[OwnedInstallation, ...]
    digest: str | None

    def __post_init__(self) -> None:
        """Validate an installation-state read result."""
        if self.digest is not None:
            _require_index_digest(self.digest)


@dataclass(frozen=True)
class StagedSkillTree:
    """One staged, validated skill tree ready for transactional placement."""

    staged_path: str
    cleanup_path: str
    installed_tree_digest: str

    def __post_init__(self) -> None:
        """Validate staged-tree metadata."""
        _require_non_empty(self.staged_path, field_name="Staged skill path")
        _require_non_empty(self.cleanup_path, field_name="Staged cleanup path")
        _require_index_digest(self.installed_tree_digest)


@dataclass(frozen=True)
class TargetInspection:
    """Current filesystem state for one planned installation target."""

    canonical_target: str
    exists: bool
    installed_tree_digest: str | None = None

    def __post_init__(self) -> None:
        """Validate target inspection output."""
        _require_non_empty(self.canonical_target, field_name="Canonical target")
        if self.exists and self.installed_tree_digest is not None:
            _require_index_digest(self.installed_tree_digest)
        if not self.exists and self.installed_tree_digest is not None:
            msg = "Missing targets must not report an installed tree digest."
            raise ValueError(msg)


@dataclass(frozen=True)
class InstallationOperationPaths:
    """Adapter-resolved paths for one locked installation operation."""

    lock_path: str
    journal_path: str
    ownership_path: str
    lockfile_path: str | None = None

    def __post_init__(self) -> None:
        """Validate generated-state and transaction paths."""
        _require_non_empty(self.lock_path, field_name="Installation lock path")
        _require_non_empty(self.journal_path, field_name="Transaction journal path")
        _require_non_empty(self.ownership_path, field_name="Ownership state path")
        _require_optional_non_empty(self.lockfile_path, field_name="Lockfile path")


@dataclass(frozen=True)
class OwnedInstallation:
    """One verified Ritebook-owned installed target."""

    workflow: InstallationWorkflow
    requirement: str
    index_name: str
    skill_name: str
    target: str
    target_id: str
    canonical_target: str
    source: str
    source_type: str
    source_revision: str
    source_branch: str
    index_digest: str
    index_schema_version: int
    skill_path: str
    skill_file: str
    installed_tree_digest: str
    desired: bool = True
    status: InstallationStatus = InstallationStatus.MATERIALIZED
    target_ref: str | None = None

    def __post_init__(self) -> None:
        """Validate ownership and provenance metadata."""
        SkillReference.parse(self.requirement)
        require_index_name(self.index_name, field_name="Local alias")
        require_kebab_case_identifier(self.skill_name, field_name="Skill name")
        _require_non_empty(self.target, field_name="Portable target")
        _require_index_digest(self.target_id)
        _require_non_empty(self.canonical_target, field_name="Canonical target")
        _require_non_empty(self.source, field_name="Index source")
        _require_non_empty(self.source_type, field_name="Index source type")
        _require_source_revision(self.source_revision)
        require_canonical_git_branch(self.source_branch, field_name="Source branch")
        _require_index_digest(self.index_digest)
        _require_non_empty(self.skill_path, field_name="Skill path")
        _require_non_empty(self.skill_file, field_name="Skill file")
        _require_index_digest(self.installed_tree_digest)
        _require_optional_non_empty(self.target_ref, field_name="Target reference")
        if self.index_schema_version != SCHEMA_VERSION:
            msg = f"unsupported index schema_version: {self.index_schema_version}"
            raise ValueError(msg)


@dataclass(frozen=True)
class ReconciliationIssue:
    """One stable target-specific reconciliation problem."""

    code: str
    target: str
    detail: str
    requirement: str | None = None

    def __post_init__(self) -> None:
        """Validate user-facing issue metadata."""
        require_kebab_case_identifier(self.code, field_name="Issue code")
        _require_non_empty(self.target, field_name="Issue target")
        _require_non_empty(self.detail, field_name="Issue detail")
        if self.requirement is not None:
            SkillReference.parse(self.requirement)


@dataclass(frozen=True)
class InstallSkillResult:
    """Result returned after installing one skill."""

    requirement: str
    target: str
    ownership_entry: OwnedInstallation

    def __post_init__(self) -> None:
        """Validate direct install result metadata."""
        SkillReference.parse(self.requirement)
        _require_non_empty(self.target, field_name="Target")


@dataclass(frozen=True)
class InstallFromRequirementsResult:
    """Result returned after installing requirements-file skills."""

    requirements_file: str
    installed_count: int
    updated_count: int
    unchanged_count: int
    pruned_count: int
    ownership_entries: tuple[OwnedInstallation, ...]
    issues: tuple[ReconciliationIssue, ...]

    def __post_init__(self) -> None:
        """Validate requirements install result metadata."""
        _require_non_empty(self.requirements_file, field_name="Requirements file")
        if self.installed_count < 0:
            msg = "Installed count must not be negative."
            raise ValueError(msg)
        if self.updated_count < 0:
            msg = "Updated count must not be negative."
            raise ValueError(msg)
        if self.unchanged_count < 0:
            msg = "Unchanged count must not be negative."
            raise ValueError(msg)
        if self.pruned_count < 0:
            msg = "Pruned count must not be negative."
            raise ValueError(msg)


def _require_optional_non_empty(value: str | None, *, field_name: str) -> None:
    if value is not None:
        _require_non_empty(value, field_name=field_name)


def _require_source_revision(value: str) -> None:
    if not GIT_OBJECT_ID_PATTERN.fullmatch(value):
        msg = "Source revision must be a full lowercase Git object ID."
        raise ValueError(msg)


def _require_index_digest(value: str) -> None:
    if not INDEX_DIGEST_PATTERN.fullmatch(value):
        msg = "Index digest must use sha256:<64 lowercase hex>."
        raise ValueError(msg)


def _require_non_empty(value: str | None, *, field_name: str) -> None:
    if not value:
        msg = f"{field_name} must not be empty."
        raise ValueError(msg)
