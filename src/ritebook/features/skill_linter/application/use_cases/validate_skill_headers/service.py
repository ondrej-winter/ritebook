"""Pure application validation for Agent Skill headers."""

from __future__ import annotations

from ritebook.features.skill_linter.application.dtos import (
    ParsedSkillHeader,
    SkillValidationIssue,
    SkillValidationReport,
)

from . import validators


class ValidateSkillHeaders:
    """Validate parsed skill headers against the Agent Skill contract."""

    def execute(
        self,
        headers: tuple[ParsedSkillHeader, ...],
    ) -> SkillValidationReport:
        """Validate parsed headers and return a deterministic report."""
        issues: list[SkillValidationIssue] = []
        for header in headers:
            issues.extend(validators.validate_header(header))

        return SkillValidationReport.create(
            validated_skill_count=len(headers),
            issues=issues,
        )
