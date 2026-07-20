"""DTOs for publishing local skill changes upstream."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath

from ritebook.shared_kernel import require_index_name, require_kebab_case_identifier

SAFE_FILE_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class SkillChangeStatus(StrEnum):
    """Comparison status for installed and upstream skill directories."""

    NO_CHANGES = "no_changes"
    CHANGED = "changed"
    UPSTREAM_CHANGED = "upstream_changed"


@dataclass(frozen=True)
class ContributionSkillReference:
    """A fully qualified contribution reference split into index and selector."""

    requirement: str
    index_name: str
    skill_selector: str
    skill_name: str

    def __post_init__(self) -> None:
        """Validate parsed contribution reference components."""
        _require_non_empty(self.requirement, field_name="Skill reference")
        require_index_name(self.index_name, field_name="Index name")
        _require_safe_posix_path(self.skill_selector, field_name="Skill selector")
        require_kebab_case_identifier(self.skill_name, field_name="Skill name")

    @classmethod
    def parse(cls, value: str) -> ContributionSkillReference:
        """Parse a `<index-name>/<skill-path>` contribution reference."""
        _require_non_empty(value, field_name="Skill reference")
        if "/" not in value:
            msg = (
                "Skill reference must be fully qualified as <index-name>/<skill-path>."
            )
            raise ValueError(msg)
        index_name, skill_selector = value.split("/", maxsplit=1)
        _require_safe_posix_path(skill_selector, field_name="Skill selector")
        return cls(
            requirement=value,
            index_name=index_name,
            skill_selector=skill_selector,
            skill_name=PurePosixPath(skill_selector).name,
        )


@dataclass(frozen=True)
class PublishSkillChangeCommand:
    """Command for preparing one installed skill as an upstream contribution."""

    skill_reference: str
    lockfile_path: str | None = None
    contribution_root: str | None = None

    def __post_init__(self) -> None:
        """Validate command shape after initialization."""
        ContributionSkillReference.parse(self.skill_reference)
        _require_optional_non_empty(self.lockfile_path, field_name="Lockfile path")
        _require_optional_non_empty(
            self.contribution_root,
            field_name="Contribution root",
        )


@dataclass(frozen=True)
class ContributionLockfileEntry:
    """Lockfile provenance required to publish one installed skill change."""

    requirement: str
    index_name: str
    skill_name: str
    target: str
    source: str
    source_type: str
    source_revision: str
    skill_path: str
    skill_file: str
    index_schema_version: int

    def __post_init__(self) -> None:
        """Validate contribution provenance required by the MVP."""
        ContributionSkillReference.parse(self.requirement)
        require_index_name(self.index_name, field_name="Index name")
        require_kebab_case_identifier(self.skill_name, field_name="Skill name")
        _require_non_empty(self.target, field_name="Installed skill target")
        _require_non_empty(self.source, field_name="Index source")
        _require_non_empty(self.source_type, field_name="Index source type")
        _require_non_empty(self.source_revision, field_name="Source revision")
        _require_safe_posix_path(self.skill_path, field_name="Skill path")
        _require_safe_file_path(self.skill_file, field_name="Skill file")
        if self.index_schema_version < 1:
            msg = "Index schema version must be positive."
            raise ValueError(msg)


@dataclass(frozen=True)
class ContributionWorkspace:
    """Prepared isolated source workspace metadata for a contribution."""

    checkout_path: str
    source_skill_path: str
    current_base_revision: str
    locked_revision: str
    has_usable_origin: bool

    def __post_init__(self) -> None:
        """Validate workspace metadata returned by outbound adapters."""
        _require_non_empty(self.checkout_path, field_name="Checkout path")
        _require_safe_posix_path(self.source_skill_path, field_name="Source skill path")
        _require_non_empty(
            self.current_base_revision,
            field_name="Current base revision",
        )
        _require_non_empty(self.locked_revision, field_name="Locked revision")


@dataclass(frozen=True)
class SkillChangeComparison:
    """Safe summary of installed, upstream, and locked skill content comparison."""

    status: SkillChangeStatus
    installed_path: str
    source_skill_path: str
    changed_file_count: int = 0

    def __post_init__(self) -> None:
        """Validate comparison summary metadata."""
        _require_non_empty(self.installed_path, field_name="Installed path")
        _require_safe_posix_path(self.source_skill_path, field_name="Source skill path")
        if self.changed_file_count < 0:
            msg = "Changed file count must not be negative."
            raise ValueError(msg)
        if self.status is SkillChangeStatus.NO_CHANGES and self.changed_file_count != 0:
            msg = "No-change comparisons must not report changed files."
            raise ValueError(msg)


@dataclass(frozen=True)
class PreparedContribution:
    """Metadata for a prepared local contribution branch and commit."""

    skill_reference: str
    checkout_path: str
    branch_name: str
    commit_hash: str
    push_command: str | None = None

    def __post_init__(self) -> None:
        """Validate prepared contribution metadata for CLI rendering."""
        ContributionSkillReference.parse(self.skill_reference)
        _require_non_empty(self.checkout_path, field_name="Checkout path")
        _require_non_empty(self.branch_name, field_name="Branch name")
        _require_non_empty(self.commit_hash, field_name="Commit hash")
        _require_optional_non_empty(self.push_command, field_name="Push command")


@dataclass(frozen=True)
class PublishSkillChangeResult:
    """Result returned after evaluating or preparing one skill contribution."""

    skill_reference: str
    status: SkillChangeStatus
    prepared_contribution: PreparedContribution | None = None

    def __post_init__(self) -> None:
        """Validate contribution result consistency."""
        ContributionSkillReference.parse(self.skill_reference)
        if (
            self.status is SkillChangeStatus.CHANGED
            and self.prepared_contribution is None
        ):
            msg = "Changed contribution results must include prepared metadata."
            raise ValueError(msg)
        if (
            self.status is not SkillChangeStatus.CHANGED
            and self.prepared_contribution is not None
        ):
            msg = "Only changed contribution results may include prepared metadata."
            raise ValueError(msg)


def _require_optional_non_empty(value: str | None, *, field_name: str) -> None:
    if value is not None:
        _require_non_empty(value, field_name=field_name)


def _require_safe_posix_path(value: str, *, field_name: str) -> None:
    _require_non_empty(value, field_name=field_name)
    if value.startswith("/") or value.endswith("/") or "//" in value or "\\" in value:
        msg = f"{field_name} must be a safe relative POSIX path."
        raise ValueError(msg)
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {".", ".."} for part in path.parts)
    ):
        msg = f"{field_name} must be a safe relative POSIX path."
        raise ValueError(msg)
    for part in path.parts:
        require_kebab_case_identifier(part, field_name=f"{field_name} segment")


def _require_safe_file_path(value: str, *, field_name: str) -> None:
    _require_non_empty(value, field_name=field_name)
    if value.startswith("/") or value.endswith("/") or "//" in value or "\\" in value:
        msg = f"{field_name} must be a safe relative POSIX path."
        raise ValueError(msg)
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {".", ".."} for part in path.parts)
    ):
        msg = f"{field_name} must be a safe relative POSIX path."
        raise ValueError(msg)
    for part in path.parts:
        if not SAFE_FILE_SEGMENT_PATTERN.fullmatch(part):
            msg = f"{field_name} must be a safe relative POSIX path."
            raise ValueError(msg)


def _require_non_empty(value: str | None, *, field_name: str) -> None:
    if not value:
        msg = f"{field_name} must not be empty."
        raise ValueError(msg)
