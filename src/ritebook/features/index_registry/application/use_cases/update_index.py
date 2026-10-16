"""Update-index application use case."""

from __future__ import annotations

from contextlib import suppress
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ritebook.features.index_registry.application.dtos import (
    AliasOrigin,
    PreparedIndexSource,
    RecoverableIndex,
    RegisteredIndex,
    UpdateIndexCommand,
    UpdateIndexResult,
)
from ritebook.features.index_registry.application.errors import (
    IndexCacheError,
    IndexRegistryError,
    IndexSourceError,
    UnknownIndexNameError,
)
from ritebook.features.index_registry.application.ports import UpdateIndexPort

if TYPE_CHECKING:
    from collections.abc import Callable
    from contextlib import AbstractContextManager

    from ritebook.features.index_registry.application.ports import (
        GitSourcePort,
        IndexCachePort,
        IndexRegistryPort,
        IndexRegistryRecoveryTransaction,
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
        with self._transaction(command) as registry:
            existing = registry.get(command.name)
            if existing is None:
                raise UnknownIndexNameError(command.name)
            return self._update_entry(existing, command, registry)

    def _execute_all(self, command: UpdateIndexCommand) -> UpdateIndexResult:
        updated_indexes: list[str] = []
        updated_metadata: list[RegisteredIndex] = []
        failed_indexes: list[str] = []
        skill_count = 0
        with self._transaction(command) as registry:
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

    def _transaction(
        self,
        command: UpdateIndexCommand,
    ) -> AbstractContextManager[IndexRegistryTransaction | IndexRegistryRecoveryTransaction]:
        if command.force:
            return self._registry.recovery_transaction(command.registry_path)
        return self._registry.write_transaction(command.registry_path)

    def _update_entry(
        self,
        existing: RegisteredIndex | RecoverableIndex,
        command: UpdateIndexCommand,
        registry: IndexRegistryTransaction | IndexRegistryRecoveryTransaction,
    ) -> UpdateIndexResult:
        """Refresh one registry entry and return its updated result."""
        prepared_source = self._git_source.refresh_source(
            source=existing.source,
            source_branch=existing.source_branch if isinstance(existing, RegisteredIndex) else None,
            source_cache_path=existing.source_cache_path if isinstance(existing, RegisteredIndex) else None,
            cache_root=command.cache_root,
            registry_path=command.registry_path,
            force=command.force,
        )
        replacement_source = _replacement_source_cache_path(
            existing,
            prepared_source,
            force=command.force,
        )
        committed = False
        try:
            result = self._commit_update(
                existing,
                prepared_source,
                command,
                registry,
            )
            committed = True
            return result
        finally:
            if replacement_source is not None and not committed:
                with suppress(IndexSourceError):
                    self._git_source.discard_source(
                        source=existing.source,
                        source_cache_path=replacement_source,
                        cache_root=command.cache_root,
                        registry_path=command.registry_path,
                    )

    def _commit_update(
        self,
        existing: RegisteredIndex | RecoverableIndex,
        prepared_source: PreparedIndexSource,
        command: UpdateIndexCommand,
        registry: IndexRegistryTransaction | IndexRegistryRecoveryTransaction,
    ) -> UpdateIndexResult:
        published_index = self._index_reader.read_index(prepared_source.index_content)
        updated_at = _utc_timestamp(self._clock())
        previous_cache = existing.cached_index_path if isinstance(existing, RegisteredIndex) else None
        cached_index_path = self._cache.write_index(
            name=existing.name,
            content=published_index.cacheable_content,
            index_digest=published_index.index_digest,
            cache_root=command.cache_root,
            preserve_path=previous_cache,
            registry_path=command.registry_path,
            force=command.force,
        )
        entry = RegisteredIndex(
            name=existing.name,
            published_name=published_index.published_name,
            alias_origin=existing.alias_origin if isinstance(existing, RegisteredIndex) else AliasOrigin.EXPLICIT,
            source=prepared_source.source,
            source_type=prepared_source.source_type,
            source_revision=prepared_source.source_revision,
            source_branch=prepared_source.source_branch,
            index_digest=published_index.index_digest,
            source_cache_path=prepared_source.source_cache_path,
            cached_index_path=cached_index_path,
            source_schema_version=published_index.schema_version,
            skill_count=published_index.skill_count,
            added_at=existing.added_at if isinstance(existing, RegisteredIndex) else updated_at,
            updated_at=updated_at,
        )
        try:
            registry.upsert(entry)
        except IndexRegistryError:
            if cached_index_path != previous_cache:
                with suppress(IndexCacheError):
                    self._cache.discard_index(
                        name=existing.name,
                        cached_index_path=cached_index_path,
                        cache_root=command.cache_root,
                        registry_path=command.registry_path,
                    )
            raise
        if previous_cache is not None and cached_index_path != previous_cache:
            with suppress(IndexCacheError):
                self._cache.discard_index(
                    name=existing.name,
                    cached_index_path=previous_cache,
                    cache_root=command.cache_root,
                    registry_path=command.registry_path,
                )
        if (
            command.force
            and isinstance(existing, RegisteredIndex)
            and existing.source_cache_path is not None
            and existing.source_cache_path != prepared_source.source_cache_path
            and not _source_cache_path_is_referenced(
                registry,
                existing.source_cache_path,
            )
        ):
            with suppress(IndexSourceError):
                self._git_source.discard_source(
                    source=existing.source,
                    source_cache_path=existing.source_cache_path,
                    cache_root=command.cache_root,
                    registry_path=command.registry_path,
                )
        return UpdateIndexResult(
            name=existing.name,
            skill_count=published_index.skill_count,
            updated_index=entry,
        )


def _replacement_source_cache_path(
    existing: RegisteredIndex | RecoverableIndex,
    prepared_source: PreparedIndexSource,
    *,
    force: bool,
) -> str | None:
    if (
        force
        and prepared_source.source_cache_path is not None
        and (
            not isinstance(existing, RegisteredIndex) or prepared_source.source_cache_path != existing.source_cache_path
        )
    ):
        return prepared_source.source_cache_path
    return None


def _source_cache_path_is_referenced(
    registry: IndexRegistryTransaction | IndexRegistryRecoveryTransaction,
    source_cache_path: str,
) -> bool:
    return any(
        isinstance(entry, RegisteredIndex) and entry.source_cache_path == source_cache_path for entry in registry.list()
    )


def _utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        msg = "Index registry timestamp source must return a timezone-aware value."
        raise ValueError(msg)
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")
