"""Outbound port for preparing isolated source workspaces."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_contribution.application.dtos import (
        ContributionLockfileEntry,
        ContributionWorkspace,
    )


class SkillSourceWorkspacePort(Protocol):
    """Prepare and inspect an isolated current-base source workspace."""

    def prepare_workspace(
        self,
        entry: ContributionLockfileEntry,
        contribution_root: str | None,
    ) -> ContributionWorkspace:
        """Prepare the source checkout used for contribution work."""
