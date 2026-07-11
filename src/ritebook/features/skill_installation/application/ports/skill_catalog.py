"""Outbound port for registered index and cached skill metadata."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        InstallableSkill,
        RegisteredSkillIndex,
    )


class SkillCatalogPort(Protocol):
    """Outbound dependency for installation-owned catalog lookup."""

    def get_index(
        self,
        name: str,
        registry_path: str | None,
    ) -> RegisteredSkillIndex | None:
        """Return registered index metadata by effective name when available."""

    def read_skills(self, cached_index_path: str) -> tuple[InstallableSkill, ...]:
        """Return installable skills from a cached index path."""
