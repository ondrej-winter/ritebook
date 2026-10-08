from ritebook.features.skill_linter.application.dtos import (
    ParsedSkillHeader,
    SkillValidationIssue,
    ValidatedSkillFile,
    ValidateSkillFileCommand,
)
from ritebook.features.skill_linter.application.use_cases import (
    ValidateSkillFile,
    ValidateSkillHeaders,
)


class FakeHeaderReader:
    def __init__(
        self,
        result: ParsedSkillHeader | SkillValidationIssue,
    ) -> None:
        self.result = result
        self.calls: list[tuple[str, str]] = []

    def read_header(
        self,
        skill_file: str,
        expected_name: str,
    ) -> ParsedSkillHeader | SkillValidationIssue:
        self.calls.append((skill_file, expected_name))
        return self.result


def test_validate_skill_file_returns_normalized_header_values() -> None:
    reader = FakeHeaderReader(
        ParsedSkillHeader(
            skill_file="/snapshot/skills/code-review/SKILL.md",
            expected_name="code-review",
            frontmatter={
                "name": "code-review",
                "description": "  Helps review code.  ",
            },
        ),
    )
    use_case = ValidateSkillFile(
        header_reader=reader,
        header_validator=ValidateSkillHeaders(),
    )

    result = use_case.execute(
        ValidateSkillFileCommand(
            skill_file="/snapshot/skills/code-review/SKILL.md",
            expected_name="code-review",
        ),
    )

    assert result.succeeded
    assert result.validated_skill == ValidatedSkillFile(
        name="code-review",
        description="Helps review code.",
    )
    assert result.issues == ()
    assert reader.calls == [
        ("/snapshot/skills/code-review/SKILL.md", "code-review"),
    ]


def test_validate_skill_file_returns_parser_issue_without_header_validation() -> None:
    issue = SkillValidationIssue(
        skill_file="/snapshot/skills/code-review/SKILL.md",
        message="skill file must be readable UTF-8 text.",
    )
    use_case = ValidateSkillFile(
        header_reader=FakeHeaderReader(issue),
        header_validator=ValidateSkillHeaders(),
    )

    result = use_case.execute(
        ValidateSkillFileCommand(
            skill_file="/snapshot/skills/code-review/SKILL.md",
            expected_name="code-review",
        ),
    )

    assert not result.succeeded
    assert result.validated_skill is None
    assert result.issues == (issue,)


def test_validate_skill_file_returns_header_validation_issues() -> None:
    use_case = ValidateSkillFile(
        header_reader=FakeHeaderReader(
            ParsedSkillHeader(
                skill_file="/snapshot/skills/code-review/SKILL.md",
                expected_name="code-review",
                frontmatter={
                    "name": "other-skill",
                    "description": "Helps review code.",
                },
            ),
        ),
        header_validator=ValidateSkillHeaders(),
    )

    result = use_case.execute(
        ValidateSkillFileCommand(
            skill_file="/snapshot/skills/code-review/SKILL.md",
            expected_name="code-review",
        ),
    )

    assert not result.succeeded
    assert result.validated_skill is None
    assert [issue.message for issue in result.issues] == [
        "name must match skill directory name 'code-review'.",
    ]
