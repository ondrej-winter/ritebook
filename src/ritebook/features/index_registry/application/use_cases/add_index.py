"""Add-index application use case."""

from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ritebook.features.index_registry.application.dtos import (
    AddIndexCommand,
    AddIndexResult,
    AliasOrigin,
    RegisteredIndex,
)
from ritebook.features.index_registry.application.errors import (
    DuplicateIndexNameError,
    IndexCacheError,
    IndexRegistryError,
)
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
        with self._registry.write_transaction(command.registry_path) as registry:
            prepared_source = self._git_source.prepare_source(
                command.source,
                command.cache_root,
                command.registry_path,
            )
            published_index = self._index_reader.read_index(
                prepared_source.index_content,
            )
            local_alias = command.alias or published_index.published_name
            existing = registry.get(local_alias)
            if existing and not command.force:
                raise DuplicateIndexNameError(local_alias)

            timestamp = _utc_timestamp(self._clock())
            cached_index_path = self._cache.write_index(
                name=local_alias,
                content=published_index.cacheable_content,
                index_digest=published_index.index_digest,
                cache_root=command.cache_root,
                preserve_path=existing.cached_index_path if existing else None,
                registry_path=command.registry_path,
            )
            entry = RegisteredIndex(
                name=local_alias,
                published_name=published_index.published_name,
                alias_origin=(
                    AliasOrigin.EXPLICIT
                    if command.alias is not None
                    else AliasOrigin.PUBLISHED_NAME
                ),
                source=prepared_source.source,
                source_type=prepared_source.source_type,
                source_revision=prepared_source.source_revision,
                source_branch=prepared_source.source_branch,
                index_digest=published_index.index_digest,
                source_cache_path=prepared_source.source_cache_path,
                cached_index_path=cached_index_path,
                source_schema_version=published_index.schema_version,
                skill_count=published_index.skill_count,
                added_at=timestamp,
                updated_at=timestamp,
            )
            try:
                registry.upsert(entry)
            except IndexRegistryError:
                if existing is None or cached_index_path != existing.cached_index_path:
                    with suppress(IndexCacheError):
                        self._cache.discard_index(
                            name=local_alias,
                            cached_index_path=cached_index_path,
                            cache_root=command.cache_root,
                            registry_path=command.registry_path,
                        )
                raise
            if existing is not None and cached_index_path != existing.cached_index_path:
                with suppress(IndexCacheError):
                    self._cache.discard_index(
                        name=local_alias,
                        cached_index_path=existing.cached_index_path,
                        cache_root=command.cache_root,
                        registry_path=command.registry_path,
                    )
        return AddIndexResult(
            name=local_alias,
            skill_count=published_index.skill_count,
        )


def _utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "Index registry timestamp source must return a timezone-aware value."
        raise ValueError(msg)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
