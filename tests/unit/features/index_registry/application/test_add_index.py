from datetime import UTC, datetime

import pytest

from ritebook.features.index_registry.application.dtos import (
    AddIndexCommand,
    IndexSourceType,
    PreparedIndexSource,
)
from ritebook.features.index_registry.application.errors import DuplicateIndexNameError
from ritebook.features.index_registry.application.use_cases import AddIndex

from .fakes import (
    FakeCache,
    FakeGitSource,
    FakeIndexReader,
    FakeRegistry,
    registered_index,
)


def test_add_index_registers_git_url_source_with_published_name() -> None:
    git_source = FakeGitSource()
    reader = FakeIndexReader()
    registry = FakeRegistry()
    cache = FakeCache()
    use_case = AddIndex(
        git_source=git_source,
        index_reader=reader,
        registry=registry,
        cache=cache,
        clock=lambda: datetime(2026, 7, 8, 18, 0, tzinfo=UTC),
    )

    result = use_case.execute(
        AddIndexCommand(
            source="git@example.com:company/skills.git",
            registry_path="/tmp/indexes.json",
            cache_root="/tmp/cache",
        ),
    )

    assert result.name == "company-skills"
    assert result.skill_count == 2
    assert git_source.prepare_calls == [
        ("git@example.com:company/skills.git", "/tmp/cache"),
    ]
    assert reader.read_contents == [b'{"schema_version":1}\n']
    assert cache.write_calls == [
        ("company-skills", '{"schema_version":1}\n', "/tmp/cache"),
    ]
    entry = registry.entries["company-skills"]
    assert entry.source_type is IndexSourceType.GIT_URL
    assert entry.source_revision == "a" * 40
    assert entry.index_digest == f"sha256:{'b' * 64}"
    assert entry.added_at == "2026-07-08T18:00:00Z"
    assert registry.upsert_calls[0][1] == "/tmp/indexes.json"


def test_add_index_uses_local_alias_without_changing_published_name() -> None:
    registry = FakeRegistry()
    cache = FakeCache()
    use_case = AddIndex(
        git_source=FakeGitSource(),
        index_reader=FakeIndexReader(),
        registry=registry,
        cache=cache,
        clock=lambda: datetime(2026, 7, 8, 18, 0, tzinfo=UTC),
    )

    result = use_case.execute(
        AddIndexCommand(source="repo", alias="platform-skills"),
    )

    assert result.name == "platform-skills"
    assert registry.entries["platform-skills"].published_name == "company-skills"
    assert cache.write_calls[0][0] == "platform-skills"


def test_add_index_registers_local_git_repository_source() -> None:
    git_source = FakeGitSource(
        PreparedIndexSource(
            source="/repos/skills",
            source_type=IndexSourceType.LOCAL_GIT_REPO,
            repository_path="/repos/skills",
            source_revision="a" * 40,
            index_content=b'{"schema_version":1}\n',
        ),
    )
    registry = FakeRegistry()
    use_case = AddIndex(
        git_source=git_source,
        index_reader=FakeIndexReader(),
        registry=registry,
        cache=FakeCache(),
        clock=lambda: datetime(2026, 7, 8, 18, 0, tzinfo=UTC),
    )

    use_case.execute(AddIndexCommand(source="/repos/skills"))

    entry = registry.entries["company-skills"]
    assert entry.source_type is IndexSourceType.LOCAL_GIT_REPO
    assert entry.source_revision == "a" * 40
    assert entry.index_digest == f"sha256:{'b' * 64}"
    assert entry.source_cache_path is None


def test_add_index_refuses_duplicate_without_force() -> None:
    use_case = AddIndex(
        git_source=FakeGitSource(),
        index_reader=FakeIndexReader(),
        registry=FakeRegistry([registered_index()]),
        cache=FakeCache(),
        clock=lambda: datetime(2026, 7, 8, 18, 0, tzinfo=UTC),
    )

    with pytest.raises(DuplicateIndexNameError, match="use --force"):
        use_case.execute(AddIndexCommand(source="repo"))


def test_add_index_replaces_duplicate_with_force() -> None:
    registry = FakeRegistry([registered_index(skill_count=1)])
    use_case = AddIndex(
        git_source=FakeGitSource(),
        index_reader=FakeIndexReader(),
        registry=registry,
        cache=FakeCache(),
        clock=lambda: datetime(2026, 7, 8, 18, 0, tzinfo=UTC),
    )

    result = use_case.execute(AddIndexCommand(source="repo", force=True))

    assert result.skill_count == 2
    assert registry.entries["company-skills"].skill_count == 2


def test_add_index_rejects_naive_clock_values() -> None:
    use_case = AddIndex(
        git_source=FakeGitSource(),
        index_reader=FakeIndexReader(),
        registry=FakeRegistry(),
        cache=FakeCache(),
        clock=lambda: datetime(2026, 7, 8, 18, 0),
    )

    with pytest.raises(ValueError, match="timezone-aware"):
        use_case.execute(AddIndexCommand(source="repo"))
