"""Outbound port for refreshing referenced registered indexes."""

from __future__ import annotations

from typing import Protocol


class IndexRefresherPort(Protocol):
    """Refresh one registered local alias before sync resolution."""

    def refresh(self, name: str, registry_path: str | None) -> None:
        """Refresh one referenced alias or raise a user-facing installation error."""
