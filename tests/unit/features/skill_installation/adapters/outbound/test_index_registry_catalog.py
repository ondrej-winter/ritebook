from ritebook.features.index_registry.application.dtos import (
    CachedSkillSummary,
    IndexSourceType,
    RegisteredIndex,
)
from ritebook.features.skill_installation.adapters.outbound import (
    IndexRegistrySkillCatalogAdapter,
)
from ritebook.features.skill_installation.application.dtos import (
    InstallableSkill,
    RegisteredSkillIndex,
)


class FakeIndexRegistry:
    def __init__(self, entry: RegisteredIndex | None) -> None:
        self.entry = entry
        self.get_calls: list[tuple[str, str | None]] = []

    def get(self, name: str, registry_path: str | None) -> RegisteredIndex | None:
        self.get_calls.append((name, registry_path))
        return self.entry


class FakeCachedIndexReader:
    def __init__(self, skills: tuple[CachedSkillSummary, ...] = ()) -> None:
        self.skills = skills
        self.read_skills_calls: list[str] = []

    def read_skills(self, cached_index_path: str) -> tuple[CachedSkillSummary, ...]:
        self.read_skills_calls.append(cached_index_path)
        return self.skills


def test_index_registry_catalog_maps_registered_index_to_installation_dto() -> None:
    registry = FakeIndexRegistry(
        registered_index(
            name="platform-skills",
            source_type=IndexSourceType.GIT_URL,
            source_cache_path="/cache/git/platform-skills",
        ),
    )

    result = IndexRegistrySkillCatalogAdapter(
        registry=registry,
        index_reader=FakeCachedIndexReader(),
    ).get_index("platform-skills", "/tmp/indexes.json")

    assert result == RegisteredSkillIndex(
        name="platform-skills",
        source="git@example.com:company/skills.git",
        source_type="git_url",
        source_cache_path="/cache/git/platform-skills",
        cached_index_path="/cache/indexes/platform-skills/ritebook-index.json",
        index_schema_version=1,
    )
    assert registry.get_calls == [("platform-skills", "/tmp/indexes.json")]


def test_index_registry_catalog_returns_none_for_missing_index() -> None:
    registry = FakeIndexRegistry(None)

    result = IndexRegistrySkillCatalogAdapter(
        registry=registry,
        index_reader=FakeCachedIndexReader(),
    ).get_index("missing-skills", None)

    assert result is None
    assert registry.get_calls == [("missing-skills", None)]


def test_index_registry_catalog_maps_cached_skills_to_installation_dtos() -> None:
    index_reader = FakeCachedIndexReader(
        (
            CachedSkillSummary(
                name="code-review",
                path="skills/code-review",
                skill_file="skills/code-review/SKILL.md",
                description="Ignored by installation.",
            ),
            CachedSkillSummary(
                name="test-writer",
                path="skills/test-writer",
                skill_file="skills/test-writer/SKILL.md",
            ),
        ),
    )

    result = IndexRegistrySkillCatalogAdapter(
        registry=FakeIndexRegistry(None),
        index_reader=index_reader,
    ).read_skills("/cache/indexes/platform-skills/ritebook-index.json")

    assert result == (
        InstallableSkill(
            name="code-review",
            path="skills/code-review",
            skill_file="skills/code-review/SKILL.md",
        ),
        InstallableSkill(
            name="test-writer",
            path="skills/test-writer",
            skill_file="skills/test-writer/SKILL.md",
        ),
    )
    assert index_reader.read_skills_calls == [
        "/cache/indexes/platform-skills/ritebook-index.json",
    ]


def registered_index(
    *,
    name: str = "company-skills",
    source: str = "git@example.com:company/skills.git",
    source_type: IndexSourceType = IndexSourceType.GIT_URL,
    source_cache_path: str | None = "/cache/git/company-skills",
) -> RegisteredIndex:
    return RegisteredIndex(
        name=name,
        published_name=name,
        source=source,
        source_type=source_type,
        source_cache_path=source_cache_path,
        cached_index_path=f"/cache/indexes/{name}/ritebook-index.json",
        source_schema_version=1,
        skill_count=2,
        added_at="2026-07-10T21:00:00Z",
        updated_at="2026-07-10T21:00:00Z",
    )
