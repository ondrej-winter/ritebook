"""Outbound port for publisher prechecks."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.publisher.application.dtos import SkillPrecheckResult


class SkillPrecheckPort(Protocol):
    """Outbound dependency for validating skills before publication."""

    def run_prechecks(self, skills_root: str) -> SkillPrecheckResult:
        """Run publisher prechecks below the supplied skills root."""
