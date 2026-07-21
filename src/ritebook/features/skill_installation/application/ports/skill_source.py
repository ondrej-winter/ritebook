"""Outbound port for resolving installation source repositories."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from contextlib import AbstractContextManager

    from ritebook.features.skill_installation.application.dtos import (
        RegisteredSkillIndex,
        ResolvedSkillSource,
    )


class SkillSourcePort(Protocol):
    """Outbound dependency for source repository resolution."""

    def open_source(
        self,
        index: RegisteredSkillIndex,
    ) -> AbstractContextManager[ResolvedSkillSource]:
        """Verify and open a temporary snapshot of the registered source commit."""
