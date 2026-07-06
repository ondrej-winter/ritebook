from ritebook.features.linter.adapters.outbound.publisher_precheck import (
    LinterPublisherPrecheck,
)
from ritebook.features.linter.application.dtos import (
    LintSkillsCommand,
    LintSkillsResult,
    SkillValidationIssue,
)

VALIDATED_SKILL_COUNT = 2


class FakeLinter:
    """Test double for the lint-skills inbound application port."""

    def __init__(self, result: LintSkillsResult) -> None:
        """Store the result to return and commands received by the adapter."""
        self.result = result
        self.commands: list[LintSkillsCommand] = []

    def execute(self, command: LintSkillsCommand) -> LintSkillsResult:
        """Record the command and return the configured result."""
        self.commands.append(command)
        return self.result


def test_linter_publisher_precheck_maps_successful_lint_result() -> None:
    linter = FakeLinter(LintSkillsResult(validated_skill_count=VALIDATED_SKILL_COUNT))

    result = LinterPublisherPrecheck(linter=linter).run_prechecks("skills")

    assert linter.commands == [LintSkillsCommand(skills_root="skills")]
    assert result.succeeded
    assert result.checked_skill_count == VALIDATED_SKILL_COUNT
    assert result.issues == ()


def test_linter_publisher_precheck_maps_lint_issues() -> None:
    linter = FakeLinter(
        LintSkillsResult.create(
            validated_skill_count=1,
            issues=[
                SkillValidationIssue(
                    skill_file="alpha/SKILL.md",
                    message="description is required.",
                ),
            ],
        ),
    )

    result = LinterPublisherPrecheck(linter=linter).run_prechecks("skills")

    assert not result.succeeded
    assert result.checked_skill_count == 1
    assert [issue.format() for issue in result.issues] == [
        "alpha/SKILL.md: description is required.",
    ]
