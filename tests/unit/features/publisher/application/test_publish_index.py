from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest

from ritebook.features.publisher.application.dtos import (
    PublishIndexCommand,
    PublishIndexValidationError,
    SkillPrecheckIssue,
    SkillPrecheckResult,
)
from ritebook.features.publisher.application.errors import PublishIndexDiscoveryError
from ritebook.features.publisher.application.use_cases import PublishIndex
from ritebook.features.publisher.domain import SkillCatalog, SkillEntry

DISCOVERED_SKILL_COUNT = 2


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


def test_publish_index_writes_exact_validated_snapshot_and_returns_result() -> None:
    generated_at = datetime(2026, 7, 4, 18, 49, tzinfo=UTC)
    validated_skills = (
        SkillEntry(
            name="zeta",
            path="zeta",
            skill_file="zeta/SKILL.md",
            description="Zeta skill.",
        ),
        SkillEntry(
            name="alpha",
            path="alpha",
            skill_file="alpha/SKILL.md",
            description="Alpha skill.",
        ),
    )
    writer = FakeIndexWriter()
    precheck = FakePrecheck(
        SkillPrecheckResult(
            checked_skill_count=2,
            skills=validated_skills,
        ),
    )
    use_case = PublishIndex(
        precheck=precheck,
        index_writer=writer,
        clock=lambda: generated_at,
    )

    result = use_case.execute(
        PublishIndexCommand(
            index_name="company-skills",
            skills_root="/repo/skills",
            published_skills_root="skills",
        ),
    )

    assert precheck.checked_roots == ["/repo/skills"]
    assert writer.output_paths == ["ritebook-index.json"]
    assert result.discovered_skill_count == DISCOVERED_SKILL_COUNT
    assert result.output_path == "ritebook-index.json"

    written_catalog = writer.written_catalogs[0]
    assert written_catalog.index_name == "company-skills"
    assert written_catalog.skills_root == "skills"
    assert written_catalog.generated_at == generated_at
    assert [skill.path for skill in written_catalog.skills] == ["alpha", "zeta"]


def test_publish_index_rejects_slash_separated_index_name() -> None:
    writer = FakeIndexWriter()
    use_case = PublishIndex(
        precheck=FakePrecheck(),
        index_writer=writer,
        clock=lambda: datetime(2026, 7, 4, 18, 49, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="Published index name"):
        use_case.execute(
            PublishIndexCommand(
                index_name="ondrej-winter/ritebook-shelf",
                skills_root="skills",
                published_skills_root="skills",
            ),
        )

    assert writer.written_catalogs == []


def test_publish_index_writes_empty_catalog() -> None:
    writer = FakeIndexWriter()
    use_case = PublishIndex(
        precheck=FakePrecheck(),
        index_writer=writer,
        clock=lambda: datetime(2026, 7, 4, 18, 49, tzinfo=UTC),
    )

    result = use_case.execute(
        PublishIndexCommand(
            index_name="company-skills",
            skills_root="/repo",
            published_skills_root=".",
        ),
    )

    assert result.discovered_skill_count == 0
    assert writer.written_catalogs[0].skills == ()


def test_publish_index_stores_explicit_portable_catalog_root_for_absolute_scan_root(
    tmp_path: Path,
) -> None:
    absolute_skills_root = str(tmp_path / "skills")
    writer = FakeIndexWriter()
    use_case = PublishIndex(
        precheck=FakePrecheck(),
        index_writer=writer,
        clock=lambda: datetime(2026, 7, 4, 18, 49, tzinfo=UTC),
    )

    use_case.execute(
        PublishIndexCommand(
            index_name="company-skills",
            skills_root=absolute_skills_root,
            published_skills_root="skills",
        ),
    )

    assert writer.written_catalogs[0].skills_root == "skills"


def test_publish_index_normalizes_generated_at_to_utc() -> None:
    plus_two = timezone(timedelta(hours=2))
    writer = FakeIndexWriter()
    use_case = PublishIndex(
        precheck=FakePrecheck(),
        index_writer=writer,
        clock=lambda: datetime(2026, 7, 4, 20, 49, tzinfo=plus_two),
    )

    use_case.execute(
        PublishIndexCommand(
            index_name="company-skills",
            skills_root="skills",
            published_skills_root="skills",
        ),
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
        precheck=FakePrecheck(),
        index_writer=FakeIndexWriter(),
        clock=lambda: generated_at,
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        use_case.execute(
            PublishIndexCommand(
                index_name="company-skills",
                skills_root="skills",
                published_skills_root="skills",
            ),
        )


def test_successful_precheck_requires_snapshot_count_to_match() -> None:
    with pytest.raises(ValueError, match="count must match validated skills"):
        SkillPrecheckResult(checked_skill_count=1)


def test_publish_index_command_rejects_empty_values() -> None:
    with pytest.raises(ValueError, match="skills root"):
        PublishIndexCommand(
            index_name="company-skills",
            skills_root="",
            published_skills_root=".",
        )

    with pytest.raises(ValueError, match="Published index name"):
        PublishIndexCommand(
            index_name="Company Skills",
            skills_root="skills",
            published_skills_root="skills",
        )

    with pytest.raises(ValueError, match="Published skills root"):
        PublishIndexCommand(
            index_name="company-skills",
            skills_root="skills",
            published_skills_root="",
        )


def test_publish_index_refuses_to_write_when_validation_fails() -> None:
    writer = FakeIndexWriter()
    precheck = FakePrecheck(
        SkillPrecheckResult.create(
            checked_skill_count=3,
            issues=[
                SkillPrecheckIssue(
                    skill_file="alpha/SKILL.md",
                    message="frontmatter contains unsupported fields.",
                ),
                SkillPrecheckIssue(
                    skill_file="beta/SKILL.md",
                    message="compatibility must not be blank.",
                ),
                SkillPrecheckIssue(
                    skill_file="gamma/SKILL.md",
                    message="metadata values must be strings.",
                ),
            ],
        ),
    )
    use_case = PublishIndex(
        precheck=precheck,
        index_writer=writer,
        clock=lambda: datetime(2026, 7, 4, 18, 49, tzinfo=UTC),
    )

    with pytest.raises(PublishIndexValidationError) as err:
        use_case.execute(
            PublishIndexCommand(
                index_name="company-skills",
                skills_root="skills",
                published_skills_root="skills",
            ),
        )

    assert [issue.format() for issue in err.value.issues] == [
        "alpha/SKILL.md: frontmatter contains unsupported fields.",
        "beta/SKILL.md: compatibility must not be blank.",
        "gamma/SKILL.md: metadata values must be strings.",
    ]
    assert writer.written_catalogs == []
    assert writer.output_paths == []


def test_publish_index_refuses_to_write_structurally_invalid_discovery() -> None:
    invalid_skills = (
        SkillEntry(
            name="quality",
            path="quality",
            skill_file="quality/SKILL.md",
            description="Quality skill.",
        ),
        SkillEntry(
            name="code-review",
            path="quality/code-review",
            skill_file="quality/code-review/SKILL.md",
            description="Code review skill.",
        ),
    )
    writer = FakeIndexWriter()
    use_case = PublishIndex(
        precheck=FakePrecheck(
            SkillPrecheckResult(checked_skill_count=2, skills=invalid_skills),
        ),
        index_writer=writer,
        clock=lambda: datetime(2026, 7, 4, 18, 49, tzinfo=UTC),
    )

    with pytest.raises(PublishIndexDiscoveryError, match="both a root skill") as err:
        use_case.execute(
            PublishIndexCommand(
                index_name="company-skills",
                skills_root="skills",
                published_skills_root="skills",
            ),
        )

    assert err.value.__cause__ is not None
    assert writer.written_catalogs == []
    assert writer.output_paths == []
