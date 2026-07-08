"""Inbound port for adding consumer indexes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.index_registry.application.dtos import (
        AddIndexCommand,
        AddIndexResult,
    )


class AddIndexPort(Protocol):
    """Application boundary for registering an index."""

    def execute(self, command: AddIndexCommand) -> AddIndexResult:
        """Register a Git-backed published index."""
