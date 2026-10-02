import pytest

from ritebook.features.skill_linter.application.dtos import (
    ParsedSkillHeader,
    SkillValidationIssue,
    SkillValidationReport,
)
from ritebook.features.skill_linter.application.use_cases import ValidateSkillHeaders

NAME_RULE_MESSAGE = (
    "name must be valid kebab-case: 1-64 lowercase ASCII letters, digits, and "
    "hyphens; no leading, trailing, or consecutive hyphens."
)


def test_validation_report_sorts_issues_and_reports_success() -> None:
    report = SkillValidationReport.create(
        validated_skill_count=2,
        issues=[
            SkillValidationIssue(
                skill_file="zeta/SKILL.md",
                message="metadata values must be strings.",
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
        "zeta/SKILL.md: metadata values must be strings.",
    ]


def test_validation_dtos_reject_empty_values() -> None:
    with pytest.raises(ValueError, match="skill file"):
        ParsedSkillHeader(skill_file="", expected_name="alpha", frontmatter={})

    with pytest.raises(ValueError, match="validation message"):
        SkillValidationIssue(skill_file="alpha/SKILL.md", message="")

    with pytest.raises(ValueError, match="count"):
        SkillValidationReport(validated_skill_count=-1)


def test_validate_skill_headers_accepts_minimal_header() -> None:
    report = _validate(
        _valid_frontmatter(name="conventional-commits"),
        expected_name="conventional-commits",
    )

    assert report.succeeded
    assert report.validated_skill_count == 1
    assert report.issues == ()


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("license", ""),
        ("compatibility", "Requires Git."),
        ("metadata", {}),
        ("metadata", {"": ""}),
        ("allowed-tools", ""),
    ],
)
def test_validate_skill_headers_accepts_each_optional_field(
    field_name: str,
    value: object,
) -> None:
    frontmatter = _valid_frontmatter()
    frontmatter[field_name] = value

    report = _validate(frontmatter)

    assert report.succeeded


def test_validate_skill_headers_accepts_all_optional_fields_together() -> None:
    report = _validate(
        {
            "name": "alpha",
            "description": "Validate Agent Skills headers. Use for skill linting.",
            "license": "MIT",
            "compatibility": "Requires Git.",
            "metadata": {"author": "ritebook", "version": "1.0.1"},
            "allowed-tools": "Bash(git:*) Read",
        },
    )

    assert report.succeeded


def test_validate_skill_headers_accepts_compatible_flat_namespaced_metadata() -> None:
    frontmatter = _valid_frontmatter()
    frontmatter["metadata"] = {
        "ritebook.schema-profile": "shelf-v1",
        "version": "1.0.0",
    }

    report = _validate(frontmatter)

    assert report.succeeded


def test_validate_skill_headers_accepts_unicode_description() -> None:
    report = _validate(
        _valid_frontmatter(
            description="Kontroluje dovednosti — použijte při lintování.",
        ),
    )

    assert report.succeeded


@pytest.mark.parametrize("frontmatter", [None, ["name", "alpha"], "name: alpha"])
def test_validate_skill_headers_rejects_non_mapping_frontmatter(
    frontmatter: object,
) -> None:
    report = _validate(frontmatter)

    assert _messages(report) == ["frontmatter must be a mapping."]


def test_validate_skill_headers_rejects_unknown_fields_without_echoing_them() -> None:
    unknown_field = "secret\x1b[31m"
    frontmatter = _valid_frontmatter()
    frontmatter[unknown_field] = "secret value"
    frontmatter["another-secret"] = "another value"

    report = _validate(frontmatter)

    assert _messages(report) == ["frontmatter contains unsupported fields."]
    assert unknown_field not in report.issues[0].message
    assert "secret value" not in report.issues[0].message


def test_validate_skill_headers_rejects_non_string_top_level_key() -> None:
    report = _validate(
        {
            "name": "alpha",
            "description": "Validate skill headers.",
            1: "not a string key",
        },
    )

    assert _messages(report) == ["frontmatter keys must be strings."]


def test_validate_skill_headers_requires_name() -> None:
    frontmatter = _valid_frontmatter()
    del frontmatter["name"]

    report = _validate(frontmatter)

    assert _messages(report) == ["name is required."]


@pytest.mark.parametrize("name", [None, 123, True])
def test_validate_skill_headers_requires_string_name(name: object) -> None:
    report = _validate(_valid_frontmatter(name=name))

    assert _messages(report) == ["name must be a string."]


@pytest.mark.parametrize(
    "name",
    [
        " ",
        "Alpha",
        "alpha_beta",
        "a" * 65,
        "-alpha",
        "alpha-",
        "alpha--beta",
    ],
)
def test_validate_skill_headers_rejects_invalid_names(name: str) -> None:
    report = _validate(_valid_frontmatter(name=name), expected_name=name)

    assert _messages(report) == [NAME_RULE_MESSAGE]


def test_validate_skill_headers_rejects_empty_name() -> None:
    report = _validate(_valid_frontmatter(name=""))

    assert _messages(report) == [
        NAME_RULE_MESSAGE,
        "name must match skill directory name 'alpha'.",
    ]


def test_validate_skill_headers_rejects_name_directory_mismatch() -> None:
    report = _validate(_valid_frontmatter(name="beta"))

    assert _messages(report) == ["name must match skill directory name 'alpha'."]


def test_validate_skill_headers_requires_description() -> None:
    frontmatter = _valid_frontmatter()
    del frontmatter["description"]

    report = _validate(frontmatter)

    assert _messages(report) == ["description is required."]


@pytest.mark.parametrize("description", [None, 123, True])
def test_validate_skill_headers_requires_string_description(
    description: object,
) -> None:
    report = _validate(_valid_frontmatter(description=description))

    assert _messages(report) == ["description must be a string."]


@pytest.mark.parametrize("description", ["", "   ", "\t"])
def test_validate_skill_headers_rejects_blank_description(description: str) -> None:
    report = _validate(_valid_frontmatter(description=description))

    assert _messages(report) == ["description must not be blank."]


def test_validate_skill_headers_rejects_overlong_description() -> None:
    report = _validate(_valid_frontmatter(description="x" * 1025))

    assert _messages(report) == ["description must be at most 1024 characters."]


def test_validate_skill_headers_rejects_description_controls() -> None:
    report = _validate(_valid_frontmatter(description="unsafe\x1b[31m description"))

    assert _messages(report) == [
        "description must not contain terminal control characters.",
    ]


@pytest.mark.parametrize("license_value", [None, 123, True, []])
def test_validate_skill_headers_requires_string_license_when_present(
    license_value: object,
) -> None:
    frontmatter = _valid_frontmatter()
    frontmatter["license"] = license_value

    report = _validate(frontmatter)

    assert _messages(report) == ["license must be a string."]


@pytest.mark.parametrize("compatibility", [None, 123, True, []])
def test_validate_skill_headers_requires_string_compatibility_when_present(
    compatibility: object,
) -> None:
    frontmatter = _valid_frontmatter()
    frontmatter["compatibility"] = compatibility

    report = _validate(frontmatter)

    assert _messages(report) == ["compatibility must be a string."]


@pytest.mark.parametrize("compatibility", ["", "   ", "\t"])
def test_validate_skill_headers_rejects_blank_compatibility(
    compatibility: str,
) -> None:
    frontmatter = _valid_frontmatter()
    frontmatter["compatibility"] = compatibility

    report = _validate(frontmatter)

    assert _messages(report) == ["compatibility must not be blank."]


def test_validate_skill_headers_rejects_overlong_compatibility() -> None:
    frontmatter = _valid_frontmatter()
    frontmatter["compatibility"] = "x" * 501

    report = _validate(frontmatter)

    assert _messages(report) == ["compatibility must be at most 500 characters."]


@pytest.mark.parametrize("metadata", [None, "metadata", 123, True, []])
def test_validate_skill_headers_requires_mapping_metadata_when_present(
    metadata: object,
) -> None:
    frontmatter = _valid_frontmatter()
    frontmatter["metadata"] = metadata

    report = _validate(frontmatter)

    assert _messages(report) == ["metadata must be a mapping."]


def test_validate_skill_headers_rejects_non_string_metadata_key() -> None:
    frontmatter = _valid_frontmatter()
    frontmatter["metadata"] = {1: "value"}

    report = _validate(frontmatter)

    assert _messages(report) == ["metadata keys must be strings."]


@pytest.mark.parametrize(
    "metadata_value",
    [123, True, None, ["value"], {"nested": "value"}],
)
def test_validate_skill_headers_rejects_non_string_metadata_values(
    metadata_value: object,
) -> None:
    frontmatter = _valid_frontmatter()
    frontmatter["metadata"] = {"key": metadata_value}

    report = _validate(frontmatter)

    assert _messages(report) == ["metadata values must be strings."]


@pytest.mark.parametrize("allowed_tools", [None, 123, True, []])
def test_validate_skill_headers_requires_string_allowed_tools_when_present(
    allowed_tools: object,
) -> None:
    frontmatter = _valid_frontmatter()
    frontmatter["allowed-tools"] = allowed_tools

    report = _validate(frontmatter)

    assert _messages(report) == ["allowed-tools must be a string."]


def test_validate_skill_headers_orders_multiple_findings_deterministically() -> None:
    report = ValidateSkillHeaders().execute(
        (
            ParsedSkillHeader(
                skill_file="zeta/SKILL.md",
                expected_name="zeta",
                frontmatter={"unknown": "value"},
            ),
            ParsedSkillHeader(
                skill_file="alpha/SKILL.md",
                expected_name="alpha",
                frontmatter={"name": "alpha", "description": " "},
            ),
        ),
    )

    assert [issue.format() for issue in report.issues] == [
        "alpha/SKILL.md: description must not be blank.",
        "zeta/SKILL.md: description is required.",
        "zeta/SKILL.md: frontmatter contains unsupported fields.",
        "zeta/SKILL.md: name is required.",
    ]


def _validate(
    frontmatter: object,
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


def _valid_frontmatter(
    *,
    name: object = "alpha",
    description: object = "Validate Agent Skills headers.",
) -> dict[object, object]:
    return {"name": name, "description": description}


def _messages(report: SkillValidationReport) -> list[str]:
    return [issue.message for issue in report.issues]
