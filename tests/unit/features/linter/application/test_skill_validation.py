import pytest

from ritebook.features.linter.application.dtos import (
    ParsedSkillHeader,
    SkillValidationIssue,
    SkillValidationReport,
)
from ritebook.features.linter.application.use_cases import ValidateSkillHeaders


def test_validation_report_sorts_issues_and_reports_success() -> None:
    report = SkillValidationReport.create(
        validated_skill_count=2,
        issues=[
            SkillValidationIssue(
                skill_file="zeta/SKILL.md",
                message="metadata is required.",
            ),
            SkillValidationIssue(
                skill_file="alpha/SKILL.md",
                message="name is required.",
            ),
        ],
    )

    assert not report.succeeded
    assert [issue.format() for issue in report.issues] == [
        "alpha/SKILL.md: name is required.",
        "zeta/SKILL.md: metadata is required.",
    ]


def test_validation_dtos_reject_empty_values() -> None:
    with pytest.raises(ValueError, match="skill file"):
        ParsedSkillHeader(skill_file="", expected_name="alpha", frontmatter={})

    with pytest.raises(ValueError, match="validation message"):
        SkillValidationIssue(skill_file="alpha/SKILL.md", message="")

    with pytest.raises(ValueError, match="count"):
        SkillValidationReport(validated_skill_count=-1)


def test_validate_skill_headers_accepts_valid_header() -> None:
    report = ValidateSkillHeaders().execute(
        (
            ParsedSkillHeader(
                skill_file="conventional-commits/SKILL.md",
                expected_name="conventional-commits",
                frontmatter=_valid_frontmatter(name="conventional-commits"),
            ),
        ),
    )

    assert report.succeeded
    assert report.validated_skill_count == 1
    assert report.issues == ()


def test_validate_skill_headers_accepts_structured_dependency_header() -> None:
    description = (
        "Verify browser-facing changes in a real browser using visual checks, "
        "console output, network behavior, accessibility basics, and user-flow "
        "smoke tests. Use when building, debugging, or validating UI behavior "
        "beyond static code and unit tests."
    )
    tool_purpose = (
        "Open the changed application in a real browser and inspect visible "
        "behavior, console output, network activity, and accessibility basics."
    )
    skill_purpose = (
        "Provide implementation-focused UI guidance when designing, building, "
        "or refactoring browser-facing interfaces."
    )

    report = ValidateSkillHeaders().execute(
        (
            ParsedSkillHeader(
                skill_file="browser-runtime-verification/SKILL.md",
                expected_name="browser-runtime-verification",
                frontmatter={
                    "name": "browser-runtime-verification",
                    "description": description,
                    "metadata": {
                        "version": "1.0.4",
                        "dependencies": {
                            "tools": [
                                {
                                    "name": "browser runtime",
                                    "purpose": tool_purpose,
                                    "required": True,
                                },
                            ],
                            "skills": [
                                {
                                    "name": "frontend-ui-engineering",
                                    "purpose": skill_purpose,
                                    "required": False,
                                },
                            ],
                        },
                    },
                },
            ),
        ),
    )

    assert report.succeeded
    assert report.issues == ()


@pytest.mark.parametrize("frontmatter", [None, [], "name: alpha"])
def test_validate_skill_headers_rejects_non_mapping_frontmatter(
    frontmatter: object,
) -> None:
    report = ValidateSkillHeaders().execute(
        (
            ParsedSkillHeader(
                skill_file="alpha/SKILL.md",
                expected_name="alpha",
                frontmatter=frontmatter,
            ),
        ),
    )

    assert _messages(report) == ["frontmatter must be a mapping."]


@pytest.mark.parametrize(
    ("name", "expected_message"),
    [
        (None, "name is required."),
        (123, "name must be a string."),
        ("", "name must be valid kebab-case"),
        ("Uppercase", "name must be valid kebab-case"),
        ("alpha_thing", "name must be valid kebab-case"),
        ("-alpha", "name must be valid kebab-case"),
        ("alpha-", "name must be valid kebab-case"),
        ("alpha--thing", "name must be valid kebab-case"),
        ("a" * 65, "name must be valid kebab-case"),
    ],
)
def test_validate_skill_headers_rejects_missing_or_invalid_names(
    name: object,
    expected_message: str,
) -> None:
    frontmatter = _valid_frontmatter()
    if name is None:
        del frontmatter["name"]
    else:
        frontmatter["name"] = name

    report = _validate(frontmatter, expected_name="alpha")

    assert any(message.startswith(expected_message) for message in _messages(report))


def test_validate_skill_headers_rejects_name_path_mismatch() -> None:
    report = _validate(_valid_frontmatter(name="alpha"), expected_name="beta")

    assert _messages(report) == ["name must match skill directory name 'beta'."]


@pytest.mark.parametrize(
    ("description", "expected_message"),
    [
        (None, "description is required."),
        (123, "description must be a string."),
        ("", "description must not be empty."),
        ("x" * 1025, "description must be at most 1024 characters."),
    ],
)
def test_validate_skill_headers_rejects_missing_or_invalid_description(
    description: object,
    expected_message: str,
) -> None:
    frontmatter = _valid_frontmatter()
    if description is None:
        del frontmatter["description"]
    else:
        frontmatter["description"] = description

    report = _validate(frontmatter)

    assert expected_message in _messages(report)


@pytest.mark.parametrize(
    "control_character",
    ["\n", "\r", "\t", "\x00", "\x1b", "\x7f", "\x85", "\x9f"],
)
def test_validate_skill_headers_rejects_control_characters_in_description(
    control_character: str,
) -> None:
    frontmatter = _valid_frontmatter()
    frontmatter["description"] = f"Safe prefix{control_character}unsafe suffix"

    report = _validate(frontmatter)

    assert _messages(report) == [
        "description must not contain terminal control characters.",
    ]


@pytest.mark.parametrize(
    "description",
    [
        "Příliš žluťoučký kůň.",
        "ブラウザーの動作を検証します。",
        "Verify browser behavior 🔍.",
    ],
)
def test_validate_skill_headers_accepts_readable_unicode_description(
    description: str,
) -> None:
    frontmatter = _valid_frontmatter()
    frontmatter["description"] = description

    report = _validate(frontmatter)

    assert report.succeeded


@pytest.mark.parametrize(
    ("metadata", "expected_messages"),
    [
        (None, ["metadata is required."]),
        ("not a mapping", ["metadata must be a mapping."]),
        ({}, ["metadata.dependencies is required.", "metadata.version is required."]),
        (
            {"version": 1, "dependencies": "not a mapping"},
            [
                "metadata.dependencies must be a mapping.",
                "metadata.version must be a string.",
            ],
        ),
        (
            {"version": "1.0.0", "dependencies": {}},
            [
                "metadata.dependencies.skills is required.",
                "metadata.dependencies.tools is required.",
            ],
        ),
        (
            {
                "version": "1.0.0",
                "dependencies": {"tools": "git", "skills": "testing"},
            },
            [
                "metadata.dependencies.skills must be a list.",
                "metadata.dependencies.tools must be a list.",
            ],
        ),
    ],
)
def test_validate_skill_headers_rejects_missing_or_invalid_metadata(
    metadata: object,
    expected_messages: list[str],
) -> None:
    frontmatter = _valid_frontmatter()
    if metadata is None:
        del frontmatter["metadata"]
    else:
        frontmatter["metadata"] = metadata

    report = _validate(frontmatter)

    assert _messages(report) == expected_messages


@pytest.mark.parametrize(
    ("dependencies", "expected_messages"),
    [
        (
            {"tools": ["git"], "skills": []},
            ["metadata.dependencies.tools[0] must be a mapping."],
        ),
        (
            {"tools": [{}], "skills": []},
            [
                "metadata.dependencies.tools[0].name is required.",
                "metadata.dependencies.tools[0].purpose is required.",
                "metadata.dependencies.tools[0].required is required.",
            ],
        ),
        (
            {
                "tools": [
                    {"name": 123, "purpose": "Run commands.", "required": True},
                ],
                "skills": [
                    {"name": "testing", "purpose": 123, "required": "yes"},
                ],
            },
            [
                "metadata.dependencies.skills[0].purpose must be a string.",
                "metadata.dependencies.skills[0].required must be a boolean.",
                "metadata.dependencies.tools[0].name must be a string.",
            ],
        ),
        (
            {
                "tools": [
                    {"name": "", "purpose": "", "required": False},
                ],
                "skills": [],
            },
            [
                "metadata.dependencies.tools[0].name must not be empty.",
                "metadata.dependencies.tools[0].purpose must not be empty.",
            ],
        ),
    ],
)
def test_validate_skill_headers_rejects_invalid_dependency_entries(
    dependencies: dict[str, object],
    expected_messages: list[str],
) -> None:
    frontmatter = _valid_frontmatter()
    metadata = frontmatter["metadata"]
    assert isinstance(metadata, dict)
    metadata["dependencies"] = dependencies

    report = _validate(frontmatter)

    assert _messages(report) == expected_messages


def _validate(
    frontmatter: dict[str, object],
    *,
    expected_name: str = "alpha",
) -> SkillValidationReport:
    return ValidateSkillHeaders().execute(
        (
            ParsedSkillHeader(
                skill_file="alpha/SKILL.md",
                expected_name=expected_name,
                frontmatter=frontmatter,
            ),
        ),
    )


def _valid_frontmatter(name: str = "alpha") -> dict[str, object]:
    return {
        "name": name,
        "description": "Validate skill metadata.",
        "metadata": {
            "version": "1.0.0",
            "dependencies": {
                "tools": [
                    {
                        "name": "git",
                        "purpose": "Inspect version-control state and changed files.",
                        "required": True,
                    },
                ],
                "skills": [
                    {
                        "name": "git-workflow-and-versioning",
                        "purpose": "Guide safe version-control workflows.",
                        "required": False,
                    },
                ],
            },
        },
    }


def _messages(report: SkillValidationReport) -> list[str]:
    return [issue.message for issue in report.issues]
