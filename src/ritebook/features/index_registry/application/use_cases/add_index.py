"""Add-index application use case."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ritebook.features.index_registry.application.dtos import (
    AddIndexCommand,
    AddIndexResult,
    RegisteredIndex,
)
from ritebook.features.index_registry.application.errors import DuplicateIndexNameError
from ritebook.features.index_registry.application.ports import AddIndexPort

if TYPE_CHECKING:
    from collections.abc import Callable

    from ritebook.features.index_registry.application.ports import (
        GitSourcePort,
        IndexCachePort,
        IndexRegistryPort,
        IndexSourceReaderPort,
    )


class AddIndex(AddIndexPort):
    """Register a Git-backed published index in the local consumer registry."""

    def __init__(
        self,
        *,
        git_source: GitSourcePort,
        index_reader: IndexSourceReaderPort,
        registry: IndexRegistryPort,
        cache: IndexCachePort,
        clock: Callable[[], datetime],
    ) -> None:
        """Initialize add-index orchestration dependencies."""
        self._git_source = git_source
        self._index_reader = index_reader
        self._registry = registry
        self._cache = cache
        self._clock = clock

    def execute(self, command: AddIndexCommand) -> AddIndexResult:
        """Prepare, validate, cache, and register an index source."""
        prepared_source = self._git_source.prepare_source(
            command.source,
            command.cache_root,
        )
        published_index = self._index_reader.read_index(prepared_source.repository_path)
        effective_name = command.name or published_index.published_name

        if (
            self._registry.get(effective_name, command.registry_path)
            and not command.force
        ):
            raise DuplicateIndexNameError(effective_name)

        cached_index_path = self._cache.write_index(
            name=effective_name,
            content=published_index.cacheable_content,
            cache_root=command.cache_root,
        )
        timestamp = _utc_timestamp(self._clock())
        self._registry.upsert(
            RegisteredIndex(
                name=effective_name,
                published_name=published_index.published_name,
                source=prepared_source.source,
                source_type=prepared_source.source_type,
                source_cache_path=prepared_source.source_cache_path,
                cached_index_path=cached_index_path,
                source_schema_version=published_index.schema_version,
                skill_count=published_index.skill_count,
                added_at=timestamp,
                updated_at=timestamp,
            ),
            command.registry_path,
        )
        return AddIndexResult(
            name=effective_name,
            skill_count=published_index.skill_count,
        )


def _utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "Index registry timestamp source must return a timezone-aware value."
        raise ValueError(msg)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
