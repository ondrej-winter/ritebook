"""Outbound port for cached published index contents."""

from __future__ import annotations

from typing import Protocol


class IndexCachePort(Protocol):
    """Outbound dependency for writing cached index contents."""

    def cached_index_path(self, *, name: str, cache_root: str | None) -> str:
        """Return the cache path for an effective index name."""

    def write_index(self, *, name: str, content: str, cache_root: str | None) -> str:
        """Write cached index contents and return the written path."""
