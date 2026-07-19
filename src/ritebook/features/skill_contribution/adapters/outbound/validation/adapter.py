"""Validate contribution checkouts through the linter application boundary."""

from ritebook.features.linter.application.dtos import LintSkillsCommand
from ritebook.features.linter.application.errors import LinterError
from ritebook.features.linter.application.ports import LintSkillsPort
from ritebook.features.skill_contribution.application.dtos import (
    ContributionLockfileEntry,
    ContributionWorkspace,
)
from ritebook.features.skill_contribution.application.errors import (
    SkillContributionValidationError,
)
from ritebook.features.skill_contribution.application.ports import SkillValidatorPort


class LinterSkillValidatorAdapter(SkillValidatorPort):
    """Validate contribution content by delegating to the linter use case."""

    def __init__(self, *, linter: LintSkillsPort) -> None:
        """Initialize the adapter with the published linter boundary."""
        self._linter = linter

    def validate(
        self,
        entry: ContributionLockfileEntry,
        workspace: ContributionWorkspace,
    ) -> None:
        """Validate every skill under the contribution checkout root."""
        del entry
        try:
            result = self._linter.execute(
                LintSkillsCommand(skills_root=workspace.checkout_path),
            )
        except LinterError as err:
            message = (
                "skill validation could not be completed; "
                "contribution commit was not created"
            )
            raise SkillContributionValidationError(message) from err

        if result.issues:
            issue_count = len(result.issues)
            issue_label = "issue" if issue_count == 1 else "issues"
            message = (
                f"skill validation failed with {issue_count} {issue_label}; "
                "contribution commit was not created"
            )
            raise SkillContributionValidationError(message)
