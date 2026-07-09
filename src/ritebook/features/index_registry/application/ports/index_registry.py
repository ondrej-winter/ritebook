"""Outbound port for local index registry metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.index_registry.application.dtos import RegisteredIndex


class IndexRegistryPort(Protocol):
    """Outbound dependency for local registry metadata persistence."""

    def get(self, name: str, registry_path: str | None) -> RegisteredIndex | None:
        """Return a registered index by effective name when it exists."""

    def list(self, registry_path: str | None) -> tuple[RegisteredIndex, ...]:
        """Return all registered indexes in deterministic effective-name order."""

    def upsert(self, entry: RegisteredIndex, registry_path: str | None) -> None:
        """Insert or replace a registered index entry."""
