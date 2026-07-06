import pytest

from ritebook.features.linter.application.dtos import (
    LintSkillsCommand,
    ParsedSkillHeader,
    SkillHeaderDiscoveryResult,
    SkillValidationIssue,
)
from ritebook.features.linter.application.use_cases import (
    LintSkills,
    ValidateSkillHeaders,
)

VALID_DISCOVERED_HEADER_COUNT = 2


class FakeHeaderDiscovery:
    """Test double for the skill header discovery outbound port."""

    def __init__(self, result: SkillHeaderDiscoveryResult) -> None:
        """Store the result to return and roots requested by the use case."""
        self.result = result
        self.discovered_roots: list[str] = []

    def discover_headers(self, skills_root: str) -> SkillHeaderDiscoveryResult:
        """Record the requested root and return configured headers/issues."""
        self.discovered_roots.append(skills_root)
        return self.result


def test_lint_skills_validates_discovered_headers_successfully() -> None:
    discovery = FakeHeaderDiscovery(
        SkillHeaderDiscoveryResult.create(
            headers=[_valid_header("alpha"), _valid_header("zeta")],
            issues=[],
        ),
    )
    use_case = LintSkills(
        header_discovery=discovery,
        header_validator=ValidateSkillHeaders(),
    )

    result = use_case.execute(LintSkillsCommand(skills_root="skills"))

    assert discovery.discovered_roots == ["skills"]
    assert result.succeeded
    assert result.validated_skill_count == VALID_DISCOVERED_HEADER_COUNT
    assert result.issues == ()


def test_lint_skills_succeeds_with_zero_discovered_headers() -> None:
    use_case = LintSkills(
        header_discovery=FakeHeaderDiscovery(
            SkillHeaderDiscoveryResult.create(headers=[], issues=[]),
        ),
        header_validator=ValidateSkillHeaders(),
    )

    result = use_case.execute(LintSkillsCommand(skills_root="empty"))

    assert result.succeeded
    assert result.validated_skill_count == 0


def test_lint_skills_returns_adapter_and_validation_issues_deterministically() -> None:
    discovery = FakeHeaderDiscovery(
        SkillHeaderDiscoveryResult.create(
            headers=[_valid_header("zeta"), _invalid_header("alpha")],
            issues=[
                SkillValidationIssue(
                    skill_file="beta/SKILL.md",
                    message="frontmatter must be valid YAML.",
                ),
            ],
        ),
    )
    use_case = LintSkills(
        header_discovery=discovery,
        header_validator=ValidateSkillHeaders(),
    )

    result = use_case.execute(LintSkillsCommand(skills_root="skills"))

    assert not result.succeeded
    assert result.validated_skill_count == VALID_DISCOVERED_HEADER_COUNT
    assert [issue.format() for issue in result.issues] == [
        "alpha/SKILL.md: description is required.",
        "beta/SKILL.md: frontmatter must be valid YAML.",
    ]


def test_lint_skills_command_rejects_empty_root() -> None:
    with pytest.raises(ValueError, match="skills root"):
        LintSkillsCommand(skills_root="")


def _valid_header(name: str) -> ParsedSkillHeader:
    return ParsedSkillHeader(
        skill_file=f"{name}/SKILL.md",
        expected_name=name,
        frontmatter={
            "name": name,
            "description": f"{name} skill.",
            "metadata": {
                "version": "1.0.0",
                "dependencies": {"tools": [], "skills": []},
            },
        },
    )


def _invalid_header(name: str) -> ParsedSkillHeader:
    return ParsedSkillHeader(
        skill_file=f"{name}/SKILL.md",
        expected_name=name,
        frontmatter={
            "name": name,
            "metadata": {
                "version": "1.0.0",
                "dependencies": {"tools": [], "skills": []},
            },
        },
    )
