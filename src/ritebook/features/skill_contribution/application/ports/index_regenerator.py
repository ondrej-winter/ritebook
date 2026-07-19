"""Outbound port for regenerating contribution publisher indexes."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_contribution.application.dtos import (
        ContributionLockfileEntry,
        ContributionWorkspace,
    )


class IndexRegeneratorPort(Protocol):
    """Regenerate ritebook-index.json before contribution commits are created."""

    def regenerate_index(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> None:
        """Regenerate the publisher index in the contribution checkout."""
