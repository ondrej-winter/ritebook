"""Outbound port for reading contribution lockfile provenance."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_contribution.application.dtos import (
        ContributionLockfileEntry,
        ContributionSkillReference,
    )


class ContributionLockfilePort(Protocol):
    """Read and resolve publishable entries from a repo-local lockfile."""

    def resolve_entry(
        self,
        reference: ContributionSkillReference,
        lockfile_path: str | None,
    ) -> ContributionLockfileEntry:
        """Resolve exactly one publishable lockfile entry for a reference."""
