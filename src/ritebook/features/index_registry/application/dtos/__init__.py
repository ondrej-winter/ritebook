"""Application DTOs for consumer index registration."""

from ritebook.features.index_registry.application.dtos.index_registry import (
    AddIndexCommand,
    AddIndexResult,
    IndexSourceType,
    ListIndexesCommand,
    ListIndexesResult,
    PreparedIndexSource,
    PublishedIndex,
    RegisteredIndex,
    RegisteredIndexSummary,
    UpdateIndexCommand,
    UpdateIndexResult,
)

__all__ = [
    "AddIndexCommand",
    "AddIndexResult",
    "IndexSourceType",
    "ListIndexesCommand",
    "ListIndexesResult",
    "PreparedIndexSource",
    "PublishedIndex",
    "RegisteredIndex",
    "RegisteredIndexSummary",
    "UpdateIndexCommand",
    "UpdateIndexResult",
]
