"""DTOs for direct skill installation workflows."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath

from ritebook.shared_kernel import require_index_name, require_kebab_case_identifier

SCHEMA_VERSION = 1
TARGET_NICKNAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class SkillReference:
    """A fully qualified skill reference split into index and skill selector."""

    requirement: str
    index_name: str
    skill_path: str
    skill_name: str

    def __post_init__(self) -> None:
        """Validate parsed reference components."""
        _require_non_empty(self.requirement, field_name="Skill reference")
        require_index_name(self.index_name, field_name="Index name")
        _require_skill_path(self.skill_path)
        require_kebab_case_identifier(self.skill_name, field_name="Skill name")

    @classmethod
    def parse(cls, value: str) -> SkillReference:
        """Parse a `<index-name>/<skill-path-or-name>` reference."""
        _require_non_empty(value, field_name="Skill reference")
        if "/" not in value:
            msg = (
                "Skill reference must be fully qualified as "
                "<index-name>/<skill-path-or-name>."
            )
            raise ValueError(msg)
        index_name, skill_path = value.split("/", maxsplit=1)
        _require_skill_path(skill_path)
        return cls(
            requirement=value,
            index_name=index_name,
            skill_path=skill_path,
            skill_name=PurePosixPath(skill_path).name,
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
    source_cache_path: str | None
    cached_index_path: str
    index_schema_version: int

    def __post_init__(self) -> None:
        """Validate registered index metadata used by installation."""
        require_index_name(self.name, field_name="Index name")
        _require_non_empty(self.source, field_name="Index source")
        _require_non_empty(self.source_type, field_name="Index source type")
        _require_optional_non_empty(
            self.source_cache_path,
            field_name="Source cache path",
        )
        _require_non_empty(self.cached_index_path, field_name="Cached index path")
        if self.index_schema_version != SCHEMA_VERSION:
            msg = f"unsupported index schema_version: {self.index_schema_version}"
            raise ValueError(msg)


@dataclass(frozen=True)
class InstallableSkill:
    """Cached skill metadata needed to install a skill directory."""

    name: str
    path: str
    skill_file: str

    def __post_init__(self) -> None:
        """Validate installable skill metadata."""
        require_kebab_case_identifier(self.name, field_name="Skill name")
        _require_non_empty(self.path, field_name="Skill path")
        _require_non_empty(self.skill_file, field_name="Skill file")


@dataclass(frozen=True)
class ResolvedSkillSource:
    """Resolved source repository metadata for an installation."""

    source: str
    source_type: str
    repository_path: str
    source_revision: str | None = None

    def __post_init__(self) -> None:
        """Validate resolved source repository metadata."""
        _require_non_empty(self.source, field_name="Index source")
        _require_non_empty(self.source_type, field_name="Index source type")
        _require_non_empty(self.repository_path, field_name="Repository path")
        _require_optional_non_empty(self.source_revision, field_name="Source revision")


@dataclass(frozen=True)
class InstallationManifestEntry:
    """Generated user-level installation manifest entry."""

    requirement: str
    index_name: str
    skill_name: str
    target: str
    source: str
    source_type: str
    index_schema_version: int
    skill_path: str
    skill_file: str
    installed_at: str
    schema_version: int = SCHEMA_VERSION
    source_revision: str | None = None

    def __post_init__(self) -> None:
        """Validate generated manifest metadata."""
        SkillReference.parse(self.requirement)
        require_index_name(self.index_name, field_name="Index name")
        require_kebab_case_identifier(self.skill_name, field_name="Skill name")
        _require_non_empty(self.target, field_name="Target")
        _require_non_empty(self.source, field_name="Index source")
        _require_non_empty(self.source_type, field_name="Index source type")
        _require_non_empty(self.skill_path, field_name="Skill path")
        _require_non_empty(self.skill_file, field_name="Skill file")
        _require_non_empty(self.installed_at, field_name="Installed timestamp")
        _require_optional_non_empty(self.source_revision, field_name="Source revision")
        if self.schema_version != SCHEMA_VERSION:
            msg = f"unsupported installation schema_version: {self.schema_version}"
            raise ValueError(msg)
        if self.index_schema_version != SCHEMA_VERSION:
            msg = f"unsupported index schema_version: {self.index_schema_version}"
            raise ValueError(msg)


@dataclass(frozen=True)
class LockfileManifestEntry:
    """Generated repo-local lockfile manifest entry."""

    requirement: str
    index_name: str
    skill_name: str
    target: str
    source: str
    source_type: str
    index_schema_version: int
    skill_path: str
    skill_file: str
    locked_at: str
    schema_version: int = SCHEMA_VERSION
    target_ref: str | None = None
    source_revision: str | None = None

    def __post_init__(self) -> None:
        """Validate generated lockfile metadata."""
        SkillReference.parse(self.requirement)
        require_index_name(self.index_name, field_name="Index name")
        require_kebab_case_identifier(self.skill_name, field_name="Skill name")
        _require_non_empty(self.target, field_name="Target")
        _require_non_empty(self.source, field_name="Index source")
        _require_non_empty(self.source_type, field_name="Index source type")
        _require_non_empty(self.skill_path, field_name="Skill path")
        _require_non_empty(self.skill_file, field_name="Skill file")
        _require_non_empty(self.locked_at, field_name="Locked timestamp")
        _require_optional_non_empty(self.target_ref, field_name="Target reference")
        _require_optional_non_empty(self.source_revision, field_name="Source revision")
        if self.schema_version != SCHEMA_VERSION:
            msg = f"unsupported lockfile schema_version: {self.schema_version}"
            raise ValueError(msg)
        if self.index_schema_version != SCHEMA_VERSION:
            msg = f"unsupported index schema_version: {self.index_schema_version}"
            raise ValueError(msg)


@dataclass(frozen=True)
class InstallSkillResult:
    """Result returned after installing one skill."""

    requirement: str
    target: str
    manifest_entry: InstallationManifestEntry

    def __post_init__(self) -> None:
        """Validate direct install result metadata."""
        SkillReference.parse(self.requirement)
        _require_non_empty(self.target, field_name="Target")


@dataclass(frozen=True)
class InstallFromRequirementsResult:
    """Result returned after installing requirements-file skills."""

    requirements_file: str
    installed_count: int
    lockfile_entries: tuple[LockfileManifestEntry, ...]

    def __post_init__(self) -> None:
        """Validate requirements install result metadata."""
        _require_non_empty(self.requirements_file, field_name="Requirements file")
        if self.installed_count < 0:
            msg = "Installed count must not be negative."
            raise ValueError(msg)


def _require_optional_non_empty(value: str | None, *, field_name: str) -> None:
    if value is not None:
        _require_non_empty(value, field_name=field_name)


def _require_skill_path(value: str) -> None:
    _require_non_empty(value, field_name="Skill path")
    if value.startswith("/") or value.endswith("/") or "//" in value or "\\" in value:
        msg = "Skill path must be a safe relative POSIX path."
        raise ValueError(msg)
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or not path.parts
        or any(part in {".", ".."} for part in path.parts)
    ):
        msg = "Skill path must be a safe relative POSIX path."
        raise ValueError(msg)
    for part in path.parts:
        require_kebab_case_identifier(part, field_name="Skill path segment")


def _require_non_empty(value: str | None, *, field_name: str) -> None:
    if not value:
        msg = f"{field_name} must not be empty."
        raise ValueError(msg)
