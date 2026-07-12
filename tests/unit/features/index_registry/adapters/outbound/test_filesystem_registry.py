import json
from pathlib import Path

from ritebook.features.index_registry.adapters.outbound.filesystem_registry import (
    FilesystemIndexRegistry,
)
from ritebook.features.index_registry.application.dtos import (
    IndexSourceType,
    RegisteredIndex,
)


def test_filesystem_registry_reads_missing_registry_as_empty(tmp_path: Path) -> None:
    registry = FilesystemIndexRegistry()

    assert registry.get("company-skills", str(tmp_path / "indexes.json")) is None


def test_filesystem_registry_writes_deterministic_entries(tmp_path: Path) -> None:
    path = tmp_path / "indexes.json"
    registry = FilesystemIndexRegistry()

    registry.upsert(entry(name="zeta-skills"), str(path))
    registry.upsert(entry(name="alpha-skills"), str(path))

    payload = json.loads(path.read_text(encoding="utf-8"))
    assert [item["name"] for item in payload["indexes"]] == [
        "alpha-skills",
        "zeta-skills",
    ]
    assert registry.get("alpha-skills", str(path)) == entry(name="alpha-skills")


def test_filesystem_registry_lists_entries_in_deterministic_order(
    tmp_path: Path,
) -> None:
    path = tmp_path / "indexes.json"
    registry = FilesystemIndexRegistry()

    registry.upsert(entry(name="zeta-skills"), str(path))
    registry.upsert(entry(name="alpha-skills"), str(path))

    assert registry.list(str(path)) == (
        entry(name="alpha-skills"),
        entry(name="zeta-skills"),
    )


def test_filesystem_registry_preserves_unrelated_entries(tmp_path: Path) -> None:
    path = tmp_path / "indexes.json"
    registry = FilesystemIndexRegistry()

    registry.upsert(entry(name="alpha-skills", skill_count=1), str(path))
    registry.upsert(entry(name="zeta-skills", skill_count=2), str(path))

    alpha_entry = registry.get("alpha-skills", str(path))
    zeta_entry = registry.get("zeta-skills", str(path))

    assert alpha_entry is not None
    assert zeta_entry is not None
    assert alpha_entry.skill_count == 1
    assert zeta_entry.skill_count == 2


def entry(*, name: str = "company-skills", skill_count: int = 1) -> RegisteredIndex:
    return RegisteredIndex(
        name=name,
        published_name="company-skills",
        source="git@example.com:company/skills.git",
        source_type=IndexSourceType.GIT_URL,
        source_cache_path="/cache/git/source-id",
        cached_index_path=f"/cache/indexes/{name}/ritebook-index.json",
        source_schema_version=1,
        skill_count=skill_count,
        added_at="2026-07-08T18:00:00Z",
        updated_at="2026-07-08T18:00:00Z",
    )
