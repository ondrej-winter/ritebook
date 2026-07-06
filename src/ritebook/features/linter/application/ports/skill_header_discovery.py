"""Outbound port for discovering parsed skill headers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.linter.application.dtos import (
        SkillHeaderDiscoveryResult,
    )


class SkillHeaderDiscoveryPort(Protocol):
    """Outbound dependency for discovering and parsing skill headers."""

    def discover_headers(self, skills_root: str) -> SkillHeaderDiscoveryResult:
        """Discover parsed skill headers below the supplied skills root."""
