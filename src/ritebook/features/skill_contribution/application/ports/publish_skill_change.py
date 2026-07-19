"""Inbound port for publishing one local skill change upstream."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_contribution.application.dtos import (
        PublishSkillChangeCommand,
        PublishSkillChangeResult,
    )


class PublishSkillChangePort(Protocol):
    """Application boundary for preparing a skill contribution."""

    def execute(self, command: PublishSkillChangeCommand) -> PublishSkillChangeResult:
        """Prepare one installed skill change for upstream review."""
