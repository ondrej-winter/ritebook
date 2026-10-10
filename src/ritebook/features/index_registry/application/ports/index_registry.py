"""Outbound port for local index registry metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from ritebook.features.index_registry.application.dtos import RegisteredIndex


class IndexRegistryTransaction(Protocol):
    """One locked registry snapshot with atomic replacement writes."""

    def get(self, name: str) -> RegisteredIndex | None:
        """Return an entry from the locked snapshot."""

    def list(self) -> tuple[RegisteredIndex, ...]:
        """Return the locked snapshot in deterministic alias order."""

    def upsert(self, entry: RegisteredIndex) -> None:
        """Commit one inserted or replaced entry by atomic registry replacement."""


class IndexRegistryPort(Protocol):
    """Outbound dependency for local registry metadata persistence."""

    def get(self, name: str, registry_path: str | None) -> RegisteredIndex | None:
        """Return a registered index by local alias when it exists."""

    def list(self, registry_path: str | None) -> tuple[RegisteredIndex, ...]:
        """Return all registered indexes in deterministic local-alias order."""

    def upsert(self, entry: RegisteredIndex, registry_path: str | None) -> None:
        """Insert or replace a registered index entry."""

    def write_transaction(
        self,
        registry_path: str | None,
    ) -> AbstractContextManager[IndexRegistryTransaction]:
        """Open one bounded exclusive registry transaction."""
