import pytest

from ritebook.features.index_registry.application.dtos import (
    AddIndexCommand,
    AddIndexResult,
    CachedSkillSummary,
    IndexSourceType,
    ListedIndexSkills,
    ListSkillsCommand,
    ListSkillsResult,
    PreparedIndexSource,
    PublishedIndex,
    RegisteredIndex,
    UpdateIndexCommand,
    UpdateIndexResult,
)


def test_add_index_command_accepts_optional_overrides() -> None:
    command = AddIndexCommand(
        source="git@example.com:company/skills.git",
        name="company-skills",
        force=True,
        registry_path="/tmp/indexes.json",
        cache_root="/tmp/cache",
    )

    assert command.name == "company-skills"
    assert command.force is True


def test_index_registry_dtos_accept_repository_style_index_names() -> None:
    AddIndexCommand(source="repo", name="ondrej-winter/ritebook-shelf")
    UpdateIndexCommand(name="ondrej-winter/ritebook-shelf")
    PublishedIndex(
        published_name="ondrej-winter/ritebook-shelf",
        schema_version=1,
        skill_count=0,
        cacheable_content="{}",
    )
    RegisteredIndex(
        name="ondrej-winter/ritebook-shelf",
        published_name="ondrej-winter/ritebook-shelf",
        source="git@example.com:ondrej-winter/ritebook-shelf.git",
        source_type=IndexSourceType.GIT_URL,
        source_cache_path="/tmp/source-cache",
        cached_index_path="/tmp/cache/indexes/ondrej-winter_ritebook-shelf/ritebook-index.json",
        source_schema_version=1,
        skill_count=1,
        added_at="2026-07-08T18:00:00Z",
        updated_at="2026-07-08T18:00:00Z",
    )
    AddIndexResult(name="ondrej-winter/ritebook-shelf", skill_count=1)
    UpdateIndexResult(name="ondrej-winter/ritebook-shelf", skill_count=1)


def test_add_index_command_rejects_empty_source_and_invalid_name() -> None:
    with pytest.raises(ValueError, match="Index source"):
        AddIndexCommand(source="")

    with pytest.raises(ValueError, match="Index name"):
        AddIndexCommand(source="repo", name="Company Skills")


@pytest.mark.parametrize(
    "name",
    [
        "../repo",
        "/owner/repo",
        "owner/repo/extra",
        "owner/",
        "owner//repo",
        "Owner/repo",
        "owner/repo_name",
    ],
)
def test_add_index_command_rejects_unsafe_repository_style_names(name: str) -> None:
    with pytest.raises(ValueError, match="Index name"):
        AddIndexCommand(source="repo", name=name)


def test_update_index_command_rejects_invalid_name() -> None:
    with pytest.raises(ValueError, match="Index name"):
        UpdateIndexCommand(name="-bad")


def test_list_skills_command_accepts_optional_filter_and_registry_path() -> None:
    command = ListSkillsCommand(
        index_name="ondrej-winter/ritebook-shelf",
        registry_path="/tmp/indexes.json",
    )

    assert command.index_name == "ondrej-winter/ritebook-shelf"
    assert command.registry_path == "/tmp/indexes.json"


def test_list_skills_command_rejects_invalid_filter_and_empty_registry_path() -> None:
    with pytest.raises(ValueError, match="Index name"):
        ListSkillsCommand(index_name="Company Skills")

    with pytest.raises(ValueError, match="Registry path"):
        ListSkillsCommand(registry_path="")


def test_list_skills_result_groups_validated_cached_skill_summaries() -> None:
    skill = CachedSkillSummary(
        name="query-helper",
        path="skills/query-helper",
        skill_file="skills/query-helper/SKILL.md",
        title="Query Helper",
    )
    index = ListedIndexSkills(index_name="data-skills", skills=(skill,))
    result = ListSkillsResult(indexes=(index,))

    assert result.indexes == (index,)
    assert result.indexes[0].skills == (skill,)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        (
            {"name": "", "path": "skills/a", "skill_file": "skills/a/SKILL.md"},
            "Skill name",
        ),
        (
            {"name": "skill-a", "path": "", "skill_file": "skills/a/SKILL.md"},
            "Skill path",
        ),
        ({"name": "skill-a", "path": "skills/a", "skill_file": ""}, "Skill file"),
        (
            {
                "name": "skill-a",
                "path": "skills/a",
                "skill_file": "skills/a/SKILL.md",
                "title": "",
            },
            "Skill title",
        ),
    ],
)
def test_cached_skill_summary_rejects_empty_required_fields(
    kwargs: dict[str, str],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        CachedSkillSummary(**kwargs)


def test_listed_index_skills_rejects_invalid_index_name() -> None:
    with pytest.raises(ValueError, match="Index name"):
        ListedIndexSkills(index_name="Data Skills", skills=())


def test_prepared_git_url_source_requires_cache_path() -> None:
    with pytest.raises(ValueError, match="Source cache path"):
        PreparedIndexSource(
            source="git@example.com:company/skills.git",
            source_type=IndexSourceType.GIT_URL,
            repository_path="/tmp/repo",
        )


def test_prepared_local_source_rejects_cache_path() -> None:
    with pytest.raises(ValueError, match="must not have a source cache path"):
        PreparedIndexSource(
            source="/tmp/repo",
            source_type=IndexSourceType.LOCAL_GIT_REPO,
            repository_path="/tmp/repo",
            source_cache_path="/tmp/cache",
        )


def test_published_index_rejects_invalid_metadata() -> None:
    with pytest.raises(ValueError, match="Published index name"):
        PublishedIndex(
            published_name="Company Skills",
            schema_version=1,
            skill_count=0,
            cacheable_content="{}",
        )

    with pytest.raises(ValueError, match="unsupported index schema_version"):
        PublishedIndex(
            published_name="company-skills",
            schema_version=2,
            skill_count=0,
            cacheable_content="{}",
        )


def test_registered_local_index_rejects_source_cache_path() -> None:
    with pytest.raises(ValueError, match="must not have a source cache path"):
        RegisteredIndex(
            name="company-skills",
            published_name="company-skills",
            source="/tmp/repo",
            source_type=IndexSourceType.LOCAL_GIT_REPO,
            source_cache_path="/tmp/cache",
            cached_index_path="/tmp/cache/index.json",
            source_schema_version=1,
            skill_count=1,
            added_at="2026-07-08T18:00:00Z",
            updated_at="2026-07-08T18:00:00Z",
        )
