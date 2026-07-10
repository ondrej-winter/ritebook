"""Outbound port for reading cached published index skill metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.index_registry.application.dtos import CachedSkillSummary


class CachedIndexReaderPort(Protocol):
    """Outbound dependency for reading local cached index skill entries."""

    def read_skills(self, cached_index_path: str) -> tuple[CachedSkillSummary, ...]:
        """Read validated skill summaries from a cached index path."""
