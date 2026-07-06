"""Inbound port for skill linting."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_catalog.application.dtos import (
        LintSkillsCommand,
        LintSkillsResult,
    )


class LintSkillsPort(Protocol):
    """Application boundary for validating skill headers."""

    def execute(self, command: LintSkillsCommand) -> LintSkillsResult:
        """Validate skill headers for the supplied command."""
