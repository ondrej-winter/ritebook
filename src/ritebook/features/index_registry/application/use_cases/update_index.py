"""Update-index application use case."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ritebook.features.index_registry.application.dtos import (
    RegisteredIndex,
    UpdateIndexCommand,
    UpdateIndexResult,
)
from ritebook.features.index_registry.application.errors import UnknownIndexNameError
from ritebook.features.index_registry.application.ports import UpdateIndexPort

if TYPE_CHECKING:
    from collections.abc import Callable

    from ritebook.features.index_registry.application.ports import (
        GitSourcePort,
        IndexCachePort,
        IndexRegistryPort,
        IndexSourceReaderPort,
    )


class UpdateIndex(UpdateIndexPort):
    """Refresh cached contents for a registered consumer index."""

    def __init__(
        self,
        *,
        git_source: GitSourcePort,
        index_reader: IndexSourceReaderPort,
        registry: IndexRegistryPort,
        cache: IndexCachePort,
        clock: Callable[[], datetime],
    ) -> None:
        """Initialize update-index orchestration dependencies."""
        self._git_source = git_source
        self._index_reader = index_reader
        self._registry = registry
        self._cache = cache
        self._clock = clock

    def execute(self, command: UpdateIndexCommand) -> UpdateIndexResult:
        """Refresh a remembered source and replace cached contents after validation."""
        existing = self._registry.get(command.name, command.registry_path)
        if existing is None:
            raise UnknownIndexNameError(command.name)

        prepared_source = self._git_source.refresh_source(
            source=existing.source,
            source_cache_path=existing.source_cache_path,
            cache_root=command.cache_root,
        )
        published_index = self._index_reader.read_index(prepared_source.repository_path)
        cached_index_path = self._cache.write_index(
            name=existing.name,
            content=published_index.cacheable_content,
            cache_root=command.cache_root,
        )
        self._registry.upsert(
            RegisteredIndex(
                name=existing.name,
                published_name=published_index.published_name,
                source=prepared_source.source,
                source_type=prepared_source.source_type,
                source_cache_path=prepared_source.source_cache_path,
                cached_index_path=cached_index_path,
                source_schema_version=published_index.schema_version,
                skill_count=published_index.skill_count,
                added_at=existing.added_at,
                updated_at=_utc_timestamp(self._clock()),
            ),
            command.registry_path,
        )
        return UpdateIndexResult(
            name=existing.name,
            skill_count=published_index.skill_count,
        )


def _utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "Index registry timestamp source must return a timezone-aware value."
        raise ValueError(msg)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
