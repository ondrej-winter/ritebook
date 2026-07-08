"""Outbound port for preparing Git index sources."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.index_registry.application.dtos import PreparedIndexSource


class GitSourcePort(Protocol):
    """Outbound dependency for Git URL and local Git repository sources."""

    def prepare_source(
        self,
        source: str,
        cache_root: str | None,
    ) -> PreparedIndexSource:
        """Prepare a user-supplied source for initial index reading."""

    def refresh_source(
        self,
        *,
        source: str,
        source_cache_path: str | None,
        cache_root: str | None,
    ) -> PreparedIndexSource:
        """Refresh or re-open a remembered source for update-index."""
