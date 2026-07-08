"""DTOs for consumer index registration workflows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from ritebook.shared_kernel import require_kebab_case_identifier


class IndexSourceType(StrEnum):
    """Supported registered index source categories."""

    GIT_URL = "git_url"
    LOCAL_GIT_REPO = "local_git_repo"


@dataclass(frozen=True)
class AddIndexCommand:
    """Command for registering a Git-backed published index."""

    source: str
    name: str | None = None
    force: bool = False
    registry_path: str | None = None
    cache_root: str | None = None

    def __post_init__(self) -> None:
        """Validate command shape after initialization."""
        _require_non_empty(self.source, field_name="Index source")
        if self.name is not None:
            require_kebab_case_identifier(self.name, field_name="Index name")
        _require_optional_non_empty(self.registry_path, field_name="Registry path")
        _require_optional_non_empty(self.cache_root, field_name="Cache root")


@dataclass(frozen=True)
class UpdateIndexCommand:
    """Command for refreshing a registered index."""

    name: str
    registry_path: str | None = None
    cache_root: str | None = None

    def __post_init__(self) -> None:
        """Validate command shape after initialization."""
        require_kebab_case_identifier(self.name, field_name="Index name")
        _require_optional_non_empty(self.registry_path, field_name="Registry path")
        _require_optional_non_empty(self.cache_root, field_name="Cache root")


@dataclass(frozen=True)
class PreparedIndexSource:
    """A Git source prepared by an outbound adapter for index reading."""

    source: str
    source_type: IndexSourceType
    repository_path: str
    source_cache_path: str | None = None

    def __post_init__(self) -> None:
        """Validate prepared source metadata."""
        _require_non_empty(self.source, field_name="Index source")
        _require_non_empty(self.repository_path, field_name="Repository path")
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

    def __post_init__(self) -> None:
        """Validate published index summary metadata."""
        require_kebab_case_identifier(
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


@dataclass(frozen=True)
class RegisteredIndex:
    """Registry metadata for one effective index name."""

    name: str
    published_name: str
    source: str
    source_type: IndexSourceType
    source_cache_path: str | None
    cached_index_path: str
    source_schema_version: int
    skill_count: int
    added_at: str
    updated_at: str

    def __post_init__(self) -> None:
        """Validate registry entry metadata."""
        require_kebab_case_identifier(self.name, field_name="Index name")
        require_kebab_case_identifier(
            self.published_name,
            field_name="Published index name",
        )
        _require_non_empty(self.source, field_name="Index source")
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
        require_kebab_case_identifier(self.name, field_name="Index name")
        if self.skill_count < 0:
            msg = "Index skill count must not be negative."
            raise ValueError(msg)


@dataclass(frozen=True)
class UpdateIndexResult:
    """Result returned after refreshing an index."""

    name: str
    skill_count: int

    def __post_init__(self) -> None:
        """Validate update-index result metadata."""
        require_kebab_case_identifier(self.name, field_name="Index name")
        if self.skill_count < 0:
            msg = "Index skill count must not be negative."
            raise ValueError(msg)


def _require_optional_non_empty(value: str | None, *, field_name: str) -> None:
    if value is not None:
        _require_non_empty(value, field_name=field_name)


def _require_non_empty(value: str | None, *, field_name: str) -> None:
    if not value:
        msg = f"{field_name} must not be empty."
        raise ValueError(msg)
