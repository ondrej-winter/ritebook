"""Outbound port for resolving installation source repositories."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        RegisteredSkillIndex,
        ResolvedSkillSource,
    )


class SkillSourcePort(Protocol):
    """Outbound dependency for source repository resolution."""

    def resolve_source(self, index: RegisteredSkillIndex) -> ResolvedSkillSource:
        """Resolve source repository metadata for a registered index."""
