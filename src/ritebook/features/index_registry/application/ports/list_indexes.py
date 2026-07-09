"""Inbound port for listing consumer indexes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.index_registry.application.dtos import (
        ListIndexesCommand,
        ListIndexesResult,
    )


class ListIndexesPort(Protocol):
    """Application boundary for listing registered indexes."""

    def execute(self, command: ListIndexesCommand) -> ListIndexesResult:
        """List registered Git-backed indexes."""
