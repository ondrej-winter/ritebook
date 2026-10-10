"""Update-index application use case."""

from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ritebook.features.index_registry.application.dtos import (
    RegisteredIndex,
    UpdateIndexCommand,
    UpdateIndexResult,
)
from ritebook.features.index_registry.application.errors import (
    IndexCacheError,
    IndexRegistryError,
    UnknownIndexNameError,
)
from ritebook.features.index_registry.application.ports import UpdateIndexPort

if TYPE_CHECKING:
    from collections.abc import Callable

    from ritebook.features.index_registry.application.ports import (
        GitSourcePort,
        IndexCachePort,
        IndexRegistryPort,
        IndexRegistryTransaction,
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
        if command.all:
            return self._execute_all(command)
        if command.name is None:
            msg = "Update index requires either a name or all=True."
            raise ValueError(msg)
        with self._registry.write_transaction(command.registry_path) as registry:
            existing = registry.get(command.name)
            if existing is None:
                raise UnknownIndexNameError(command.name)
            return self._update_entry(existing, command, registry)

    def _execute_all(self, command: UpdateIndexCommand) -> UpdateIndexResult:
        updated_indexes: list[str] = []
        updated_metadata: list[RegisteredIndex] = []
        failed_indexes: list[str] = []
        skill_count = 0
        with self._registry.write_transaction(command.registry_path) as registry:
            for existing in registry.list():
                try:
                    result = self._update_entry(existing, command, registry)
                except (IndexRegistryError, ValueError):
                    failed_indexes.append(existing.name)
                    continue
                updated_indexes.append(existing.name)
                if result.updated_index is not None:
                    updated_metadata.append(result.updated_index)
                skill_count += result.skill_count
        return UpdateIndexResult(
            name=None,
            skill_count=skill_count,
            updated_indexes=tuple(updated_indexes),
            failed_indexes=tuple(failed_indexes),
            updated_indexes_metadata=tuple(updated_metadata),
        )

    def _update_entry(
        self,
        existing: RegisteredIndex,
        command: UpdateIndexCommand,
        registry: IndexRegistryTransaction,
    ) -> UpdateIndexResult:
        """Refresh one registry entry and return its updated result."""
        prepared_source = self._git_source.refresh_source(
            source=existing.source,
            source_branch=existing.source_branch,
            source_cache_path=existing.source_cache_path,
            cache_root=command.cache_root,
            registry_path=command.registry_path,
        )
        published_index = self._index_reader.read_index(prepared_source.index_content)
        updated_at = _utc_timestamp(self._clock())
        cached_index_path = self._cache.write_index(
            name=existing.name,
            content=published_index.cacheable_content,
            index_digest=published_index.index_digest,
            cache_root=command.cache_root,
            preserve_path=existing.cached_index_path,
            registry_path=command.registry_path,
        )
        entry = RegisteredIndex(
            name=existing.name,
            published_name=published_index.published_name,
            alias_origin=existing.alias_origin,
            source=prepared_source.source,
            source_type=prepared_source.source_type,
            source_revision=prepared_source.source_revision,
            source_branch=prepared_source.source_branch,
            index_digest=published_index.index_digest,
            source_cache_path=prepared_source.source_cache_path,
            cached_index_path=cached_index_path,
            source_schema_version=published_index.schema_version,
            skill_count=published_index.skill_count,
            added_at=existing.added_at,
            updated_at=updated_at,
        )
        try:
            registry.upsert(entry)
        except IndexRegistryError:
            if cached_index_path != existing.cached_index_path:
                with suppress(IndexCacheError):
                    self._cache.discard_index(
                        name=existing.name,
                        cached_index_path=cached_index_path,
                        cache_root=command.cache_root,
                        registry_path=command.registry_path,
                    )
            raise
        if cached_index_path != existing.cached_index_path:
            with suppress(IndexCacheError):
                self._cache.discard_index(
                    name=existing.name,
                    cached_index_path=existing.cached_index_path,
                    cache_root=command.cache_root,
                    registry_path=command.registry_path,
                )
        return UpdateIndexResult(
            name=existing.name,
            skill_count=published_index.skill_count,
            updated_index=entry,
        )


def _utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "Index registry timestamp source must return a timezone-aware value."
        raise ValueError(msg)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
