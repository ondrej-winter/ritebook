import pytest

from ritebook.features.index_registry.application.dtos import (
    AddIndexCommand,
    IndexSourceType,
    PreparedIndexSource,
    PublishedIndex,
    RegisteredIndex,
    UpdateIndexCommand,
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


def test_add_index_command_rejects_empty_source_and_invalid_name() -> None:
    with pytest.raises(ValueError, match="Index source"):
        AddIndexCommand(source="")

    with pytest.raises(ValueError, match="Index name"):
        AddIndexCommand(source="repo", name="Company Skills")


def test_update_index_command_rejects_invalid_name() -> None:
    with pytest.raises(ValueError, match="Index name"):
        UpdateIndexCommand(name="-bad")


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
