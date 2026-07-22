"""DTOs for consumer index registration workflows."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from ritebook.shared_kernel import require_index_name

_GIT_OBJECT_ID_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")
_INDEX_DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")


class IndexSourceType(StrEnum):
    """Supported registered index source categories."""

    GIT_URL = "git_url"
    LOCAL_GIT_REPO = "local_git_repo"


@dataclass(frozen=True)
class AddIndexCommand:
    """Command for registering a Git-backed published index."""

    source: str
    alias: str | None = None
    force: bool = False
    registry_path: str | None = None
    cache_root: str | None = None

    def __post_init__(self) -> None:
        """Validate command shape after initialization."""
        _require_non_empty(self.source, field_name="Index source")
        if self.alias is not None:
            require_index_name(self.alias, field_name="Local alias")
        _require_optional_non_empty(self.registry_path, field_name="Registry path")
        _require_optional_non_empty(self.cache_root, field_name="Cache root")


@dataclass(frozen=True)
class UpdateIndexCommand:
    """Command for refreshing a registered index."""

    name: str | None = None
    all: bool = False
    registry_path: str | None = None
    cache_root: str | None = None

    def __post_init__(self) -> None:
        """Validate command shape after initialization."""
        if (self.name is None) == (not self.all):
            msg = "Update index requires either a name or all=True."
            raise ValueError(msg)
        if self.name is not None:
            require_index_name(self.name, field_name="Local alias")
        _require_optional_non_empty(self.registry_path, field_name="Registry path")
        _require_optional_non_empty(self.cache_root, field_name="Cache root")


@dataclass(frozen=True)
class ListIndexesCommand:
    """Command for listing registered indexes."""

    registry_path: str | None = None

    def __post_init__(self) -> None:
        """Validate command shape after initialization."""
        _require_optional_non_empty(self.registry_path, field_name="Registry path")


@dataclass(frozen=True)
class ListSkillsCommand:
    """Command for listing skills from registered cached indexes."""

    index_name: str | None = None
    registry_path: str | None = None
    show_description: bool = False

    def __post_init__(self) -> None:
        """Validate command shape after initialization."""
        if self.index_name is not None:
            require_index_name(self.index_name, field_name="Local alias")
        _require_optional_non_empty(self.registry_path, field_name="Registry path")


@dataclass(frozen=True)
class PreparedIndexSource:
    """A Git source prepared by an outbound adapter for index reading."""

    source: str
    source_type: IndexSourceType
    repository_path: str
    source_revision: str
    index_content: bytes
    source_cache_path: str | None = None

    def __post_init__(self) -> None:
        """Validate prepared source metadata."""
        _require_non_empty(self.source, field_name="Index source")
        _require_non_empty(self.repository_path, field_name="Repository path")
        _require_source_revision(self.source_revision)
        if not self.index_content:
            msg = "Committed index content must not be empty."
            raise ValueError(msg)
        if self.source_type is IndexSourceType.GIT_URL:
            _require_non_empty(
                self.source_cache_path,
                field_name="Source cache path",
            )
        elif self.source_cache_path is not None:
            msg = "Local Git repository sources must not have a source cache path."
            raise ValueError(msg)


@dataclass(frozen=True)
class PublishedIndex:
    """Validated root ritebook-index.json contents from a source repository."""

    published_name: str
    schema_version: int
    skill_count: int
    cacheable_content: str
    index_digest: str

    def __post_init__(self) -> None:
        """Validate published index summary metadata."""
        require_index_name(
            self.published_name,
            field_name="Published index name",
        )
        if self.schema_version != 1:
            msg = f"unsupported index schema_version: {self.schema_version}"
            raise ValueError(msg)
        if self.skill_count < 0:
            msg = "Published index skill count must not be negative."
            raise ValueError(msg)
        _require_non_empty(self.cacheable_content, field_name="Cacheable index content")
        _require_index_digest(self.index_digest)


@dataclass(frozen=True)
class RegisteredIndex:
    """Registry metadata for one local index alias."""

    name: str
    published_name: str
    source: str
    source_type: IndexSourceType
    source_revision: str
    index_digest: str
    source_cache_path: str | None
    cached_index_path: str
    source_schema_version: int
    skill_count: int
    added_at: str
    updated_at: str

    def __post_init__(self) -> None:
        """Validate registry entry metadata."""
        require_index_name(self.name, field_name="Local alias")
        require_index_name(
            self.published_name,
            field_name="Published index name",
        )
        _require_non_empty(self.source, field_name="Index source")
        _require_source_revision(self.source_revision)
        _require_index_digest(self.index_digest)
        _require_non_empty(self.cached_index_path, field_name="Cached index path")
        _require_non_empty(self.added_at, field_name="Added timestamp")
        _require_non_empty(self.updated_at, field_name="Updated timestamp")
        if self.source_schema_version != 1:
            msg = f"unsupported index schema_version: {self.source_schema_version}"
            raise ValueError(msg)
        if self.skill_count < 0:
            msg = "Registered index skill count must not be negative."
            raise ValueError(msg)
        if self.source_type is IndexSourceType.GIT_URL:
            _require_non_empty(
                self.source_cache_path,
                field_name="Source cache path",
            )
        elif self.source_cache_path is not None:
            msg = "Local Git repository entries must not have a source cache path."
            raise ValueError(msg)


@dataclass(frozen=True)
class AddIndexResult:
    """Result returned after registering an index."""

    name: str
    skill_count: int

    def __post_init__(self) -> None:
        """Validate add-index result metadata."""
        require_index_name(self.name, field_name="Local alias")
        if self.skill_count < 0:
            msg = "Index skill count must not be negative."
            raise ValueError(msg)


@dataclass(frozen=True)
class UpdateIndexResult:
    """Result returned after refreshing an index."""

    name: str | None
    skill_count: int
    updated_indexes: tuple[str, ...] = ()
    failed_indexes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Validate update-index result metadata."""
        if self.name is not None:
            require_index_name(self.name, field_name="Local alias")
        if self.skill_count < 0:
            msg = "Index skill count must not be negative."
            raise ValueError(msg)
        for name in self.updated_indexes:
            require_index_name(name, field_name="Updated local alias")
        for name in self.failed_indexes:
            require_index_name(name, field_name="Failed local alias")


@dataclass(frozen=True)
class RegisteredIndexSummary:
    """User-facing summary for one registered index."""

    name: str
    published_name: str
    source_type: str
    source: str
    skill_count: int
    updated_at: str

    def __post_init__(self) -> None:
        """Validate list-indexes summary metadata."""
        require_index_name(self.name, field_name="Local alias")
        require_index_name(self.published_name, field_name="Published index name")
        _require_non_empty(self.source_type, field_name="Index source type")
        _require_non_empty(self.source, field_name="Index source")
        _require_non_empty(self.updated_at, field_name="Updated timestamp")
        if self.skill_count < 0:
            msg = "Index skill count must not be negative."
            raise ValueError(msg)


@dataclass(frozen=True)
class ListIndexesResult:
    """Result returned after listing registered indexes."""

    indexes: tuple[RegisteredIndexSummary, ...]


@dataclass(frozen=True)
class CachedSkillSummary:
    """Skill metadata loaded from a cached published index."""

    name: str
    path: str
    skill_file: str
    description: str
    source_root: str = "."

    def __post_init__(self) -> None:
        """Validate cached skill metadata."""
        _require_non_empty(self.name, field_name="Skill name")
        _require_non_empty(self.path, field_name="Skill path")
        _require_non_empty(self.skill_file, field_name="Skill file")
        _require_non_empty(self.description, field_name="Skill description")
        _require_non_empty(self.source_root, field_name="Skill source root")


@dataclass(frozen=True)
class ListedIndexSkills:
    """Cached skills grouped under one local index alias."""

    index_name: str
    skills: tuple[CachedSkillSummary, ...]

    def __post_init__(self) -> None:
        """Validate listed index metadata."""
        require_index_name(self.index_name, field_name="Local alias")


@dataclass(frozen=True)
class ListSkillsResult:
    """Result returned after listing skills from cached registered indexes."""

    indexes: tuple[ListedIndexSkills, ...]


def _require_optional_non_empty(value: str | None, *, field_name: str) -> None:
    if value is not None:
        _require_non_empty(value, field_name=field_name)


def _require_non_empty(value: str | None, *, field_name: str) -> None:
    if not value:
        msg = f"{field_name} must not be empty."
        raise ValueError(msg)


def _require_source_revision(value: str) -> None:
    if not _GIT_OBJECT_ID_PATTERN.fullmatch(value):
        msg = "Source revision must be a full lowercase Git object ID."
        raise ValueError(msg)


def _require_index_digest(value: str) -> None:
    if not _INDEX_DIGEST_PATTERN.fullmatch(value):
        msg = "Index digest must use sha256:<lowercase-hex>."
        raise ValueError(msg)
