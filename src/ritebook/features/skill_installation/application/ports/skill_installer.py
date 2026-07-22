"""Outbound port for copying skill directories into targets."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        InstallableSkill,
        PlannedInstallTarget,
        ResolvedSkillSource,
    )


class SkillInstallerPort(Protocol):
    """Outbound dependency for skill directory installation."""

    def plan_target(self, target: str) -> PlannedInstallTarget:
        """Resolve and validate a target without mutating the filesystem."""

    def install(
        self,
        *,
        source: ResolvedSkillSource,
        skill: InstallableSkill,
        target: str,
        force: bool,
    ) -> None:
        """Copy a skill directory into the requested target path."""
