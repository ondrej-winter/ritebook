"""Outbound port for copying skill directories into targets."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        InstallableSkill,
        PlannedInstallTarget,
        ResolvedSkillSource,
        StagedSkillTree,
        TargetInspection,
    )


class SkillInstallerPort(Protocol):
    """Outbound dependency for skill directory installation."""

    def plan_target(self, target: str) -> PlannedInstallTarget:
        """Resolve and validate a target without mutating the filesystem."""

    def inspect_target(self, target: PlannedInstallTarget) -> TargetInspection:
        """Inspect one planned target without mutating it."""

    def stage(
        self,
        *,
        source: ResolvedSkillSource,
        skill: InstallableSkill,
        target: PlannedInstallTarget,
    ) -> StagedSkillTree:
        """Stage and hash a complete candidate beside its target."""

    def cleanup_staged(self, staged: StagedSkillTree) -> None:
        """Remove a staged candidate that was not consumed by a transaction."""
