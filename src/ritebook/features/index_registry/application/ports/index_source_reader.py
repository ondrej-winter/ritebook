"""Outbound port for reading published indexes from prepared sources."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.index_registry.application.dtos import PublishedIndex


class IndexSourceReaderPort(Protocol):
    """Outbound dependency for validating root ritebook-index.json files."""

    def read_index(self, repository_path: str) -> PublishedIndex:
        """Read and validate the root index from a prepared repository path."""
