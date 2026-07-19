"""Outbound port for comparing installed and upstream skill content."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_contribution.application.dtos import (
        ContributionLockfileEntry,
        ContributionWorkspace,
        SkillChangeComparison,
    )


class SkillChangeDetectorPort(Protocol):
    """Detect local changes and upstream changes for one skill path."""

    def compare(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> SkillChangeComparison:
        """Compare installed, current upstream, and locked skill content."""
