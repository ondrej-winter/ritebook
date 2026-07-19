import pytest

from ritebook.features.linter.application.dtos import (
    LintSkillsCommand,
    LintSkillsResult,
    SkillValidationIssue,
)
from ritebook.features.linter.application.errors import LintSkillsDiscoveryError
from ritebook.features.skill_contribution.adapters.outbound.validation import (
    LinterSkillValidatorAdapter,
)
from ritebook.features.skill_contribution.application.dtos import (
    ContributionLockfileEntry,
    ContributionWorkspace,
)
from ritebook.features.skill_contribution.application.errors import (
    SkillContributionValidationError,
)


class FakeLinter:
    def __init__(
        self,
        *,
        result: LintSkillsResult | None = None,
        failure: Exception | None = None,
    ) -> None:
        self.result = result or LintSkillsResult(validated_skill_count=1)
        self.failure = failure
        self.commands: list[LintSkillsCommand] = []

    def execute(self, command: LintSkillsCommand) -> LintSkillsResult:
        self.commands.append(command)
        if self.failure is not None:
            raise self.failure
        return self.result


def test_validation_adapter_lints_checkout_root() -> None:
    linter = FakeLinter()
    adapter = LinterSkillValidatorAdapter(linter=linter)

    adapter.validate(contribution_entry(), contribution_workspace())

    assert linter.commands == [
        LintSkillsCommand(skills_root="/tmp/contributions/platform-skills-code-review"),
    ]


def test_validation_adapter_converts_lint_issues_without_exposing_issue_details() -> (
    None
):
    expected_message = (
        "skill validation failed with 1 issue; contribution commit was not created"
    )
    linter = FakeLinter(
        result=LintSkillsResult.create(
            validated_skill_count=1,
            issues=[
                SkillValidationIssue(
                    skill_file="skills/code-review/SKILL.md",
                    message="secret skill content is invalid",
                ),
            ],
        ),
    )

    with pytest.raises(
        SkillContributionValidationError,
        match=expected_message,
    ) as exc_info:
        LinterSkillValidatorAdapter(linter=linter).validate(
            contribution_entry(),
            contribution_workspace(),
        )

    assert "secret skill content" not in str(exc_info.value)
    assert "SKILL.md" not in str(exc_info.value)


def test_validation_adapter_converts_linter_errors() -> None:
    expected_message = (
        "skill validation could not be completed; contribution commit was not created"
    )
    linter = FakeLinter(
        failure=LintSkillsDiscoveryError("private checkout details"),
    )

    with pytest.raises(
        SkillContributionValidationError,
        match=expected_message,
    ) as exc_info:
        LinterSkillValidatorAdapter(linter=linter).validate(
            contribution_entry(),
            contribution_workspace(),
        )

    assert "private checkout details" not in str(exc_info.value)


def contribution_entry() -> ContributionLockfileEntry:
    return ContributionLockfileEntry(
        requirement="platform-skills/code-review",
        index_name="platform-skills",
        skill_name="code-review",
        target=".agents/skills/code-review",
        source="git@example.com:example/skills.git",
        source_type="git_url",
        source_revision="abc123",
        skill_path="skills/code-review",
        skill_file="skills/code-review/SKILL.md",
        index_schema_version=1,
    )


def contribution_workspace() -> ContributionWorkspace:
    return ContributionWorkspace(
        checkout_path="/tmp/contributions/platform-skills-code-review",
        source_skill_path="skills/code-review",
        current_base_revision="def456",
        locked_revision="abc123",
        has_usable_origin=True,
    )
