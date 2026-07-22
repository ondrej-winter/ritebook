"""Validate contribution checkouts through the linter application boundary."""

from pathlib import Path, PurePosixPath

from ritebook.features.linter.application.dtos import LintSkillsCommand
from ritebook.features.linter.application.errors import LinterError
from ritebook.features.linter.application.ports import LintSkillsPort
from ritebook.features.skill_contribution.application.dtos import (
    ContributionLockfileEntry,
    ContributionSkillReference,
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
        """Validate every skill under the contribution catalog root."""
        try:
            result = self._linter.execute(
                LintSkillsCommand(skills_root=_catalog_root(entry, workspace)),
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


def _catalog_root(
    entry: ContributionLockfileEntry,
    workspace: ContributionWorkspace,
) -> str:
    selector = PurePosixPath(
        ContributionSkillReference.parse(entry.requirement).skill_selector,
    )
    skill_path = PurePosixPath(entry.skill_path)
    selector_depth = len(selector.parts)
    if skill_path.parts[-selector_depth:] != selector.parts:
        msg = "Contribution skill path does not match its catalog selector."
        raise SkillContributionValidationError(msg)
    root_parts = skill_path.parts[:-selector_depth]
    return str(Path(workspace.checkout_path).joinpath(*root_parts))
