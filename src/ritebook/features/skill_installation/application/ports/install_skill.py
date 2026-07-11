"""Inbound port for direct skill installation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        InstallSkillCommand,
        InstallSkillResult,
    )


class InstallSkillPort(Protocol):
    """Inbound dependency for installing one selected skill."""

    def execute(self, command: InstallSkillCommand) -> InstallSkillResult:
        """Install one skill and return generated installation metadata."""
