"""DTOs for direct skill installation workflows."""

from __future__ import annotations

from dataclasses import dataclass

from ritebook.shared_kernel import require_index_name, require_kebab_case_identifier

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class SkillReference:
    """A fully qualified skill reference split into index and skill names."""

    requirement: str
    index_name: str
    skill_name: str

    def __post_init__(self) -> None:
        """Validate parsed reference components."""
        _require_non_empty(self.requirement, field_name="Skill reference")
        require_index_name(self.index_name, field_name="Index name")
        require_kebab_case_identifier(self.skill_name, field_name="Skill name")

    @classmethod
    def parse(cls, value: str) -> SkillReference:
        """Parse a `<index-name>/<skill-name>` reference."""
        _require_non_empty(value, field_name="Skill reference")
        if "/" not in value:
            msg = (
                "Skill reference must be fully qualified as <index-name>/<skill-name>."
            )
            raise ValueError(msg)
        index_name, skill_name = value.rsplit("/", maxsplit=1)
        return cls(requirement=value, index_name=index_name, skill_name=skill_name)


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
class InstallSkillResult:
    """Result returned after installing one skill."""

    requirement: str
    target: str
    manifest_entry: InstallationManifestEntry

    def __post_init__(self) -> None:
        """Validate direct install result metadata."""
        SkillReference.parse(self.requirement)
        _require_non_empty(self.target, field_name="Target")


def _require_optional_non_empty(value: str | None, *, field_name: str) -> None:
    if value is not None:
        _require_non_empty(value, field_name=field_name)


def _require_non_empty(value: str | None, *, field_name: str) -> None:
    if not value:
        msg = f"{field_name} must not be empty."
        raise ValueError(msg)
