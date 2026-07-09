from datetime import UTC, datetime, timedelta, timezone

import pytest

from ritebook.features.publisher.application.dtos import (
    PublishIndexCommand,
    PublishIndexValidationError,
    SkillPrecheckIssue,
    SkillPrecheckResult,
)
from ritebook.features.publisher.application.use_cases import PublishIndex
from ritebook.features.publisher.domain import SkillCatalog, SkillEntry

DISCOVERED_SKILL_COUNT = 2


class FakeSkillDiscovery:
    """Test double for the skill discovery outbound port."""

    def __init__(self, skills: tuple[SkillEntry, ...]) -> None:
        """Store skills to return and calls made by the use case."""
        self.skills = skills
        self.discovered_roots: list[str] = []

    def discover_skills(self, skills_root: str) -> tuple[SkillEntry, ...]:
        """Record the requested root and return configured skills."""
        self.discovered_roots.append(skills_root)
        return self.skills


class FakeIndexWriter:
    """Test double for the skill index writer outbound port."""

    def __init__(self) -> None:
        """Store catalogs and output paths written by the use case."""
        self.written_catalogs: list[SkillCatalog] = []
        self.output_paths: list[str] = []

    def write_index(self, catalog: SkillCatalog, output_path: str) -> None:
        """Record the catalog and output path supplied by the use case."""
        self.written_catalogs.append(catalog)
        self.output_paths.append(output_path)


class FakePrecheck:
    """Test double for the publisher precheck outbound port."""

    def __init__(self, result: SkillPrecheckResult | None = None) -> None:
        """Store the result to return and calls made by the use case."""
        self.result = result or SkillPrecheckResult(checked_skill_count=0)
        self.checked_roots: list[str] = []

    def run_prechecks(self, skills_root: str) -> SkillPrecheckResult:
        """Record the requested root and return configured precheck result."""
        self.checked_roots.append(skills_root)
        return self.result


def test_publish_index_discovers_writes_and_returns_result() -> None:
    generated_at = datetime(2026, 7, 4, 18, 49, tzinfo=UTC)
    discovery = FakeSkillDiscovery(
        skills=(
            SkillEntry(name="zeta", path="zeta", skill_file="zeta/SKILL.md"),
            SkillEntry(name="alpha", path="alpha", skill_file="alpha/SKILL.md"),
        ),
    )
    writer = FakeIndexWriter()
    precheck = FakePrecheck(SkillPrecheckResult(checked_skill_count=2))
    use_case = PublishIndex(
        skill_discovery=discovery,
        precheck=precheck,
        index_writer=writer,
        clock=lambda: generated_at,
    )

    result = use_case.execute(
        PublishIndexCommand(index_name="company-skills", skills_root="skills"),
    )

    assert precheck.checked_roots == ["skills"]
    assert discovery.discovered_roots == ["skills"]
    assert writer.output_paths == ["ritebook-index.json"]
    assert result.discovered_skill_count == DISCOVERED_SKILL_COUNT
    assert result.output_path == "ritebook-index.json"

    written_catalog = writer.written_catalogs[0]
    assert written_catalog.index_name == "company-skills"
    assert written_catalog.skills_root == "skills"
    assert written_catalog.generated_at == generated_at
    assert [skill.path for skill in written_catalog.skills] == ["alpha", "zeta"]


def test_publish_index_accepts_repository_style_index_name() -> None:
    writer = FakeIndexWriter()
    use_case = PublishIndex(
        skill_discovery=FakeSkillDiscovery(skills=()),
        precheck=FakePrecheck(),
        index_writer=writer,
        clock=lambda: datetime(2026, 7, 4, 18, 49, tzinfo=UTC),
    )

    use_case.execute(
        PublishIndexCommand(
            index_name="ondrej-winter/ritebook-shelf",
            skills_root="skills",
        ),
    )

    assert writer.written_catalogs[0].index_name == "ondrej-winter/ritebook-shelf"


def test_publish_index_writes_empty_catalog() -> None:
    discovery = FakeSkillDiscovery(skills=())
    writer = FakeIndexWriter()
    use_case = PublishIndex(
        skill_discovery=discovery,
        precheck=FakePrecheck(),
        index_writer=writer,
        clock=lambda: datetime(2026, 7, 4, 18, 49, tzinfo=UTC),
    )

    result = use_case.execute(
        PublishIndexCommand(index_name="company-skills", skills_root="."),
    )

    assert result.discovered_skill_count == 0
    assert writer.written_catalogs[0].skills == ()


def test_publish_index_normalizes_generated_at_to_utc() -> None:
    plus_two = timezone(timedelta(hours=2))
    discovery = FakeSkillDiscovery(skills=())
    writer = FakeIndexWriter()
    use_case = PublishIndex(
        skill_discovery=discovery,
        precheck=FakePrecheck(),
        index_writer=writer,
        clock=lambda: datetime(2026, 7, 4, 20, 49, tzinfo=plus_two),
    )

    use_case.execute(
        PublishIndexCommand(index_name="company-skills", skills_root="skills"),
    )

    assert writer.written_catalogs[0].generated_at == datetime(
        2026,
        7,
        4,
        18,
        49,
        tzinfo=UTC,
    )


def test_publish_index_rejects_naive_clock_values() -> None:
    generated_at = datetime(2026, 7, 4, 18, 49, tzinfo=UTC).replace(tzinfo=None)
    use_case = PublishIndex(
        skill_discovery=FakeSkillDiscovery(skills=()),
        precheck=FakePrecheck(),
        index_writer=FakeIndexWriter(),
        clock=lambda: generated_at,
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        use_case.execute(
            PublishIndexCommand(index_name="company-skills", skills_root="skills"),
        )


def test_publish_index_command_rejects_empty_values() -> None:
    with pytest.raises(ValueError, match="skills root"):
        PublishIndexCommand(index_name="company-skills", skills_root="")

    with pytest.raises(ValueError, match="Publish index name"):
        PublishIndexCommand(index_name="Company Skills", skills_root="skills")


def test_publish_index_refuses_to_write_when_validation_fails() -> None:
    discovery = FakeSkillDiscovery(
        skills=(SkillEntry(name="alpha", path="alpha", skill_file="alpha/SKILL.md"),),
    )
    writer = FakeIndexWriter()
    precheck = FakePrecheck(
        SkillPrecheckResult.create(
            checked_skill_count=2,
            issues=[
                SkillPrecheckIssue(
                    skill_file="alpha/SKILL.md",
                    message="description is required.",
                ),
                SkillPrecheckIssue(
                    skill_file="beta/SKILL.md",
                    message="frontmatter must be valid YAML.",
                ),
            ],
        ),
    )
    use_case = PublishIndex(
        skill_discovery=discovery,
        precheck=precheck,
        index_writer=writer,
        clock=lambda: datetime(2026, 7, 4, 18, 49, tzinfo=UTC),
    )

    with pytest.raises(PublishIndexValidationError) as err:
        use_case.execute(
            PublishIndexCommand(index_name="company-skills", skills_root="skills"),
        )

    assert [issue.format() for issue in err.value.issues] == [
        "alpha/SKILL.md: description is required.",
        "beta/SKILL.md: frontmatter must be valid YAML.",
    ]
    assert discovery.discovered_roots == []
    assert writer.written_catalogs == []
    assert writer.output_paths == []
