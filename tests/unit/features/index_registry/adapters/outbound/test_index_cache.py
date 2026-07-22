import hashlib
import os
from pathlib import Path

import pytest

from ritebook.features.index_registry.adapters.outbound.index_cache import (
    FilesystemIndexCache,
)
from ritebook.features.index_registry.application.errors import IndexCacheError


def test_index_cache_writes_content_addressed_generation(tmp_path: Path) -> None:
    cache = FilesystemIndexCache()
    content = '{"schema_version":1}\n'
    digest = _digest(content)

    path = cache.write_index(
        name="company-skills",
        content=content,
        index_digest=digest,
        cache_root=str(tmp_path),
        preserve_path=None,
    )

    expected = (
        tmp_path
        / "indexes"
        / "company-skills"
        / digest.removeprefix("sha256:")
        / "ritebook-index.json"
    )
    assert path == str(expected)
    assert expected.read_text(encoding="utf-8") == content


def test_index_cache_preserves_current_generation_while_staging_next(
    tmp_path: Path,
) -> None:
    cache = FilesystemIndexCache()
    old_content = "old"
    old_path = cache.write_index(
        name="company-skills",
        content=old_content,
        index_digest=_digest(old_content),
        cache_root=str(tmp_path),
        preserve_path=None,
    )

    new_content = "new"
    new_path = cache.write_index(
        name="company-skills",
        content=new_content,
        index_digest=_digest(new_content),
        cache_root=str(tmp_path),
        preserve_path=old_path,
    )

    assert Path(old_path).read_text(encoding="utf-8") == old_content
    assert Path(new_path).read_text(encoding="utf-8") == new_content


def test_index_cache_rejects_content_that_does_not_match_digest(tmp_path: Path) -> None:
    cache = FilesystemIndexCache()

    with pytest.raises(IndexCacheError, match="does not match"):
        cache.write_index(
            name="company-skills",
            content="candidate",
            index_digest=_digest("different"),
            cache_root=str(tmp_path),
            preserve_path=None,
        )

    assert not (tmp_path / "indexes").exists()


def test_index_cache_sync_failure_leaves_no_visible_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = FilesystemIndexCache()
    content = "candidate"

    def fail_sync(_descriptor: int) -> None:
        message = "injected cache sync failure"
        raise OSError(message)

    monkeypatch.setattr(os, "fsync", fail_sync)

    with pytest.raises(IndexCacheError, match="unable to write"):
        cache.write_index(
            name="company-skills",
            content=content,
            index_digest=_digest(content),
            cache_root=str(tmp_path),
            preserve_path=None,
        )

    alias_root = tmp_path / "indexes" / "company-skills"
    assert list(alias_root.rglob("*")) == []


def test_index_cache_recovers_abandoned_generation_before_next_write(
    tmp_path: Path,
) -> None:
    cache = FilesystemIndexCache()
    current_content = "current"
    current_path = cache.write_index(
        name="company-skills",
        content=current_content,
        index_digest=_digest(current_content),
        cache_root=str(tmp_path),
        preserve_path=None,
    )
    orphan_directory = tmp_path / "indexes" / "company-skills" / ("f" * 64)
    orphan_directory.mkdir()
    (orphan_directory / "ritebook-index.json").write_text("orphan", encoding="utf-8")
    current_directory = Path(current_path).parent
    abandoned_temporary = current_directory / ".ritebook-index.json.abandoned.tmp"
    abandoned_temporary.write_text("partial", encoding="utf-8")

    cache.write_index(
        name="company-skills",
        content=current_content,
        index_digest=_digest(current_content),
        cache_root=str(tmp_path),
        preserve_path=current_path,
    )

    assert Path(current_path).exists()
    assert not abandoned_temporary.exists()
    assert not orphan_directory.exists()


def test_index_cache_discards_only_owned_generation(tmp_path: Path) -> None:
    cache = FilesystemIndexCache()
    content = "candidate"
    path = cache.write_index(
        name="company-skills",
        content=content,
        index_digest=_digest(content),
        cache_root=str(tmp_path),
        preserve_path=None,
    )

    cache.discard_index(
        name="company-skills",
        cached_index_path=path,
        cache_root=str(tmp_path),
    )

    assert not Path(path).exists()


def _digest(content: str) -> str:
    return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"
