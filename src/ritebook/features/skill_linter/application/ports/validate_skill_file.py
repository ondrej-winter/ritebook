"""Inbound port for validating one explicit skill file."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_linter.application.dtos import (
        ValidateSkillFileCommand,
        ValidateSkillFileResult,
    )


class ValidateSkillFilePort(Protocol):
    """Application boundary for validating one explicit skill file."""

    def execute(self, command: ValidateSkillFileCommand) -> ValidateSkillFileResult:
        """Parse and validate the supplied explicit skill file."""
