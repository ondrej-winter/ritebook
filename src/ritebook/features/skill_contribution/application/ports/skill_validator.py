"""Outbound port for validating changed contribution skill content."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_contribution.application.dtos import (
        ContributionLockfileEntry,
        ContributionWorkspace,
    )


class SkillValidatorPort(Protocol):
    """Validate changed skills before contribution commits are created."""

    def validate(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> None:
        """Validate changed skill content in the contribution checkout."""
