import pytest

from ritebook.features.skill_linter.application.dtos import (
    LintSkillsCommand,
    LintSkillsResult,
    ParsedSkillHeader,
    SkillHeaderDiscoveryResult,
    SkillValidationIssue,
    ValidatedSkill,
)
from ritebook.features.skill_linter.application.use_cases import (
    LintSkills,
    ValidateSkillHeaders,
)

DISCOVERED_SKILL_COUNT = 2


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
            discovered_skill_count=DISCOVERED_SKILL_COUNT,
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
    assert result.discovered_skill_count == DISCOVERED_SKILL_COUNT
    assert result.issues == ()
    assert result.validated_skills == (
        ValidatedSkill(
            path="alpha",
            name="alpha",
            skill_file="alpha/SKILL.md",
            description="alpha skill.",
        ),
        ValidatedSkill(
            path="zeta",
            name="zeta",
            skill_file="zeta/SKILL.md",
            description="zeta skill.",
        ),
    )


def test_lint_skills_succeeds_with_zero_discovered_headers() -> None:
    use_case = LintSkills(
        header_discovery=FakeHeaderDiscovery(
            SkillHeaderDiscoveryResult.create(
                discovered_skill_count=0,
                headers=[],
                issues=[],
            ),
        ),
        header_validator=ValidateSkillHeaders(),
    )

    result = use_case.execute(LintSkillsCommand(skills_root="empty"))

    assert result.succeeded
    assert result.discovered_skill_count == 0
    assert result.validated_skills == ()


def test_lint_skills_snapshot_uses_trimmed_description() -> None:
    header = _valid_header("alpha")
    header = ParsedSkillHeader(
        skill_file=header.skill_file,
        expected_name=header.expected_name,
        frontmatter={
            "name": "alpha",
            "description": "  alpha skill.  ",
        },
    )
    use_case = LintSkills(
        header_discovery=FakeHeaderDiscovery(
            SkillHeaderDiscoveryResult.create(
                discovered_skill_count=1,
                headers=[header],
                issues=[],
            ),
        ),
        header_validator=ValidateSkillHeaders(),
    )

    result = use_case.execute(LintSkillsCommand(skills_root="skills"))

    assert result.validated_skills[0].description == "alpha skill."


def test_lint_skills_returns_adapter_and_validation_issues_deterministically() -> None:
    discovery = FakeHeaderDiscovery(
        SkillHeaderDiscoveryResult.create(
            discovered_skill_count=3,
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
    assert result.discovered_skill_count == 3
    assert result.validated_skills == ()
    assert [issue.format() for issue in result.issues] == [
        "alpha/SKILL.md: description is required.",
        "beta/SKILL.md: frontmatter must be valid YAML.",
    ]


def test_lint_skills_command_rejects_empty_root() -> None:
    with pytest.raises(ValueError, match="skills root"):
        LintSkillsCommand(skills_root="")


def test_lint_result_and_discovery_result_reject_negative_counts() -> None:
    with pytest.raises(ValueError, match="Discovered skill count"):
        SkillHeaderDiscoveryResult(discovered_skill_count=-1)

    with pytest.raises(ValueError, match="Discovered skill count"):
        LintSkillsResult(discovered_skill_count=-1)


def test_successful_lint_result_requires_snapshot_count_to_match() -> None:
    with pytest.raises(ValueError, match="count must match validated skills"):
        LintSkillsResult(discovered_skill_count=1)


def _valid_header(name: str) -> ParsedSkillHeader:
    return ParsedSkillHeader(
        skill_file=f"{name}/SKILL.md",
        expected_name=name,
        frontmatter={
            "name": name,
            "description": f"{name} skill.",
        },
    )


def _invalid_header(name: str) -> ParsedSkillHeader:
    return ParsedSkillHeader(
        skill_file=f"{name}/SKILL.md",
        expected_name=name,
        frontmatter={
            "name": name,
        },
    )
