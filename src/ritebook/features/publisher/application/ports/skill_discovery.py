"""Outbound port for discovering skills."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.publisher.domain import SkillEntry


class SkillDiscoveryPort(Protocol):
    """Outbound dependency for discovering skill entries."""

    def discover_skills(self, skills_root: str) -> tuple[SkillEntry, ...]:
        """Discover skill entries below the supplied skills root."""
