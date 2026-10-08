"""Outbound port for reading one parsed skill header."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from ritebook.features.skill_linter.application.dtos import (
        ParsedSkillHeader,
        SkillValidationIssue,
    )


class SkillHeaderReaderPort(Protocol):
    """Outbound dependency for parsing one explicit skill file."""

    def read_header(
        self,
        skill_file: str,
        expected_name: str,
    ) -> ParsedSkillHeader | SkillValidationIssue:
        """Read one parsed header or return one path-scoped parsing issue."""
