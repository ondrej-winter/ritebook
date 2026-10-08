"""Outbound port for committed skill-header validation."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_installation.application.dtos import (
        CommittedSkillHeader,
        InstallableSkill,
        ResolvedSkillSource,
    )


class CommittedSkillValidatorPort(Protocol):
    """Validate one selected skill header from a verified source snapshot."""

    def validate(
        self,
        source: ResolvedSkillSource,
        skill: InstallableSkill,
    ) -> CommittedSkillHeader:
        """Return normalized committed header values for the selected skill."""
