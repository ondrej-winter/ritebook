"""Outbound port for cached published index contents."""

from __future__ import annotations

from typing import Protocol


class IndexCachePort(Protocol):
    """Outbound dependency for writing cached index contents."""

    def cached_index_path(
        self,
        *,
        name: str,
        index_digest: str,
        cache_root: str | None,
        registry_path: str | None = None,
    ) -> str:
        """Return the immutable cache path for validated index contents."""

    def write_index(  # noqa: PLR0913
        self,
        *,
        name: str,
        content: bytes,
        index_digest: str,
        cache_root: str | None,
        preserve_path: str | None,
        registry_path: str | None = None,
    ) -> str:
        """Write an immutable cache generation and return its path."""

    def discard_index(
        self,
        *,
        name: str,
        cached_index_path: str,
        cache_root: str | None,
        registry_path: str | None = None,
    ) -> None:
        """Remove an unreferenced cache generation when it is adapter-owned."""
