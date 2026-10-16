from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from ritebook.cli import main
from ritebook.features.index_registry.adapters.outbound.filesystem_registry import (
    FilesystemIndexRegistry,
)

if TYPE_CHECKING:
    from tests.integration.conftest import GitRepositoryFactory


@pytest.mark.parametrize("git_url", [True, False])
@pytest.mark.parametrize("all_indexes", [True, False])
def test_force_update_recovers_legacy_source_without_trusting_old_metadata(
    tmp_path: Path,
    git_repository: GitRepositoryFactory,
    *,
    git_url: bool,
    all_indexes: bool,
) -> None:
    repository = git_repository(tmp_path / "upstream")
    content = _published_index()
    (repository.path / "ritebook-index.json").write_bytes(content)
    revision = repository.commit_all("Publish index")
    legacy_cache = tmp_path / "legacy-cache"
    legacy_cache.write_bytes(b"untrusted old cache")
    registry_path = tmp_path / "indexes.json"
    source = repository.path.as_uri() if git_url else str(repository.path)
    _write_legacy_registry(registry_path, [_legacy_entry("local-alias", source, legacy_cache, git_url=git_url)])
    arguments = _update_arguments(registry_path, tmp_path / "cache")
    arguments += ["--all"] if all_indexes else ["local-alias"]

    assert main(arguments) == 0

    recovered = FilesystemIndexRegistry().get("local-alias", str(registry_path))
    assert recovered is not None
    assert recovered.source == source
    assert recovered.source_revision == revision
    assert recovered.source_branch.startswith("refs/heads/")
    assert recovered.index_digest == f"sha256:{hashlib.sha256(content).hexdigest()}"
    assert Path(recovered.cached_index_path).read_bytes() == content
    assert recovered.published_name == "published-skills"
    assert json.loads(registry_path.read_bytes())["schema_version"] == 2
    assert legacy_cache.read_bytes() == b"untrusted old cache"


def test_force_update_all_preserves_failed_legacy_entry_and_can_retry(
    tmp_path: Path,
    git_repository: GitRepositoryFactory,
    capsys: pytest.CaptureFixture[str],
) -> None:
    repository = git_repository(tmp_path / "upstream")
    (repository.path / "ritebook-index.json").write_bytes(_published_index())
    repository.commit_all("Publish index")
    broken = git_repository(tmp_path / "broken")
    (broken.path / "ritebook-index.json").write_bytes(b"invalid JSON")
    broken.commit_all("Publish broken index")
    registry_path = tmp_path / "indexes.json"
    failed_entry = _legacy_entry("alpha", broken.path.as_uri(), tmp_path / "old-alpha", git_url=True)
    _write_legacy_registry(
        registry_path,
        [failed_entry, _legacy_entry("zeta", repository.path.as_uri(), tmp_path / "old-zeta", git_url=True)],
    )
    arguments = [*_update_arguments(registry_path, tmp_path / "cache"), "--all"]

    assert main(arguments) == 1
    output = capsys.readouterr()
    assert "Updated 1 index(es)" in output.out
    assert "Failed to update 1 index(es): alpha" in output.err
    partial = json.loads(registry_path.read_bytes())
    assert partial["schema_version"] == 1
    assert partial["indexes"][0] == failed_entry
    assert partial["indexes"][1]["source_branch"].startswith("refs/heads/")

    (broken.path / "ritebook-index.json").write_bytes(_published_index())
    broken.commit_all("Repair published index")

    assert main(arguments) == 0
    assert [entry.name for entry in FilesystemIndexRegistry().list(str(registry_path))] == ["alpha", "zeta"]


def test_force_update_all_converts_empty_legacy_registry(tmp_path: Path) -> None:
    registry_path = tmp_path / "indexes.json"
    _write_legacy_registry(registry_path, [])

    assert main([*_update_arguments(registry_path, tmp_path / "cache"), "--all"]) == 0
    assert json.loads(registry_path.read_bytes())["schema_version"] == 2


def _published_index() -> bytes:
    return json.dumps(
        {
            "schema_version": 1,
            "index": {"name": "published-skills"},
            "generated_at": "2026-10-16T00:00:00Z",
            "skills_root": ".",
            "skills": [],
        }
    ).encode()


def _legacy_entry(name: str, source: str, legacy_cache: Path, *, git_url: bool) -> dict[str, object]:
    return {
        "name": name,
        "source": source,
        "source_type": "git_url" if git_url else "local_git_repo",
        "cached_index_path": str(legacy_cache),
        "source_cache_path": str(legacy_cache) if git_url else None,
    }


def _write_legacy_registry(path: Path, entries: list[dict[str, object]]) -> None:
    path.write_text(json.dumps({"schema_version": 1, "indexes": entries}), encoding="utf-8")


def _update_arguments(registry_path: Path, cache_root: Path) -> list[str]:
    return ["indexes", "update", "--force", "--registry-path", str(registry_path), "--cache-root", str(cache_root)]
