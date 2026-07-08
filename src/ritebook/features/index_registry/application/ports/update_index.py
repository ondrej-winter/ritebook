"""Inbound port for updating consumer indexes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.index_registry.application.dtos import (
        UpdateIndexCommand,
        UpdateIndexResult,
    )


class UpdateIndexPort(Protocol):
    """Application boundary for refreshing a registered index."""

    def execute(self, command: UpdateIndexCommand) -> UpdateIndexResult:
        """Refresh a registered Git-backed index."""
