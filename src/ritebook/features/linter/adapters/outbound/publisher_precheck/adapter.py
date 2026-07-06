"""Adapter that exposes linter validation as publisher prechecks."""

from ritebook.features.linter.application.dtos import LintSkillsCommand
from ritebook.features.linter.application.ports import LintSkillsPort
from ritebook.features.publisher.application.dtos import (
    SkillPrecheckIssue,
    SkillPrecheckResult,
)


class LinterPublisherPrecheck:
    """Run publisher prechecks by delegating to the linter application port."""

    def __init__(self, *, linter: LintSkillsPort) -> None:
        """Initialize the adapter with the published linter boundary."""
        self._linter = linter

    def run_prechecks(self, skills_root: str) -> SkillPrecheckResult:
        """Run linter validation and map its report to publisher precheck DTOs."""
        result = self._linter.execute(LintSkillsCommand(skills_root=skills_root))
        return SkillPrecheckResult.create(
            checked_skill_count=result.validated_skill_count,
            issues=[
                SkillPrecheckIssue(
                    skill_file=issue.skill_file,
                    message=issue.message,
                )
                for issue in result.issues
            ],
        )
