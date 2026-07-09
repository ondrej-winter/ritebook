"""List-indexes application use case."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ritebook.features.index_registry.application.dtos import (
    ListIndexesCommand,
    ListIndexesResult,
    RegisteredIndex,
    RegisteredIndexSummary,
)
from ritebook.features.index_registry.application.ports import ListIndexesPort

if TYPE_CHECKING:
    from ritebook.features.index_registry.application.ports import IndexRegistryPort


class ListIndexes(ListIndexesPort):
    """List registered consumer indexes from the local registry."""

    def __init__(self, *, registry: IndexRegistryPort) -> None:
        """Initialize list-indexes dependencies."""
        self._registry = registry

    def execute(self, command: ListIndexesCommand) -> ListIndexesResult:
        """Return user-facing summaries for all registered indexes."""
        return ListIndexesResult(
            indexes=tuple(
                _summary(entry) for entry in self._registry.list(command.registry_path)
            ),
        )


def _summary(entry: RegisteredIndex) -> RegisteredIndexSummary:
    return RegisteredIndexSummary(
        name=entry.name,
        published_name=entry.published_name,
        source_type=entry.source_type.value,
        source=entry.source,
        skill_count=entry.skill_count,
        updated_at=entry.updated_at,
    )
