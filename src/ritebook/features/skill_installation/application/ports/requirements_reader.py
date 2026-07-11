"""Outbound port for reading parsed installation requirements."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import SkillRequirements


class RequirementsReaderPort(Protocol):
    """Outbound dependency for requirements-file parsing."""

    def read_requirements(self, requirements_file: str) -> SkillRequirements:
        """Return parsed skill requirements for application planning."""
