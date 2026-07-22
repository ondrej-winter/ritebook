import json
from pathlib import Path

import pytest

from ritebook.features.index_registry.adapters.outbound.filesystem_registry import (
    FilesystemIndexRegistry,
)
from ritebook.features.index_registry.application.dtos import (
    IndexSourceType,
    RegisteredIndex,
)
from ritebook.features.index_registry.application.errors import (
    IndexRegistryPersistenceError,
)

SOURCE_REVISION = "a" * 40
INDEX_DIGEST = f"sha256:{'b' * 64}"


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
    assert payload["indexes"][0]["source_revision"] == SOURCE_REVISION
    assert payload["indexes"][0]["index_digest"] == INDEX_DIGEST


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


def test_filesystem_registry_recovers_abandoned_temporary_file(tmp_path: Path) -> None:
    path = tmp_path / "indexes.json"
    abandoned = tmp_path / ".indexes.json.abandoned.tmp"
    abandoned.write_text("partial", encoding="utf-8")

    FilesystemIndexRegistry().upsert(entry(), str(path))

    assert path.is_file()
    assert not abandoned.exists()


def test_filesystem_registry_replace_failure_preserves_previous_registry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "indexes.json"
    registry = FilesystemIndexRegistry()
    registry.upsert(entry(skill_count=1), str(path))
    previous_content = path.read_text(encoding="utf-8")

    def fail_replace(_source: Path, _destination: Path) -> None:
        message = "injected registry replace failure"
        raise OSError(message)

    monkeypatch.setattr(Path, "replace", fail_replace)

    with pytest.raises(IndexRegistryPersistenceError, match="unable to write"):
        registry.upsert(entry(skill_count=2), str(path))

    assert path.read_text(encoding="utf-8") == previous_content
    assert list(tmp_path.glob(".indexes.json.*.tmp")) == []


@pytest.mark.parametrize("missing_field", ["source_revision", "index_digest"])
def test_filesystem_registry_rejects_legacy_entries_without_provenance(
    tmp_path: Path,
    missing_field: str,
) -> None:
    path = tmp_path / "indexes.json"
    registry = FilesystemIndexRegistry()
    registry.upsert(entry(), str(path))
    payload = json.loads(path.read_text(encoding="utf-8"))
    del payload["indexes"][0][missing_field]
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        IndexRegistryPersistenceError,
        match="regenerate it with add-index",
    ):
        registry.get("company-skills", str(path))


def entry(*, name: str = "company-skills", skill_count: int = 1) -> RegisteredIndex:
    return RegisteredIndex(
        name=name,
        published_name="company-skills",
        source="git@example.com:company/skills.git",
        source_type=IndexSourceType.GIT_URL,
        source_revision=SOURCE_REVISION,
        index_digest=INDEX_DIGEST,
        source_cache_path="/cache/git/source-id",
        cached_index_path=f"/cache/indexes/{name}/ritebook-index.json",
        source_schema_version=1,
        skill_count=skill_count,
        added_at="2026-07-08T18:00:00Z",
        updated_at="2026-07-08T18:00:00Z",
    )
