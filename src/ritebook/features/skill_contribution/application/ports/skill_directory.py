"""Outbound port for copying installed skill content into a workspace."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_contribution.application.dtos import (
        ContributionLockfileEntry,
        ContributionWorkspace,
    )


class SkillDirectoryPort(Protocol):
    """Copy installed skill directories into isolated contribution checkouts."""

    def copy_installed_skill(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> None:
        """Copy installed skill contents into the workspace source skill path."""
