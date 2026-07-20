from datetime import UTC, datetime

import pytest

from ritebook.features.index_registry.application.dtos import (
    IndexSourceType,
    PreparedIndexSource,
    PublishedIndex,
    UpdateIndexCommand,
    UpdateIndexResult,
)
from ritebook.features.index_registry.application.errors import (
    InvalidPublishedIndexError,
    UnknownIndexNameError,
)
from ritebook.features.index_registry.application.use_cases import UpdateIndex

from .fakes import (
    FailingIndexReader,
    FakeCache,
    FakeGitSource,
    FakeIndexReader,
    FakeRegistry,
    registered_index,
)


def test_update_index_refreshes_git_url_source() -> None:
    registry = FakeRegistry([registered_index()])
    cache = FakeCache()
    git_source = FakeGitSource()
    use_case = UpdateIndex(
        git_source=git_source,
        index_reader=FakeIndexReader(
            PublishedIndex(
                published_name="company-skills",
                schema_version=1,
                skill_count=3,
                cacheable_content='{"schema_version":1,"skills":[]}\n',
            ),
        ),
        registry=registry,
        cache=cache,
        clock=lambda: datetime(2026, 7, 8, 19, 0, tzinfo=UTC),
    )

    result = use_case.execute(
        UpdateIndexCommand(
            name="company-skills",
            registry_path="/tmp/indexes.json",
            cache_root="/tmp/cache",
        ),
    )

    assert result.name == "company-skills"
    assert result.skill_count == 3
    assert git_source.refresh_calls == [
        ("git@example.com:company/skills.git", "/cache/git/source-id", "/tmp/cache"),
    ]
    assert cache.write_calls == [
        ("company-skills", '{"schema_version":1,"skills":[]}\n', "/tmp/cache"),
    ]
    entry = registry.entries["company-skills"]
    assert entry.added_at == "2026-07-08T18:00:00Z"
    assert entry.updated_at == "2026-07-08T19:00:00Z"


def test_update_index_refreshes_local_git_repository_source() -> None:
    registry = FakeRegistry(
        [
            registered_index(
                source="/repos/skills",
                source_type=IndexSourceType.LOCAL_GIT_REPO,
                source_cache_path=None,
            ),
        ],
    )
    git_source = FakeGitSource(
        PreparedIndexSource(
            source="/repos/skills",
            source_type=IndexSourceType.LOCAL_GIT_REPO,
            repository_path="/repos/skills",
        ),
    )
    use_case = UpdateIndex(
        git_source=git_source,
        index_reader=FakeIndexReader(),
        registry=registry,
        cache=FakeCache(),
        clock=lambda: datetime(2026, 7, 8, 19, 0, tzinfo=UTC),
    )

    use_case.execute(UpdateIndexCommand(name="company-skills"))

    assert git_source.refresh_calls == [("/repos/skills", None, None)]
    assert registry.entries["company-skills"].source_cache_path is None


def test_update_index_fails_for_unknown_name() -> None:
    use_case = UpdateIndex(
        git_source=FakeGitSource(),
        index_reader=FakeIndexReader(),
        registry=FakeRegistry(),
        cache=FakeCache(),
        clock=lambda: datetime(2026, 7, 8, 19, 0, tzinfo=UTC),
    )

    with pytest.raises(UnknownIndexNameError, match="is not registered"):
        use_case.execute(UpdateIndexCommand(name="missing-index"))


def test_update_index_keeps_local_alias_when_published_name_changes() -> None:
    registry = FakeRegistry([registered_index(name="local-name")])
    use_case = UpdateIndex(
        git_source=FakeGitSource(),
        index_reader=FakeIndexReader(
            PublishedIndex(
                published_name="renamed-upstream",
                schema_version=1,
                skill_count=4,
                cacheable_content='{"schema_version":1}\n',
            ),
        ),
        registry=registry,
        cache=FakeCache(),
        clock=lambda: datetime(2026, 7, 8, 19, 0, tzinfo=UTC),
    )

    result = use_case.execute(UpdateIndexCommand(name="local-name"))

    assert result.name == "local-name"
    assert registry.entries["local-name"].published_name == "renamed-upstream"


def test_update_index_preserves_cache_and_registry_when_validation_fails() -> None:
    existing = registered_index()
    registry = FakeRegistry([existing])
    cache = FakeCache()
    use_case = UpdateIndex(
        git_source=FakeGitSource(),
        index_reader=FailingIndexReader(InvalidPublishedIndexError("invalid index")),
        registry=registry,
        cache=cache,
        clock=lambda: datetime(2026, 7, 8, 19, 0, tzinfo=UTC),
    )

    with pytest.raises(InvalidPublishedIndexError, match="invalid index"):
        use_case.execute(UpdateIndexCommand(name="company-skills"))

    assert cache.write_calls == []
    assert registry.entries["company-skills"] == existing
    assert registry.upsert_calls == []


def test_update_index_requires_name_or_all() -> None:
    with pytest.raises(ValueError, match="requires either a name or all=True"):
        UpdateIndexCommand()


def test_update_index_rejects_name_and_all_together() -> None:
    with pytest.raises(ValueError, match="requires either a name or all=True"):
        UpdateIndexCommand(name="company-skills", all=True)


def test_update_index_all_continues_after_failure() -> None:
    alpha = registered_index(
        name="alpha-skills",
        source="git@example.com:company/alpha-skills.git",
        skill_count=1,
    )
    beta = registered_index(
        name="beta-skills",
        source="git@example.com:company/beta-skills.git",
        skill_count=2,
    )
    gamma = registered_index(
        name="gamma-skills",
        source="git@example.com:company/gamma-skills.git",
        skill_count=3,
    )
    registry = FakeRegistry([gamma, beta, alpha])
    cache = FakeCache()
    git_source = FakeGitSource()
    index_reader = FakeIndexReader(
        published={
            "alpha-skills": PublishedIndex(
                published_name="alpha-skills",
                schema_version=1,
                skill_count=11,
                cacheable_content='{"schema_version":1,"skills":[]}\n',
            ),
            "gamma-skills": PublishedIndex(
                published_name="gamma-skills",
                schema_version=1,
                skill_count=13,
                cacheable_content='{"schema_version":1,"skills":[{}]}\n',
            ),
        },
        failures={"beta-skills": InvalidPublishedIndexError("invalid beta index")},
    )
    use_case = UpdateIndex(
        git_source=git_source,
        index_reader=index_reader,
        registry=registry,
        cache=cache,
        clock=lambda: datetime(2026, 7, 8, 19, 0, tzinfo=UTC),
    )

    result = use_case.execute(UpdateIndexCommand(all=True))

    assert result == UpdateIndexResult(
        name=None,
        skill_count=24,
        updated_indexes=(
            "alpha-skills",
            "gamma-skills",
        ),
        failed_indexes=("beta-skills",),
    )
    assert registry.list_calls == [None]
    assert cache.write_calls == [
        ("alpha-skills", '{"schema_version":1,"skills":[]}\n', None),
        ("gamma-skills", '{"schema_version":1,"skills":[{}]}\n', None),
    ]
    assert registry.entries["beta-skills"] == beta
