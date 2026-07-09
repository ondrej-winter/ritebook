from datetime import UTC, datetime

import pytest

from ritebook.features.publisher.domain import SkillCatalog, SkillEntry


def test_skill_entry_represents_discovered_skill() -> None:
    entry = SkillEntry(
        name="example-skill",
        path="nested/example-skill",
        skill_file="nested/example-skill/SKILL.md",
        title="Example Skill",
    )

    assert entry.name == "example-skill"
    assert entry.path == "nested/example-skill"
    assert entry.skill_file == "nested/example-skill/SKILL.md"
    assert entry.title == "Example Skill"


def test_skill_entry_allows_omitted_title() -> None:
    entry = SkillEntry(
        name="untitled-skill",
        path="untitled-skill",
        skill_file="untitled-skill/SKILL.md",
    )

    assert entry.title is None


def test_skill_entry_rejects_absolute_paths() -> None:
    with pytest.raises(ValueError, match="relative"):
        SkillEntry(
            name="example-skill",
            path="/example-skill",
            skill_file="example-skill/SKILL.md",
        )


def test_skill_entry_rejects_platform_specific_path_separators() -> None:
    with pytest.raises(ValueError, match="POSIX-style"):
        SkillEntry(
            name="example-skill",
            path="example-skill",
            skill_file="example-skill\\SKILL.md",
        )


def test_skill_catalog_sorts_entries_by_relative_path() -> None:
    catalog = SkillCatalog.create(
        index_name="company-skills",
        generated_at=datetime(2026, 7, 4, 18, 49, tzinfo=UTC),
        skills_root=".",
        skills=[
            SkillEntry(
                name="zeta",
                path="zeta",
                skill_file="zeta/SKILL.md",
            ),
            SkillEntry(
                name="alpha",
                path="alpha",
                skill_file="alpha/SKILL.md",
            ),
        ],
    )

    assert [skill.path for skill in catalog.skills] == ["alpha", "zeta"]


def test_skill_catalog_exposes_schema_version_generated_at_and_root() -> None:
    generated_at = datetime(2026, 7, 4, 18, 49, tzinfo=UTC)

    catalog = SkillCatalog.create(
        index_name="company-skills",
        generated_at=generated_at,
        skills_root="skills",
        skills=(),
    )

    assert catalog.schema_version == 1
    assert catalog.index_name == "company-skills"
    assert catalog.generated_at == generated_at
    assert catalog.skills_root == "skills"
    assert catalog.skills == ()


def test_skill_catalog_accepts_repository_style_index_name() -> None:
    catalog = SkillCatalog.create(
        index_name="ondrej-winter/ritebook-shelf",
        generated_at=datetime(2026, 7, 4, 18, 49, tzinfo=UTC),
        skills_root="skills",
        skills=(),
    )

    assert catalog.index_name == "ondrej-winter/ritebook-shelf"


def test_skill_catalog_requires_valid_index_name() -> None:
    with pytest.raises(ValueError, match="Catalog index name"):
        SkillCatalog.create(
            index_name="Company Skills",
            generated_at=datetime(2026, 7, 4, 18, 49, tzinfo=UTC),
            skills_root="skills",
            skills=(),
        )


def test_skill_catalog_requires_timezone_aware_generated_at() -> None:
    generated_at = datetime(2026, 7, 4, 18, 49, tzinfo=UTC).replace(tzinfo=None)

    with pytest.raises(ValueError, match="timezone-aware"):
        SkillCatalog.create(
            index_name="company-skills",
            generated_at=generated_at,
            skills_root="skills",
            skills=(),
        )
