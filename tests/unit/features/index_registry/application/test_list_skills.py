import pytest

from ritebook.features.index_registry.application.dtos import (
    CachedSkillSummary,
    ListedIndexSkills,
    ListSkillsCommand,
    ListSkillsResult,
)
from ritebook.features.index_registry.application.errors import UnknownIndexNameError
from ritebook.features.index_registry.application.use_cases import ListSkills

from .fakes import FakeCachedIndexReader, FakeRegistry, registered_index


def test_list_skills_lists_all_registered_indexes_in_deterministic_order() -> None:
    alpha = registered_index(
        name="alpha-skills",
        cached_index_path="/cache/indexes/alpha-skills/ritebook-index.json",
    )
    beta = registered_index(
        name="beta-skills",
        cached_index_path="/cache/indexes/beta-skills/ritebook-index.json",
    )
    cached_reader = FakeCachedIndexReader(
        {
            beta.cached_index_path: (_skill("beta-helper"),),
            alpha.cached_index_path: (_skill("alpha-helper"),),
        },
    )
    use_case = ListSkills(
        registry=FakeRegistry([beta, alpha]),
        cached_index_reader=cached_reader,
    )

    result = use_case.execute(ListSkillsCommand(registry_path="/tmp/indexes.json"))

    assert result == ListSkillsResult(
        indexes=(
            ListedIndexSkills(
                index_name="alpha-skills",
                skills=(_skill("alpha-helper"),),
            ),
            ListedIndexSkills(
                index_name="beta-skills",
                skills=(_skill("beta-helper"),),
            ),
        ),
    )
    assert cached_reader.read_paths == [
        "/cache/indexes/alpha-skills/ritebook-index.json",
        "/cache/indexes/beta-skills/ritebook-index.json",
    ]


def test_list_skills_filters_by_effective_index_name() -> None:
    alpha = registered_index(
        name="alpha-skills",
        cached_index_path="/cache/indexes/alpha-skills/ritebook-index.json",
    )
    beta = registered_index(
        name="beta-skills",
        cached_index_path="/cache/indexes/beta-skills/ritebook-index.json",
    )
    registry = FakeRegistry([alpha, beta])
    cached_reader = FakeCachedIndexReader(
        {
            beta.cached_index_path: (_skill("beta-helper"),),
        },
    )
    use_case = ListSkills(registry=registry, cached_index_reader=cached_reader)

    result = use_case.execute(
        ListSkillsCommand(index_name="beta-skills", registry_path="/tmp/indexes.json"),
    )

    assert result == ListSkillsResult(
        indexes=(
            ListedIndexSkills(
                index_name="beta-skills",
                skills=(_skill("beta-helper"),),
            ),
        ),
    )
    assert registry.get_calls == [("beta-skills", "/tmp/indexes.json")]
    assert registry.list_calls == []
    assert cached_reader.read_paths == [beta.cached_index_path]


def test_list_skills_fails_for_unknown_index_name() -> None:
    cached_reader = FakeCachedIndexReader()
    use_case = ListSkills(
        registry=FakeRegistry(),
        cached_index_reader=cached_reader,
    )

    with pytest.raises(UnknownIndexNameError, match="is not registered"):
        use_case.execute(ListSkillsCommand(index_name="missing-index"))

    assert cached_reader.read_paths == []


def test_list_skills_sorts_skills_by_name_within_each_index() -> None:
    entry = registered_index()
    use_case = ListSkills(
        registry=FakeRegistry([entry]),
        cached_index_reader=FakeCachedIndexReader(
            {
                entry.cached_index_path: (
                    _skill("zebra-helper"),
                    _skill("alpha-helper"),
                ),
            },
        ),
    )

    result = use_case.execute(ListSkillsCommand())

    assert result.indexes[0].skills == (
        _skill("alpha-helper"),
        _skill("zebra-helper"),
    )


def test_list_skills_sorts_nested_skills_by_path_within_each_index() -> None:
    entry = registered_index()
    nested = _skill(
        "runtime-verification",
        path="browser/runtime-verification",
    )
    root = _skill("alpha-helper")
    use_case = ListSkills(
        registry=FakeRegistry([entry]),
        cached_index_reader=FakeCachedIndexReader(
            {
                entry.cached_index_path: (nested, root),
            },
        ),
    )

    result = use_case.execute(ListSkillsCommand())

    assert result.indexes[0].skills == (nested, root)


def test_list_skills_preserves_duplicate_names_at_distinct_paths() -> None:
    entry = registered_index()
    backend = _skill("code-review", path="backend/code-review")
    frontend = _skill("code-review", path="frontend/code-review")
    use_case = ListSkills(
        registry=FakeRegistry([entry]),
        cached_index_reader=FakeCachedIndexReader(
            {entry.cached_index_path: (frontend, backend)},
        ),
    )

    result = use_case.execute(ListSkillsCommand())

    assert result.indexes[0].skills == (backend, frontend)


def test_list_skills_returns_empty_result_for_empty_registry() -> None:
    cached_reader = FakeCachedIndexReader()
    use_case = ListSkills(
        registry=FakeRegistry(),
        cached_index_reader=cached_reader,
    )

    result = use_case.execute(ListSkillsCommand())

    assert result == ListSkillsResult(indexes=())
    assert cached_reader.read_paths == []


def test_list_skills_preserves_selected_index_group_when_no_skills_exist() -> None:
    entry = registered_index()
    use_case = ListSkills(
        registry=FakeRegistry([entry]),
        cached_index_reader=FakeCachedIndexReader(),
    )

    result = use_case.execute(ListSkillsCommand(index_name="company-skills"))

    assert result == ListSkillsResult(
        indexes=(ListedIndexSkills(index_name="company-skills", skills=()),),
    )


def _skill(name: str, *, path: str | None = None) -> CachedSkillSummary:
    skill_path = path or f"skills/{name}"
    return CachedSkillSummary(
        name=name,
        path=skill_path,
        skill_file=f"{skill_path}/SKILL.md",
        description=f"Helps with {name} workflows.",
    )
