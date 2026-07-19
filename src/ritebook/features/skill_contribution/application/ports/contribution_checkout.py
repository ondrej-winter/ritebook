"""Outbound port for branch and commit operations in contribution checkouts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_contribution.application.dtos import (
        ContributionLockfileEntry,
        ContributionWorkspace,
        PreparedContribution,
    )


class ContributionCheckoutPort(Protocol):
    """Create contribution branches and commits in isolated checkouts."""

    def prepare_branch(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> str:
        """Create or reset the contribution branch and return its name."""

    def commit_changes(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
        branch_name: str,
    ) -> PreparedContribution:
        """Stage expected files, create a commit, and return contribution metadata."""
